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
        
        # Clear Flask session business account data
        business_keys = ['business_user_id', 'business_session_id', 'business_account_id', 
                        'business_account_name', 'user_role']
        for key in business_keys:
            session.pop(key, None)
        
        logger.info("Business account user logged out")
        flash('You have been logged out successfully.', 'info')
        
    except Exception as e:
        logger.error(f"Business logout error: {e}")
    
    return redirect(url_for('business_auth.login'))


@business_auth_bp.route('/admin')
def admin_panel():
    """Admin panel for Rivvalue demo campaign management"""
    # Check business account authentication
    if not is_business_authenticated():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('business_auth.login'))
    
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
            from models import Campaign, SurveyResponse
            
            # Get demo campaigns (for Rivvalue)
            campaigns = Campaign.query.filter_by(
                client_identifier='archelo_group'
            ).order_by(Campaign.created_at.desc()).limit(5).all()
            
            # Get recent demo responses
            recent_responses = SurveyResponse.query.filter(
                SurveyResponse.campaign_id.isnot(None)
            ).order_by(SurveyResponse.created_at.desc()).limit(10).all()
            
            # Basic stats for demo account
            total_responses = SurveyResponse.query.count()
            total_campaigns = Campaign.query.count()
            
            admin_data = {
                'account_type': 'demo',
                'campaigns': [c.to_dict() for c in campaigns],
                'recent_responses': [r.to_dict() for r in recent_responses],
                'stats': {
                    'total_responses': total_responses,
                    'total_campaigns': total_campaigns,
                    'active_campaigns': len([c for c in campaigns if c.is_active()])
                }
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
                             business_account=business_account.to_dict(),
                             current_user=current_business_user.to_dict(),
                             admin_data=admin_data)
        
    except Exception as e:
        logger.error(f"Admin panel error: {e}")
        flash('Error loading admin panel.', 'error')
        return redirect(url_for('business_auth.login'))


@business_auth_bp.route('/api/session-status')
def session_status():
    """Check business account session status"""
    try:
        if not is_business_authenticated():
            return jsonify({
                'authenticated': False,
                'message': 'Not authenticated'
            })
        
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


def require_business_auth():
    """Decorator to require business account authentication"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if not is_business_authenticated():
                if request.is_json:
                    return jsonify({'error': 'Business authentication required'}), 401
                else:
                    flash('Please log in to access this page.', 'error')
                    return redirect(url_for('business_auth.login'))
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator


def get_current_business_user():
    """Get current authenticated business user"""
    if not is_business_authenticated():
        return None
    
    user_id = session.get('business_user_id')
    return BusinessAccountUser.query.get(user_id)


def get_current_business_account():
    """Get current business account"""
    if not is_business_authenticated():
        return None
    
    account_id = session.get('business_account_id')
    return BusinessAccount.query.get(account_id)


# Session cleanup utility
@business_auth_bp.route('/api/cleanup-sessions', methods=['POST'])
def cleanup_expired_sessions():
    """Clean up expired sessions (admin only)"""
    if not is_business_authenticated():
        return jsonify({'error': 'Authentication required'}), 401
    
    # Only allow admin users to cleanup sessions
    current_user = get_current_business_user()
    if not current_user or not current_user.has_permission('manage_users'):
        return jsonify({'error': 'Admin access required'}), 403
    
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
        admin_user = BusinessAccountUser(
            business_account_id=rivvalue_account.id,
            email=admin_email,
            first_name='Admin',
            last_name='User',
            role='admin',
            is_active=True,
            email_verified=True
        )
        admin_user.set_password('admin123')  # Default password - should be changed
        
        db.session.add(admin_user)
        db.session.commit()
        
        logger.info(f"Created admin user {admin_email} for Rivvalue Inc")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize admin user: {e}")
        return False