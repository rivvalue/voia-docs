"""
Phase 3: Participant Management Routes
Provides CRUD operations for campaign participants with proper tenant scoping
"""

from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from business_auth_routes import require_business_auth, require_permission, current_tenant_id, get_current_business_account
from models import Participant, Campaign, BusinessAccount, CampaignParticipant, EmailDelivery, db
from task_queue import add_email_task
from email_service import email_service
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
        participant.source = 'admin_single'  # Track that this was admin-created via single form
        
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
        
        created_count = 0
        error_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 for header row
            try:
                email = row.get('email', '').strip().lower()
                name = row.get('name', '').strip()
                company_name = row.get('company_name', '').strip()
                
                if not email or not name or not company_name:
                    errors.append(f"Row {row_num}: Email, name, and company name are required")
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
def manage_campaign_participants(campaign_id: int):
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
            if assigned_participant_ids:
                available_participants = Participant.query.filter(
                    Participant.business_account_id == current_account.id,
                    ~Participant.id.in_(assigned_participant_ids)
                ).order_by(Participant.name).all()
            else:
                available_participants = Participant.query.filter(
                    Participant.business_account_id == current_account.id
                ).order_by(Participant.name).all()
            
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
                    
                    # Create campaign-participant association (no separate token - uses participant's unified token)
                    association = CampaignParticipant()
                    association.campaign_id = campaign_id
                    association.participant_id = participant_id
                    association.business_account_id = current_account.id
                    association.status = 'invited'  # Campaign-specific status tracking
                    # Note: Using unified token system - no separate campaign tokens needed
                    
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
        return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))


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
        db.session.delete(association)
        db.session.commit()
        
        logger.info(f"Removed participant {participant_name} from campaign {campaign.name} (ID: {campaign_id})")
        flash(f'Removed {participant_name} from campaign {campaign.name}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing participant from campaign {campaign_id}: {e}")
        flash('Error removing participant from campaign.', 'error')
    
    return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))


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
        
        # Check if email service is configured
        if not email_service.is_configured():
            flash('Email service is not configured. Please configure SMTP settings first.', 'error')
            return redirect(url_for('participants.list_participants'))
        
        # Get active campaigns for this participant
        active_campaign_participants = CampaignParticipant.query.filter_by(
            participant_id=participant_id,
            business_account_id=current_account.id
        ).join(Campaign).filter(
            Campaign.status == 'active'
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
            flash('Business account context not found.', 'error')
            return redirect(url_for('participants.manage_campaign_participants', campaign_id=campaign_id))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campaign not found.', 'error')
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
        
        # Check if email service is configured
        if not email_service.is_configured():
            flash('Email service is not configured. Please configure SMTP settings first.', 'error')
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