"""
Campaign Management Routes (Phase 3 Completion)
Dedicated routes for campaign lifecycle management
"""

import logging
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import desc

from business_auth_routes import require_business_auth, require_permission, get_current_business_account
from models import Campaign, CampaignParticipant, Participant, BusinessAccount, db

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
        campaign = Campaign(
            name=name,
            description=description or None,
            start_date=start_date_obj,
            end_date=end_date_obj,
            business_account_id=current_account.id,
            status='draft'  # Initial status
        )
        
        db.session.add(campaign)
        db.session.commit()
        
        logger.info(f"Campaign '{name}' created for business account {current_account.id}")
        flash(f'Campaign "{name}" created successfully!', 'success')
        
        return redirect(url_for('campaigns.list_campaigns'))
        
    except Exception as e:
        logger.error(f"Campaign creation error: {e}")
        db.session.rollback()
        flash('Failed to create campaign. Please try again.', 'error')
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