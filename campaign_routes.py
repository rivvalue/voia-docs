"""
Campaign Management Routes (Phase 3 Completion)
Dedicated routes for campaign lifecycle management
"""

import logging
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
        
        # Validate dates
        try:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
            
            if start_datetime >= end_datetime:
                flash('End date must be after start date.', 'error')
                return render_template('campaigns/create.html',
                                     business_account=current_account.to_dict())
            
        except ValueError:
            flash('Invalid date format.', 'error')
            return render_template('campaigns/create.html',
                                 business_account=current_account.to_dict())
        
        # Create campaign
        campaign = Campaign(
            name=name,
            description=description or None,
            start_date=start_datetime,
            end_date=end_datetime,
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