"""
Phase 3: Participant Management Routes
Provides CRUD operations for campaign participants with proper tenant scoping
"""

from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, session
from flask_babel import gettext as _
from sqlalchemy.orm import joinedload
from business_auth_routes import require_business_auth, require_permission, current_tenant_id, get_current_business_account
from models import Participant, Campaign, BusinessAccount, CampaignParticipant, EmailDelivery, db
from task_queue import add_email_task
from email_service import email_service
from license_service import LicenseService
from datetime import datetime
import logging
import csv
import io
import json
import uuid
from audit_utils import queue_audit_log

# Create blueprint for participant management
participant_bp = Blueprint('participants', __name__, url_prefix='/business/participants')

logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS - Shared filtering logic
# ============================================================================

def get_filter_options(business_account_id):
    """
    Get all available filter options for participant attributes
    Used to populate filter dropdowns on initial page load
    OPTIMIZED: Single query fetches all filter columns at once, then processes in Python
    """
    # Fetch all distinct filter values in a single query (6 queries -> 1 query)
    results = db.session.query(
        Participant.company_name,
        Participant.role,
        Participant.region,
        Participant.customer_tier,
        Participant.client_industry,
        Participant.language,
        Participant.tenure_years
    ).filter(
        Participant.business_account_id == business_account_id
    ).distinct().all()
    
    # Process results in Python (efficient for typical dataset sizes)
    companies = set()
    roles = set()
    regions = set()
    tiers = set()
    industries = set()
    languages = set()
    tenure_ranges = set()
    
    for row in results:
        if row.company_name:
            companies.add(row.company_name)
        if row.role:
            roles.add(row.role)
        if row.region:
            regions.add(row.region)
        if row.customer_tier:
            tiers.add(row.customer_tier)
        if row.client_industry:
            industries.add(row.client_industry)
        if row.language:
            languages.add(row.language)
        if row.tenure_years is not None:
            tenure_ranges.add(str(row.tenure_years))
    
    return {
        'companies': sorted(list(companies)),
        'roles': sorted(list(roles)),
        'regions': sorted(list(regions)),
        'tiers': sorted(list(tiers)),
        'industries': sorted(list(industries)),
        'languages': sorted(list(languages)),
        'tenure_ranges': sorted(list(tenure_ranges), key=lambda x: float(x) if x.replace('.', '', 1).isdigit() else 0)
    }


def apply_participant_filters(query, filter_companies=None, filter_roles=None, 
                             filter_regions=None, filter_tiers=None, 
                             filter_industries=None, filter_languages=None, 
                             filter_tenure_ranges=None, search_query=None):
    """
    Apply filters to a participant query
    Shared by both list_participants() and api_filter_participants()
    """
    # Apply attribute filters
    if filter_companies:
        query = query.filter(Participant.company_name.in_(filter_companies))
    if filter_roles:
        query = query.filter(Participant.role.in_(filter_roles))
    if filter_regions:
        query = query.filter(Participant.region.in_(filter_regions))
    if filter_tiers:
        query = query.filter(Participant.customer_tier.in_(filter_tiers))
    if filter_industries:
        query = query.filter(Participant.client_industry.in_(filter_industries))
    if filter_languages:
        query = query.filter(Participant.language.in_(filter_languages))
    if filter_tenure_ranges:
        # Convert tenure values to float (handles both "3" and "3.0" formats)
        tenure_values = []
        for t in filter_tenure_ranges:
            try:
                tenure_values.append(float(t))
            except (ValueError, TypeError):
                logger.warning(f"Invalid tenure value in filter: {t}")
        if tenure_values:
            query = query.filter(Participant.tenure_years.in_(tenure_values))
    
    # Apply search filter if provided
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Participant.name.ilike(search_term),
                Participant.email.ilike(search_term),
                Participant.company_name.ilike(search_term)
            )
        )
    
    return query


def calculate_participant_kpi_stats(business_account_id, filter_companies=None, 
                                   filter_roles=None, filter_regions=None, 
                                   filter_tiers=None, filter_industries=None, 
                                   filter_languages=None, filter_tenure_ranges=None, 
                                   search_query=None):
    """
    Calculate KPI stats for participants with optional filters
    Returns dict with total, completed, started, invited, created, active, companies counts
    """
    from sqlalchemy import case, func as sql_func
    
    kpi_query = db.session.query(
        sql_func.count(Participant.id).label('total'),
        sql_func.count(case((Participant.status == 'completed', 1))).label('completed'),
        sql_func.count(case((Participant.status == 'started', 1))).label('started'),
        sql_func.count(case((Participant.status == 'invited', 1))).label('invited'),
        sql_func.count(case((Participant.status == 'created', 1))).label('created'),
        sql_func.count(sql_func.distinct(case(
            ((Participant.company_name.isnot(None)) & (Participant.company_name != ''), Participant.company_name)
        ))).label('companies')
    ).filter(Participant.business_account_id == business_account_id)
    
    # Apply same filters using helper function
    kpi_query = apply_participant_filters(
        kpi_query, 
        filter_companies=filter_companies,
        filter_roles=filter_roles,
        filter_regions=filter_regions,
        filter_tiers=filter_tiers,
        filter_industries=filter_industries,
        filter_languages=filter_languages,
        filter_tenure_ranges=filter_tenure_ranges,
        search_query=search_query
    )
    
    # Execute query
    kpi_result = kpi_query.first()
    
    # Build stats dictionary
    kpi_stats = {
        'total': kpi_result.total,
        'completed': kpi_result.completed,
        'started': kpi_result.started,
        'invited': kpi_result.invited,
        'created': kpi_result.created,
        'companies': kpi_result.companies
    }
    kpi_stats['active'] = kpi_stats['created'] + kpi_stats['invited']
    
    # Calculate participants per company ratio
    if kpi_stats['companies'] > 0:
        ratio = kpi_stats['total'] / kpi_stats['companies']
        kpi_stats['participants_per_company'] = round(float(ratio), 1)
    else:
        kpi_stats['participants_per_company'] = 0.0
    
    return kpi_stats


# ============================================================================
# ROUTES
# ============================================================================

@participant_bp.route('/')
@require_business_auth
@require_permission('manage_participants')
def list_participants():
    """
    Initial page load for participant list
    Provides filter options and unfiltered initial state
    All filtering is handled client-side via AJAX (api_filter_participants endpoint)
    """
    try:
        # Get current business account context
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.login'))
        
        per_page = 20
        
        # Get filter options for dropdowns (all available values)
        filter_options = get_filter_options(current_account.id)
        
        # Get unfiltered KPI stats for initial display
        kpi_stats = calculate_participant_kpi_stats(current_account.id)
        
        # Get first page of unfiltered participants for initial display
        participants = Participant.query.filter_by(
            business_account_id=current_account.id
        ).order_by(Participant.created_at.desc()).limit(per_page).all()
        
        # Calculate initial pagination (unfiltered total)
        total_participants = kpi_stats['total']
        total_pages = (total_participants + per_page - 1) // per_page if total_participants > 0 else 1
        
        # Get campaigns for dropdown (scoped to current business account)
        campaigns = Campaign.query.filter_by(
            business_account_id=current_account.id
        ).order_by(Campaign.name).all()
        
        # Prepare participant data
        participant_data = [p.to_dict() for p in participants]
        
        return render_template('participants/list.html',
                             participants=participant_data,
                             campaigns=[c.to_dict() for c in campaigns],
                             business_account=current_account.to_dict(),
                             search_query='',  # Initial state has no search
                             kpi_stats=kpi_stats,
                             filter_options=filter_options,
                             pagination={
                                 'page': 1,
                                 'per_page': per_page,
                                 'total': total_participants,
                                 'total_pages': total_pages,
                                 'has_prev': False,
                                 'has_next': total_pages > 1,
                                 'prev_page': None,
                                 'next_page': 2 if total_pages > 1 else None
                             })
        
    except Exception as e:
        logger.error(f"Error listing participants: {e}")
        flash('Error loading participants.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@participant_bp.route('/api/filter')
@require_business_auth
@require_permission('manage_participants')
def api_filter_participants():
    """JSON API endpoint for filtered participant data - used by AJAX filtering"""
    try:
        # Get current business account context
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            return jsonify({'error': 'Business account context not found'}), 401
        
        # Get search and pagination parameters
        search_query = request.args.get('search', '').strip() or None
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Get filter parameters
        filter_companies = request.args.getlist('filter_company') or None
        filter_roles = request.args.getlist('filter_role') or None
        filter_regions = request.args.getlist('filter_region') or None
        filter_tiers = request.args.getlist('filter_tier') or None
        filter_industries = request.args.getlist('filter_industry') or None
        filter_languages = request.args.getlist('filter_language') or None
        filter_tenure_ranges = request.args.getlist('filter_tenure') or None
        
        # Build filtered query using helper function
        query = Participant.query.filter_by(business_account_id=current_account.id)
        query = apply_participant_filters(
            query,
            filter_companies=filter_companies,
            filter_roles=filter_roles,
            filter_regions=filter_regions,
            filter_tiers=filter_tiers,
            filter_industries=filter_industries,
            filter_languages=filter_languages,
            filter_tenure_ranges=filter_tenure_ranges,
            search_query=search_query
        )
        
        # Calculate KPI stats with same filters using helper function
        kpi_stats = calculate_participant_kpi_stats(
            current_account.id,
            filter_companies=filter_companies,
            filter_roles=filter_roles,
            filter_regions=filter_regions,
            filter_tiers=filter_tiers,
            filter_industries=filter_industries,
            filter_languages=filter_languages,
            filter_tenure_ranges=filter_tenure_ranges,
            search_query=search_query
        )
        
        total_participants = kpi_stats['total']
        
        # Apply pagination
        participants = query.order_by(Participant.created_at.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        
        # Calculate pagination info
        total_pages = (total_participants + per_page - 1) // per_page if total_participants > 0 else 1
        has_prev = page > 1
        has_next = page < total_pages
        
        # Prepare participant data
        participant_data = [p.to_dict() for p in participants]
        
        return jsonify({
            'success': True,
            'participants': participant_data,
            'kpi_stats': kpi_stats,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_participants,
                'total_pages': total_pages,
                'has_prev': has_prev,
                'has_next': has_next,
                'prev_page': page - 1 if has_prev else None,
                'next_page': page + 1 if has_next else None
            }
        })
        
    except Exception as e:
        logger.error(f"Error filtering participants API: {e}")
        return jsonify({'error': 'Error filtering participants', 'message': str(e)}), 500


@participant_bp.route('/create', methods=['GET', 'POST'])
@require_business_auth
@require_permission('manage_participants')
def create_participant():
    """Create new participant"""
    
    if request.method == 'GET':
        # Show create form
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.login'))
        
        return render_template('participants/create.html',
                             business_account=current_account.to_dict() if current_account else {})
    
    # Handle form submission
    try:
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.login'))
        
        # Note: License limits are enforced per-campaign when participants are assigned to campaigns
        # Standalone participant creation doesn't have global limits
        
        # Extract form data
        email = request.form.get('email', '').strip().lower()
        name = request.form.get('name', '').strip()
        company_name = request.form.get('company_name', '').strip()
        
        # Optional segmentation attributes
        role = request.form.get('role', '').strip() or None
        region = request.form.get('region', '').strip() or None
        customer_tier = request.form.get('customer_tier', '').strip() or None
        language = request.form.get('language', '').strip() or 'en'
        client_industry = request.form.get('client_industry', '').strip() or None
        
        # Validate client_industry if provided
        if client_industry:
            from industry_topic_hints_config import INDUSTRY_TOPIC_HINTS
            valid_industries = list(INDUSTRY_TOPIC_HINTS.keys())
            if client_industry not in valid_industries:
                flash(f'Invalid client industry. Must be one of: {", ".join(valid_industries)}', 'error')
                return redirect(url_for('participants.create_participant'))
        
        # Parse commercial_value (optional, company-level)
        commercial_value = None
        commercial_value_str = request.form.get('company_commercial_value', '').strip()
        if commercial_value_str:
            try:
                commercial_value = float(commercial_value_str)
                if commercial_value < 0:
                    flash('Commercial value must be a positive number.', 'error')
                    return redirect(url_for('participants.create_participant'))
            except ValueError:
                flash('Invalid commercial value. Please enter a valid number.', 'error')
                return redirect(url_for('participants.create_participant'))
        
        # Parse tenure_years (optional)
        tenure_years = None
        tenure_years_str = request.form.get('tenure_years', '').strip()
        if tenure_years_str:
            try:
                tenure_years = float(tenure_years_str)
                if tenure_years < 0:
                    flash('Tenure must be a positive number.', 'error')
                    return redirect(url_for('participants.create_participant'))
            except ValueError:
                flash('Invalid tenure value. Please enter a valid number.', 'error')
                return redirect(url_for('participants.create_participant'))
        
        # Validate required fields
        if not email or not name or not company_name:
            flash('Email, name, and company name are required.', 'error')
            return redirect(url_for('participants.create_participant'))
        
        # Check for duplicate participant (email within business account)
        existing = Participant.query.filter_by(
            business_account_id=current_account.id,
            email=email
        ).first()
        
        if existing:
            flash(f'Participant with email {email} already exists in your account.', 'error')
            return redirect(url_for('participants.create_participant'))
        
        # Create participant with origin tracking and unified token system
        participant = Participant()
        participant.business_account_id = current_account.id
        participant.email = email
        participant.name = name
        participant.company_name = company_name if company_name else None
        participant.role = role
        participant.region = region
        participant.customer_tier = customer_tier
        participant.language = language
        participant.client_industry = client_industry
        participant.company_commercial_value = commercial_value
        participant.tenure_years = tenure_years
        participant.source = 'admin_single'  # Track that this was admin-created via single form
        
        # Generate unified token for seamless UX
        participant.generate_token()
        
        # Set appropriate status for business context
        participant.set_appropriate_status_for_context(is_trial=False)
        
        db.session.add(participant)
        db.session.commit()
        
        # Sync commercial_value to all existing participants from the same company
        if commercial_value is not None and company_name:
            from sqlalchemy import func
            company_key = company_name.upper()
            updated_count = Participant.query.filter(
                func.upper(Participant.company_name) == company_key,
                Participant.business_account_id == current_account.id,
                Participant.id != participant.id  # Exclude the one we just created
            ).update({'company_commercial_value': commercial_value}, synchronize_session=False)
            
            db.session.commit()
            
            if updated_count > 0:
                flash(f'Commercial value synced to {updated_count} existing participant(s) from {company_name}.', 'info')
        
        # Audit logging for participant creation
        try:
            queue_audit_log(
                business_account_id=current_account.id,
                action_type='participant_created',
                resource_type='participant',
                resource_id=participant.id,
                resource_name=participant.name,
                details={
                    'email': participant.email,
                    'company_name': participant.company_name,
                    'source': 'admin_single'
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to log participant creation audit: {audit_error}")
        
        account_name = current_account.name if current_account and hasattr(current_account, 'name') else 'Unknown'
        logger.info(f"Created participant {email} (Business Account: {account_name})")
        flash(f'Participant {name} created successfully. You can now assign them to campaigns.', 'success')
        return redirect(url_for('participants.list_participants'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating participant: {e}")
        flash('Error creating participant.', 'error')
        return redirect(url_for('participants.create_participant'))


@participant_bp.route('/<int:participant_id>/edit', methods=['GET', 'POST'])
@require_business_auth
@require_permission('manage_participants')
def edit_participant(participant_id):
    """Edit existing participant with conditional email locking"""
    
    try:
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get participant (scoped to current business account)
        participant = Participant.query.filter_by(
            id=participant_id,
            business_account_id=current_account.id
        ).first()
        
        if not participant:
            flash('Participant not found.', 'error')
            return redirect(url_for('participants.list_participants'))
        
        # Check if participant has survey history (determines email editability)
        has_history = participant.has_survey_history()
        
        if request.method == 'GET':
            # Show edit form with prefilled values
            return render_template('participants/edit.html',
                                 participant=participant.to_dict(),
                                 has_survey_history=has_history,
                                 business_account=current_account.to_dict() if current_account else {})
        
        # Handle form submission (POST)
        # DEBUG: Log form data
        logger.info(f"Edit participant form data: {dict(request.form)}")
        
        # Extract form data
        email = request.form.get('email', '').strip().lower()
        name = request.form.get('name', '').strip()
        company_name = request.form.get('company_name', '').strip()
        
        # Optional segmentation attributes
        role = request.form.get('role', '').strip() or None
        region = request.form.get('region', '').strip() or None
        customer_tier = request.form.get('customer_tier', '').strip() or None
        language = request.form.get('language', '').strip() or 'en'
        client_industry = request.form.get('client_industry', '').strip() or None
        
        # Validate client_industry if provided
        if client_industry:
            from industry_topic_hints_config import INDUSTRY_TOPIC_HINTS
            valid_industries = list(INDUSTRY_TOPIC_HINTS.keys())
            if client_industry not in valid_industries:
                flash(f'Invalid client industry. Must be one of: {", ".join(valid_industries)}', 'error')
                return redirect(url_for('participants.edit_participant', participant_id=participant_id))
        
        # Parse commercial_value (optional, company-level)
        commercial_value = None
        commercial_value_str = request.form.get('company_commercial_value', '').strip()
        if commercial_value_str:
            try:
                commercial_value = float(commercial_value_str)
                if commercial_value < 0:
                    flash('Commercial value must be a positive number.', 'error')
                    return redirect(url_for('participants.edit_participant', participant_id=participant_id))
            except ValueError:
                flash('Invalid commercial value. Please enter a valid number.', 'error')
                return redirect(url_for('participants.edit_participant', participant_id=participant_id))
        
        # Parse tenure_years (optional)
        tenure_years = None
        tenure_years_str = request.form.get('tenure_years', '').strip()
        if tenure_years_str:
            try:
                tenure_years = float(tenure_years_str)
                if tenure_years < 0:
                    flash('Tenure must be a positive number.', 'error')
                    return redirect(url_for('participants.edit_participant', participant_id=participant_id))
            except ValueError:
                flash('Invalid tenure value. Please enter a valid number.', 'error')
                return redirect(url_for('participants.edit_participant', participant_id=participant_id))
        
        # Validate required fields
        if not email or not name or not company_name:
            flash('Email, name, and company name are required.', 'error')
            return redirect(url_for('participants.edit_participant', participant_id=participant_id))
        
        # CRITICAL: Block email changes if participant has survey history
        if has_history and email != participant.email:
            flash('Email cannot be changed - this participant has survey history (responses, campaigns, or email deliveries).', 'error')
            return redirect(url_for('participants.edit_participant', participant_id=participant_id))
        
        # If email changed and no survey history, check for duplicates
        if email != participant.email:
            existing = Participant.query.filter_by(
                business_account_id=current_account.id,
                email=email
            ).first()
            
            if existing:
                flash(f'Participant with email {email} already exists in your account.', 'error')
                return redirect(url_for('participants.edit_participant', participant_id=participant_id))
        
        # Track changes for audit logging
        changes = {}
        if participant.email != email:
            changes['email'] = {'old': participant.email, 'new': email}
        if participant.name != name:
            changes['name'] = {'old': participant.name, 'new': name}
        if participant.company_name != company_name:
            changes['company_name'] = {'old': participant.company_name, 'new': company_name}
        if participant.role != role:
            changes['role'] = {'old': participant.role, 'new': role}
        if participant.region != region:
            changes['region'] = {'old': participant.region, 'new': region}
        if participant.customer_tier != customer_tier:
            changes['customer_tier'] = {'old': participant.customer_tier, 'new': customer_tier}
        if participant.language != language:
            changes['language'] = {'old': participant.language, 'new': language}
        if participant.client_industry != client_industry:
            changes['client_industry'] = {'old': participant.client_industry, 'new': client_industry}
        if participant.company_commercial_value != commercial_value:
            changes['company_commercial_value'] = {'old': participant.company_commercial_value, 'new': commercial_value}
        if participant.tenure_years != tenure_years:
            changes['tenure_years'] = {'old': participant.tenure_years, 'new': tenure_years}
        
        # Update participant fields
        participant.email = email
        participant.name = name
        participant.company_name = company_name
        participant.role = role
        participant.region = region
        participant.customer_tier = customer_tier
        participant.language = language
        participant.client_industry = client_industry
        participant.company_commercial_value = commercial_value
        participant.tenure_years = tenure_years
        
        db.session.commit()
        
        # Sync commercial_value to all existing participants from the same company (if changed)
        if 'company_commercial_value' in changes and commercial_value is not None and company_name:
            from sqlalchemy import func
            company_key = company_name.upper()
            updated_count = Participant.query.filter(
                func.upper(Participant.company_name) == company_key,
                Participant.business_account_id == current_account.id,
                Participant.id != participant.id  # Exclude current participant
            ).update({'company_commercial_value': commercial_value}, synchronize_session=False)
            
            db.session.commit()
            
            if updated_count > 0:
                flash(f'Commercial value synced to {updated_count} existing participant(s) from {company_name}.', 'info')
        
        # Audit logging for participant update
        if changes:
            try:
                queue_audit_log(
                    business_account_id=current_account.id,
                    action_type='participant_updated',
                    resource_type='participant',
                    resource_id=participant.id,
                    resource_name=participant.name,
                    details={
                        'changes': changes,
                        'has_survey_history': has_history
                    }
                )
            except Exception as audit_error:
                logger.error(f"Failed to log participant update audit: {audit_error}")
        
        account_name = current_account.name if current_account and hasattr(current_account, 'name') else 'Unknown'
        logger.info(f"Updated participant {email} (Business Account: {account_name})")
        flash(f'Participant {name} updated successfully.', 'success')
        return redirect(url_for('participants.list_participants'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error editing participant: {e}")
        flash('Error updating participant.', 'error')
        return redirect(url_for('participants.list_participants'))


@participant_bp.route('/upload', methods=['GET', 'POST'])
@require_business_auth
@require_permission('manage_participants')
def upload_participants():
    """Bulk upload participants via CSV"""
    
    if request.method == 'GET':
        # Show upload form
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.login'))
        
        return render_template('participants/upload.html',
                             business_account=current_account.to_dict() if current_account else {})
    
    # Handle CSV upload
    try:
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.login'))
            
        # No campaign validation needed for independent participants
        
        # Process CSV file
        if 'csv_file' not in request.files:
            flash('No CSV file provided.', 'error')
            return redirect(url_for('participants.upload_participants'))
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('participants.upload_participants'))
        
        # Read and process CSV
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        # Validate CSV headers
        required_columns = {'email', 'name', 'company_name'}
        if csv_reader.fieldnames is None:
            flash('CSV file appears to be empty or invalid.', 'error')
            return redirect(url_for('participants.upload_participants'))
        
        actual_columns = set(csv_reader.fieldnames)
        missing_columns = required_columns - actual_columns
        
        if missing_columns:
            missing_text = ', '.join(missing_columns)
            flash(f'CSV file is missing required columns: {missing_text}. Required columns are: email, name, company_name', 'error')
            return redirect(url_for('participants.upload_participants'))
        
        # Count participants to be uploaded and check license limits
        participant_rows = list(csv_reader)
        participant_count = len(participant_rows)
        
        # Note: License limits are enforced per-campaign when participants are assigned to campaigns
        # Standalone participant creation doesn't have global limits
        
        # Pre-validate commercial_value consistency across same companies
        company_commercial_values = {}
        for row_num, row in enumerate(participant_rows, start=2):
            company_name = row.get('company_name', '').strip()
            commercial_value_str = row.get('commercial_value', '').strip()
            
            if commercial_value_str and company_name:
                try:
                    commercial_value = float(commercial_value_str)
                    if commercial_value < 0:
                        errors.append(f"Row {row_num}: Commercial value must be positive")
                        continue
                    
                    company_key = company_name.upper()
                    if company_key in company_commercial_values:
                        if company_commercial_values[company_key] != commercial_value:
                            existing_value = company_commercial_values[company_key]
                            flash(f'CSV validation error: Company "{company_name}" has conflicting commercial values: ${existing_value:,.0f} and ${commercial_value:,.0f}. All participants from the same company must have the same value.', 'error')
                            return redirect(url_for('participants.upload_participants'))
                    else:
                        company_commercial_values[company_key] = commercial_value
                except ValueError:
                    errors.append(f"Row {row_num}: Invalid commercial value '{commercial_value_str}' - must be a number")
        
        created_count = 0
        error_count = 0
        if not errors:
            errors = []
        
        for row_num, row in enumerate(participant_rows, start=2):  # Start at 2 for header row
            try:
                email = row.get('email', '').strip().lower()
                name = row.get('name', '').strip()
                company_name = row.get('company_name', '').strip()
                
                if not email or not name or not company_name:
                    errors.append(f"Row {row_num}: Email, name, and company name are required")
                    error_count += 1
                    continue
                
                # Optional segmentation attributes (backward compatible)
                role = row.get('role', '').strip() or None
                region = row.get('region', '').strip() or None
                customer_tier = row.get('customer_tier', '').strip() or None
                language = row.get('language', '').strip() or 'en'
                client_industry = row.get('client_industry', '').strip() or None
                
                # Validate client_industry if provided
                if client_industry:
                    from industry_topic_hints_config import INDUSTRY_TOPIC_HINTS
                    valid_industries = list(INDUSTRY_TOPIC_HINTS.keys())
                    if client_industry not in valid_industries:
                        errors.append(f"Row {row_num}: Invalid client industry '{client_industry}'. Must be one of: {', '.join(valid_industries)}")
                        error_count += 1
                        continue
                
                # Parse commercial_value (optional, company-level)
                commercial_value = None
                commercial_value_str = row.get('commercial_value', '').strip()
                if commercial_value_str:
                    try:
                        commercial_value = float(commercial_value_str)
                        if commercial_value < 0:
                            errors.append(f"Row {row_num}: Commercial value must be positive")
                            error_count += 1
                            continue
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid commercial value '{commercial_value_str}'")
                        error_count += 1
                        continue
                
                # Parse tenure_years (optional)
                tenure_years = None
                tenure_years_str = row.get('tenure_years', '').strip()
                if tenure_years_str:
                    try:
                        tenure_years = float(tenure_years_str)
                        if tenure_years < 0:
                            errors.append(f"Row {row_num}: Tenure must be positive")
                            error_count += 1
                            continue
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid tenure value '{tenure_years_str}'")
                        error_count += 1
                        continue
                
                # Check for duplicate participant (email within business account)
                existing = Participant.query.filter_by(
                    business_account_id=current_account.id,
                    email=email
                ).first()
                
                if existing:
                    errors.append(f"Row {row_num}: Participant {email} already exists in your account")
                    error_count += 1
                    continue
                
                # Create participant with origin tracking and unified token system
                participant = Participant()
                participant.business_account_id = current_account.id
                participant.email = email
                participant.name = name
                participant.company_name = company_name if company_name else None
                participant.role = role
                participant.region = region
                participant.customer_tier = customer_tier
                participant.language = language
                participant.client_industry = client_industry
                participant.company_commercial_value = commercial_value
                participant.tenure_years = tenure_years
                participant.source = 'admin_bulk'  # Track that this was admin-created via bulk upload
                
                # Generate unified token for seamless UX
                participant.generate_token()
                
                # Set appropriate status for business context
                participant.set_appropriate_status_for_context(is_trial=False)
                db.session.add(participant)
                created_count += 1
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                error_count += 1
        
        db.session.commit()
        
        # Sync commercial_value to all existing participants from the same companies
        if company_commercial_values:
            from sqlalchemy import func
            for company_key, commercial_value in company_commercial_values.items():
                # Update all participants with matching company (case-insensitive)
                Participant.query.filter(
                    func.upper(Participant.company_name) == company_key,
                    Participant.business_account_id == current_account.id
                ).update({'company_commercial_value': commercial_value}, synchronize_session=False)
            
            db.session.commit()
        
        # Audit logging for bulk participant upload
        if created_count > 0:
            try:
                queue_audit_log(
                    business_account_id=current_account.id,
                    action_type='participants_uploaded',
                    resource_type='participant',
                    details={
                        'count': created_count,
                        'errors': error_count,
                        'source': 'admin_bulk'
                    }
                )
            except Exception as audit_error:
                logger.error(f"Failed to log bulk participant upload audit: {audit_error}")
        
        # Show results
        if created_count > 0:
            flash(f'Successfully created {created_count} participants. You can now assign them to campaigns.', 'success')
        
        if error_count > 0:
            flash(f'{error_count} errors occurred during upload. Check the details below.', 'warning')
            for error in errors[:10]:  # Show first 10 errors
                flash(error, 'error')
        
        account_name = current_account.name if current_account and hasattr(current_account, 'name') else 'Unknown'
        logger.info(f"CSV upload completed: {created_count} created, {error_count} errors (Business Account: {account_name})")
        return redirect(url_for('participants.list_participants'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error uploading participants: {e}")
        flash('Error processing CSV file.', 'error')
        return redirect(url_for('participants.upload_participants'))


@participant_bp.route('/<int:participant_id>/delete', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def delete_participant(participant_id):
    """Delete participant"""
    
    try:
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('participants.list_participants'))
        
        # Get participant (scoped to current business account)
        participant = Participant.query.filter_by(
            id=participant_id,
            business_account_id=current_account.id
        ).first()
        
        if not participant:
            flash('Participant not found.', 'error')
            return redirect(url_for('participants.list_participants'))
        
        # CRITICAL: Check if participant has survey history (prevents data integrity issues)
        if participant.has_survey_history():
            flash(f'Cannot delete participant {participant.name} - they have survey history (responses, campaigns, or email deliveries). This protects data integrity.', 'error')
            return redirect(url_for('participants.list_participants'))
        
        participant_name = participant.name
        participant_email = participant.email
        db.session.delete(participant)
        db.session.commit()
        
        # Audit logging for participant deletion
        try:
            queue_audit_log(
                business_account_id=current_account.id,
                action_type='participant_deleted',
                resource_type='participant',
                resource_id=participant_id,
                resource_name=participant_name,
                details={
                    'email': participant_email
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to log participant deletion audit: {audit_error}")
        
        account_name = current_account.name if current_account and hasattr(current_account, 'name') else 'Unknown'
        logger.info(f"Deleted participant {participant_name} (ID: {participant_id}, Business Account: {account_name})")
        flash(f'Participant {participant_name} deleted successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting participant {participant_id}: {e}")
        flash('Error deleting participant.', 'error')
    
    return redirect(url_for('participants.list_participants'))


@participant_bp.route('/<int:participant_id>/regenerate-token', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def regenerate_token(participant_id):
    """Regenerate participant token"""
    
    try:
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('participants.list_participants'))
        
        # Get participant (scoped to current business account)
        participant = Participant.query.filter_by(
            id=participant_id,
            business_account_id=current_account.id
        ).first()
        
        if not participant:
            flash('Participant not found.', 'error')
            return redirect(url_for('participants.list_participants'))
        
        # Generate new token
        old_token = participant.token
        participant.generate_token()
        db.session.commit()
        
        # Audit logging for token regeneration
        try:
            queue_audit_log(
                business_account_id=current_account.id,
                action_type='participant_token_regenerated',
                resource_type='participant',
                resource_id=participant_id,
                resource_name=participant.name,
                details={
                    'email': participant.email
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to log token regeneration audit: {audit_error}")
        
        account_name = current_account.name if current_account and hasattr(current_account, 'name') else 'Unknown'
        participant_name = participant.name if participant and hasattr(participant, 'name') else 'Unknown'
        logger.info(f"Regenerated token for participant {participant_name} (ID: {participant_id}, Business Account: {account_name})")
        flash(f'New token generated for {participant_name}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error regenerating token for participant {participant_id}: {e}")
        flash('Error regenerating token.', 'error')
    
    return redirect(url_for('participants.list_participants'))


@participant_bp.route('/bulk-edit', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def bulk_edit_participants():
    """
    Bulk edit participants - maximum 50 at a time
    Allowed fields: role, region, customer_tier, language, tenure_years, company_commercial_value
    Excluded: company_name (too risky), email (locked for survey history)
    """
    
    MAX_BATCH_SIZE = 50
    
    try:
        logger.info("Bulk edit request received")
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            logger.error("Bulk edit: Business account context not found")
            return jsonify({
                'success': False,
                'error': 'Business account context not found'
            }), 401
        
        # Parse request data
        data = request.get_json()
        logger.info(f"Bulk edit data received: participant_ids count={len(data.get('participant_ids', []))}, updates={data.get('updates', {})}")
        participant_ids = data.get('participant_ids', [])
        updates = data.get('updates', {})
        
        # Validate batch size
        if len(participant_ids) > MAX_BATCH_SIZE:
            return jsonify({
                'success': False,
                'error': 'Batch limit exceeded',
                'message': f'Bulk edits limited to {MAX_BATCH_SIZE} participants. Please apply this batch before selecting more.',
                'max_allowed': MAX_BATCH_SIZE,
                'requested': len(participant_ids)
            }), 413
        
        if not participant_ids:
            return jsonify({
                'success': False,
                'error': 'No participants selected'
            }), 400
        
        if not updates:
            return jsonify({
                'success': False,
                'error': 'No updates provided'
            }), 400
        
        # Validate allowed fields only
        allowed_fields = {'role', 'region', 'customer_tier', 'language', 'tenure_years', 'company_commercial_value'}
        invalid_fields = set(updates.keys()) - allowed_fields
        if invalid_fields:
            return jsonify({
                'success': False,
                'error': f'Invalid fields: {", ".join(invalid_fields)}. Company name cannot be edited in bulk.'
            }), 400
        
        # Generate unique bulk operation ID for audit trail correlation
        bulk_operation_id = str(uuid.uuid4())
        
        # Fetch participants (scoped to current business account)
        participants = Participant.query.filter(
            Participant.id.in_(participant_ids),
            Participant.business_account_id == current_account.id
        ).all()
        
        if not participants:
            return jsonify({
                'success': False,
                'error': 'No valid participants found'
            }), 404
        
        # Track results
        updated_count = 0
        skipped_count = 0
        skipped_participants = []
        
        # Process updates
        for participant in participants:
            # Check if customer_tier is being changed and participant has survey history
            if 'customer_tier' in updates and participant.has_survey_history():
                skipped_count += 1
                skipped_participants.append({
                    'id': participant.id,
                    'name': participant.name,
                    'reason': 'Customer tier locked (has survey history)'
                })
                continue
            
            # Track changes for audit
            changes = {}
            
            # Apply updates
            for field, new_value in updates.items():
                old_value = getattr(participant, field, None)
                
                # Only update if value actually changed
                if old_value != new_value:
                    changes[field] = {
                        'old': old_value,
                        'new': new_value
                    }
                    setattr(participant, field, new_value)
            
            # If no changes, skip audit logging
            if not changes:
                continue
            
            # Sync commercial value across same company if changed
            if 'company_commercial_value' in changes and participant.company_name:
                normalized_company = participant.company_name.strip().lower()
                same_company_participants = Participant.query.filter(
                    db.func.lower(db.func.trim(Participant.company_name)) == normalized_company,
                    Participant.business_account_id == current_account.id
                ).all()
                
                new_commercial_value = changes['company_commercial_value']['new']
                
                for other_participant in same_company_participants:
                    if other_participant.id != participant.id:
                        old_commercial_value = other_participant.company_commercial_value
                        other_participant.company_commercial_value = new_commercial_value
                        
                        # Audit log for automatic commercial value sync
                        try:
                            queue_audit_log(
                                business_account_id=current_account.id,
                                action_type='participant_updated',
                                resource_type='participant',
                                resource_id=other_participant.id,
                                resource_name=other_participant.name,
                                details={
                                    'email': other_participant.email,
                                    'changes': {
                                        'company_commercial_value': {
                                            'old': old_commercial_value,
                                            'new': new_commercial_value
                                        }
                                    },
                                    'bulk_operation_id': bulk_operation_id,
                                    'auto_synced_from_participant_id': participant.id,
                                    'auto_synced_from_participant_name': participant.name,
                                    'sync_reason': 'Company commercial value automatic synchronization',
                                    'company_name': participant.company_name
                                }
                            )
                        except Exception as audit_error:
                            logger.error(f"Failed to log commercial value auto-sync audit: {audit_error}")
            
            updated_count += 1
            
            # Audit logging for each participant update
            try:
                queue_audit_log(
                    business_account_id=current_account.id,
                    action_type='participant_updated',
                    resource_type='participant',
                    resource_id=participant.id,
                    resource_name=participant.name,
                    details={
                        'email': participant.email,
                        'changes': changes,
                        'bulk_operation_id': bulk_operation_id,
                        'has_survey_history': participant.has_survey_history()
                    }
                )
            except Exception as audit_error:
                logger.error(f"Failed to log bulk participant update audit: {audit_error}")
        
        db.session.commit()
        
        account_name = current_account.name if current_account and hasattr(current_account, 'name') else 'Unknown'
        logger.info(f"Bulk edit completed: {updated_count} updated, {skipped_count} skipped (Bulk ID: {bulk_operation_id}, Business Account: {account_name})")
        
        return jsonify({
            'success': True,
            'updated': updated_count,
            'skipped': skipped_count,
            'skipped_participants': skipped_participants,
            'bulk_operation_id': bulk_operation_id,
            'message': f'Successfully updated {updated_count} participant(s). {skipped_count} skipped due to restrictions.'
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error in bulk edit: {e}")
        logger.error(f"Bulk edit traceback: {error_traceback}")
        return jsonify({
            'success': False,
            'error': 'An error occurred during bulk edit',
            'details': str(e)
        }), 500


# ==============================================================================
# CAMPAIGN-PARTICIPANT ASSOCIATION MANAGEMENT ROUTES
# ==============================================================================

@participant_bp.route('/campaigns/<int:campaign_id>/participants', methods=['GET', 'POST'])
@require_business_auth
@require_permission('manage_participants')
def manage_campaign_participants(campaign_id: int):
    """Manage participants for a specific campaign"""
    
    try:
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash(_('Campaign not found.'), 'error')
            return redirect(url_for('participants.list_participants'))
        
        if request.method == 'GET':
            # Get search parameter for current participants
            search_query = request.args.get('search', '').strip()
            
            # Get current campaign participants with optional search
            campaign_participants_query = CampaignParticipant.query.filter_by(
                campaign_id=campaign_id,
                business_account_id=current_account.id
            ).join(Participant)
            
            # Apply search filter if provided
            if search_query:
                search_term = f"%{search_query}%"
                campaign_participants_query = campaign_participants_query.filter(
                    db.or_(
                        Participant.name.ilike(search_term),
                        Participant.email.ilike(search_term),
                        Participant.company_name.ilike(search_term)
                    )
                )
            
            # Execute with eager loading to prevent N+1 queries
            campaign_participants = campaign_participants_query.options(
                joinedload(CampaignParticipant.participant)
            ).all()
            
            # Get all campaign participants for KPI calculations (not just searched ones)
            all_campaign_participants = CampaignParticipant.query.filter_by(
                campaign_id=campaign_id,
                business_account_id=current_account.id
            ).options(joinedload(CampaignParticipant.participant)).all()
            
            # Calculate KPI stats from ALL campaign participants
            campaign_stats = {
                'total': len(all_campaign_participants),
                'invited': len([cp for cp in all_campaign_participants if cp.status == 'invited']),
                'started': len([cp for cp in all_campaign_participants if cp.status == 'started']),
                'completed': len([cp for cp in all_campaign_participants if cp.status == 'completed'])
            }
            assigned_participant_ids = [cp.participant_id for cp in all_campaign_participants]
            
            # Build base query for available participants
            available_query = Participant.query.filter(
                Participant.business_account_id == current_account.id
            )
            
            # Exclude already assigned participants
            if assigned_participant_ids:
                available_query = available_query.filter(~Participant.id.in_(assigned_participant_ids))
            
            # Apply multi-value filters if provided
            filter_companies = request.args.getlist('filter_company')
            filter_roles = request.args.getlist('filter_role')
            filter_regions = request.args.getlist('filter_region')
            filter_tiers = request.args.getlist('filter_tier')
            filter_industries = request.args.getlist('filter_industry')
            filter_languages = request.args.getlist('filter_language')
            filter_tenure_ranges = request.args.getlist('filter_tenure')
            
            # Company name filter (support multiple companies)
            if filter_companies:
                # Handle "Unspecified" as NULL
                if 'Unspecified' in filter_companies:
                    other_companies = [c for c in filter_companies if c != 'Unspecified']
                    if other_companies:
                        available_query = available_query.filter(
                            db.or_(
                                Participant.company_name.in_(other_companies),
                                Participant.company_name.is_(None)
                            )
                        )
                    else:
                        available_query = available_query.filter(Participant.company_name.is_(None))
                else:
                    available_query = available_query.filter(Participant.company_name.in_(filter_companies))
            
            # Role filter (support multiple roles)
            if filter_roles:
                if 'Unspecified' in filter_roles:
                    other_roles = [r for r in filter_roles if r != 'Unspecified']
                    if other_roles:
                        available_query = available_query.filter(
                            db.or_(
                                Participant.role.in_(other_roles),
                                Participant.role.is_(None)
                            )
                        )
                    else:
                        available_query = available_query.filter(Participant.role.is_(None))
                else:
                    available_query = available_query.filter(Participant.role.in_(filter_roles))
            
            # Region filter (support multiple regions)
            if filter_regions:
                if 'Unspecified' in filter_regions:
                    other_regions = [r for r in filter_regions if r != 'Unspecified']
                    if other_regions:
                        available_query = available_query.filter(
                            db.or_(
                                Participant.region.in_(other_regions),
                                Participant.region.is_(None)
                            )
                        )
                    else:
                        available_query = available_query.filter(Participant.region.is_(None))
                else:
                    available_query = available_query.filter(Participant.region.in_(filter_regions))
            
            # Customer tier filter (support multiple tiers)
            if filter_tiers:
                if 'Unspecified' in filter_tiers:
                    other_tiers = [t for t in filter_tiers if t != 'Unspecified']
                    if other_tiers:
                        available_query = available_query.filter(
                            db.or_(
                                Participant.customer_tier.in_(other_tiers),
                                Participant.customer_tier.is_(None)
                            )
                        )
                    else:
                        available_query = available_query.filter(Participant.customer_tier.is_(None))
                else:
                    available_query = available_query.filter(Participant.customer_tier.in_(filter_tiers))
            
            # Client industry filter (support multiple industries)
            if filter_industries:
                if 'Unspecified' in filter_industries:
                    other_industries = [i for i in filter_industries if i != 'Unspecified']
                    if other_industries:
                        available_query = available_query.filter(
                            db.or_(
                                Participant.client_industry.in_(other_industries),
                                Participant.client_industry.is_(None)
                            )
                        )
                    else:
                        available_query = available_query.filter(Participant.client_industry.is_(None))
                else:
                    available_query = available_query.filter(Participant.client_industry.in_(filter_industries))
            
            # Language filter (support multiple languages)
            if filter_languages:
                if 'Unspecified' in filter_languages:
                    other_languages = [l for l in filter_languages if l != 'Unspecified']
                    if other_languages:
                        available_query = available_query.filter(
                            db.or_(
                                Participant.language.in_(other_languages),
                                Participant.language.is_(None)
                            )
                        )
                    else:
                        available_query = available_query.filter(Participant.language.is_(None))
                else:
                    available_query = available_query.filter(Participant.language.in_(filter_languages))
            
            # Tenure filter (support multiple tenure ranges)
            if filter_tenure_ranges:
                tenure_conditions = []
                for tenure_range in filter_tenure_ranges:
                    if tenure_range == 'Unspecified':
                        tenure_conditions.append(Participant.tenure_years.is_(None))
                    elif tenure_range == '0-1':
                        tenure_conditions.append(db.and_(Participant.tenure_years >= 0, Participant.tenure_years < 1))
                    elif tenure_range == '1-3':
                        tenure_conditions.append(db.and_(Participant.tenure_years >= 1, Participant.tenure_years < 3))
                    elif tenure_range == '3-5':
                        tenure_conditions.append(db.and_(Participant.tenure_years >= 3, Participant.tenure_years < 5))
                    elif tenure_range == '5+':
                        tenure_conditions.append(Participant.tenure_years >= 5)
                
                if tenure_conditions:
                    available_query = available_query.filter(db.or_(*tenure_conditions))
            
            # Execute query with ordering
            available_participants = available_query.order_by(Participant.name).all()
            
            # Calculate total available participants (excluding already assigned)
            total_available_query = Participant.query.filter(
                Participant.business_account_id == current_account.id
            )
            if assigned_participant_ids:
                total_available_query = total_available_query.filter(~Participant.id.in_(assigned_participant_ids))
            total_available_count = total_available_query.count()
            
            # Get unique filter options from all participants in this business account
            all_participants_for_filters = Participant.query.filter(
                Participant.business_account_id == current_account.id
            ).all()
            
            filter_options = {
                'companies': sorted(list(set([p.company_name for p in all_participants_for_filters if p.company_name]))) + ['Unspecified'],
                'roles': sorted(list(set([p.role for p in all_participants_for_filters if p.role]))) + ['Unspecified'],
                'regions': sorted(list(set([p.region for p in all_participants_for_filters if p.region]))) + ['Unspecified'],
                'tiers': sorted(list(set([p.customer_tier for p in all_participants_for_filters if p.customer_tier]))) + ['Unspecified'],
                'industries': sorted(list(set([p.client_industry for p in all_participants_for_filters if p.client_industry]))) + ['Unspecified'],
                'languages': sorted(list(set([p.language for p in all_participants_for_filters if p.language]))) + ['Unspecified'],
                'tenure_ranges': ['0-1', '1-3', '3-5', '5+', 'Unspecified']
            }
            
            # Track active filters for UI
            active_filters = {
                'companies': filter_companies,
                'roles': filter_roles,
                'regions': filter_regions,
                'tiers': filter_tiers,
                'industries': filter_industries,
                'languages': filter_languages,
                'tenure_ranges': filter_tenure_ranges
            }
            
            # Prepare data for template
            current_participants = []
            for cp in campaign_participants:
                participant_data = cp.participant.to_dict() if cp.participant else {}
                participant_data.update({
                    'association_id': cp.id,
                    'token': cp.token,  # Use campaign-participant token, not participant token
                    'status': cp.status,
                    'invited_at': cp.invited_at.isoformat() if cp.invited_at else None,
                    'started_at': cp.started_at.isoformat() if cp.started_at else None,
                    'completed_at': cp.completed_at.isoformat() if cp.completed_at else None
                })
                current_participants.append(participant_data)
            
            # Check for active bulk job
            active_bulk_job = None
            if campaign.has_active_bulk_job and campaign.active_bulk_job_id:
                from models import BulkOperationJob
                active_bulk_job = BulkOperationJob.query.get(campaign.active_bulk_job_id)
            
            return render_template('participants/campaign_participants.html',
                                 campaign=campaign.to_dict(),
                                 current_participants=current_participants,
                                 available_participants=[p.to_dict() for p in available_participants],
                                 business_account=current_account.to_dict(),
                                 search_query=search_query,
                                 campaign_stats=campaign_stats,
                                 filter_options=filter_options,
                                 active_filters=active_filters,
                                 total_available_count=total_available_count,
                                 active_bulk_job=active_bulk_job.to_dict() if active_bulk_job else None)
        
        # Handle POST - Add participants to campaign
        if request.method == 'POST':
            # Validate campaign status - can only add participants if campaign is draft or ready
            if campaign.status not in ['draft', 'ready']:
                flash(f'Cannot add participants to {campaign.status} campaign. Campaign must be draft or ready.', 'error')
                return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))
            
            participant_ids = request.form.getlist('participant_ids')
            if not participant_ids:
                flash('No participants selected.', 'error')
                return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))
            
            # License enforcement: Check if adding these participants would exceed license limit
            if not LicenseService.can_add_participants(
                business_account_id=current_account.id,
                campaign_id=campaign_id,
                additional_count=len(participant_ids)
            ):
                # Get license details for user-friendly message
                current_license = LicenseService.get_current_license(current_account.id)
                if current_license:
                    limit = current_license.max_invitations_per_campaign
                    license_name = current_license.license_type.title()
                    flash(f'Cannot add {len(participant_ids)} participant(s). Your {license_name} license allows a maximum of {limit:,} participants per campaign. Please upgrade your license to add more participants.', 'error')
                else:
                    flash('Cannot add participants. License limit exceeded.', 'error')
                return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))
            
            # Determine processing strategy based on count
            BULK_THRESHOLD = 100  # Process asynchronously if adding 100+ participants
            participant_count = len(participant_ids)
            
            if participant_count >= BULK_THRESHOLD:
                # Use background job for bulk operations
                from models import BulkOperationJob
                from task_queue import task_queue
                import uuid
                from sqlalchemy import text
                
                # Atomic lock acquisition using SELECT FOR UPDATE OF campaigns
                # (of=Campaign avoids "FOR UPDATE on nullable outer join" error from classic_survey_configs join)
                campaign_locked = db.session.query(Campaign).filter(
                    Campaign.id == campaign_id
                ).with_for_update(of=Campaign).first()
                
                # Check for active bulk job (now atomic - row is locked)
                if campaign_locked.has_active_bulk_job:
                    db.session.rollback()
                    flash(f'A bulk operation is already in progress for this campaign ({campaign_locked.active_bulk_operation}). Please wait for it to complete.', 'warning')
                    return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))
                
                # Create job record
                job = BulkOperationJob(
                    job_id=str(uuid.uuid4()),
                    business_account_id=current_account.id,
                    user_id=session.get('business_user_id'),
                    operation_type='bulk_participant_add',
                    operation_data=json.dumps({
                        'campaign_id': campaign_id,
                        'campaign_name': campaign_locked.name,
                        'participant_count': participant_count
                    }),
                    status='pending',
                    progress=0
                )
                
                db.session.add(job)
                db.session.flush()  # Get job.id before setting campaign lock
                
                # Set campaign lock atomically (row is already locked)
                campaign_locked.has_active_bulk_job = True
                campaign_locked.active_bulk_job_id = job.id
                campaign_locked.active_bulk_operation = 'add'
                
                db.session.commit()
                
                # Queue background task
                task_queue.add_task(
                    task_type='bulk_participant_add',
                    priority=1,
                    task_data={
                        'job_id': job.id,
                        'campaign_id': campaign_id,
                        'participant_ids': [int(pid) for pid in participant_ids],
                        'business_account_id': current_account.id,
                        'user_id': session.get('business_user_id')
                    }
                )
                
                flash(f'Adding {participant_count} participants in the background. You will be notified when complete.', 'info')
                logger.info(f"Queued bulk participant add job {job.job_id} for campaign {campaign_id} ({participant_count} participants)")
                return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))
            
            else:
                # Process synchronously for small operations (< 100 participants)
                added_count = 0
                for participant_id in participant_ids:
                    try:
                        # Verify participant exists and belongs to current business account
                        participant = Participant.query.filter_by(
                            id=int(participant_id),
                            business_account_id=current_account.id
                        ).first()
                        
                        if not participant:
                            continue
                        
                        # Check if association already exists
                        existing = CampaignParticipant.query.filter_by(
                            campaign_id=campaign_id,
                            participant_id=participant_id
                        ).first()
                        
                        if existing:
                            continue
                        
                        # Create campaign-participant association
                        association = CampaignParticipant()
                        association.campaign_id = campaign_id
                        association.participant_id = participant_id
                        association.business_account_id = current_account.id
                        association.status = 'invited'
                        
                        db.session.add(association)
                        added_count += 1
                        
                    except ValueError:
                        continue
                
                db.session.commit()
                
                # Audit logging for adding participants to campaign
                if added_count > 0:
                    try:
                        queue_audit_log(
                            business_account_id=current_account.id,
                            action_type='participants_added',
                            resource_type='campaign',
                            resource_id=campaign_id,
                            resource_name=campaign.name,
                            details={
                                'count': added_count
                            }
                        )
                    except Exception as audit_error:
                        logger.error(f"Failed to log participants added to campaign audit: {audit_error}")
                        
                    flash(f'Added {added_count} participant(s) to campaign {campaign.name}.', 'success')
                    logger.info(f"Added {added_count} participants to campaign {campaign.name} (ID: {campaign_id})")
                else:
                    flash('No new participants were added.', 'warning')
                
                return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error managing campaign participants for campaign {campaign_id}: {e}")
        flash('Error managing campaign participants.', 'error')
        return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))


@participant_bp.route('/campaigns/<int:campaign_id>/participants/<int:association_id>/remove', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def remove_campaign_participant(campaign_id, association_id):
    """Remove participant from campaign"""
    
    try:
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('participants.list_participants'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash(_('Campaign not found.'), 'error')
            return redirect(url_for('participants.list_participants'))
        
        # Validate campaign status - can only remove participants if campaign is draft or ready
        if campaign.status in ['active', 'completed']:
            status_msg = 'active and collecting responses' if campaign.status == 'active' else 'completed'
            flash(f'Cannot remove participants from {status_msg} campaign. Participants can only be modified when campaign is in draft or ready status.', 'error')
            return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))
        
        # Get association (scoped to current business account)
        association = CampaignParticipant.query.filter_by(
            id=association_id,
            campaign_id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not association:
            flash('Participant association not found.', 'error')
            return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))
        
        participant_name = association.participant.name if association.participant else 'Unknown'
        participant_email = association.participant.email if association.participant else 'Unknown'
        db.session.delete(association)
        db.session.commit()
        
        # Audit logging for removing participant from campaign
        try:
            queue_audit_log(
                business_account_id=current_account.id,
                action_type='participants_removed',
                resource_type='campaign',
                resource_id=campaign_id,
                resource_name=campaign.name,
                details={
                    'participant_name': participant_name,
                    'participant_email': participant_email
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to log participant removal from campaign audit: {audit_error}")
        
        logger.info(f"Removed participant {participant_name} from campaign {campaign.name} (ID: {campaign_id})")
        flash(f'Removed {participant_name} from campaign {campaign.name}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing participant from campaign {campaign_id}: {e}")
        flash('Error removing participant from campaign.', 'error')
    
    return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))


@participant_bp.route('/campaigns/<int:campaign_id>/participants/bulk-remove', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def bulk_remove_campaign_participants(campaign_id):
    """
    Bulk remove participants from campaign
    Only allowed for campaigns in draft or ready status
    Uses background jobs for large batches (>100)
    """
    
    SYNC_BATCH_SIZE = 100
    
    try:
        logger.info(f"Bulk remove request received for campaign {campaign_id}")
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            logger.error("Bulk remove: Business account context not found")
            return jsonify({
                'success': False,
                'error': 'Business account context not found'
            }), 401
        
        # Parse request data
        data = request.get_json()
        association_ids = data.get('association_ids', [])
        
        logger.info(f"Bulk remove data received: association_ids count={len(association_ids)}")
        
        # Handle large batches via background job
        if len(association_ids) > SYNC_BATCH_SIZE:
            from models import BulkOperationJob
            from task_queue import task_queue
            
            # Atomic lock acquisition using SELECT FOR UPDATE OF campaigns
            # (of=Campaign avoids "FOR UPDATE on nullable outer join" error from classic_survey_configs join)
            campaign_locked = db.session.query(Campaign).filter(
                Campaign.id == campaign_id
            ).with_for_update(of=Campaign).first()
            
            # Check for active bulk job (now atomic - row is locked)
            if campaign_locked.has_active_bulk_job:
                db.session.rollback()
                return jsonify({
                    'success': False,
                    'error': 'Bulk operation in progress',
                    'message': f'A bulk {campaign_locked.active_bulk_operation} operation is already in progress. Please wait for it to complete.'
                }), 409
            
            # Create job record
            job_uuid = str(uuid.uuid4())
            job = BulkOperationJob(
                job_id=job_uuid,
                business_account_id=current_account.id,
                user_id=session.get('business_user_id'),
                operation_type='bulk_participant_remove',
                operation_data=json.dumps({
                    'campaign_id': campaign_id,
                    'association_count': len(association_ids)
                })
            )
            db.session.add(job)
            db.session.flush()  # Get job.id before setting campaign lock
            
            # Set campaign lock atomically (row is already locked)
            campaign_locked.has_active_bulk_job = True
            campaign_locked.active_bulk_job_id = job.id
            campaign_locked.active_bulk_operation = 'remove'
            
            db.session.commit()
            
            # Queue background task
            task_queue.add_task(
                task_type='bulk_participant_remove',
                task_data={
                    'job_id': job.id,
                    'campaign_id': campaign_id,
                    'association_ids': association_ids,
                    'business_account_id': current_account.id,
                    'user_id': session.get('business_user_id')
                },
                priority=1
            )
            
            logger.info(f"Queued background job for removing {len(association_ids)} participants from campaign {campaign_id}")
            
            return jsonify({
                'success': True,
                'async': True,
                'job_id': job_uuid,
                'message': f'Removing {len(association_ids)} participants in the background. You will be notified when complete.',
                'count': len(association_ids)
            }), 202
        
        if not association_ids:
            return jsonify({
                'success': False,
                'error': 'No participants selected'
            }), 400
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            return jsonify({
                'success': False,
                'error': 'Campaign not found'
            }), 404
        
        # Validate campaign status - can only remove participants if campaign is draft or ready
        if campaign.status in ['active', 'completed']:
            status_msg = 'active and collecting responses' if campaign.status == 'active' else 'completed'
            return jsonify({
                'success': False,
                'error': f'Cannot remove participants from {status_msg} campaign',
                'message': 'Participants can only be removed when campaign is in draft or ready status.'
            }), 403
        
        # Generate unique bulk operation ID for audit trail correlation
        bulk_operation_id = str(uuid.uuid4())
        
        # Fetch associations (scoped to current business account and campaign)
        associations = CampaignParticipant.query.filter(
            CampaignParticipant.id.in_(association_ids),
            CampaignParticipant.campaign_id == campaign_id,
            CampaignParticipant.business_account_id == current_account.id
        ).all()
        
        if not associations:
            return jsonify({
                'success': False,
                'error': 'No valid participant associations found'
            }), 404
        
        # Track results
        removed_count = 0
        removed_participants = []
        
        # Process removals
        for association in associations:
            participant_name = association.participant.name if association.participant else 'Unknown'
            participant_email = association.participant.email if association.participant else 'Unknown'
            
            removed_participants.append({
                'id': association.participant_id,
                'name': participant_name,
                'email': participant_email
            })
            
            db.session.delete(association)
            removed_count += 1
        
        db.session.commit()
        
        # Audit logging for bulk removal
        try:
            queue_audit_log(
                business_account_id=current_account.id,
                action_type='participants_removed',
                resource_type='campaign',
                resource_id=campaign_id,
                resource_name=campaign.name,
                details={
                    'bulk_operation_id': bulk_operation_id,
                    'removed_count': removed_count,
                    'participants': removed_participants,
                    'campaign_status': campaign.status
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to log bulk participant removal audit: {audit_error}")
        
        account_name = current_account.name if current_account and hasattr(current_account, 'name') else 'Unknown'
        logger.info(f"Bulk removal completed: {removed_count} participants removed from campaign {campaign.name} (Bulk ID: {bulk_operation_id}, Business Account: {account_name})")
        
        return jsonify({
            'success': True,
            'removed': removed_count,
            'bulk_operation_id': bulk_operation_id,
            'message': f'Successfully removed {removed_count} participant(s) from {campaign.name}.'
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error in bulk removal: {e}")
        logger.error(f"Bulk removal traceback: {error_traceback}")
        return jsonify({
            'success': False,
            'error': 'An error occurred during bulk removal',
            'details': str(e)
        }), 500


# ==============================================================================
# BULK OPERATION STATUS API
# ==============================================================================

@participant_bp.route('/api/bulk-jobs/<job_id>/status', methods=['GET'])
@require_business_auth
def get_bulk_job_status(job_id):
    """Get status of a bulk operation job for polling"""
    try:
        from models import BulkOperationJob
        
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account not found'}), 401
        
        # Query job by UUID and business account
        # Expire session to get fresh data from database (avoid caching stale progress)
        db.session.expire_all()
        
        job = BulkOperationJob.query.filter_by(
            job_id=job_id,
            business_account_id=current_account.id
        ).first()
        
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        # Prepare response
        response_data = {
            'job_id': job.job_id,
            'operation_type': job.operation_type,
            'status': job.status,
            'progress': job.progress,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None
        }
        
        # Add result details if completed
        if job.status == 'completed' and job.result:
            try:
                result = json.loads(job.result) if isinstance(job.result, str) else job.result
                response_data['result'] = result
            except:
                pass
        
        # Add error if failed
        if job.status == 'failed' and job.error:
            response_data['error'] = job.error
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting bulk job status: {e}")
        return jsonify({'error': 'Failed to get job status'}), 500


# ==============================================================================
# INDIVIDUAL PARTICIPANT INVITATION ROUTES
# ==============================================================================

@participant_bp.route('/<int:participant_id>/send-invitation', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def send_individual_invitation(participant_id):
    """Send email invitation to individual participant for all their active campaigns"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('participants.list_participants'))
        
        # Get participant (scoped to current business account)
        participant = Participant.query.filter_by(
            id=participant_id,
            business_account_id=current_account.id
        ).first()
        
        if not participant:
            flash('Participant not found.', 'error')
            return redirect(url_for('participants.list_participants'))
        
        # Check if email service is configured for this business account
        if not email_service.is_configured(current_account.id):
            flash(_('The email service is not configured. Please configure your SMTP settings first.'), 'error')
            return redirect(url_for('participants.list_participants'))
        
        # Get active campaigns for this participant
        active_campaign_participants = CampaignParticipant.query.filter_by(
            participant_id=participant_id,
            business_account_id=current_account.id
        ).join(Campaign).filter(
            Campaign.status == 'active'  # type: ignore
        ).all()
        
        if not active_campaign_participants:
            flash(f'Participant {participant.name} is not associated with any active campaigns.', 'warning')
            return redirect(url_for('participants.list_participants'))
        
        # Send invitations for each active campaign
        sent_count = 0
        failed_count = 0
        
        for cp in active_campaign_participants:
            try:
                # Check if there's already a successful delivery for this campaign
                existing_delivery = EmailDelivery.query.filter_by(
                    campaign_participant_id=cp.id,
                    email_type='participant_invitation',
                    status='sent'
                ).first()
                
                if existing_delivery:
                    continue  # Skip if already sent successfully
                
                # Create EmailDelivery record for tracking
                email_delivery = EmailDelivery()
                email_delivery.business_account_id = current_account.id
                email_delivery.campaign_id = cp.campaign_id
                email_delivery.participant_id = participant_id
                email_delivery.campaign_participant_id = cp.id
                email_delivery.email_type = 'participant_invitation'
                email_delivery.recipient_email = participant.email
                email_delivery.recipient_name = participant.name
                email_delivery.subject = f"Survey Invitation - {cp.campaign.name}"
                email_delivery.status = 'pending'
                
                db.session.add(email_delivery)
                db.session.flush()  # Get the ID
                
                # Prepare task data
                task_data = {
                    'participant_email': participant.email,
                    'participant_name': participant.name,
                    'campaign_name': cp.campaign.name,
                    'survey_token': cp.token,
                    'business_account_name': current_account.name,
                    'email_delivery_id': email_delivery.id
                }
                
                # Add to task queue
                add_email_task('participant_invitation', task_data, priority=2)
                
                # Update campaign participant status
                cp.status = 'invited'
                cp.invited_at = datetime.utcnow()
                
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Failed to queue invitation for participant {participant.email} in campaign {cp.campaign.name}: {e}")
                failed_count += 1
        
        db.session.commit()
        
        # Provide feedback to user
        if sent_count > 0:
            flash(f'Successfully queued {sent_count} invitation(s) for {participant.name}. Emails will be sent in the background.', 'success')
        
        if failed_count > 0:
            flash(f'{failed_count} invitation(s) failed to queue for {participant.name}. Please check logs and try again.', 'error')
        
        if sent_count == 0 and failed_count == 0:
            flash(f'All invitations for {participant.name} have already been sent successfully.', 'info')
        
        logger.info(f"Individual invitations queued for participant {participant.name} (ID: {participant_id}): {sent_count} successful, {failed_count} failed")
        
        return redirect(url_for('participants.list_participants'))
        
    except Exception as e:
        logger.error(f"Error sending individual invitation for participant {participant_id}: {e}")
        db.session.rollback()
        flash('Failed to send invitation. Please try again.', 'error')
        return redirect(url_for('participants.list_participants'))


@participant_bp.route('/campaigns/<int:campaign_id>/participants/<int:participant_id>/send-invitation', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def send_campaign_participant_invitation(campaign_id, participant_id):
    """Send email invitation to specific participant for specific campaign"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash(_('Campaign not found.'), 'error')
            return redirect(url_for('participants.list_participants'))
        
        # Get campaign-participant association
        cp = CampaignParticipant.query.filter_by(
            campaign_id=campaign_id,
            participant_id=participant_id,
            business_account_id=current_account.id
        ).first()
        
        if not cp or not cp.participant:
            flash('Participant association not found.', 'error')
            return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))
        
        # Validate campaign status
        if campaign.status != 'active':
            flash(f'Cannot send invitations for {campaign.status} campaign. Campaign must be active.', 'error')
            return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))
        
        # Check if email service is configured for this business account
        if not email_service.is_configured(current_account.id):
            flash(_('The email service is not configured. Please configure your SMTP settings first.'), 'error')
            return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))
        
        # Check if there's already a successful delivery
        existing_delivery = EmailDelivery.query.filter_by(
            campaign_participant_id=cp.id,
            email_type='participant_invitation',
            status='sent'
        ).first()
        
        if existing_delivery:
            flash(f'Invitation for {cp.participant.name} has already been sent successfully.', 'info')
            return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))
        
        try:
            # Create EmailDelivery record for tracking
            email_delivery = EmailDelivery()
            email_delivery.business_account_id = current_account.id
            email_delivery.campaign_id = campaign_id
            email_delivery.participant_id = participant_id
            email_delivery.campaign_participant_id = cp.id
            email_delivery.email_type = 'participant_invitation'
            email_delivery.recipient_email = cp.participant.email
            email_delivery.recipient_name = cp.participant.name
            email_delivery.subject = f"Survey Invitation - {campaign.name}"
            email_delivery.status = 'pending'
            
            db.session.add(email_delivery)
            db.session.flush()  # Get the ID
            
            # Prepare task data
            task_data = {
                'participant_email': cp.participant.email,
                'participant_name': cp.participant.name,
                'campaign_name': campaign.name,
                'survey_token': cp.token,
                'business_account_name': current_account.name,
                'business_account_id': current_account.id,  # Critical for tenant-specific email config
                'campaign_id': campaign.id,
                'participant_id': participant_id,
                'campaign_participant_id': cp.id,
                'email_delivery_id': email_delivery.id
            }
            
            # Add to task queue
            add_email_task('participant_invitation', task_data, priority=2)
            
            # Update campaign participant status
            cp.status = 'invited'
            cp.invited_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Successfully queued invitation for {cp.participant.name}. Email will be sent in the background.', 'success')
            logger.info(f"Individual campaign invitation queued for participant {cp.participant.name} (ID: {participant_id}) in campaign {campaign.name} (ID: {campaign_id})")
            
        except Exception as e:
            logger.error(f"Failed to queue invitation for participant {cp.participant.email} in campaign {campaign.name}: {e}")
            flash(f'Failed to queue invitation for {cp.participant.name}. Please try again.', 'error')
        
        return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))
        
    except Exception as e:
        logger.error(f"Error sending campaign participant invitation for participant {participant_id} in campaign {campaign_id}: {e}")
        db.session.rollback()
        flash('Failed to send invitation. Please try again.', 'error')
        return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))


@participant_bp.route('/<int:participant_id>/invitation-history')
@require_business_auth
@require_permission('manage_participants')
def participant_invitation_history(participant_id):
    """Get invitation history for a specific participant"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account context not found'}), 401
        
        # Get participant (scoped to current business account)
        participant = Participant.query.filter_by(
            id=participant_id,
            business_account_id=current_account.id
        ).first()
        
        if not participant:
            return jsonify({'error': 'Participant not found'}), 404
        
        # Get all email deliveries for this participant
        email_deliveries = EmailDelivery.query.filter_by(
            participant_id=participant_id,
            business_account_id=current_account.id,
            email_type='participant_invitation'
        ).order_by(EmailDelivery.created_at.desc()).all()
        
        # Build history response
        invitation_history = []
        for delivery in email_deliveries:
            history_item = {
                'delivery_id': delivery.id,
                'campaign_name': delivery.campaign.name if delivery.campaign else 'Unknown',
                'campaign_id': delivery.campaign_id,
                'status': delivery.status,
                'subject': delivery.subject,
                'created_at': delivery.created_at.isoformat() if delivery.created_at else None,
                'sent_at': delivery.sent_at.isoformat() if delivery.sent_at else None,
                'retry_count': delivery.retry_count,
                'last_error': delivery.last_error
            }
            invitation_history.append(history_item)
        
        return jsonify({
            'participant_id': participant_id,
            'participant_name': participant.name,
            'participant_email': participant.email,
            'invitation_history': invitation_history,
            'summary': {
                'total_invitations': len(invitation_history),
                'sent': len([h for h in invitation_history if h['status'] == 'sent']),
                'pending': len([h for h in invitation_history if h['status'] in ['pending', 'sending']]),
                'failed': len([h for h in invitation_history if h['status'] in ['failed', 'permanent_failure']])
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting invitation history for participant {participant_id}: {e}")
        return jsonify({'error': 'Failed to get invitation history'}), 500