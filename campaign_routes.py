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
from models import Campaign, CampaignParticipant, Participant, BusinessAccount, EmailDelivery, SurveyResponse, db
from task_queue import add_email_task
from email_service import email_service
from sqlalchemy import func, text

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
        
        # Get participant counts and engagement metrics for each campaign
        campaign_data = []
        for campaign in campaigns:
            participant_count = CampaignParticipant.query.filter_by(
                campaign_id=campaign.id,
                business_account_id=current_account.id
            ).count()
            
            campaign_dict = campaign.to_dict()
            campaign_dict['participant_count'] = participant_count
            campaign_dict['engagement_metrics'] = campaign.get_engagement_metrics()
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
        
        # Check license limits before creation
        from license_service import LicenseService
        if not LicenseService.can_activate_campaign(current_account.id):
            license_info = LicenseService.get_license_info(current_account.id)
            flash(f'Cannot create campaign. Your {license_info["license_type"]} license allows {license_info["campaigns_limit"]} campaigns per year and you have already used {license_info["campaigns_used"]} campaigns. Please contact support to upgrade your license.', 'error')
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
        
        # Audit log campaign creation
        try:
            from audit_utils import queue_audit_log
            queue_audit_log(
                business_account_id=current_account.id,
                action_type='campaign_created',
                resource_type='campaign',
                resource_id=campaign.id,
                resource_name=campaign.name,
                details={
                    'start_date': start_date_obj.isoformat(),
                    'end_date': end_date_obj.isoformat(),
                    'status': 'draft'
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to audit campaign creation: {audit_error}")
        
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
        
        # Get campaign data with engagement metrics
        campaign_data = campaign.to_dict()
        campaign_data['engagement_metrics'] = campaign.get_engagement_metrics()
        
        return render_template('campaigns/view.html',
                             campaign=campaign_data,
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
        
        # Check license limits before activation using new LicenseService
        from license_service import LicenseService
        if not LicenseService.can_activate_campaign(current_account.id):
            # Get license info for detailed error message
            license_info = LicenseService.get_license_info(current_account.id)
            flash(f'Cannot activate campaign. Your {license_info["license_type"]} license allows {license_info["campaigns_limit"]} campaigns per license period and you have already used {license_info["campaigns_used"]} campaigns. Please contact support to upgrade your license.', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Activate campaign
        campaign.status = 'active'
        
        # Note: License tracking now uses time-scoped counting via can_activate_campaign() method
        
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
        
        # Audit log campaign activation
        try:
            from audit_utils import queue_audit_log
            queue_audit_log(
                business_account_id=current_account.id,
                action_type='campaign_activated',
                resource_type='campaign',
                resource_id=campaign.id,
                resource_name=campaign.name,
                details={
                    'participants_with_tokens': token_success_count,
                    'token_generation_failures': token_error_count,
                    'previous_status': 'ready'
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to audit campaign activation: {audit_error}")
        
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
        
        # Audit log campaign completion
        try:
            from audit_utils import queue_audit_log
            queue_audit_log(
                business_account_id=current_account.id,
                action_type='campaign_completed',
                resource_type='campaign',
                resource_id=campaign.id,
                resource_name=campaign.name,
                details={
                    'previous_status': 'active',
                    'kpi_snapshot_generated': True
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to audit campaign completion: {audit_error}")
        
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
                    'business_account_id': current_account.id,  # Critical for tenant-specific email config
                    'campaign_id': campaign.id,
                    'participant_id': cp.participant_id,
                    'campaign_participant_id': cp.id,
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


@campaign_bp.route('/<int:campaign_id>/survey-config')
@require_business_auth
@require_permission('manage_participants')
def survey_config(campaign_id):
    """Display campaign survey configuration form"""
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
        
        # Check if campaign can be modified
        if campaign.status in ['active', 'completed']:
            flash(f'Survey configuration cannot be modified for {campaign.status} campaigns.', 'warning')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        return render_template('campaigns/survey_config.html',
                             campaign=campaign.to_dict(),
                             business_account=current_account.to_dict())
        
    except Exception as e:
        logger.error(f"Survey config display error for campaign {campaign_id}: {e}")
        flash('Error loading survey configuration.', 'error')
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))


@campaign_bp.route('/<int:campaign_id>/survey-config/save', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def save_survey_config(campaign_id):
    """Save campaign survey configuration"""
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
        
        # Check if campaign can be modified
        if campaign.status in ['active', 'completed']:
            flash(f'Survey configuration cannot be modified for {campaign.status} campaigns.', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Product Focus section
        campaign.product_description = request.form.get('product_description', '').strip() or None
        campaign.target_clients_description = request.form.get('target_clients_description', '').strip() or None
        
        # Survey Goals (multi-select checkboxes)
        survey_goals = request.form.getlist('survey_goals')
        campaign.survey_goals = survey_goals if survey_goals else None
        
        # Survey Controls - validate numeric ranges
        try:
            max_questions = int(request.form.get('max_questions', 8))
            if not (3 <= max_questions <= 15):
                flash('Max questions must be between 3 and 15.', 'error')
                return redirect(url_for('campaigns.survey_config', campaign_id=campaign_id))
            campaign.max_questions = max_questions
            
            max_duration = int(request.form.get('max_duration_seconds', 120))
            if not (60 <= max_duration <= 300):
                flash('Max duration must be between 60 and 300 seconds.', 'error')
                return redirect(url_for('campaigns.survey_config', campaign_id=campaign_id))
            campaign.max_duration_seconds = max_duration
            
            max_follow_ups = int(request.form.get('max_follow_ups_per_topic', 2))
            if not (1 <= max_follow_ups <= 3):
                flash('Max follow-ups per topic must be between 1 and 3.', 'error')
                return redirect(url_for('campaigns.survey_config', campaign_id=campaign_id))
            campaign.max_follow_ups_per_topic = max_follow_ups
            
        except ValueError:
            flash('Invalid numeric values in survey controls.', 'error')
            return redirect(url_for('campaigns.survey_config', campaign_id=campaign_id))
        
        # Topic Prioritization - handle multi-select lists
        prioritized_topics = [topic.strip() for topic in request.form.getlist('prioritized_topics') if topic.strip()]
        campaign.prioritized_topics = prioritized_topics if prioritized_topics else None
        
        optional_topics = [topic.strip() for topic in request.form.getlist('optional_topics') if topic.strip()]
        campaign.optional_topics = optional_topics if optional_topics else None
        
        # Customization section
        campaign.custom_end_message = request.form.get('custom_end_message', '').strip() or None
        campaign.custom_system_prompt = request.form.get('custom_system_prompt', '').strip() or None
        
        # Save changes
        db.session.commit()
        
        # Audit log configuration update
        try:
            from audit_utils import queue_audit_log
            queue_audit_log(
                business_account_id=current_account.id,
                action_type='campaign_survey_config_updated',
                resource_type='campaign',
                resource_id=campaign.id,
                resource_name=campaign.name,
                details={
                    'has_product_description': bool(campaign.product_description),
                    'has_target_clients': bool(campaign.target_clients_description),
                    'survey_goals_count': len(campaign.survey_goals) if campaign.survey_goals else 0,
                    'max_questions': campaign.max_questions,
                    'max_duration_seconds': campaign.max_duration_seconds,
                    'prioritized_topics_count': len(campaign.prioritized_topics) if campaign.prioritized_topics else 0,
                    'has_custom_end_message': bool(campaign.custom_end_message),
                    'has_custom_system_prompt': bool(campaign.custom_system_prompt)
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to audit survey config update: {audit_error}")
        
        logger.info(f"Survey configuration updated for campaign '{campaign.name}' (ID: {campaign_id}) by business account {current_account.id}")
        flash('Survey configuration saved successfully!', 'success')
        
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
    except Exception as e:
        logger.error(f"Error saving survey config for campaign {campaign_id}: {e}")
        db.session.rollback()
        flash('Failed to save survey configuration. Please try again.', 'error')
        return redirect(url_for('campaigns.survey_config', campaign_id=campaign_id))


@campaign_bp.route('/<int:campaign_id>/responses')
@require_business_auth
@require_permission('manage_participants')
def campaign_responses(campaign_id):
    """List all participant responses within a specific campaign"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            if request.is_json:
                return jsonify({'error': 'Business account context not found'}), 401
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            if request.is_json:
                return jsonify({'error': 'Campaign not found'}), 404
            flash('Campaign not found.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        search_query = request.args.get('search', '').strip()
        
        # Build query for survey responses in this campaign
        # Join with campaign participants to get participant details
        response_query = SurveyResponse.query.join(
            CampaignParticipant, SurveyResponse.campaign_participant_id == CampaignParticipant.id
        ).join(
            Participant, CampaignParticipant.participant_id == Participant.id
        ).filter(
            SurveyResponse.campaign_id == campaign_id,
            CampaignParticipant.business_account_id == current_account.id
        )
        
        # Apply search filter if provided
        if search_query:
            # Search in participant name, email, company name, and conversation history
            search_filter = db.or_(
                Participant.name.ilike(f'%{search_query}%'),
                Participant.email.ilike(f'%{search_query}%'),
                Participant.company_name.ilike(f'%{search_query}%'),
                SurveyResponse.conversation_history.ilike(f'%{search_query}%')
            )
            response_query = response_query.filter(search_filter)
        
        # Add ordering by creation date (newest first)
        response_query = response_query.order_by(desc(SurveyResponse.created_at))
        
        # Execute pagination
        pagination = response_query.paginate(
            page=page,
            per_page=per_page,
            error_out=False,
            max_per_page=100
        )
        
        # Prepare response data
        responses_data = []
        for response in pagination.items:
            response_dict = response.to_dict()
            # Add participant details
            if response.campaign_participant and response.campaign_participant.participant:
                participant = response.campaign_participant.participant
                response_dict.update({
                    'participant_name': participant.name,
                    'participant_email': participant.email,
                    'participant_company': participant.company_name,
                    'completion_status': response.campaign_participant.status,
                    'completed_at': response.campaign_participant.completed_at.isoformat() if response.campaign_participant.completed_at else None
                })
            responses_data.append(response_dict)
        
        if request.is_json:
            return jsonify({
                'campaign': campaign.to_dict(),
                'responses': responses_data,
                'pagination': {
                    'page': pagination.page,
                    'pages': pagination.pages,
                    'per_page': pagination.per_page,
                    'total': pagination.total,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                },
                'search_query': search_query
            })
        
        # For HTML requests, render template
        return render_template('campaigns/responses_list.html',
                             campaign=campaign.to_dict(),
                             responses=responses_data,
                             pagination=pagination,
                             search_query=search_query,
                             business_account=current_account.to_dict())
        
    except Exception as e:
        logger.error(f"Error loading campaign responses for campaign {campaign_id}: {e}")
        if request.is_json:
            return jsonify({'error': 'Failed to load campaign responses'}), 500
        flash('Error loading campaign responses.', 'error')
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))


@campaign_bp.route('/<int:campaign_id>/responses/<int:participant_id>')
@require_business_auth
@require_permission('manage_participants')
def individual_response(campaign_id, participant_id):
    """View individual participant response with full conversational transcript"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            if request.is_json:
                return jsonify({'error': 'Business account context not found'}), 401
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            if request.is_json:
                return jsonify({'error': 'Campaign not found'}), 404
            flash('Campaign not found.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Get participant (scoped to current business account)
        participant = Participant.query.filter_by(
            id=participant_id,
            business_account_id=current_account.id
        ).first()
        
        if not participant:
            if request.is_json:
                return jsonify({'error': 'Participant not found'}), 404
            flash('Participant not found.', 'error')
            return redirect(url_for('campaigns.campaign_responses', campaign_id=campaign_id))
        
        # Get the survey response for this participant in this campaign
        survey_response = SurveyResponse.query.join(
            CampaignParticipant, SurveyResponse.campaign_participant_id == CampaignParticipant.id
        ).filter(
            SurveyResponse.campaign_id == campaign_id,
            CampaignParticipant.participant_id == participant_id,
            CampaignParticipant.business_account_id == current_account.id
        ).first()
        
        if not survey_response:
            if request.is_json:
                return jsonify({'error': 'Survey response not found for this participant'}), 404
            flash('Survey response not found for this participant.', 'error')
            return redirect(url_for('campaigns.campaign_responses', campaign_id=campaign_id))
        
        # Get search highlighting parameter
        search_query = request.args.get('search', '').strip()
        
        # Prepare comprehensive response data
        response_data = survey_response.to_dict()
        response_data.update({
            'participant': participant.to_dict(),
            'campaign': campaign.to_dict()
        })
        
        # Parse conversation history for chat display
        conversation_history = []
        if survey_response.conversation_history:
            try:
                import json
                conversation_history = json.loads(survey_response.conversation_history)
                
                # Apply search highlighting if search query provided
                if search_query:
                    for msg in conversation_history:
                        if 'content' in msg and search_query.lower() in msg['content'].lower():
                            # Simple highlighting by wrapping matches in <mark> tags
                            content = msg['content']
                            highlighted = content.replace(
                                search_query, f'<mark>{search_query}</mark>'
                            )
                            msg['highlighted_content'] = highlighted
                        else:
                            msg['highlighted_content'] = msg.get('content', '')
                            
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse conversation_history for response {survey_response.id}")
                conversation_history = []
        
        response_data['parsed_conversation_history'] = conversation_history
        response_data['search_query'] = search_query
        
        if request.is_json:
            return jsonify(response_data)
        
        # For HTML requests, render detailed response template
        return render_template('campaigns/individual_response.html',
                             response=response_data,
                             participant=participant.to_dict(),
                             campaign=campaign.to_dict(),
                             conversation_history=conversation_history,
                             search_query=search_query,
                             business_account=current_account.to_dict())
        
    except Exception as e:
        logger.error(f"Error loading individual response for participant {participant_id} in campaign {campaign_id}: {e}")
        if request.is_json:
            return jsonify({'error': 'Failed to load individual response'}), 500
        flash('Error loading individual response.', 'error')
        return redirect(url_for('campaigns.campaign_responses', campaign_id=campaign_id))