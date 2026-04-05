"""
QBR (Quarterly Business Review) Transcript Intelligence Routes
Standalone module for QBR session management - upload, analysis, and review
"""

from flask import Blueprint, request, render_template, redirect, url_for, session, flash, jsonify, g
from business_auth_routes import require_business_auth, get_current_business_user
from audit_utils import queue_audit_log
from app import db, cache
import logging
import hashlib
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

qbr_bp = Blueprint('qbr', __name__, url_prefix='/qbr')
qbr_api_bp = Blueprint('qbr_api', __name__, url_prefix='/api/qbr')

MAX_TRANSCRIPT_SIZE_BYTES = 500 * 1024  # 500 KB


def _get_business_account_id():
    current_user = get_current_business_user()
    if current_user and hasattr(current_user, 'business_account_id') and current_user.business_account_id:
        return current_user.business_account_id
    return session.get('business_account_id')


def _get_task_queue():
    return getattr(g, 'task_queue', None)


def _get_distinct_company_names(business_account_id):
    """Get distinct client company names for this business account.

    Sources (merged, deduped, sorted):
      1. Participant.company_name — the authoritative client company roster for the account
      2. QBRSession.company_name — any company that already has a QBR session (in case it
         was entered on first upload before participants existed)
    Cached 60 s to avoid repeated table scans.
    """
    cache_key = f"qbr_companies_{business_account_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    from models import QBRSession, Participant
    from sqlalchemy import distinct as sql_distinct

    participant_companies = {
        row[0] for row in
        db.session.query(sql_distinct(Participant.company_name))
        .filter(
            Participant.business_account_id == business_account_id,
            Participant.company_name.isnot(None),
            Participant.company_name != ''
        )
        .all()
    }

    qbr_companies = {
        row[0] for row in
        db.session.query(sql_distinct(QBRSession.company_name))
        .filter_by(business_account_id=business_account_id)
        .all()
    }

    companies = sorted(participant_companies | qbr_companies)
    # NOTE: SimpleCache is in-process only — this cache.set is not visible to other
    # gunicorn workers. Each worker maintains its own independent in-memory cache.
    cache.set(cache_key, companies, timeout=60)
    return companies


@qbr_bp.route('/')
@require_business_auth
def qbr_dashboard():
    """QBR dashboard — paginated list of all QBR sessions for this business account"""
    try:
        business_account_id = _get_business_account_id()
        current_user = get_current_business_user()

        from models import QBRSession
        from sqlalchemy import desc

        page = request.args.get('page', 1, type=int)
        per_page = 20

        company_filter = request.args.get('company', '').strip()
        quarter_filter = request.args.get('quarter', '', type=str).strip()

        query = QBRSession.query.filter_by(business_account_id=business_account_id)

        if company_filter:
            query = query.filter(QBRSession.company_name.ilike(f'%{company_filter}%'))

        if quarter_filter and quarter_filter.isdigit():
            query = query.filter(QBRSession.quarter == int(quarter_filter))

        query = query.order_by(desc(QBRSession.created_at))
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        companies = _get_distinct_company_names(business_account_id)

        return render_template(
            'qbr/qbr_dashboard.html',
            sessions=pagination.items,
            pagination=pagination,
            companies=companies,
            company_filter=company_filter,
            quarter_filter=quarter_filter,
            current_user=current_user,
        )

    except Exception as e:
        logger.error(f"QBR dashboard error: {e}")
        flash('Failed to load QBR dashboard.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@qbr_bp.route('/upload', methods=['GET', 'POST'])
@require_business_auth
def qbr_upload():
    """Upload page for a new QBR transcript"""
    business_account_id = _get_business_account_id()
    current_user = get_current_business_user()

    if request.method == 'GET':
        companies = _get_distinct_company_names(business_account_id)
        current_year = datetime.utcnow().year
        return render_template(
            'qbr/qbr_upload.html',
            companies=companies,
            current_year=current_year,
            current_user=current_user,
        )

    # POST: process upload
    try:
        company_name = request.form.get('company_name', '').strip()
        quarter_str = request.form.get('quarter', '').strip()
        year_str = request.form.get('year', '').strip()
        transcript_file = request.files.get('transcript_file')

        companies = _get_distinct_company_names(business_account_id)

        # Validate required fields
        errors = []
        if not company_name:
            errors.append('Company name is required.')
        elif company_name not in companies:
            errors.append(
                f'"{company_name}" is not a recognised client company for this account. '
                'Please select a company from the autocomplete list.'
            )
        if not quarter_str or not quarter_str.isdigit() or int(quarter_str) not in range(1, 5):
            errors.append('Quarter must be Q1, Q2, Q3, or Q4.')
        if not year_str or not year_str.isdigit():
            errors.append('Year is required.')
        if not transcript_file or transcript_file.filename == '':
            errors.append('A transcript file is required.')
        elif not transcript_file.filename.lower().endswith('.txt'):
            errors.append('Only .txt transcript files are accepted.')

        if errors:
            for err in errors:
                flash(err, 'error')
            return render_template(
                'qbr/qbr_upload.html',
                companies=companies,
                current_year=datetime.utcnow().year,
                current_user=current_user,
            )

        quarter = int(quarter_str)
        year = int(year_str)
        transcript_filename = transcript_file.filename

        # Read and validate file size
        transcript_bytes = transcript_file.read()
        if len(transcript_bytes) > MAX_TRANSCRIPT_SIZE_BYTES:
            flash('Transcript file is too large. Maximum size is 500 KB.', 'error')
            return render_template(
                'qbr/qbr_upload.html',
                companies=companies,
                current_year=datetime.utcnow().year,
                current_user=current_user,
            )

        transcript_content = transcript_bytes.decode('utf-8', errors='replace')
        transcript_hash = hashlib.sha256(transcript_bytes).hexdigest()

        from models import QBRSession

        # Check for duplicate within this business account
        existing = QBRSession.query.filter_by(
            business_account_id=business_account_id,
            transcript_hash=transcript_hash
        ).first()

        if existing:
            flash(
                f'This transcript has already been uploaded (session for {existing.company_name} '
                f'Q{existing.quarter} {existing.year}). Duplicate transcripts are not allowed.',
                'error'
            )
            return render_template(
                'qbr/qbr_upload.html',
                companies=companies,
                current_year=datetime.utcnow().year,
                current_user=current_user,
            )

        # Create QBR session
        user_id = session.get('business_user_id')
        qbr_session = QBRSession(
            business_account_id=business_account_id,
            company_name=company_name,
            quarter=quarter,
            year=year,
            transcript_content=transcript_content,
            transcript_hash=transcript_hash,
            transcript_filename=transcript_filename,
            uploaded_by_user_id=user_id,
            status='pending',
        )
        db.session.add(qbr_session)
        db.session.commit()

        # Enqueue analysis task
        task_queue = _get_task_queue()
        if task_queue:
            task_queue.add_task(
                task_type='qbr_analysis',
                task_data={
                    'session_id': qbr_session.id,
                    'business_account_id': business_account_id,
                    'uploaded_by_user_id': user_id,
                    'company_name': company_name,
                }
            )
        else:
            logger.warning("Task queue not available for QBR analysis")

        # Audit log
        queue_audit_log(
            business_account_id=business_account_id,
            action_type='qbr_transcript_uploaded',
            resource_type='qbr_session',
            resource_id=str(qbr_session.id),
            resource_name=company_name,
            details={
                'quarter': quarter,
                'year': year,
                'transcript_filename': transcript_filename,
                'session_uuid': qbr_session.uuid,
            }
        )

        # Invalidate company name cache.
        # NOTE: SimpleCache invalidation is in-process only; other gunicorn workers will not see this delete.
        cache.delete(f"qbr_companies_{business_account_id}")

        flash(
            f'QBR transcript for {company_name} Q{quarter} {year} uploaded successfully. '
            'Analysis is running in the background.',
            'success'
        )
        return redirect(url_for('qbr.qbr_dashboard'))

    except Exception as e:
        logger.error(f"QBR upload error: {e}")
        db.session.rollback()
        flash('Failed to upload QBR transcript. Please try again.', 'error')
        companies = _get_distinct_company_names(business_account_id)
        return render_template(
            'qbr/qbr_upload.html',
            companies=companies,
            current_year=datetime.utcnow().year,
            current_user=current_user,
        )


@qbr_bp.route('/sessions/<session_uuid>')
@require_business_auth
def qbr_session_detail(session_uuid):
    """Detail page for a single QBR session"""
    try:
        business_account_id = _get_business_account_id()
        current_user = get_current_business_user()

        from models import QBRSession
        qbr_session = QBRSession.query.filter_by(
            uuid=session_uuid,
            business_account_id=business_account_id
        ).first_or_404()

        return render_template(
            'qbr/qbr_session_detail.html',
            qbr_session=qbr_session,
            current_user=current_user,
        )

    except Exception as e:
        logger.error(f"QBR session detail error: {e}")
        flash('QBR session not found.', 'error')
        return redirect(url_for('qbr.qbr_dashboard'))


@qbr_bp.route('/company/<path:company_name>')
@require_business_auth
def qbr_company_history(company_name):
    """All QBR sessions for a specific company"""
    try:
        business_account_id = _get_business_account_id()
        current_user = get_current_business_user()

        from models import QBRSession
        from sqlalchemy import desc
        sessions = QBRSession.query.filter_by(
            business_account_id=business_account_id,
            company_name=company_name
        ).order_by(
            desc(QBRSession.year),
            desc(QBRSession.quarter)
        ).all()

        return render_template(
            'qbr/qbr_company_history.html',
            sessions=sessions,
            company_name=company_name,
            current_user=current_user,
        )

    except Exception as e:
        logger.error(f"QBR company history error: {e}")
        flash('Failed to load company QBR history.', 'error')
        return redirect(url_for('qbr.qbr_dashboard'))


@qbr_api_bp.route('/sessions/<session_uuid>', methods=['DELETE'])
@require_business_auth
def qbr_session_delete(session_uuid):
    """Delete a QBR session — restricted to uploader or admin. Endpoint: DELETE /api/qbr/sessions/<uuid>"""
    try:
        business_account_id = _get_business_account_id()
        current_user = get_current_business_user()

        from models import QBRSession
        qbr_session = QBRSession.query.filter_by(
            uuid=session_uuid,
            business_account_id=business_account_id
        ).first()

        if not qbr_session:
            return jsonify({'error': 'Session not found'}), 404

        user_id = session.get('business_user_id')
        is_uploader = (qbr_session.uploaded_by_user_id == user_id)
        is_admin = current_user and current_user.role in ['admin', 'business_account_admin', 'platform_admin']

        if not (is_uploader or is_admin):
            return jsonify({'error': 'Permission denied. Only the uploader or an admin can delete this session.'}), 403

        company_name = qbr_session.company_name
        quarter = qbr_session.quarter
        year = qbr_session.year

        db.session.delete(qbr_session)
        db.session.commit()

        # Audit log
        queue_audit_log(
            business_account_id=business_account_id,
            action_type='qbr_session_deleted',
            resource_type='qbr_session',
            resource_id=session_uuid,
            resource_name=company_name,
            details={'quarter': quarter, 'year': year, 'deleted_by_user_id': user_id}
        )

        # Invalidate company name cache.
        # NOTE: SimpleCache invalidation is in-process only; other gunicorn workers will not see this delete.
        cache.delete(f"qbr_companies_{business_account_id}")

        return jsonify({'success': True, 'message': 'QBR session deleted successfully'}), 200

    except Exception as e:
        logger.error(f"QBR delete error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete QBR session'}), 500
