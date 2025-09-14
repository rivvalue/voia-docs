"""
Phase 2: Business Account Authentication Routes
Provides login/logout routes for business account users without affecting public survey access
"""

from flask import Blueprint, request, render_template, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash
from models import BusinessAccountUser, UserSession, BusinessAccount, db
import logging
from datetime import datetime, timedelta
import json

# Create blueprint for business account authentication
business_auth_bp = Blueprint('business_auth', __name__, url_prefix='/business')

logger = logging.getLogger(__name__)

# ==== TENANT SCOPING HELPERS (PHASE 2.5 MINIMAL ACCOUNT MANAGEMENT) ====

def current_tenant_id():
    """Get current business account ID from session"""
    return session.get('business_account_id')

def get_current_business_account():
    """Get current BusinessAccount object from session"""
    business_account_id = current_tenant_id()
    if not business_account_id:
        return None
    return BusinessAccount.query.get(business_account_id)

def require_business_auth(f):
    """Decorator to ensure valid business authentication with active account"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated
        business_user_id = session.get('business_user_id')
        if not business_user_id:
            if request.is_json:
                return jsonify({'error': 'Business authentication required'}), 401
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get current business account
        current_account = get_current_business_account()
        if not current_account:
            if request.is_json:
                return jsonify({'error': 'Invalid session'}), 401
            flash('Invalid session. Please log in again.', 'error')
            session.clear()
            return redirect(url_for('business_auth.login'))
        
        # Check account status
        if current_account.status != 'active':
            if current_account.status == 'suspended':
                if request.is_json:
                    return jsonify({'error': 'Account suspended'}), 403
                flash('Your account has been suspended. Please contact support.', 'error')
            elif current_account.status == 'trial':
                if not request.is_json:
                    flash('Your account is in trial mode.', 'info')
            else:
                if request.is_json:
                    return jsonify({'error': 'Account not active'}), 403
                flash('Your account is not active. Please contact support.', 'error')
            
            # For suspended/inactive accounts, block access
            if current_account.status in ['suspended', 'inactive', 'closed']:
                if request.is_json:
                    return jsonify({'error': 'Account access blocked', 'status': current_account.status}), 403
                return render_template('business_auth/account_status.html', 
                                     account_status=current_account.status)
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_permission(permission):
    """Decorator to check user permissions"""
    from functools import wraps
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # First ensure business auth - check manually since we can't call decorator
            business_user_id = session.get('business_user_id')
            if not business_user_id:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('business_auth.login'))
            
            current_account = get_current_business_account()
            if not current_account or current_account.status != 'active':
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('business_auth.login'))
            
            # Get current user
            business_user_id = session.get('business_user_id')
            current_user = BusinessAccountUser.query.get(business_user_id)
            
            if not current_user or not current_user.has_permission(permission):
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('business_auth.admin_panel'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@business_auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Business account login page and handler"""
    if request.method == 'GET':
        # Show login form
        return render_template('business_auth/login.html')
    
    # Handle login submission
    try:
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember_me = request.form.get('remember_me') == 'on'
        
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('business_auth/login.html')
        
        # Find user by email
        user = BusinessAccountUser.get_by_email(email)
        
        if not user or not user.check_password(password):
            flash('Invalid email or password', 'error')
            return render_template('business_auth/login.html')
        
        if not user.is_active:
            flash('Account is deactivated. Please contact support.', 'error')
            return render_template('business_auth/login.html')
        
        # Create user session
        session_duration = 168 if remember_me else 24  # 7 days vs 24 hours
        user_session = UserSession(
            user_id=user.id,
            ip_address=request.environ.get('HTTP_X_FORWARDED_FOR', 
                                         request.environ.get('REMOTE_ADDR', ''))[:45],
            user_agent=request.headers.get('User-Agent', '')[:500],
            duration_hours=session_duration
        )
        
        # Set session data
        session_data = {
            'business_account_id': user.business_account_id,
            'business_account_name': user.business_account.name,
            'user_role': user.role,
            'login_time': datetime.utcnow().isoformat()
        }
        user_session.set_session_data(session_data)
        
        db.session.add(user_session)
        db.session.commit()
        
        # Update user last login
        user.update_last_login()
        db.session.commit()
        
        # Set Flask session
        session['business_user_id'] = user.id
        session['business_session_id'] = user_session.session_id
        session['business_account_id'] = user.business_account_id
        session['business_account_name'] = user.business_account.name
        session['user_role'] = user.role
        session.permanent = remember_me
        
        logger.info(f"Business account user {email} logged in successfully")
        flash(f'Welcome back, {user.get_full_name()}!', 'success')
        
        # Redirect to admin panel
        return redirect(url_for('business_auth.admin_panel'))
        
    except Exception as e:
        logger.error(f"Business login error: {e}")
        flash('Login failed. Please try again.', 'error')
        return render_template('business_auth/login.html')


@business_auth_bp.route('/logout')
def logout():
    """Business account logout"""
    try:
        # Deactivate user session if exists
        session_id = session.get('business_session_id')
        if session_id:
            user_session = UserSession.get_active_session(session_id)
            if user_session:
                user_session.deactivate()
                db.session.commit()
        
        # Clear accumulated flash messages from session to prevent them from showing on login page
        from flask import get_flashed_messages
        get_flashed_messages()  # This consumes and clears all existing flash messages
        
        # Clear Flask session business account data
        business_keys = ['business_user_id', 'business_session_id', 'business_account_id', 
                        'business_account_name', 'user_role']
        for key in business_keys:
            session.pop(key, None)
        
        logger.info("Business account user logged out")
        flash('You have been logged out successfully.', 'info')
        
    except Exception as e:
        logger.error(f"Business logout error: {e}")
        # Even on error, clear flash messages to prevent accumulation
        from flask import get_flashed_messages
        get_flashed_messages()
        flash('Logout completed. Please log in again if needed.', 'info')
    
    return redirect(url_for('business_auth.login'))


@business_auth_bp.route('/admin')
@require_permission('manage_participants')
def admin_panel():
    """Admin panel for Rivvalue demo campaign management"""
    
    try:
        # Get current business account context
        business_account_id = session.get('business_account_id')
        business_account = BusinessAccount.query.get(business_account_id)
        
        if not business_account:
            flash('Business account not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get current user
        user_id = session.get('business_user_id')
        current_business_user = BusinessAccountUser.query.get(user_id)
        
        # Admin panel data depends on account type
        if business_account.account_type == 'demo':
            # Rivvalue demo account - show demo campaign management
            from models import Campaign, SurveyResponse, Participant, CampaignParticipant, EmailDelivery
            from email_service import email_service
            
            # Get demo campaigns (for Rivvalue) - now using proper business account ownership
            campaigns = Campaign.query.filter_by(
                business_account_id=business_account.id
            ).order_by(Campaign.created_at.desc()).limit(5).all()
            
            # Get recent demo responses (properly scoped to business account)
            recent_responses = SurveyResponse.query.join(Campaign).filter(
                Campaign.business_account_id == business_account.id
            ).order_by(SurveyResponse.created_at.desc()).limit(10).all()
            
            # Basic stats for demo account (properly scoped to business account)
            total_responses = SurveyResponse.query.join(Campaign).filter(
                Campaign.business_account_id == business_account.id
            ).count()
            total_campaigns = Campaign.query.filter(
                Campaign.business_account_id == business_account.id
            ).count()
            
            # Add participant count for demo account
            total_participants = Participant.query.filter_by(
                business_account_id=business_account.id
            ).count()
            
            # Email delivery statistics
            total_invitations = EmailDelivery.query.filter_by(
                business_account_id=business_account.id,
                email_type='participant_invitation'
            ).count()
            
            sent_invitations = EmailDelivery.query.filter_by(
                business_account_id=business_account.id,
                email_type='participant_invitation',
                status='sent'
            ).count()
            
            failed_invitations = EmailDelivery.query.filter_by(
                business_account_id=business_account.id,
                email_type='participant_invitation',
                status='failed'
            ).count()
            
            pending_invitations = EmailDelivery.query.filter_by(
                business_account_id=business_account.id,
                email_type='participant_invitation',
                status='pending'
            ).count()
            
            # Get active campaigns with invitation status
            active_campaigns = []
            for campaign in campaigns:
                if campaign.is_active():
                    # Get participant count for this campaign
                    participant_count = CampaignParticipant.query.filter_by(
                        campaign_id=campaign.id,
                        business_account_id=business_account.id
                    ).count()
                    
                    # Get invitation statistics for this campaign
                    campaign_invitations = EmailDelivery.query.filter_by(
                        campaign_id=campaign.id,
                        business_account_id=business_account.id,
                        email_type='participant_invitation'
                    ).count()
                    
                    campaign_sent = EmailDelivery.query.filter_by(
                        campaign_id=campaign.id,
                        business_account_id=business_account.id,
                        email_type='participant_invitation',
                        status='sent'
                    ).count()
                    
                    campaign_data = campaign.to_dict()
                    campaign_data.update({
                        'participant_count': participant_count,
                        'invitation_stats': {
                            'total': campaign_invitations,
                            'sent': campaign_sent,
                            'pending': campaign_invitations - campaign_sent,
                            'can_send_invitations': participant_count > 0 and email_service.is_configured()
                        }
                    })
                    active_campaigns.append(campaign_data)
            
            admin_data = {
                'account_type': 'demo',
                'campaigns': [c.to_dict() for c in campaigns],
                'active_campaigns': active_campaigns,
                'recent_responses': [r.to_dict() for r in recent_responses],
                'stats': {
                    'total_responses': total_responses,
                    'total_campaigns': total_campaigns,
                    'total_participants': total_participants,
                    'active_campaigns': len(active_campaigns),
                    'email_stats': {
                        'total_invitations': total_invitations,
                        'sent_invitations': sent_invitations,
                        'failed_invitations': failed_invitations,
                        'pending_invitations': pending_invitations
                    }
                },
                'email_configured': email_service.is_configured()
            }
        else:
            # Customer account - placeholder for future Phase 3
            admin_data = {
                'account_type': 'customer',
                'message': 'Customer participant management coming in Phase 3',
                'stats': {
                    'total_participants': 0,
                    'total_campaigns': 0,
                    'completed_surveys': 0
                }
            }
        
        return render_template('business_auth/admin_panel.html',
                             business_account=business_account.to_dict() if business_account else {},
                             current_user=current_business_user.to_dict() if current_business_user else {},
                             admin_data=admin_data)
        
    except Exception as e:
        logger.error(f"Admin panel error: {e}")
        flash('Error loading admin panel.', 'error')
        return redirect(url_for('business_auth.login'))


@business_auth_bp.route('/api/session-status')
@require_business_auth
def session_status():
    """Check business account session status"""
    try:
        
        session_id = session.get('business_session_id')
        user_session = UserSession.get_active_session(session_id)
        
        if not user_session:
            return jsonify({
                'authenticated': False,
                'message': 'Session expired'
            })
        
        # Update activity
        user_session.update_activity()
        db.session.commit()
        
        return jsonify({
            'authenticated': True,
            'user_id': session.get('business_user_id'),
            'business_account_id': session.get('business_account_id'),
            'business_account_name': session.get('business_account_name'),
            'user_role': session.get('user_role'),
            'session_expires_at': user_session.expires_at.isoformat(),
            'last_activity': user_session.last_activity_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Session status error: {e}")
        return jsonify({
            'authenticated': False,
            'message': 'Session check failed'
        }), 500


def is_business_authenticated():
    """Check if user is authenticated to a business account"""
    session_id = session.get('business_session_id')
    user_id = session.get('business_user_id')
    
    if not session_id or not user_id:
        return False
    
    # Check session validity
    user_session = UserSession.get_active_session(session_id)
    if not user_session or user_session.user_id != user_id:
        return False
    
    return True




def get_current_business_user():
    """Get current authenticated business user"""
    if not is_business_authenticated():
        return None
    
    user_id = session.get('business_user_id')
    return BusinessAccountUser.query.get(user_id)




# Database health check utilities
@business_auth_bp.route('/api/database-health', methods=['GET'])
@require_permission('manage_campaigns')
def database_health_check():
    """Check database schema health including critical constraints (admin only)"""
    
    try:
        health_status = {
            'constraints': {},
            'indexes': {},
            'overall_status': 'healthy'
        }
        
        # Check if the partial unique index for single active campaign exists
        constraint_check_query = """
        SELECT schemaname, tablename, indexname, indexdef
        FROM pg_indexes 
        WHERE tablename = 'campaigns' 
        AND indexname = 'idx_single_active_campaign_per_account'
        """
        
        from sqlalchemy import text
        result = db.session.execute(text(constraint_check_query)).fetchall()
        
        if result:
            health_status['constraints']['single_active_campaign_constraint'] = {
                'status': 'present',
                'index_name': result[0][2],
                'definition': result[0][3]
            }
            
            # Test the constraint by checking for violations
            violation_check_query = """
            SELECT business_account_id, COUNT(*) as active_campaigns
            FROM campaigns 
            WHERE status = 'active' 
            GROUP BY business_account_id 
            HAVING COUNT(*) > 1
            """
            
            violations = db.session.execute(text(violation_check_query)).fetchall()
            
            if violations:
                health_status['constraints']['single_active_campaign_constraint']['violations'] = [
                    {'business_account_id': v[0], 'active_campaigns': v[1]} for v in violations
                ]
                health_status['overall_status'] = 'warning'
            else:
                health_status['constraints']['single_active_campaign_constraint']['violations'] = []
                
        else:
            health_status['constraints']['single_active_campaign_constraint'] = {
                'status': 'missing',
                'message': 'Critical constraint not found in database'
            }
            health_status['overall_status'] = 'critical'
        
        # Check other important indexes
        index_check_query = """
        SELECT indexname, indexdef
        FROM pg_indexes 
        WHERE tablename = 'campaigns' 
        AND indexname IN ('idx_campaign_business_status', 'idx_campaign_dates')
        """
        
        indexes = db.session.execute(text(index_check_query)).fetchall()
        for index in indexes:
            health_status['indexes'][index[0]] = {
                'status': 'present',
                'definition': index[1]
            }
        
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"Database health check error: {e}")
        return jsonify({
            'overall_status': 'error',
            'message': f'Health check failed: {str(e)}'
        }), 500


# Session cleanup utility
@business_auth_bp.route('/api/cleanup-sessions', methods=['POST'])
@require_permission('manage_users')
def cleanup_expired_sessions():
    """Clean up expired sessions (admin only)"""
    
    # Permission already checked by decorator
    
    try:
        cleaned_count = UserSession.cleanup_expired_sessions()
        db.session.commit()
        
        return jsonify({
            'message': f'Cleaned up {cleaned_count} expired sessions',
            'cleaned_sessions': cleaned_count
        })
        
    except Exception as e:
        logger.error(f"Session cleanup error: {e}")
        return jsonify({'error': 'Session cleanup failed'}), 500


# Initialize Rivvalue demo account user (run once)
def init_rivvalue_admin_user():
    """Initialize default admin user for Rivvalue demo account"""
    try:
        # Check if Rivvalue account exists
        rivvalue_account = BusinessAccount.query.filter_by(name='Rivvalue Inc').first()
        if not rivvalue_account:
            logger.warning("Rivvalue Inc business account not found - cannot create admin user")
            return False
        
        # Check if admin user already exists
        admin_email = '7amdoulilah@rivvalue.com'
        existing_user = BusinessAccountUser.get_by_email(admin_email)
        if existing_user:
            logger.info(f"Admin user {admin_email} already exists")
            return True
        
        # Create admin user
        admin_user = BusinessAccountUser()
        admin_user.business_account_id = rivvalue_account.id
        admin_user.email = admin_email
        admin_user.first_name = 'Admin'
        admin_user.last_name = 'User'
        admin_user.role = 'admin'
        admin_user.is_active = True
        admin_user.email_verified = True
        # Generate secure temporary password
        import secrets
        import string
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits + '!@#$%^&*') for _ in range(16))
        admin_user.set_password(temp_password)
        
        # Log that admin user was created (without exposing password)
        logger.info(f"SECURITY: Admin user {admin_email} created with secure temporary password. Use admin panel to reset password.")
        
        # Store password securely in environment or secure storage for admin access
        # For development: password should be retrieved through secure admin interface
        print(f"\n=== ADMIN USER CREATED ===\nEmail: {admin_email}\nTemporary Password: {temp_password}\nPlease change immediately via admin panel!\n==========================\n")
        
        db.session.add(admin_user)
        db.session.commit()
        
        logger.info(f"Created admin user {admin_email} for Rivvalue Inc")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize admin user: {e}")
        return False


# ==== ADMIN ROUTES FOR SCHEDULER TESTING ====

@business_auth_bp.route('/admin/scheduler/run', methods=['POST'])
@require_business_auth
@require_permission('admin')
def force_scheduler_run():
    """Force immediate scheduler run (admin only) for testing purposes"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            if request.is_json:
                return jsonify({'error': 'Business account context not found'}), 400
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        # Import task queue to access scheduler
        from task_queue import task_queue
        
        logger.info(f"Admin forcing scheduler run - initiated by business account {current_account.id} ({current_account.name})")
        
        # Force immediate scheduler execution
        success = task_queue.force_scheduler_run()
        
        if success:
            message = "Scheduler executed successfully! Check campaign statuses for any automatic transitions."
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': message,
                    'scheduler_stats': task_queue.get_stats()
                })
            flash(message, 'success')
        else:
            message = "Scheduler execution failed. Check server logs for details."
            if request.is_json:
                return jsonify({'error': message}), 500
            flash(message, 'error')
        
        return redirect(url_for('business_auth.admin_panel'))
        
    except Exception as e:
        logger.error(f"Error forcing scheduler run: {e}")
        if request.is_json:
            return jsonify({'error': 'Failed to execute scheduler'}), 500
        flash('Failed to execute scheduler. Please try again.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@business_auth_bp.route('/admin/scheduler/status')
@require_business_auth
@require_permission('admin')
def scheduler_status():
    """Get scheduler status and statistics (admin only)"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            if request.is_json:
                return jsonify({'error': 'Business account context not found'}), 400
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        # Import task queue to access scheduler stats
        from task_queue import task_queue
        
        scheduler_stats = task_queue.get_stats()
        
        # Get campaign counts for current business account
        from models import Campaign
        campaign_counts = {
            'draft': Campaign.query.filter_by(business_account_id=current_account.id, status='draft').count(),
            'ready': Campaign.query.filter_by(business_account_id=current_account.id, status='ready').count(),
            'active': Campaign.query.filter_by(business_account_id=current_account.id, status='active').count(),
            'completed': Campaign.query.filter_by(business_account_id=current_account.id, status='completed').count()
        }
        
        if request.is_json:
            return jsonify({
                'scheduler_stats': scheduler_stats,
                'campaign_counts': campaign_counts,
                'business_account': {
                    'id': current_account.id,
                    'name': current_account.name
                }
            })
        
        # For HTML requests, redirect to admin panel with flash message
        flash(f"Scheduler Status: Running={scheduler_stats['running']}, Last Run={scheduler_stats['last_scheduler_run'] or 'Never'}", 'info')
        flash(f"Campaign Counts: Draft={campaign_counts['draft']}, Ready={campaign_counts['ready']}, Active={campaign_counts['active']}, Completed={campaign_counts['completed']}", 'info')
        return redirect(url_for('business_auth.admin_panel'))
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        if request.is_json:
            return jsonify({'error': 'Failed to get scheduler status'}), 500
        flash('Failed to get scheduler status.', 'error')
        return redirect(url_for('business_auth.admin_panel'))