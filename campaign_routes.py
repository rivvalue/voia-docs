"""
Campaign Management Routes (Phase 3 Completion)
Dedicated routes for campaign lifecycle management with email invitation functionality
"""

import logging
import os
import uuid
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

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
    """List all campaigns for current business account - OPTIMIZED to fix N+1 query problem"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Contexte du compte entreprise introuvable.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get all campaigns for this business account
        campaigns = Campaign.query.filter_by(
            business_account_id=current_account.id
        ).order_by(desc(Campaign.created_at)).all()
        
        # OPTIMIZATION: Get all metrics in 3 batch queries instead of N+1 queries
        campaign_ids = [c.id for c in campaigns]
        
        # Batch query 1: Get participant counts for all campaigns
        participant_counts = dict(
            db.session.query(
                CampaignParticipant.campaign_id,
                func.count(CampaignParticipant.id)
            ).filter(
                CampaignParticipant.campaign_id.in_(campaign_ids),
                CampaignParticipant.business_account_id == current_account.id
            ).group_by(CampaignParticipant.campaign_id).all()
        ) if campaign_ids else {}
        
        # Batch query 2: Get invitation counts for all campaigns
        invitation_counts = dict(
            db.session.query(
                EmailDelivery.campaign_id,
                func.count(EmailDelivery.id)
            ).filter(
                EmailDelivery.campaign_id.in_(campaign_ids),
                EmailDelivery.status == 'sent',
                EmailDelivery.email_type == 'participant_invitation'
            ).group_by(EmailDelivery.campaign_id).all()
        ) if campaign_ids else {}
        
        # Batch query 3: Get survey completion counts for all campaigns
        survey_counts = dict(
            db.session.query(
                SurveyResponse.campaign_id,
                func.count(SurveyResponse.id)
            ).filter(
                SurveyResponse.campaign_id.in_(campaign_ids)
            ).group_by(SurveyResponse.campaign_id).all()
        ) if campaign_ids else {}
        
        # Build campaign data with pre-loaded metrics (no additional queries)
        campaign_data = []
        for campaign in campaigns:
            # Get metrics from pre-loaded data FIRST
            participant_count = participant_counts.get(campaign.id, 0)
            invitations_sent = invitation_counts.get(campaign.id, 0)
            surveys_completed = survey_counts.get(campaign.id, 0)
            
            # Pass pre-computed response_count to avoid N+1 query
            campaign_dict = campaign.to_dict(response_count=surveys_completed)
            
            # Calculate rates
            participation_rate = None
            if participant_count > 0:
                participation_rate = round((surveys_completed / participant_count) * 100, 1)
            
            email_success_rate = None
            if invitations_sent > 0:
                email_success_rate = round((surveys_completed / invitations_sent) * 100, 1)
            
            campaign_dict['participant_count'] = participant_count
            campaign_dict['engagement_metrics'] = {
                'invitations_sent': invitations_sent,
                'surveys_completed': surveys_completed,
                'total_participants': participant_count,
                'participation_rate': participation_rate,
                'email_success_rate': email_success_rate
            }
            campaign_data.append(campaign_dict)
        
        logger.info(f"📊 Campaigns list loaded: {len(campaigns)} campaigns, optimized query (no N+1)")
        
        return render_template('campaigns/list.html',
                             campaigns=campaign_data,
                             business_account=current_account.to_dict())
        
    except Exception as e:
        logger.error(f"Campaign list error: {e}")
        flash('Erreur lors du chargement des campagnes.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@campaign_bp.route('/create', methods=['GET', 'POST'])
@require_business_auth
@require_permission('manage_participants')
def create_campaign():
    """Create new campaign"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Contexte du compte entreprise introuvable.', 'error')
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
        anonymize_responses = 'anonymize_responses' in request.form
        
        # Validate required fields
        if not name or not start_date or not end_date:
            flash('Le nom de la campagne, la date de début et la date de fin sont requis.', 'error')
            return render_template('campaigns/create.html',
                                 business_account=current_account.to_dict())
        
        # Validate dates and convert to date objects
        try:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
            
            if start_datetime >= end_datetime:
                flash('La date de fin doit être postérieure à la date de début.', 'error')
                return render_template('campaigns/create.html',
                                     business_account=current_account.to_dict())
            
            # Convert to date objects for consistency
            start_date_obj = start_datetime.date()
            end_date_obj = end_datetime.date()
            
        except ValueError:
            flash('Format de date invalide.', 'error')
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
        campaign.anonymize_responses = anonymize_responses
        
        # Language configuration
        language_code = request.form.get('language_code', 'en').strip().lower()
        if language_code not in ['en', 'fr']:
            language_code = 'en'  # Safe fallback
        campaign.language_code = language_code
        
        # Reminder settings with validation
        reminder_enabled = 'reminder_enabled' in request.form
        try:
            reminder_delay_days = int(request.form.get('reminder_delay_days', 7))
            # Validate delay is in allowed range
            if reminder_delay_days not in [3, 5, 7, 10, 14]:
                reminder_delay_days = 7  # Safe fallback
        except (ValueError, TypeError):
            reminder_delay_days = 7  # Safe fallback
        
        campaign.reminder_enabled = reminder_enabled
        campaign.reminder_delay_days = reminder_delay_days
        
        # Custom email content
        use_custom_email_content = request.form.get('use_custom_email_content') == 'on'
        campaign.use_custom_email_content = use_custom_email_content
        
        if use_custom_email_content:
            campaign.custom_subject_template = request.form.get('custom_subject_template', '').strip() or None
            campaign.custom_intro_message = request.form.get('custom_intro_message', '').strip() or None
            campaign.custom_cta_text = request.form.get('custom_cta_text', '').strip() or None
            campaign.custom_closing_message = request.form.get('custom_closing_message', '').strip() or None
            campaign.custom_footer_note = request.form.get('custom_footer_note', '').strip() or None
        
        # Validate custom email content if enabled
        content_errors = campaign.validate_custom_email_content()
        if content_errors:
            for error in content_errors:
                flash(error, 'error')
            return render_template('campaigns/create.html',
                                 business_account=current_account.to_dict())
        
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
                    'status': 'draft',
                    'anonymize_responses': anonymize_responses
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
        flash('Échec de la création de la campagne. Veuillez réessayer.', 'error')
        current_account = get_current_business_account()
        return render_template('campaigns/create.html',
                             business_account=current_account.to_dict() if current_account else {})


@campaign_bp.route('/<int:campaign_id>')
@require_business_auth
def view_campaign(campaign_id):
    """View campaign details (read-only access for all authenticated users)"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Contexte du compte entreprise introuvable.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campagne introuvable.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Get participant summary stats (optimized - no full list loading)
        from sqlalchemy import func, case
        
        participant_stats = db.session.query(
            func.count(CampaignParticipant.id).label('total'),
            func.count(case((CampaignParticipant.status == 'completed', 1))).label('completed'),
            func.count(case((CampaignParticipant.status == 'started', 1))).label('started'),
            func.count(case((CampaignParticipant.status == 'invited', 1))).label('invited'),
            func.count(case((CampaignParticipant.status == 'pending', 1))).label('pending')
        ).filter(
            CampaignParticipant.campaign_id == campaign_id,
            CampaignParticipant.business_account_id == current_account.id
        ).first()
        
        # Build stats dictionary
        campaign_participant_stats = {
            'total': participant_stats.total if participant_stats else 0,
            'completed': participant_stats.completed if participant_stats else 0,
            'started': participant_stats.started if participant_stats else 0,
            'invited': participant_stats.invited if participant_stats else 0,
            'pending': participant_stats.pending if participant_stats else 0
        }
        
        # Get campaign data with engagement metrics
        campaign_data = campaign.to_dict()
        campaign_data['engagement_metrics'] = campaign.get_engagement_metrics()
        
        # Fetch campaign configuration data for readonly view (active/completed campaigns)
        campaign_config = None
        if campaign.status in ['active', 'completed']:
            from models import EmailConfiguration
            email_config = EmailConfiguration.get_for_business_account(current_account.id)
            
            campaign_config = {
                # Overview section
                'language_code': campaign.language_code,
                'anonymize_responses': campaign.anonymize_responses,
                'created_at': campaign.created_at,
                'completed_at': campaign.completed_at if hasattr(campaign, 'completed_at') else None,
                
                # Schedule & Audience section
                'reminder_enabled': campaign.reminder_enabled,
                'reminder_delay_days': campaign.reminder_delay_days,
                'start_date': campaign.start_date,
                'end_date': campaign.end_date,
                
                # Survey Experience section
                'product_description': campaign.product_description,
                'target_clients_description': campaign.target_clients_description,
                'survey_goals': campaign.survey_goals,
                'max_questions': campaign.max_questions,
                'max_duration_seconds': campaign.max_duration_seconds,
                'max_follow_ups_per_topic': campaign.max_follow_ups_per_topic,
                'prioritized_topics': campaign.prioritized_topics,
                'optional_topics': campaign.optional_topics,
                'custom_end_message': campaign.custom_end_message,
                'custom_system_prompt': campaign.custom_system_prompt,
                
                # Communications section
                'use_custom_email_content': campaign.use_custom_email_content,
                'custom_subject_template': campaign.custom_subject_template if campaign.use_custom_email_content else None,
                'custom_intro_message': campaign.custom_intro_message if campaign.use_custom_email_content else None,
                'custom_cta_text': campaign.custom_cta_text if campaign.use_custom_email_content else None,
                'custom_closing_message': campaign.custom_closing_message if campaign.use_custom_email_content else None,
                'custom_footer_note': campaign.custom_footer_note if campaign.use_custom_email_content else None,
                'email_provider': email_config.email_provider if email_config else 'voila_managed',
                'sender_name': email_config.sender_name if email_config else 'VOÏA Team',
                'sender_email': email_config.sender_email if email_config else None,
            }
        
        return render_template('campaigns/view.html',
                             campaign=campaign_data,
                             participant_stats=campaign_participant_stats,
                             business_account=current_account.to_dict(),
                             campaign_config=campaign_config)
        
    except Exception as e:
        logger.error(f"Campaign view error: {e}")
        flash('Erreur lors du chargement des détails de la campagne.', 'error')
        return redirect(url_for('campaigns.list_campaigns'))


@campaign_bp.route('/<int:campaign_id>/edit', methods=['GET', 'POST'])
@require_business_auth
@require_permission('manage_participants')
def edit_draft_campaign(campaign_id):
    """Edit draft campaign details (name, dates, description)"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Contexte du compte entreprise introuvable.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campagne introuvable.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Validate: Only draft campaigns can be edited
        if campaign.status != 'draft':
            flash(f'Only draft campaigns can be edited. This campaign is {campaign.status}.', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        if request.method == 'GET':
            # Show edit form
            return render_template('campaigns/edit.html',
                                 campaign=campaign.to_dict(),
                                 business_account=current_account.to_dict())
        
        # Handle form submission (POST)
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        start_date = request.form.get('start_date', '').strip()
        end_date = request.form.get('end_date', '').strip()
        
        # Validate required fields
        if not name or not start_date or not end_date:
            flash('Le nom de la campagne, la date de début et la date de fin sont requis.', 'error')
            return render_template('campaigns/edit.html',
                                 campaign=campaign.to_dict(),
                                 business_account=current_account.to_dict())
        
        # Validate dates
        try:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
            
            if start_datetime >= end_datetime:
                flash('La date de fin doit être postérieure à la date de début.', 'error')
                return render_template('campaigns/edit.html',
                                     campaign=campaign.to_dict(),
                                     business_account=current_account.to_dict())
            
            start_date_obj = start_datetime.date()
            end_date_obj = end_datetime.date()
            
        except ValueError:
            flash('Format de date invalide.', 'error')
            return render_template('campaigns/edit.html',
                                 campaign=campaign.to_dict(),
                                 business_account=current_account.to_dict())
        
        # Check if dates changed and participants already invited
        dates_changed = (campaign.start_date != start_date_obj or campaign.end_date != end_date_obj)
        invited_count = 0
        
        if dates_changed:
            invited_count = CampaignParticipant.query.filter_by(
                campaign_id=campaign_id,
                business_account_id=current_account.id,
                status='invited'
            ).count()
            
            if invited_count > 0:
                flash(f'Warning: {invited_count} participants have already been invited with the previous dates. '
                      f'Consider re-sending invitations with updated information.', 'warning')
        
        # Track changes for audit log
        changes = {}
        if campaign.name != name:
            changes['name'] = {'old': campaign.name, 'new': name}
        if campaign.description != description:
            changes['description'] = {'old': campaign.description, 'new': description}
        if campaign.start_date != start_date_obj:
            changes['start_date'] = {'old': campaign.start_date.isoformat(), 'new': start_date_obj.isoformat()}
        if campaign.end_date != end_date_obj:
            changes['end_date'] = {'old': campaign.end_date.isoformat(), 'new': end_date_obj.isoformat()}
        
        # Reminder settings with validation
        reminder_enabled = 'reminder_enabled' in request.form
        try:
            reminder_delay_days = int(request.form.get('reminder_delay_days', 7))
            # Validate delay is in allowed range
            if reminder_delay_days not in [3, 5, 7, 10, 14]:
                reminder_delay_days = 7  # Safe fallback
        except (ValueError, TypeError):
            reminder_delay_days = 7  # Safe fallback
        
        if campaign.reminder_enabled != reminder_enabled:
            changes['reminder_enabled'] = {'old': campaign.reminder_enabled, 'new': reminder_enabled}
        if campaign.reminder_delay_days != reminder_delay_days:
            changes['reminder_delay_days'] = {'old': campaign.reminder_delay_days, 'new': reminder_delay_days}
        
        # Language configuration
        language_code = request.form.get('language_code', 'en').strip().lower()
        if language_code not in ['en', 'fr']:
            language_code = 'en'  # Safe fallback
        
        if campaign.language_code != language_code:
            changes['language_code'] = {'old': campaign.language_code, 'new': language_code}
        
        # Update campaign
        campaign.name = name
        campaign.description = description or None
        campaign.start_date = start_date_obj
        campaign.end_date = end_date_obj
        campaign.reminder_enabled = reminder_enabled
        campaign.reminder_delay_days = reminder_delay_days
        campaign.language_code = language_code
        
        # Custom email content
        use_custom_email_content = request.form.get('use_custom_email_content') == 'on'
        if campaign.use_custom_email_content != use_custom_email_content:
            changes['use_custom_email_content'] = {'old': campaign.use_custom_email_content, 'new': use_custom_email_content}
        
        campaign.use_custom_email_content = use_custom_email_content
        
        if use_custom_email_content:
            custom_subject = request.form.get('custom_subject_template', '').strip() or None
            custom_intro = request.form.get('custom_intro_message', '').strip() or None
            custom_cta = request.form.get('custom_cta_text', '').strip() or None
            custom_closing = request.form.get('custom_closing_message', '').strip() or None
            custom_footer = request.form.get('custom_footer_note', '').strip() or None
            
            # Track changes
            if campaign.custom_subject_template != custom_subject:
                changes['custom_subject_template'] = {'old': campaign.custom_subject_template, 'new': custom_subject}
            if campaign.custom_intro_message != custom_intro:
                changes['custom_intro_message'] = {'old': campaign.custom_intro_message, 'new': custom_intro}
            if campaign.custom_cta_text != custom_cta:
                changes['custom_cta_text'] = {'old': campaign.custom_cta_text, 'new': custom_cta}
            if campaign.custom_closing_message != custom_closing:
                changes['custom_closing_message'] = {'old': campaign.custom_closing_message, 'new': custom_closing}
            if campaign.custom_footer_note != custom_footer:
                changes['custom_footer_note'] = {'old': campaign.custom_footer_note, 'new': custom_footer}
            
            campaign.custom_subject_template = custom_subject
            campaign.custom_intro_message = custom_intro
            campaign.custom_cta_text = custom_cta
            campaign.custom_closing_message = custom_closing
            campaign.custom_footer_note = custom_footer
        else:
            # Clear custom content if disabled
            campaign.custom_subject_template = None
            campaign.custom_intro_message = None
            campaign.custom_cta_text = None
            campaign.custom_closing_message = None
            campaign.custom_footer_note = None
        
        # Validate custom email content if enabled
        content_errors = campaign.validate_custom_email_content()
        if content_errors:
            db.session.rollback()
            for error in content_errors:
                flash(error, 'error')
            return redirect(url_for('campaigns.edit_draft_campaign', campaign_id=campaign_id))
        
        db.session.commit()
        
        # Audit log if changes were made
        if changes:
            try:
                from audit_utils import queue_audit_log
                queue_audit_log(
                    business_account_id=current_account.id,
                    action_type='campaign_updated',
                    resource_type='campaign',
                    resource_id=campaign.id,
                    resource_name=campaign.name,
                    details={
                        'changes': changes,
                        'invited_participants': invited_count if dates_changed else 0
                    }
                )
            except Exception as audit_error:
                logger.error(f"Failed to audit campaign edit: {audit_error}")
        
        logger.info(f"Campaign '{campaign.name}' (ID: {campaign_id}) edited by business account {current_account.id}")
        flash(f'Campaign "{campaign.name}" updated successfully!', 'success')
        
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
    except Exception as e:
        logger.error(f"Campaign edit error: {e}")
        db.session.rollback()
        flash('Échec de la mise à jour de la campagne. Veuillez réessayer.', 'error')
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))


@campaign_bp.route('/<int:campaign_id>/delete', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def delete_draft_campaign(campaign_id):
    """Delete draft campaign and cascade associations"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Contexte du compte entreprise introuvable.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campagne introuvable.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Validate: Only draft campaigns can be deleted
        if campaign.status != 'draft':
            flash(f'Only draft campaigns can be deleted. This campaign is {campaign.status}.', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Get counts for audit trail
        participant_count = CampaignParticipant.query.filter_by(
            campaign_id=campaign_id,
            business_account_id=current_account.id
        ).count()
        
        response_count = SurveyResponse.query.filter_by(
            campaign_id=campaign_id
        ).count()
        
        # Store campaign info for audit log (before deletion)
        campaign_name = campaign.name
        campaign_start = campaign.start_date.isoformat()
        campaign_end = campaign.end_date.isoformat()
        
        # Delete cascade: Remove campaign_participants associations first
        CampaignParticipant.query.filter_by(
            campaign_id=campaign_id,
            business_account_id=current_account.id
        ).delete()
        
        # Delete the campaign
        db.session.delete(campaign)
        db.session.commit()
        
        # Audit log deletion
        try:
            from audit_utils import queue_audit_log
            queue_audit_log(
                business_account_id=current_account.id,
                action_type='campaign_deleted',
                resource_type='campaign',
                resource_id=campaign_id,
                resource_name=campaign_name,
                details={
                    'campaign_name': campaign_name,
                    'start_date': campaign_start,
                    'end_date': campaign_end,
                    'participant_count': participant_count,
                    'response_count': response_count,
                    'deleted_by': session.get('business_user_email', 'unknown')
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to audit campaign deletion: {audit_error}")
        
        logger.info(f"Campaign '{campaign_name}' (ID: {campaign_id}) deleted by business account {current_account.id}")
        flash(f'Campaign "{campaign_name}" has been deleted.', 'success')
        
        return redirect(url_for('campaigns.list_campaigns'))
        
    except Exception as e:
        logger.error(f"Campaign deletion error: {e}")
        db.session.rollback()
        flash('Échec de la suppression de la campagne. Veuillez réessayer.', 'error')
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))


@campaign_bp.route('/<int:campaign_id>/mark-ready', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def mark_ready(campaign_id):
    """Mark campaign as ready for activation"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Contexte du compte entreprise introuvable.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campagne introuvable.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Validate campaign can be marked ready
        if campaign.status != 'draft':
            flash(f'Campaign must be in draft status to mark as ready. Current status: {campaign.status}', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Check if campaign has basic requirements
        if not campaign.name or not campaign.description:
            flash('La campagne doit comporter un nom et une description pour être marquée comme prête.', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Check if campaign has participants
        participant_count = CampaignParticipant.query.filter_by(
            campaign_id=campaign_id,
            business_account_id=current_account.id
        ).count()
        
        if participant_count == 0:
            flash('La campagne doit comporter au moins un participant pour être marquée comme prête.', 'error')
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
        flash('Échec du marquage de la campagne comme prête. Veuillez réessayer.', 'error')
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))


@campaign_bp.route('/<int:campaign_id>/activate', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def activate_campaign(campaign_id):
    """Activate campaign (enforce single active campaign constraint)"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Contexte du compte entreprise introuvable.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campagne introuvable.', 'error')
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
        try:
            if not LicenseService.can_activate_campaign(current_account.id):
                # Get license info for detailed error message
                try:
                    license_info = LicenseService.get_license_info(current_account.id)
                    flash(f'Cannot activate campaign. Your {license_info["license_type"]} license allows {license_info["campaigns_limit"]} campaigns per license period and you have already used {license_info["campaigns_used"]} campaigns. Please contact support to upgrade your license.', 'error')
                except Exception as info_error:
                    logger.error(f"Failed to get license info for error message: {info_error}")
                    flash('Cannot activate campaign. License limit reached. Please contact support to upgrade your license.', 'error')
                return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        except Exception as license_error:
            logger.error(f"License check failed during campaign activation: {license_error}")
            flash('Cannot activate campaign due to a license system error. Please contact support for assistance.', 'error')
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
        flash('Échec de l’activation de la campagne. Veuillez réessayer.', 'error')
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))


@campaign_bp.route('/<int:campaign_id>/complete', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def complete_campaign(campaign_id):
    """Complete campaign"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Contexte du compte entreprise introuvable.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campagne introuvable.', 'error')
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
        flash('Échec de la finalisation de la campagne. Veuillez réessayer.', 'error')
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
            flash('Contexte du compte entreprise introuvable.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campagne introuvable.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Validate campaign status - only send invitations for active campaigns
        if campaign.status != 'active':
            flash(f'Cannot send invitations for {campaign.status} campaign. Campaign must be active.', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Check if email service is configured for this business account
        if not email_service.is_configured(current_account.id):
            flash('Le service de messagerie n’est pas configuré. Veuillez d’abord configurer les paramètres SMTP.', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Get all campaign participants that haven't been invited yet
        campaign_participants = CampaignParticipant.query.filter_by(
            campaign_id=campaign_id,
            business_account_id=current_account.id
        ).all()
        
        if not campaign_participants:
            flash('Aucun participant trouvé pour cette campagne.', 'warning')
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
            flash('Tous les participants ont déjà été invités avec succès.', 'info')
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
        flash('Échec de l’envoi des invitations. Veuillez réessayer.', 'error')
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
        
        # Get campaign participants with eager loading to prevent N+1 queries
        campaign_participants = CampaignParticipant.query.filter_by(
            campaign_id=campaign_id,
            business_account_id=current_account.id
        ).options(joinedload(CampaignParticipant.participant)).all()
        
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
            flash('Contexte du compte entreprise introuvable.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campagne introuvable.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Check if email service is configured for this business account
        if not email_service.is_configured(current_account.id):
            flash('Le service de messagerie n’est pas configuré. Veuillez d’abord configurer les paramètres SMTP.', 'error')
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
            flash('Aucune invitation échouée ne peut être renvoyée.', 'info')
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
            flash('Aucune invitation n’a été mise en file d’attente pour un nouvel envoi.', 'warning')
        
        logger.info(f"Resent {resent_count} failed invitations for campaign '{campaign.name}' (ID: {campaign_id})")
        
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
    except Exception as e:
        logger.error(f"Error resending failed invitations for campaign {campaign_id}: {e}")
        db.session.rollback()
        flash('Échec du renvoi des invitations. Veuillez réessayer.', 'error')
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))


@campaign_bp.route('/<int:campaign_id>/survey-config')
@require_business_auth
@require_permission('manage_participants')
def survey_config(campaign_id):
    """Display campaign survey configuration form"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Contexte du compte entreprise introuvable.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campagne introuvable.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Import industry topic hints config for industry verticalization (Phase 2)
        from industry_topic_hints_config import get_available_industries, INDUSTRY_TOPIC_HINTS
        import json
        
        # Prepare business account defaults for inheritance preview
        business_defaults = {
            'topics': {
                'prioritized': current_account.prioritized_topics or [],
                'optional': current_account.optional_topics or []
            },
            'controls': {
                'max_questions': current_account.max_questions or 8,
                'max_duration_seconds': current_account.max_duration_seconds or 120,
                'max_follow_ups_per_topic': current_account.max_follow_ups_per_topic or 2
            },
            'product_focus': {
                'product_description': current_account.product_description or '',
                'target_clients_description': current_account.target_clients_description or ''
            }
        }
        
        # Allow viewing for all statuses - template handles read-only mode for active/completed
        return render_template('campaigns/survey_config.html',
                             campaign=campaign.to_dict(),
                             business_account=current_account.to_dict(),
                             business_defaults=business_defaults,
                             available_industries=get_available_industries(),
                             industry_topic_hints_json=json.dumps(INDUSTRY_TOPIC_HINTS),
                             ENABLE_PROMPT_PREVIEW=os.getenv('ENABLE_PROMPT_PREVIEW') == 'true')
        
    except Exception as e:
        logger.error(f"Survey config display error for campaign {campaign_id}: {e}")
        flash('Erreur lors du chargement de la configuration de l’enquête.', 'error')
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))


@campaign_bp.route('/<int:campaign_id>/survey-config/save', methods=['POST'])
@require_business_auth
@require_permission('manage_participants')
def save_survey_config(campaign_id):
    """Save campaign survey configuration"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Contexte du compte entreprise introuvable.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            flash('Campagne introuvable.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Check if campaign can be modified
        if campaign.status in ['active', 'completed']:
            flash(f'Survey configuration cannot be modified for {campaign.status} campaigns.', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Process inheritance flags (convert form values to boolean)
        campaign.use_business_product_focus = request.form.get('use_business_product_focus') == 'true'
        campaign.use_business_controls = request.form.get('use_business_controls') == 'true'
        campaign.use_business_topics = request.form.get('use_business_topics') == 'true'
        
        # Product Focus section - only save if not inheriting
        if campaign.use_business_product_focus:
            # Reset overrides when inheriting
            campaign.product_description = None
            campaign.target_clients_description = None
        else:
            # Save campaign-specific customizations
            campaign.product_description = request.form.get('product_description', '').strip() or None
            campaign.target_clients_description = request.form.get('target_clients_description', '').strip() or None
        
        # Industry Override (Phase 2: Topic Hints verticalization)
        campaign.industry = request.form.get('industry', '').strip() or None
        
        # Survey Controls section - only save if not inheriting
        if campaign.use_business_controls:
            # Reset overrides when inheriting
            campaign.max_questions = None
            campaign.max_duration_seconds = None
            campaign.max_follow_ups_per_topic = None
        else:
            # Save campaign-specific customizations
            try:
                max_questions = int(request.form.get('max_questions', 8))
                if not (3 <= max_questions <= 15):
                    flash('Le nombre maximal de questions doit être compris entre 3 et 15.', 'error')
                    return redirect(url_for('campaigns.survey_config', campaign_id=campaign_id))
                campaign.max_questions = max_questions
                
                max_duration = int(request.form.get('max_duration_seconds', 120))
                if not (60 <= max_duration <= 300):
                    flash('La durée maximale doit être comprise entre 60 et 300 secondes.', 'error')
                    return redirect(url_for('campaigns.survey_config', campaign_id=campaign_id))
                campaign.max_duration_seconds = max_duration
                
                max_follow_ups = int(request.form.get('max_follow_ups_per_topic', 2))
                if not (1 <= max_follow_ups <= 3):
                    flash('Le nombre maximal de relances par sujet doit être compris entre 1 et 3.', 'error')
                    return redirect(url_for('campaigns.survey_config', campaign_id=campaign_id))
                campaign.max_follow_ups_per_topic = max_follow_ups
                
            except ValueError:
                flash('Valeurs numériques invalides dans les contrôles de l’enquête.', 'error')
                return redirect(url_for('campaigns.survey_config', campaign_id=campaign_id))
        
        # Topic Prioritization section - only save if not inheriting
        if campaign.use_business_topics:
            # Reset overrides when inheriting
            campaign.prioritized_topics = None
            campaign.optional_topics = None
        else:
            # Save campaign-specific customizations
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
        flash('Configuration de l’enquête enregistrée avec succès !', 'success')
        
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
    except Exception as e:
        logger.error(f"Error saving survey config for campaign {campaign_id}: {e}")
        db.session.rollback()
        flash('Échec de l’enregistrement de la configuration de l’enquête. Veuillez réessayer.', 'error')
        return redirect(url_for('campaigns.survey_config', campaign_id=campaign_id))


@campaign_bp.route('/<int:campaign_id>/email-preview')
@require_business_auth
@require_permission('manage_participants')
def email_preview(campaign_id):
    """Preview campaign email without sending"""
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
        
        # Get email type from query parameter (default: invitation)
        email_type = request.args.get('email_type', 'invitation')
        
        # Validate email type
        valid_types = ['invitation', 'reminder_primary', 'reminder_midpoint']
        if email_type not in valid_types:
            return jsonify({'error': f'Invalid email type. Must be one of: {", ".join(valid_types)}'}), 400
        
        # Generate email preview using email service
        result = email_service.preview_campaign_email(campaign, email_type=email_type)
        
        if not result['success']:
            logger.error(f"Email preview generation failed: {result.get('error')}")
            return jsonify({'error': 'Failed to generate email preview'}), 500
        
        # Return HTML preview
        return result['html_body'], 200, {'Content-Type': 'text/html; charset=utf-8'}
        
    except Exception as e:
        logger.error(f"Error generating email preview for campaign {campaign_id}: {e}")
        return jsonify({'error': 'Failed to generate email preview'}), 500


@campaign_bp.route('/<int:campaign_id>/responses')
@require_business_auth
# @require_permission('manage_participants')  # Temporarily disabled for testing
def campaign_responses(campaign_id):
    """List all participant responses within a specific campaign"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            if request.is_json:
                return jsonify({'error': 'Business account context not found'}), 401
            flash('Contexte du compte entreprise introuvable.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            if request.is_json:
                return jsonify({'error': 'Campaign not found'}), 404
            flash('Campagne introuvable.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        search_query = request.args.get('search', '').strip()
        
        # Build query for survey responses in this campaign
        # Join with campaign participants to get participant details
        response_query = SurveyResponse.query.options(
            joinedload(SurveyResponse.campaign_participant).joinedload(CampaignParticipant.participant)
        ).join(
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
                    'participant_id': participant.id,
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
        flash('Erreur lors du chargement des réponses de la campagne.', 'error')
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
            flash('Contexte du compte entreprise introuvable.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get campaign (scoped to current business account)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            if request.is_json:
                return jsonify({'error': 'Campaign not found'}), 404
            flash('Campagne introuvable.', 'error')
            return redirect(url_for('campaigns.list_campaigns'))
        
        # Get the survey response for this participant in this campaign through campaign_participants
        survey_response = SurveyResponse.query.join(
            CampaignParticipant, SurveyResponse.campaign_participant_id == CampaignParticipant.id
        ).join(
            Participant, CampaignParticipant.participant_id == Participant.id
        ).filter(
            SurveyResponse.campaign_id == campaign_id,
            CampaignParticipant.participant_id == participant_id,
            CampaignParticipant.business_account_id == current_account.id
        ).first()
        
        if not survey_response:
            if request.is_json:
                return jsonify({'error': 'Survey response not found for this participant'}), 404
            flash('Réponse à l’enquête introuvable pour ce participant.', 'error')
            return redirect(url_for('campaigns.campaign_responses', campaign_id=campaign_id))
        
        # Get participant through the campaign_participants relationship  
        campaign_participant = CampaignParticipant.query.filter_by(
            participant_id=participant_id,
            campaign_id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign_participant:
            if request.is_json:
                return jsonify({'error': 'Participant not found in this campaign'}), 404
            flash('Participant introuvable dans cette campagne.', 'error')
            return redirect(url_for('campaigns.campaign_responses', campaign_id=campaign_id))
        
        participant = campaign_participant.participant
        
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
        flash('Erreur lors du chargement de la réponse individuelle.', 'error')
        return redirect(url_for('campaigns.campaign_responses', campaign_id=campaign_id))


@campaign_bp.route('/api/campaigns/<int:campaign_id>/export', methods=['POST'])
@require_business_auth
@require_permission('export_data')
def export_campaign_async(campaign_id):
    """Queue async campaign export job (unified pattern with bulk operations)"""
    try:
        from models import BulkOperationJob
        from task_queue import task_queue
        import uuid
        
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account not found'}), 401
        
        # Get campaign and verify access
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Create BulkOperationJob for export
        job = BulkOperationJob(
            job_id=str(uuid.uuid4()),
            business_account_id=current_account.id,
            user_id=session.get('business_user_id'),
            operation_type='export_campaign',
            operation_data=json.dumps({
                'campaign_id': campaign_id,
                'campaign_name': campaign.name
            }),
            status='pending',
            progress=0
        )
        
        db.session.add(job)
        db.session.commit()
        
        # Queue export task
        task_data = {
            'job_id': job.job_id,
            'campaign_id': campaign_id,
            'business_account_id': current_account.id,
            'user_id': session.get('business_user_id')
        }
        task_queue.add_task('export_campaign', priority=1, task_data=task_data)
        
        logger.info(f"Queued async campaign export for campaign {campaign_id} (job_id: {job.job_id})")
        
        return jsonify({
            'job_id': job.job_id,
            'status': 'pending',
            'message': 'Export job queued successfully'
        }), 202
        
    except Exception as e:
        logger.error(f"Error queuing campaign export for {campaign_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to queue export job'}), 500


@campaign_bp.route('/api/campaigns/<int:campaign_id>/export/download/<job_id>', methods=['GET'])
@require_business_auth
@require_permission('export_data')
def download_campaign_export(campaign_id, job_id):
    """Download completed campaign export file"""
    try:
        from models import BulkOperationJob
        import os
        
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account not found'}), 401
        
        # Get and verify export job
        job = BulkOperationJob.query.filter_by(
            job_id=job_id,
            business_account_id=current_account.id,
            operation_type='export_campaign'
        ).first()
        
        if not job:
            return jsonify({'error': 'Export job not found'}), 404
        
        if job.status != 'completed':
            return jsonify({
                'error': 'Export not ready',
                'status': job.status,
                'progress': job.progress
            }), 400
        
        # Get file path from result JSON
        result_data = json.loads(job.result) if job.result else {}
        file_path = result_data.get('file_path')
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'Export file not found'}), 404
        
        # Verify campaign access
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        logger.info(f"Downloading export {job_id} for campaign {campaign_id}")
        
        return send_file(
            file_path,
            mimetype='application/json',
            as_attachment=True,
            download_name=f"{campaign.name}_export.json"
        )
        
    except Exception as e:
        logger.error(f"Error downloading campaign export {job_id}: {e}")
        return jsonify({'error': 'Failed to download export'}), 500


@campaign_bp.route('/api/campaigns/<int:campaign_id>/export/legacy', methods=['GET'])
@require_business_auth
@require_permission('export_data')
def export_campaign_responses_legacy(campaign_id):
    """
    DEPRECATED: Legacy synchronous export endpoint.
    Use POST /api/campaigns/<id>/export for async exports with progress tracking.
    This endpoint is kept for backwards compatibility only.
    """
    try:
        logger.warning(f"DEPRECATED: Legacy synchronous export endpoint used for campaign {campaign_id}. Migrate to async export.")
        
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account not found'}), 401
        
        # Get campaign and verify access
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        logger.info(f"Campaign export initiated for campaign {campaign_id} ({campaign.name}) by business account {current_account.id}")
        
        # Query responses for this specific campaign
        responses = SurveyResponse.query.filter_by(
            campaign_id=campaign_id
        ).all()
        
        logger.info(f"Export query returned {len(responses)} responses for campaign {campaign_id}")
        
        # Convert responses to dictionaries
        data = []
        for response in responses:
            response_dict = response.to_dict()
            response_dict['campaign_name'] = campaign.name
            data.append(response_dict)
        
        export_info = {
            'total_responses': len(responses),
            'campaign_id': campaign_id,
            'campaign_name': campaign.name,
            'business_account': current_account.name,
            'exported_at': datetime.utcnow().isoformat(),
            'exported_by': session.get('business_user_email', 'Unknown')
        }
        
        return jsonify({
            'data': data,
            'export_info': export_info
        })
        
    except Exception as e:
        logger.error(f"Error exporting campaign {campaign_id}: {e}")
        return jsonify({'error': 'Failed to export campaign data'}), 500


@campaign_bp.route('/api/timeline-data')
@require_business_auth
@require_permission('manage_participants')
def get_timeline_data():
    """Get campaign timeline data for visualization"""
    try:
        from flask_babel import gettext as _
        from dateutil.relativedelta import relativedelta
        
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account not found'}), 400
        
        # Get license information
        from license_service import LicenseService
        license_info = LicenseService.get_license_info(current_account.id, bypass_admin_override=True)
        
        if not license_info:
            return jsonify({'error': 'License information not available'}), 400
        
        # Get license dates from license_info (uses LicenseHistory, not deprecated BusinessAccount columns)
        license_start = license_info.get('license_start')
        license_end = license_info.get('license_end')
        
        logger.debug(f"Timeline data for business_account_id {current_account.id}: license_start={license_start}, license_end={license_end}, license_type={license_info.get('license_type')}")
        
        # Handle accounts without license dates (trials, newly onboarded)
        if not license_start or not license_end:
            # Return empty timeline with message
            logger.info(f"Timeline requested for business account {current_account.id} without license dates (trial/new account)")
            return jsonify({
                'license_months': 0,
                'license_start': None,
                'license_end': None,
                'campaigns': [],
                'message': _('License not activated yet. Timeline will be available once your license is activated.')
            })
        
        # Calculate months between start and end
        months_diff = (license_end.year - license_start.year) * 12 + (license_end.month - license_start.month)
        
        # Get all campaigns for this business account
        campaigns = Campaign.query.filter_by(
            business_account_id=current_account.id
        ).order_by(Campaign.start_date).all()
        
        # Build timeline data
        timeline_data = []
        for campaign in campaigns:
            # Calculate campaign position in months from license start
            start_month = (campaign.start_date.year - license_start.year) * 12 + (campaign.start_date.month - license_start.month)
            end_month = (campaign.end_date.year - license_start.year) * 12 + (campaign.end_date.month - license_start.month)
            
            # Clamp to license duration
            start_month = max(0, min(start_month, months_diff))
            end_month = max(0, min(end_month, months_diff))
            
            timeline_data.append({
                'name': campaign.name,
                'status': campaign.status,
                'start_month': start_month,
                'end_month': end_month,
                'start_date': campaign.start_date.isoformat(),
                'end_date': campaign.end_date.isoformat()
            })
        
        return jsonify({
            'license_months': months_diff,
            'license_start': license_start.isoformat(),
            'license_end': license_end.isoformat(),
            'campaigns': timeline_data
        })
        
    except Exception as e:
        logger.error(f"Error getting timeline data: {e}")
        return jsonify({'error': 'Failed to load timeline data'}), 500