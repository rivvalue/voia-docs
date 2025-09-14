"""
Campaign Management Routes (Phase 3 Completion)
Dedicated routes for campaign lifecycle management with email invitation functionality
"""

import logging
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import desc

from business_auth_routes import require_business_auth, require_permission, get_current_business_account
from models import Campaign, CampaignParticipant, Participant, BusinessAccount, EmailDelivery, db
from task_queue import add_email_task
from email_service import email_service

# Create blueprint for campaign management
campaign_bp = Blueprint('campaigns', __name__, url_prefix='/business/campaigns')

logger = logging.getLogger(__name__)


@campaign_bp.route('/')
@require_business_auth
@require_permission('manage_participants')
def list_campaigns():
    """List all campaigns for current business account"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get all campaigns for this business account
        campaigns = Campaign.query.filter_by(
            business_account_id=current_account.id
        ).order_by(desc(Campaign.created_at)).all()
        
        # Get participant counts for each campaign
        campaign_data = []
        for campaign in campaigns:
            participant_count = CampaignParticipant.query.filter_by(
                campaign_id=campaign.id,
                business_account_id=current_account.id
            ).count()
            
            campaign_dict = campaign.to_dict()
            campaign_dict['participant_count'] = participant_count
            campaign_data.append(campaign_dict)
        
        return render_template('campaigns/list.html',
                             campaigns=campaign_data,
                             business_account=current_account.to_dict())
        
    except Exception as e:
        logger.error(f"Campaign list error: {e}")
        flash('Error loading campaigns.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@campaign_bp.route('/create', methods=['GET', 'POST'])
@require_business_auth
@require_permission('manage_participants')
def create_campaign():
    """Create new campaign"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        if request.method == 'GET':
            # Show create form
            return render_template('campaigns/create.html',
                                 business_account=current_account.to_dict())
        
        # Handle form submission
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        start_date = request.form.get('start_date', '').strip()
        end_date = request.form.get('end_date', '').strip()
        
        # Validate required fields
        if not name or not start_date or not end_date:
            flash('Campaign name, start date, and end date are required.', 'error')
            return render_template('campaigns/create.html',
                                 business_account=current_account.to_dict())
        
        # Validate dates and convert to date objects
        try:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
            
            if start_datetime >= end_datetime:
                flash('End date must be after start date.', 'error')
                return render_template('campaigns/create.html',
                                     business_account=current_account.to_dict())
            
            # Convert to date objects for consistency
            start_date_obj = start_datetime.date()
            end_date_obj = end_datetime.date()
            
        except ValueError:
            flash('Invalid date format.', 'error')
            return render_template('campaigns/create.html',
                                 business_account=current_account.to_dict())
        
        # Create campaign
        campaign = Campaign()
        campaign.name = name
        campaign.description = description or None
        campaign.start_date = start_date_obj
        campaign.end_date = end_date_obj
        campaign.business_account_id = current_account.id
        campaign.status = 'draft'  # Initial status
        
        db.session.add(campaign)
        db.session.commit()
        
        logger.info(f"Campaign '{name}' created for business account {current_account.id}")
        flash(f'Campaign "{name}" created successfully!', 'success')
        
        return redirect(url_for('campaigns.list_campaigns'))
        
    except Exception as e:
        logger.error(f"Campaign creation error: {e}")
        db.session.rollback()
        flash('Failed to create campaign. Please try again.', 'error')
        current_account = get_current_business_account()
        return render_template('campaigns/create.html',
                             business_account=current_account.to_dict() if current_account else {})


@campaign_bp.route('/<int:campaign_id>')
@require_business_auth
@require_permission('manage_participants')
def view_campaign(campaign_id):
    """View campaign details"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campaign not found.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Get campaign participants
        campaign_participants = CampaignParticipant.query.filter_by(
            campaign_id=campaign_id,
            business_account_id=current_account.id
        ).all()
        
        participants_data = []
        for cp in campaign_participants:
            if cp.participant:
                participant_data = cp.participant.to_dict()
                participant_data.update({
                    'association_id': cp.id,
                    'token': cp.token,  # Add campaign-participant token
                    'status': cp.status,
                    'invited_at': cp.invited_at.isoformat() if cp.invited_at else None,
                    'completed_at': cp.completed_at.isoformat() if cp.completed_at else None
                })
                participants_data.append(participant_data)
        
        return render_template('campaigns/view.html',
                             campaign=campaign.to_dict(),
                             participants=participants_data,
                             business_account=current_account.to_dict())
        
    except Exception as e:
        logger.error(f"Campaign view error: {e}")
        flash('Error loading campaign details.', 'error')
        return redirect(url_for('campaigns.list_campaigns'))


@campaign_bp.route('/<int:campaign_id>/mark-ready', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def mark_ready(campaign_id):
    """Mark campaign as ready for activation"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campaign not found.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Validate campaign can be marked ready
        if campaign.status != 'draft':
            flash(f'Campaign must be in draft status to mark as ready. Current status: {campaign.status}', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Check if campaign has basic requirements
        if not campaign.name or not campaign.description:
            flash('Campaign must have name and description to be marked ready.', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Check if campaign has participants
        participant_count = CampaignParticipant.query.filter_by(
            campaign_id=campaign_id,
            business_account_id=current_account.id
        ).count()
        
        if participant_count == 0:
            flash('Campaign must have at least one participant to be marked ready.', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Mark as ready
        campaign.status = 'ready'
        db.session.commit()
        
        logger.info(f"Campaign '{campaign.name}' (ID: {campaign_id}) marked as ready by business account {current_account.id}")
        flash(f'Campaign "{campaign.name}" is now ready for activation!', 'success')
        
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
    except Exception as e:
        logger.error(f"Error marking campaign as ready: {e}")
        db.session.rollback()
        flash('Failed to mark campaign as ready. Please try again.', 'error')
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))


@campaign_bp.route('/<int:campaign_id>/activate', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def activate_campaign(campaign_id):
    """Activate campaign (enforce single active campaign constraint)"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campaign not found.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Validate campaign can be activated
        if campaign.status != 'ready':
            flash(f'Campaign must be ready to activate. Current status: {campaign.status}', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Enforce single active campaign constraint
        existing_active = Campaign.query.filter_by(
            business_account_id=current_account.id,
            status='active'
        ).first()
        
        if existing_active:
            flash(f'Cannot activate campaign. Another campaign "{existing_active.name}" is already active. Only one campaign can be active at a time.', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Check date constraints using consistent date handling
        today = datetime.now().date()
        if campaign.start_date > today:
            flash(f'Cannot activate campaign before start date ({campaign.start_date}). Please wait until the start date.', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        if campaign.end_date < today:
            flash(f'Cannot activate campaign past end date ({campaign.end_date}). Please update the campaign dates.', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Activate campaign
        campaign.status = 'active'
        
        # Get all campaign-participant associations for token generation
        campaign_participants = CampaignParticipant.query.filter_by(
            campaign_id=campaign_id,
            business_account_id=current_account.id
        ).all()
        
        # Generate tokens for all associations that need them
        token_success_count = 0
        token_error_count = 0
        batch_size = 100
        total_participants = len(campaign_participants)
        
        logger.info(f"Starting token generation for {total_participants} campaign participants")
        
        # Process participants in batches
        for i in range(0, total_participants, batch_size):
            batch = campaign_participants[i:i + batch_size]
            
            for cp in batch:
                try:
                    # Generate association token if missing
                    if not cp.token:
                        cp.token = str(uuid.uuid4())
                        logger.debug(f"Generated token for association {cp.id}: {cp.token}")
                    
                    # Update participant status and timestamps
                    if cp.status == 'pending':
                        cp.status = 'invited'
                        cp.invited_at = datetime.utcnow()
                    
                    token_success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error generating token for association {cp.id}: {e}")
                    token_error_count += 1
                    # Continue processing other participants
                    continue
            
            # Commit batch to avoid long-running transactions
            try:
                db.session.commit()
                logger.debug(f"Committed batch {i//batch_size + 1} of {(total_participants + batch_size - 1)//batch_size}")
            except Exception as e:
                logger.error(f"Error committing batch {i//batch_size + 1}: {e}")
                db.session.rollback()
                token_error_count += len(batch)
                continue
        
        # Log activation summary with token generation results
        logger.info(f"Campaign '{campaign.name}' (ID: {campaign_id}) activated by business account {current_account.id}")
        logger.info(f"Token generation results: {token_success_count} successful, {token_error_count} failed")
        
        # Create detailed flash message with token generation summary
        if token_error_count == 0:
            flash(f'Campaign "{campaign.name}" is now active! All {token_success_count} participant tokens generated successfully.', 'success')
        elif token_success_count > 0:
            flash(f'Campaign "{campaign.name}" is now active! {token_success_count} participant tokens generated, {token_error_count} failed. Check logs for details.', 'warning')
        else:
            flash(f'Campaign "{campaign.name}" is active but token generation failed for all {token_error_count} participants. Check logs and retry.', 'error')
        
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
    except Exception as e:
        logger.error(f"Error activating campaign: {e}")
        db.session.rollback()
        flash('Failed to activate campaign. Please try again.', 'error')
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))


@campaign_bp.route('/<int:campaign_id>/complete', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def complete_campaign(campaign_id):
    """Complete campaign"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campaign not found.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Validate campaign can be completed
        if campaign.status not in ['active']:
            flash(f'Only active campaigns can be completed. Current status: {campaign.status}', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Complete campaign and generate KPI snapshot
        campaign.close_campaign()
        
        db.session.commit()
        
        logger.info(f"Campaign '{campaign.name}' (ID: {campaign_id}) completed by business account {current_account.id}")
        flash(f'Campaign "{campaign.name}" has been completed!', 'success')
        
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
    except Exception as e:
        logger.error(f"Error completing campaign: {e}")
        db.session.rollback()
        flash('Failed to complete campaign. Please try again.', 'error')
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))


# ==============================================================================
# PARTICIPANT INVITATION ROUTES
# ==============================================================================

@campaign_bp.route('/<int:campaign_id>/send-invitations', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def send_bulk_invitations(campaign_id):
    """Send bulk email invitations to all campaign participants"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campaign not found.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Validate campaign status - only send invitations for active campaigns
        if campaign.status != 'active':
            flash(f'Cannot send invitations for {campaign.status} campaign. Campaign must be active.', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Check if email service is configured
        if not email_service.is_configured():
            flash('Email service is not configured. Please configure SMTP settings first.', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Get all campaign participants that haven't been invited yet
        campaign_participants = CampaignParticipant.query.filter_by(
            campaign_id=campaign_id,
            business_account_id=current_account.id
        ).all()
        
        if not campaign_participants:
            flash('No participants found for this campaign.', 'warning')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Filter participants - only send to those who haven't been invited or failed previous attempts
        invitable_participants = []
        for cp in campaign_participants:
            if cp.participant and cp.status in ['pending', 'invited']:
                # Check if there's already a successful delivery
                existing_delivery = EmailDelivery.query.filter_by(
                    campaign_participant_id=cp.id,
                    email_type='participant_invitation',
                    status='sent'
                ).first()
                
                if not existing_delivery:
                    invitable_participants.append(cp)
        
        if not invitable_participants:
            flash('All participants have already been invited successfully.', 'info')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Create email delivery records and add to task queue
        successful_queued = 0
        failed_queued = 0
        
        for cp in invitable_participants:
            try:
                # Create EmailDelivery record for tracking
                email_delivery = EmailDelivery()
                email_delivery.business_account_id = current_account.id
                email_delivery.campaign_id = campaign_id
                email_delivery.participant_id = cp.participant_id
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
                    'survey_token': cp.token,  # Use campaign-participant token
                    'business_account_name': current_account.name,
                    'email_delivery_id': email_delivery.id
                }
                
                # Add to task queue
                add_email_task('participant_invitation', task_data, priority=2)
                
                # Update campaign participant status
                cp.status = 'invited'
                cp.invited_at = datetime.utcnow()
                
                successful_queued += 1
                
            except Exception as e:
                logger.error(f"Failed to queue invitation for participant {cp.participant.email}: {e}")
                failed_queued += 1
                
        db.session.commit()
        
        # Provide feedback to user
        if successful_queued > 0:
            flash(f'Successfully queued {successful_queued} invitation(s) for sending. Emails will be sent in the background.', 'success')
        
        if failed_queued > 0:
            flash(f'{failed_queued} invitation(s) failed to queue. Please check logs and try again.', 'error')
        
        logger.info(f"Bulk invitations queued for campaign '{campaign.name}' (ID: {campaign_id}): {successful_queued} successful, {failed_queued} failed")
        
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
    except Exception as e:
        logger.error(f"Error sending bulk invitations for campaign {campaign_id}: {e}")
        db.session.rollback()
        flash('Failed to send invitations. Please try again.', 'error')
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))


@campaign_bp.route('/<int:campaign_id>/invitation-status')
@require_business_auth
@require_permission('manage_participants')
def invitation_status(campaign_id):
    """Get invitation status for campaign participants"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account context not found'}), 401
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Get all email deliveries for this campaign
        email_deliveries = EmailDelivery.query.filter_by(
            campaign_id=campaign_id,
            business_account_id=current_account.id,
            email_type='participant_invitation'
        ).all()
        
        # Get campaign participants
        campaign_participants = CampaignParticipant.query.filter_by(
            campaign_id=campaign_id,
            business_account_id=current_account.id
        ).all()
        
        # Build status response
        participant_status = []
        for cp in campaign_participants:
            if cp.participant:
                # Find latest email delivery for this participant
                latest_delivery = None
                for ed in email_deliveries:
                    if ed.campaign_participant_id == cp.id:
                        if not latest_delivery or ed.created_at > latest_delivery.created_at:
                            latest_delivery = ed
                
                status_info = {
                    'participant_id': cp.participant_id,
                    'participant_name': cp.participant.name,
                    'participant_email': cp.participant.email,
                    'campaign_status': cp.status,
                    'invited_at': cp.invited_at.isoformat() if cp.invited_at else None,
                    'email_status': latest_delivery.status if latest_delivery else 'not_sent',
                    'email_sent_at': latest_delivery.sent_at.isoformat() if latest_delivery and latest_delivery.sent_at else None,
                    'email_error': latest_delivery.last_error if latest_delivery else None,
                    'retry_count': latest_delivery.retry_count if latest_delivery else 0
                }
                participant_status.append(status_info)
        
        return jsonify({
            'campaign_id': campaign_id,
            'campaign_name': campaign.name,
            'participants': participant_status,
            'summary': {
                'total': len(participant_status),
                'sent': len([p for p in participant_status if p['email_status'] == 'sent']),
                'pending': len([p for p in participant_status if p['email_status'] in ['pending', 'sending']]),
                'failed': len([p for p in participant_status if p['email_status'] in ['failed', 'permanent_failure']])
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting invitation status for campaign {campaign_id}: {e}")
        return jsonify({'error': 'Failed to get invitation status'}), 500


@campaign_bp.route('/<int:campaign_id>/resend-failed-invitations', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def resend_failed_invitations(campaign_id):
    """Resend invitations for participants with failed email deliveries"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campaign not found.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Check if email service is configured
        if not email_service.is_configured():
            flash('Email service is not configured. Please configure SMTP settings first.', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Find failed email deliveries that can be retried
        failed_deliveries = EmailDelivery.query.filter_by(
            campaign_id=campaign_id,
            business_account_id=current_account.id,
            email_type='participant_invitation',
            status='failed'
        ).filter(
            EmailDelivery.retry_count < EmailDelivery.max_retries
        ).all()
        
        if not failed_deliveries:
            flash('No failed invitations found that can be retried.', 'info')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Resend failed invitations
        resent_count = 0
        for delivery in failed_deliveries:
            try:
                cp = delivery.campaign_participant
                if cp and cp.participant:
                    # Prepare task data
                    task_data = {
                        'participant_email': cp.participant.email,
                        'participant_name': cp.participant.name,
                        'campaign_name': campaign.name,
                        'survey_token': cp.token,
                        'business_account_name': current_account.name,
                        'email_delivery_id': delivery.id
                    }
                    
                    # Reset delivery status for retry
                    delivery.status = 'pending'
                    delivery.last_error = None
                    
                    # Add to task queue
                    add_email_task('participant_invitation', task_data, priority=1)  # High priority for retries
                    resent_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to queue retry for delivery {delivery.id}: {e}")
        
        db.session.commit()
        
        if resent_count > 0:
            flash(f'Successfully queued {resent_count} failed invitation(s) for retry.', 'success')
        else:
            flash('No invitations were queued for retry.', 'warning')
        
        logger.info(f"Resent {resent_count} failed invitations for campaign '{campaign.name}' (ID: {campaign_id})")
        
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
    except Exception as e:
        logger.error(f"Error resending failed invitations for campaign {campaign_id}: {e}")
        db.session.rollback()
        flash('Failed to resend invitations. Please try again.', 'error')
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))