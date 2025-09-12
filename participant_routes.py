"""
Phase 3: Participant Management Routes
Provides CRUD operations for campaign participants with proper tenant scoping
"""

from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from business_auth_routes import require_business_auth, require_permission, current_tenant_id, get_current_business_account
from models import Participant, Campaign, BusinessAccount, CampaignParticipant, db
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
        
        return render_template('participants/create.html',
                             business_account=current_account.to_dict() if current_account else {})
    
    # Handle form submission
    try:
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Extract form data
        email = request.form.get('email', '').strip().lower()
        name = request.form.get('name', '').strip()
        company_name = request.form.get('company_name', '').strip()
        
        # Validate required fields
        if not email or not name:
            flash('Email and name are required.', 'error')
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
        participant = Participant(
            business_account_id=current_account.id,
            email=email,
            name=name,
            company_name=company_name if company_name else None,
            source='admin_single'  # Track that this was admin-created via single form
        )
        
        # Generate unified token for seamless UX
        participant.generate_token()
        
        # Set appropriate status for business context
        participant.set_appropriate_status_for_context(is_trial=False)
        
        db.session.add(participant)
        db.session.commit()
        
        account_name = current_account.name if current_account and hasattr(current_account, 'name') else 'Unknown'
        logger.info(f"Created participant {email} (Business Account: {account_name})")
        flash(f'Participant {name} created successfully. You can now assign them to campaigns.', 'success')
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
        
        return render_template('participants/upload.html',
                             business_account=current_account.to_dict() if current_account else {})
    
    # Handle CSV upload
    try:
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash('Business account context not found.', 'error')
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
                participant = Participant(
                    business_account_id=current_account.id,
                    email=email,
                    name=name,
                    company_name=company_name if company_name else None,
                    source='admin_bulk'  # Track that this was admin-created via bulk upload
                )
                
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
        
        # Check for existing campaign associations (prevent FK constraint violations)
        existing_associations = CampaignParticipant.query.filter_by(participant_id=participant_id).all()
        
        if existing_associations:
            # Show which campaigns they're associated with
            campaign_names = [assoc.campaign.name for assoc in existing_associations]
            campaigns_text = ', '.join(campaign_names)
            flash(f'Cannot delete participant {participant.name} - they are associated with campaigns: {campaigns_text}. Remove from campaigns first.', 'error')
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


# ==============================================================================
# CAMPAIGN-PARTICIPANT ASSOCIATION MANAGEMENT ROUTES
# ==============================================================================

@participant_bp.route('/campaigns/<int:campaign_id>/participants', methods=['GET', 'POST'])
@require_business_auth
@require_permission('manage_participants')
def manage_campaign_participants(campaign_id):
    """Manage participants for a specific campaign"""
    
    try:
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campaign not found.', 'error')
            return redirect(url_for('participants.list_participants'))
        
        if request.method == 'GET':
            # Get current campaign participants
            campaign_participants = CampaignParticipant.query.filter_by(
                campaign_id=campaign_id,
                business_account_id=current_account.id
            ).all()
            
            # Get all available participants not in this campaign
            assigned_participant_ids = [cp.participant_id for cp in campaign_participants]
            available_participants = Participant.query.filter(
                Participant.business_account_id == current_account.id,
                ~Participant.id.in_(assigned_participant_ids) if assigned_participant_ids else True
            ).order_by(Participant.name).all()
            
            # Prepare data for template
            current_participants = []
            for cp in campaign_participants:
                participant_data = cp.participant.to_dict() if cp.participant else {}
                participant_data.update({
                    'association_id': cp.id,
                    'token': cp.token,
                    'status': cp.status,
                    'invited_at': cp.invited_at.isoformat() if cp.invited_at else None,
                    'started_at': cp.started_at.isoformat() if cp.started_at else None,
                    'completed_at': cp.completed_at.isoformat() if cp.completed_at else None
                })
                current_participants.append(participant_data)
            
            return render_template('participants/campaign_participants.html',
                                 campaign=campaign.to_dict(),
                                 current_participants=current_participants,
                                 available_participants=[p.to_dict() for p in available_participants],
                                 business_account=current_account.to_dict())
        
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
                    
                    # Create campaign-participant association with token
                    association = CampaignParticipant(
                        campaign_id=campaign_id,
                        participant_id=participant_id,
                        business_account_id=current_account.id,
                        token=str(uuid.uuid4()),
                        status='pending'
                    )
                    
                    db.session.add(association)
                    added_count += 1
                    
                except ValueError:
                    continue
            
            db.session.commit()
            
            if added_count > 0:
                flash(f'Added {added_count} participant(s) to campaign {campaign.name}.', 'success')
                logger.info(f"Added {added_count} participants to campaign {campaign.name} (ID: {campaign_id})")
            else:
                flash('No new participants were added.', 'warning')
            
            return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error managing campaign participants for campaign {campaign_id}: {e}")
        flash('Error managing campaign participants.', 'error')
        return redirect(url_for('participants.list_participants'))


@participant_bp.route('/campaigns/<int:campaign_id>/participants/<int:association_id>/remove', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def remove_campaign_participant(campaign_id, association_id):
    """Remove participant from campaign"""
    
    try:
        current_account = get_current_business_account()
        if not current_account or not current_account.id:
            flash('Business account context not found.', 'error')
            return redirect(url_for('participants.list_participants'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campaign not found.', 'error')
            return redirect(url_for('participants.list_participants'))
        
        # Validate campaign status - can only remove participants if campaign is not active
        if campaign.status == 'active':
            flash(f'Cannot remove participants from active campaign. Please wait until campaign is completed.', 'error')
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
        db.session.delete(association)
        db.session.commit()
        
        logger.info(f"Removed participant {participant_name} from campaign {campaign.name} (ID: {campaign_id})")
        flash(f'Removed {participant_name} from campaign {campaign.name}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing participant from campaign {campaign_id}: {e}")
        flash('Error removing participant from campaign.', 'error')
    
    return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))