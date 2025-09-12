"""
Phase 3: Participant Management Routes
Provides CRUD operations for campaign participants with proper tenant scoping
"""

from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from business_auth_routes import require_business_auth, require_permission, current_tenant_id, get_current_business_account
from models import Participant, Campaign, BusinessAccount, db
from datetime import datetime
import logging
import csv
import io
import uuid

# Create blueprint for participant management
participant_bp = Blueprint('participants', __name__, url_prefix='/business/participants')

logger = logging.getLogger(__name__)


@participant_bp.route('/')
@require_business_auth
@require_permission('manage_participants')
def list_participants():
    """List all participants for current business account"""
    
    try:
        # Get current business account context
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get participants scoped to current business account
        participants = Participant.query.filter_by(
            business_account_id=current_account.id
        ).order_by(Participant.created_at.desc()).all()
        
        # Get campaigns for dropdown (scoped to current business account)
        campaigns = Campaign.query.filter_by(
            business_account_id=current_account.id
        ).order_by(Campaign.name).all()
        
        # Prepare participant data
        participant_data = []
        for participant in participants:
            data = participant.to_dict()
            participant_data.append(data)
        
        return render_template('participants/list.html',
                             participants=participant_data,
                             campaigns=[c.to_dict() if c else {} for c in campaigns],
                             business_account=current_account.to_dict() if current_account else {})
        
    except Exception as e:
        logger.error(f"Error listing participants: {e}")
        flash('Error loading participants.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@participant_bp.route('/create', methods=['GET', 'POST'])
@require_business_auth
@require_permission('manage_participants')
def create_participant():
    """Create new participant"""
    
    if request.method == 'GET':
        # Show create form
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.login'))
            
        campaigns = Campaign.query.filter_by(
            business_account_id=current_account.id
        ).order_by(Campaign.name).all()
        
        return render_template('participants/create.html',
                             campaigns=[c.to_dict() if c else {} for c in campaigns],
                             business_account=current_account.to_dict() if current_account else {})
    
    # Handle form submission
    try:
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Extract form data
        campaign_id = request.form.get('campaign_id')
        email = request.form.get('email', '').strip().lower()
        name = request.form.get('name', '').strip()
        company_name = request.form.get('company_name', '').strip()
        
        # Validate required fields
        if not campaign_id or not email or not name:
            flash('Campaign, email, and name are required.', 'error')
            return redirect(url_for('participants.create_participant'))
        
        # Validate campaign belongs to current business account
        campaign = Campaign.query.filter_by(
            id=campaign_id, 
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Invalid campaign selected.', 'error')
            return redirect(url_for('participants.create_participant'))
        
        # Check for duplicate participant (email + campaign combination)
        existing = Participant.query.filter_by(
            business_account_id=current_account.id,
            campaign_id=campaign_id,
            email=email
        ).first()
        
        if existing:
            flash(f'Participant {email} already exists for campaign {campaign.name}.', 'error')
            return redirect(url_for('participants.create_participant'))
        
        # Create participant
        participant = Participant(
            business_account_id=current_account.id,
            campaign_id=campaign_id,
            email=email,
            name=name,
            company_name=company_name if company_name else None,
            status='invited',
            invited_at=datetime.utcnow()
        )
        
        # Generate token
        participant.generate_token()
        
        db.session.add(participant)
        db.session.commit()
        
        account_name = current_account.name if current_account and hasattr(current_account, 'name') else 'Unknown'
        campaign_name = campaign.name if campaign and hasattr(campaign, 'name') else 'Unknown'
        logger.info(f"Created participant {email} for campaign {campaign_name} (Business Account: {account_name})")
        flash(f'Participant {name} created successfully for campaign {campaign_name}.', 'success')
        return redirect(url_for('participants.list_participants'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating participant: {e}")
        flash('Error creating participant.', 'error')
        return redirect(url_for('participants.create_participant'))


@participant_bp.route('/upload', methods=['GET', 'POST'])
@require_business_auth
@require_permission('manage_participants')
def upload_participants():
    """Bulk upload participants via CSV"""
    
    if request.method == 'GET':
        # Show upload form
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.login'))
            
        campaigns = Campaign.query.filter_by(
            business_account_id=current_account.id
        ).order_by(Campaign.name).all()
        
        return render_template('participants/upload.html',
                             campaigns=[c.to_dict() if c else {} for c in campaigns],
                             business_account=current_account.to_dict() if current_account else {})
    
    # Handle CSV upload
    try:
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.login'))
            
        campaign_id = request.form.get('campaign_id')
        
        # Validate campaign
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Invalid campaign selected.', 'error')
            return redirect(url_for('participants.upload_participants'))
        
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
        
        created_count = 0
        error_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 for header row
            try:
                email = row.get('email', '').strip().lower()
                name = row.get('name', '').strip()
                company_name = row.get('company_name', '').strip()
                
                if not email or not name:
                    errors.append(f"Row {row_num}: Email and name are required")
                    error_count += 1
                    continue
                
                # Check for duplicate
                existing = Participant.query.filter_by(
                    business_account_id=current_account.id,
                    campaign_id=campaign_id,
                    email=email
                ).first()
                
                if existing:
                    errors.append(f"Row {row_num}: Participant {email} already exists")
                    error_count += 1
                    continue
                
                # Create participant
                participant = Participant(
                    business_account_id=current_account.id,
                    campaign_id=campaign_id,
                    email=email,
                    name=name,
                    company_name=company_name if company_name else None,
                    status='invited',
                    invited_at=datetime.utcnow()
                )
                
                participant.generate_token()
                db.session.add(participant)
                created_count += 1
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                error_count += 1
        
        db.session.commit()
        
        # Show results
        if created_count > 0:
            campaign_name = campaign.name if campaign and hasattr(campaign, 'name') else 'Unknown'
            flash(f'Successfully created {created_count} participants for campaign {campaign_name}.', 'success')
        
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
            flash('Business account context not found.', 'error')
            return redirect(url_for('participants.list_participants'))
        
        # Get participant (scoped to current business account)
        participant = Participant.query.filter_by(
            id=participant_id,
            business_account_id=current_account.id
        ).first()
        
        if not participant:
            flash('Participant not found.', 'error')
            return redirect(url_for('participants.list_participants'))
        
        participant_name = participant.name
        db.session.delete(participant)
        db.session.commit()
        
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
            flash('Business account context not found.', 'error')
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
        
        account_name = current_account.name if current_account and hasattr(current_account, 'name') else 'Unknown'
        participant_name = participant.name if participant and hasattr(participant, 'name') else 'Unknown'
        logger.info(f"Regenerated token for participant {participant_name} (ID: {participant_id}, Business Account: {account_name})")
        flash(f'New token generated for {participant_name}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error regenerating token for participant {participant_id}: {e}")
        flash('Error regenerating token.', 'error')
    
    return redirect(url_for('participants.list_participants'))