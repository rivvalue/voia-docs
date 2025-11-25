"""
Phase 2: Business Account Authentication Routes
Provides login/logout routes for business account users without affecting public survey access
"""

from flask import Blueprint, request, render_template, redirect, url_for, session, flash, jsonify, send_file, get_flashed_messages
from werkzeug.security import check_password_hash, generate_password_hash
from models import BusinessAccountUser, UserSession, BusinessAccount, EmailConfiguration, EmailDelivery, LicenseHistory, db
from rate_limiter import rate_limit
from license_service import LicenseService
from feature_flags import feature_flags
from audit_utils import queue_audit_log
from flask_babel import gettext as _
import logging
import os
from datetime import datetime, timedelta, date
import json
import re

# Create blueprint for business account authentication
business_auth_bp = Blueprint('business_auth', __name__, url_prefix='/business')

logger = logging.getLogger(__name__)

def get_branding_context(business_account_id=None):
    """
    Get branding context for templates including company name and logo URL.
    
    Args:
        business_account_id: ID of the business account, if None will try to get from session
    
    Returns:
        dict: Branding context with company_name, logo_url, and has_branding flag
    """
    branding_context = {
        'company_name': 'VOÏA - Voice Of Client Agent',  # Default fallback
        'logo_url': None,
        'has_branding': False,
        'branding_config': None
    }
    
    try:
        # Try to get business_account_id from parameter or session
        if not business_account_id:
            business_account_id = session.get('business_account_id')
        
        if business_account_id:
            from models import BrandingConfig
            branding_config = BrandingConfig.query.filter_by(business_account_id=business_account_id).first()
            
            if branding_config:
                # Update context with custom branding
                branding_context.update({
                    'company_name': branding_config.get_company_display_name(),
                    'logo_url': branding_config.get_logo_url(),
                    'has_branding': branding_config.has_logo(),
                    'branding_config': branding_config
                })
                
                logger.info(f"Loaded branding for business account {business_account_id}: {branding_context['company_name']}")
            else:
                logger.info(f"No branding config found for business account {business_account_id}, using defaults")
    
    except Exception as e:
        logger.warning(f"Error loading branding context: {e}")
        # Keep default fallback values
    
    return branding_context

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
        
        # Track onboarding status but don't block access (Solution 2: Conditional Access)
        current_user = BusinessAccountUser.query.get(business_user_id)
        if current_user and current_user.requires_onboarding():
            # Initialize onboarding progress if not set
            if not current_user.onboarding_progress:
                current_user.initialize_onboarding()
                db.session.commit()
            
            # Store incomplete onboarding flag in session for banner display
            session['onboarding_incomplete'] = True
            session['onboarding_url'] = url_for('business_auth.onboarding_progress')
        else:
            # Clear the flag if onboarding is complete
            session.pop('onboarding_incomplete', None)
            session.pop('onboarding_url', None)
        
        return f(*args, **kwargs)
    
    return decorated_function

def get_onboarding_status():
    """Get detailed onboarding status for the current user"""
    business_user_id = session.get('business_user_id')
    if not business_user_id:
        return None
    
    current_user = BusinessAccountUser.query.get(business_user_id)
    if not current_user or not current_user.requires_onboarding():
        return None
    
    # Get onboarding progress
    progress = current_user.get_onboarding_progress()
    if not progress:
        return None
    
    # Calculate incomplete steps
    incomplete_steps = []
    steps_info = {
        'smtp_config': {'label': 'Email Setup', 'url': url_for('business_auth.email_config')},
        'brand_config': {'label': 'Brand Configuration', 'url': url_for('business_auth.brand_config')},
        'team_members': {'label': 'Team Members', 'url': url_for('business_auth.manage_users')}
    }
    
    for step, info in steps_info.items():
        if not progress.get(step, {}).get('completed', False):
            incomplete_steps.append({
                'name': step,
                'label': info['label'],
                'url': info['url'],
                'required': progress.get(step, {}).get('required', False)
            })
    
    if not incomplete_steps:
        return None
    
    return {
        'incomplete_steps': incomplete_steps,
        'progress_url': url_for('business_auth.onboarding_progress'),
        'total_steps': len(steps_info),
        'completed_steps': len(steps_info) - len(incomplete_steps)
    }

def require_permission(permission):
    """Decorator to check user permissions"""
    from functools import wraps
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # First ensure business auth - check manually since we can't call decorator
            business_user_id = session.get('business_user_id')
            if not business_user_id:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Business authentication required'}), 401
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('business_auth.login'))
            
            current_account = get_current_business_account()
            if not current_account:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Invalid session'}), 401
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('business_auth.login'))
            
            # Check account status - mirror require_business_auth logic
            if current_account.status in ['suspended', 'inactive', 'closed']:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Account access blocked', 'status': current_account.status}), 403
                flash('Account access blocked. Please contact support.', 'error')
                return redirect(url_for('business_auth.login'))
            
            # Allow active and trial accounts to proceed
            if current_account.status == 'trial':
                flash('Your account is in trial mode.', 'info')
            
            # Get current user
            business_user_id = session.get('business_user_id')
            current_user = BusinessAccountUser.query.get(business_user_id)
            
            if not current_user or not current_user.has_permission(permission):
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': f'Permission denied. {permission.replace("_", " ").title()} access required'}), 403
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('business_auth.admin_panel'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_platform_admin(f):
    """Decorator to require platform administrator permissions for cross-tenant operations"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First ensure business auth
        business_user_id = session.get('business_user_id')
        if not business_user_id:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('business_auth.login'))
        
        current_account = get_current_business_account()
        if not current_account:
            if request.is_json:
                return jsonify({'error': 'Invalid session'}), 401
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Check account status
        if current_account.status in ['suspended', 'inactive', 'closed']:
            if request.is_json:
                return jsonify({'error': 'Account access blocked'}), 403
            flash('Account access blocked. Please contact support.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get current user and check for platform admin permissions
        current_user = BusinessAccountUser.query.get(business_user_id)
        if not current_user:
            if request.is_json:
                return jsonify({'error': 'User not found'}), 401
            flash('User session invalid. Please log in again.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Platform admin check - only allow users with platform_admin role or specific admin emails
        if not current_user.is_platform_admin():
            logger.warning(f"Platform admin access denied for user {current_user.email} from IP {request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))[:45]}")
            if request.is_json:
                return jsonify({'error': 'Platform administrator access required'}), 403
            flash('Platform administrator access required. This action requires cross-tenant permissions.', 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        logger.info(f"Platform admin access granted to {current_user.email} for {request.endpoint}")
        return f(*args, **kwargs)
    
    return decorated_function


def validate_business_account_access(business_id, allow_platform_admin=False):
    """Validate that current user can access the specified business account"""
    try:
        business_id = int(business_id)
    except (ValueError, TypeError):
        return False, None, "Invalid business account ID"
    
    # Get target business account
    target_account = BusinessAccount.query.get(business_id)
    if not target_account:
        return False, None, "Business account not found"
    
    # Get current user and account context
    current_user_id = session.get('business_user_id')
    current_account_id = session.get('business_account_id')
    
    if not current_user_id or not current_account_id:
        return False, None, "Authentication required"
    
    current_user = BusinessAccountUser.query.get(current_user_id)
    if not current_user:
        return False, None, "User not found"
    
    # Platform admins can access any business account
    if allow_platform_admin and current_user.is_platform_admin():
        return True, target_account, "Platform admin access"
    
    # Regular users can only access their own business account
    if current_account_id != business_id:
        logger.warning(f"Cross-tenant access attempt: User {current_user.email} (account {current_account_id}) tried to access account {business_id}")
        return False, None, "Access denied - cannot access other business accounts"
    
    return True, target_account, "Same tenant access"


# ==== USER MANAGEMENT ROUTES (PHASE 2) ====

@business_auth_bp.route('/users')
@require_business_auth
@require_permission('manage_users')
def manage_users():
    """User management page for business account admins"""
    try:
        current_user_id = session.get('business_user_id')
        current_account_id = session.get('business_account_id')
        
        if not current_user_id or not current_account_id:
            logger.warning("Missing user or account session data")
            flash('Authentication required.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get current business account
        business_account = BusinessAccount.query.get(current_account_id)
        if not business_account:
            logger.error(f"Business account {current_account_id} not found")
            flash('Business account not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get current user
        current_user = BusinessAccountUser.query.get(current_user_id)
        if not current_user:
            logger.error(f"Current user {current_user_id} not found")
            flash('User not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # PERFORMANCE: Pass business_account to avoid duplicate query
        from license_service import LicenseService
        is_platform_admin = current_user.is_platform_admin()
        license_info = LicenseService.get_license_info(
            current_account_id,
            business_account=business_account,
            is_platform_admin=is_platform_admin
        )
        
        # Get all users for this business account
        users = BusinessAccountUser.get_by_business_account(current_account_id)
        # Count only active users to match license system
        users_count = business_account.current_users_count
        
        logger.info(f"User {current_user.email} accessing user management for account {business_account.name}")
        
        return render_template('business_auth/manage_users.html',
                             business_account=business_account,
                             current_user=current_user,
                             users=users,
                             users_count=users_count,
                             license_info=license_info)
    
    except Exception as e:
        logger.error(f"Error loading user management page: {e}")
        flash('Failed to load user management page.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@business_auth_bp.route('/users/add', methods=['POST'])
@require_business_auth
@require_permission('manage_users')
def add_user():
    """Add new user to business account with license validation"""
    try:
        current_user_id = session.get('business_user_id')
        current_account_id = session.get('business_account_id')
        
        if not current_user_id or not current_account_id:
            logger.warning("Missing user or account session data")
            flash('Authentication required.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get form data
        email = request.form.get('email', '').strip().lower()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        role = request.form.get('role', 'manager').strip()
        
        # Validate input
        if not email or not first_name or not last_name:
            flash('All fields are required.', 'error')
            return redirect(url_for('business_auth.manage_users'))
        
        # Validate email format
        from email_validator import validate_email, EmailNotValidError
        try:
            valid_email = validate_email(email)
            email = valid_email.email
        except EmailNotValidError as e:
            flash(f'Invalid email address: {str(e)}', 'error')
            return redirect(url_for('business_auth.manage_users'))
        
        # Check if user already exists
        existing_user = BusinessAccountUser.get_by_email(email)
        if existing_user:
            flash('A user with this email address already exists.', 'error')
            return redirect(url_for('business_auth.manage_users'))
        
        # Check license limits
        from license_service import LicenseService
        if not LicenseService.can_add_user(current_account_id):
            license_info = LicenseService.get_license_info(current_account_id)
            flash(f'Cannot add user: License limit reached ({license_info.get("users_used", 0)}/{license_info.get("users_limit", 5)} users). Contact support to upgrade your license.', 'error')
            return redirect(url_for('business_auth.manage_users'))
        
        # Get current business account and user for role validation
        current_account = get_current_business_account()
        current_user = BusinessAccountUser.query.get(current_user_id)
        
        # Validate role based on account type and user permissions
        allowed_roles = ['admin', 'manager', 'viewer']  # Simplified roles
        
        # Allow platform_admin role only for platform_owner accounts by platform admins
        if (current_account.account_type == 'platform_owner' and 
            current_user and current_user.is_platform_admin() and 
            role == 'platform_admin'):
            allowed_roles.append('platform_admin')
        
        # Backward compatibility for old business_account_admin role
        if role == 'business_account_admin':
            role = 'admin'
        
        if role not in allowed_roles:
            role = 'manager'  # Default to manager
        
        # Create new user
        new_user = BusinessAccountUser()
        new_user.business_account_id = current_account_id
        new_user.email = email
        new_user.first_name = first_name
        new_user.last_name = last_name
        new_user.role = role
        new_user.is_active_user = True
        new_user.email_verified = False  # Will be verified when they activate account
        
        # Generate invitation token
        invitation_token = new_user.generate_invitation_token()
        
        # Save to database
        db.session.add(new_user)
        db.session.commit()
        
        logger.info(f"User {email} created successfully for business account {current_account_id} by user {current_user_id}")
        
        # Audit log the user creation
        try:
            from audit_utils import queue_audit_log
            queue_audit_log(
                business_account_id=current_account_id,
                action_type='user_created',
                resource_type='business_account_user',
                resource_id=new_user.id,
                resource_name=f"{first_name} {last_name}",
                details={
                    'user_email': email,
                    'user_name': f"{first_name} {last_name}",
                    'role': role,
                    'created_by_user_id': current_user_id
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to create audit log for user creation: {audit_error}")
        
        # Send invitation email using business account's SMTP configuration
        try:
            from email_service import EmailService
            email_service = EmailService()
            
            # Get business account details for email
            business_account = BusinessAccount.query.get(current_account_id)
            business_account_name = business_account.name if business_account else "VOÏA Platform"
            
            # Send invitation email using business account's SMTP settings
            email_result = email_service.send_business_account_invitation(
                user_email=email,
                user_first_name=first_name,
                user_last_name=last_name,
                business_account_name=business_account_name,
                invitation_token=invitation_token,
                business_account_id=current_account_id  # Pass business account ID
            )
            
            if email_result.get('success'):
                flash(f'User {new_user.get_full_name()} has been added successfully! Invitation email sent to {email}.', 'success')
                logger.info(f"Invitation email sent successfully to {email} for business account {current_account_id}")
            else:
                flash(f'User {new_user.get_full_name()} has been added, but invitation email failed to send. Invitation token: {invitation_token[:8]}...', 'warning')
                logger.warning(f"Failed to send invitation email to {email}: {email_result.get('error', 'Unknown error')}")
            
        except Exception as email_error:
            flash(f'User {new_user.get_full_name()} has been added, but invitation email failed to send. Invitation token: {invitation_token[:8]}...', 'warning')
            logger.error(f"Exception sending invitation email to {email}: {email_error}")
        
        return redirect(url_for('business_auth.manage_users'))
    
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        db.session.rollback()
        flash('Failed to add user. Please try again.', 'error')
        return redirect(url_for('business_auth.manage_users'))


@business_auth_bp.route('/users/<int:user_id>/edit', methods=['POST'])
@require_business_auth
@require_permission('manage_users')
def edit_user(user_id):
    """Edit user details (name, email, role)"""
    try:
        current_user_id = session.get('business_user_id')
        current_account_id = session.get('business_account_id')
        
        if not current_user_id or not current_account_id:
            logger.warning("Missing user or account session data")
            flash('Authentication required.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get user to edit
        user_to_edit = BusinessAccountUser.query.filter_by(
            id=user_id, 
            business_account_id=current_account_id
        ).first()
        
        if not user_to_edit:
            flash('User not found.', 'error')
            return redirect(url_for('business_auth.manage_users'))
        
        # Get form data
        email = request.form.get('email', '').strip().lower()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        role = request.form.get('role', '').strip()
        
        # Validate input
        if not email or not first_name or not last_name:
            flash('All fields are required.', 'error')
            return redirect(url_for('business_auth.manage_users'))
        
        # Validate email format
        from email_validator import validate_email, EmailNotValidError
        try:
            valid_email = validate_email(email)
            email = valid_email.email
        except EmailNotValidError as e:
            flash(f'Invalid email address: {str(e)}', 'error')
            return redirect(url_for('business_auth.manage_users'))
        
        # Check if email is already taken by another user
        existing_user = BusinessAccountUser.query.filter(
            BusinessAccountUser.email == email,
            BusinessAccountUser.id != user_id
        ).first()
        
        if existing_user:
            flash('A user with this email address already exists.', 'error')
            return redirect(url_for('business_auth.manage_users'))
        
        # Validate role
        allowed_roles = ['business_account_admin', 'admin', 'manager', 'viewer']
        if role not in allowed_roles:
            flash('Invalid role selected.', 'error')
            return redirect(url_for('business_auth.manage_users'))
        
        # Update user
        old_email = user_to_edit.email
        user_to_edit.email = email
        user_to_edit.first_name = first_name
        user_to_edit.last_name = last_name
        user_to_edit.role = role
        user_to_edit.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"User {user_id} updated successfully. Email: {old_email} -> {email}, Role: {role}")
        flash(f'User {user_to_edit.get_full_name()} has been updated successfully.', 'success')
        
        return redirect(url_for('business_auth.manage_users'))
    
    except Exception as e:
        logger.error(f"Error editing user {user_id}: {e}")
        db.session.rollback()
        flash('Failed to update user. Please try again.', 'error')
        return redirect(url_for('business_auth.manage_users'))


@business_auth_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@require_business_auth
@require_permission('manage_users')
def toggle_user_status(user_id):
    """Activate or deactivate user with last admin protection"""
    try:
        current_user_id = session.get('business_user_id')
        current_account_id = session.get('business_account_id')
        
        if not current_user_id or not current_account_id:
            logger.warning("Missing user or account session data")
            flash('Authentication required.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get user to toggle
        user_to_toggle = BusinessAccountUser.query.filter_by(
            id=user_id, 
            business_account_id=current_account_id
        ).first()
        
        if not user_to_toggle:
            flash('User not found.', 'error')
            return redirect(url_for('business_auth.manage_users'))
        
        # Prevent self-deactivation
        if user_id == current_user_id:
            flash('You cannot deactivate your own account.', 'error')
            return redirect(url_for('business_auth.manage_users'))
        
        # Last admin protection - prevent deactivating the last admin
        if user_to_toggle.is_active_user and user_to_toggle.role in ['business_account_admin', 'admin']:
            # Count active admins
            active_admins = BusinessAccountUser.query.filter_by(
                business_account_id=current_account_id,
                is_active_user=True
            ).filter(
                BusinessAccountUser.role.in_(['business_account_admin', 'admin'])
            ).count()
            
            if active_admins <= 1:
                flash('Cannot deactivate the last admin. Add another admin first.', 'error')
                return redirect(url_for('business_auth.manage_users'))
        
        # Toggle status
        new_status = not user_to_toggle.is_active_user
        user_to_toggle.is_active_user = new_status
        user_to_toggle.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        status_text = 'activated' if new_status else 'deactivated'
        logger.info(f"User {user_id} ({user_to_toggle.email}) {status_text} by user {current_user_id}")
        flash(f'User {user_to_toggle.get_full_name()} has been {status_text}.', 'success')
        
        return redirect(url_for('business_auth.manage_users'))
    
    except Exception as e:
        logger.error(f"Error toggling user status {user_id}: {e}")
        db.session.rollback()
        flash('Failed to update user status. Please try again.', 'error')
        return redirect(url_for('business_auth.manage_users'))


@business_auth_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@require_business_auth
@require_permission('manage_users')
def reset_user_password(user_id):
    """Generate password reset token for user (admin-triggered)"""
    try:
        current_user_id = session.get('business_user_id')
        current_account_id = session.get('business_account_id')
        
        if not current_user_id or not current_account_id:
            logger.warning("Missing user or account session data")
            flash('Authentication required.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get user to reset password for
        user_to_reset = BusinessAccountUser.query.filter_by(
            id=user_id, 
            business_account_id=current_account_id
        ).first()
        
        if not user_to_reset:
            flash('User not found.', 'error')
            return redirect(url_for('business_auth.manage_users'))
        
        # Prevent resetting own password through admin interface
        if user_id == current_user_id:
            flash('You cannot reset your own password through this interface. Use the account settings instead.', 'error')
            return redirect(url_for('business_auth.manage_users'))
        
        # Generate password reset token
        reset_token = user_to_reset.generate_password_reset_token()
        
        # Save to database
        db.session.commit()
        
        logger.info(f"Password reset token generated for user {user_id} ({user_to_reset.email}) by admin {current_user_id}")
        
        # TODO: Send password reset email (implement with email service)
        # For now, show the token to the admin
        flash(f'Password reset initiated for {user_to_reset.get_full_name()}. Reset token: {reset_token[:8]}... (expires in 24 hours)', 'success')
        
        return redirect(url_for('business_auth.manage_users'))
    
    except Exception as e:
        logger.error(f"Error resetting password for user {user_id}: {e}")
        db.session.rollback()
        flash('Failed to reset password. Please try again.', 'error')
        return redirect(url_for('business_auth.manage_users'))


# ==== BUSINESS ACCOUNT ONBOARDING ROUTES (PHASE 1) ====

@business_auth_bp.route('/admin/onboarding')
@require_platform_admin
def business_account_onboarding():
    """Platform admin business account onboarding page"""
    try:
        from license_templates import LicenseTemplateManager
        
        # Get available license templates
        license_templates = LicenseTemplateManager.get_all_templates()
        
        return render_template('business_auth/business_account_onboarding.html',
                             license_templates=license_templates)
    
    except Exception as e:
        logger.error(f"Error loading business account onboarding page: {e}")
        flash('Failed to load onboarding page.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@business_auth_bp.route('/admin/onboarding/create', methods=['POST'])
@require_platform_admin
def create_business_account_with_admin():
    """Create business account with admin user and send invitation"""
    try:
        # Get form data
        business_name = request.form.get('business_name', '').strip()
        license_template_id = request.form.get('license_template', '').strip()
        admin_first_name = request.form.get('admin_first_name', '').strip()
        admin_last_name = request.form.get('admin_last_name', '').strip()
        admin_email = request.form.get('admin_email', '').strip().lower()
        
        # Validate required fields
        if not all([business_name, license_template_id, admin_first_name, admin_last_name, admin_email]):
            flash('All fields are required.', 'error')
            return redirect(url_for('business_auth.business_account_onboarding'))
        
        # Validate email format
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(admin_email):
            flash('Please provide a valid email address.', 'error')
            return redirect(url_for('business_auth.business_account_onboarding'))
        
        # Check if email already exists
        existing_user = BusinessAccountUser.query.filter_by(email=admin_email).first()
        if existing_user:
            flash(f'A user with email {admin_email} already exists.', 'error')
            return redirect(url_for('business_auth.business_account_onboarding'))
        
        # Create business account
        business_account = BusinessAccount(
            name=business_name,
            account_type='customer',
            status='active',
            contact_email=admin_email,
            contact_name=f"{admin_first_name} {admin_last_name}"
        )
        
        db.session.add(business_account)
        db.session.flush()  # Get the ID
        
        # Assign license using LicenseService
        from license_service import LicenseService
        from license_templates import LicenseTemplateManager
        
        license_template = LicenseTemplateManager.get_template(license_template_id)
        if not license_template:
            flash('Invalid license template selected.', 'error')
            db.session.rollback()
            return redirect(url_for('business_auth.business_account_onboarding'))
        
        # Assign license to the business account
        license_result = LicenseService.assign_license_from_template(
            business_account_id=business_account.id,
            template_id=license_template_id,
            assigned_by_user_id=session.get('business_user_id'),
            notes=f"Initial license assignment for business account onboarding"
        )
        
        if not license_result.get('success'):
            flash(f'Failed to assign license: {license_result.get("error", "Unknown error")}', 'error')
            db.session.rollback()
            return redirect(url_for('business_auth.business_account_onboarding'))
        
        # Create admin user (not activated yet)
        admin_user = BusinessAccountUser(
            business_account_id=business_account.id,
            email=admin_email,
            first_name=admin_first_name,
            last_name=admin_last_name,
            role='business_account_admin',
            is_active_user=True,
            email_verified=False,
            password_hash=generate_password_hash('temporary_password_to_be_changed')  # Temporary password
        )
        
        # Generate invitation token
        invitation_token = admin_user.generate_invitation_token()
        
        db.session.add(admin_user)
        db.session.commit()
        
        # Audit log the creation IMMEDIATELY after commit (regardless of email outcome)
        try:
            from audit_utils import queue_audit_log
            queue_audit_log(
                business_account_id=business_account.id,
                action_type='business_account_created',
                resource_type='business_account',
                details={
                    'business_name': business_name,
                    'admin_email': admin_email,
                    'license_template': license_template_id,
                    'created_by': session.get('business_user_id')
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to log business account creation audit: {audit_error}")
        
        # Create EmailDelivery record for tracking
        email_delivery = EmailDelivery()
        email_delivery.business_account_id = business_account.id
        email_delivery.email_type = 'business_account_invitation'
        email_delivery.recipient_email = admin_email
        email_delivery.recipient_name = f"{admin_first_name} {admin_last_name}"
        email_delivery.subject = f"Welcome to VOÏA - Activate Your Business Account"
        email_delivery.status = 'pending'
        
        db.session.add(email_delivery)
        db.session.flush()  # Get the ID
        
        # Send invitation email using platform owner's email service
        # NOTE: Use platform_owner business account's SMTP config
        # because the newly created business account doesn't have email config yet
        from email_service import EmailService
        email_service = EmailService()
        
        # Get platform owner business account for SMTP configuration
        platform_owner = BusinessAccount.query.filter_by(account_type='platform_owner').first()
        platform_business_account_id = platform_owner.id if platform_owner else None
        
        email_result = email_service.send_business_account_invitation(
            user_email=admin_email,
            user_first_name=admin_first_name,
            user_last_name=admin_last_name,
            business_account_name=business_name,
            invitation_token=invitation_token,
            email_delivery_id=email_delivery.id,
            business_account_id=platform_business_account_id  # Use platform owner's SMTP config
        )
        
        db.session.commit()
        
        if email_result.get('success'):
            logger.info(f"Business account '{business_name}' created successfully with admin user {admin_email}")
            flash(f'Business account "{business_name}" created successfully! Invitation email sent to {admin_email}.', 'success')
        else:
            logger.warning(f"Business account created but invitation email failed: {email_result.get('error')}")
            flash(f'Business account "{business_name}" created successfully, but invitation email failed. Please manually send invitation to {admin_email}.', 'warning')
        
        # Redirect to license dashboard to show the new account
        return redirect(url_for('business_auth.license_dashboard'))
        
    except Exception as e:
        logger.error(f"Error creating business account: {e}")
        db.session.rollback()
        flash('Failed to create business account. Please try again.', 'error')
        return redirect(url_for('business_auth.business_account_onboarding'))


@business_auth_bp.route('/admin/onboarding/<int:user_id>/resend-invitation', methods=['POST'])
@require_platform_admin
def resend_business_account_invitation(user_id):
    """Resend activation invitation to a business account administrator"""
    try:
        # Get the user
        user = BusinessAccountUser.query.get(user_id)
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('business_auth.business_account_onboarding'))
        
        # Check if user is already activated
        if user.email_verified:
            flash(f'User {user.email} is already activated.', 'warning')
            return redirect(url_for('business_auth.business_account_onboarding'))
        
        # Get business account
        business_account = BusinessAccount.query.get(user.business_account_id)
        if not business_account:
            flash('Business account not found.', 'error')
            return redirect(url_for('business_auth.business_account_onboarding'))
        
        # Generate new invitation token
        invitation_token = user.generate_invitation_token()
        db.session.commit()
        
        # Create EmailDelivery record for tracking
        email_delivery = EmailDelivery()
        email_delivery.business_account_id = business_account.id
        email_delivery.email_type = 'business_account_invitation'
        email_delivery.recipient_email = user.email
        email_delivery.recipient_name = user.get_full_name()
        email_delivery.subject = f"Welcome to VOÏA - Activate Your Business Account"
        email_delivery.status = 'pending'
        
        db.session.add(email_delivery)
        db.session.flush()  # Get the ID
        
        # Send invitation email using platform owner's SMTP
        from email_service import EmailService
        email_service = EmailService()
        
        platform_owner = BusinessAccount.query.filter_by(account_type='platform_owner').first()
        platform_business_account_id = platform_owner.id if platform_owner else None
        
        email_result = email_service.send_business_account_invitation(
            user_email=user.email,
            user_first_name=user.first_name,
            user_last_name=user.last_name,
            business_account_name=business_account.name,
            invitation_token=invitation_token,
            email_delivery_id=email_delivery.id,
            business_account_id=platform_business_account_id
        )
        
        db.session.commit()
        
        # Log the resend attempt
        from audit_utils import queue_audit_log
        queue_audit_log(
            business_account_id=business_account.id,
            action_type='invitation_resent',
            resource_type='business_account_user',
            resource_id=user.id,
            details={
                'user_email': user.email,
                'user_id': user.id,
                'user_name': user.get_full_name(),
                'business_account_name': business_account.name,
                'resent_by': session.get('business_user_id'),
                'email_success': email_result.get('success')
            }
        )
        
        if email_result.get('success'):
            logger.info(f"Invitation resent successfully to {user.email} for business account {business_account.name}")
            flash(f'Invitation email resent successfully to {user.email}.', 'success')
        else:
            logger.warning(f"Failed to resend invitation to {user.email}: {email_result.get('error')}")
            flash(f'Failed to resend invitation email: {email_result.get("error")}', 'error')
        
        return redirect(url_for('business_auth.business_account_onboarding'))
        
    except Exception as e:
        logger.error(f"Error resending business account invitation: {e}")
        db.session.rollback()
        flash('Failed to resend invitation. Please try again.', 'error')
        return redirect(url_for('business_auth.business_account_onboarding'))


# ==== BUSINESS ACCOUNT ADMIN ONBOARDING FLOW ====

@business_auth_bp.route('/onboarding')
@require_business_auth
def onboarding_redirect():
    """Redirect to onboarding progress dashboard"""
    try:
        business_user_id = session.get('business_user_id')
        current_user = BusinessAccountUser.query.get(business_user_id)
        
        if not current_user or not current_user.requires_onboarding():
            # User doesn't need onboarding, redirect to admin panel
            return redirect(url_for('business_auth.admin_panel'))
        
        # Initialize onboarding if needed
        if not current_user.onboarding_progress:
            current_user.initialize_onboarding()
            db.session.commit()
        
        # Redirect to progress dashboard (self-assessment hub)
        return redirect(url_for('business_auth.onboarding_progress'))
        
    except Exception as e:
        logger.error(f"Error in onboarding redirect: {e}")
        flash('Error accessing onboarding. Please try again.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@business_auth_bp.route('/onboarding/progress')
@require_business_auth
def onboarding_progress():
    """Display onboarding progress dashboard"""
    try:
        business_user_id = session.get('business_user_id')
        current_user = BusinessAccountUser.query.get(business_user_id)
        
        if not current_user:
            flash('Authentication required.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Check if user is admin (only admins have onboarding)
        if current_user.role not in ['admin', 'business_account_admin']:
            flash('Access denied. This feature is for administrators only.', 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        # Get license type for flow configuration
        from license_service import LicenseService
        license_info = LicenseService.get_license_info(current_user.business_account_id)
        license_type = license_info.get('license_type', 'core')
        
        # Import onboarding configuration
        from onboarding_config import OnboardingFlowManager
        
        # Initialize onboarding if needed
        if not current_user.onboarding_progress:
            current_user.initialize_onboarding()
            db.session.commit()
        
        # Get all steps for this license
        all_steps = OnboardingFlowManager.get_steps_for_license(license_type)
        
        # Get progress data
        progress = current_user.get_onboarding_progress()
        progress_percentage = OnboardingFlowManager.get_progress_percentage(progress, license_type)
        current_step = current_user.get_current_onboarding_step()
        
        # Build step status list with detailed information
        step_statuses = []
        for i, step_def in enumerate(all_steps):
            step_data = progress.get('steps', {}).get(step_def.step_id, {})
            is_completed = step_data.get('completed', False)
            is_current = (step_def.step_id == current_step)
            
            # Determine status
            if is_completed:
                status = 'completed'
                status_label = _('Completed')
                status_icon = 'fa-check-circle'
                status_class = 'status-completed'
            elif is_current:
                status = 'in_progress'
                status_label = _('In Progress')
                status_icon = 'fa-play-circle'
                status_class = 'status-in-progress'
            else:
                status = 'not_started'
                status_label = _('Not Started')
                status_icon = 'fa-circle'
                status_class = 'status-not-started'
            
            step_statuses.append({
                'step_id': step_def.step_id,
                'name': step_def.name,
                'description': step_def.description,
                'target_link': step_def.target_link,
                'required': step_def.required,
                'status': status,
                'status_label': status_label,
                'status_icon': status_icon,
                'status_class': status_class,
                'is_completed': is_completed,
                'is_current': is_current,
                'step_number': i + 1,
                'completed_at': step_data.get('completed_at')
            })
        
        return render_template('business_auth/onboarding_progress.html',
                             current_user=current_user,
                             business_account=current_user.business_account,
                             all_steps=step_statuses,
                             progress_percentage=progress_percentage,
                             current_step=current_step,
                             is_onboarding_completed=current_user.onboarding_completed,
                             total_steps=len(all_steps))
        
    except Exception as e:
        logger.error(f"Error displaying onboarding progress: {e}")
        flash('Error loading onboarding progress. Please try again.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@business_auth_bp.route('/onboarding/progress/update', methods=['POST'])
@require_business_auth
def onboarding_update_progress():
    """Update onboarding progress based on user self-assessment"""
    try:
        business_user_id = session.get('business_user_id')
        current_user = BusinessAccountUser.query.get(business_user_id)
        
        if not current_user:
            flash('Authentication required.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Check if user is admin (only admins have onboarding)
        if current_user.role not in ['admin', 'business_account_admin']:
            flash('Access denied. This feature is for administrators only.', 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        # Get license type for flow configuration
        from license_service import LicenseService
        license_info = LicenseService.get_license_info(current_user.business_account_id)
        license_type = license_info.get('license_type', 'core')
        
        # Import onboarding configuration
        from onboarding_config import OnboardingFlowManager
        
        # Get all steps for this license
        all_steps = OnboardingFlowManager.get_steps_for_license(license_type)
        
        # Initialize onboarding if needed
        if not current_user.onboarding_progress:
            current_user.initialize_onboarding()
        
        # Get current progress - make a deep copy to avoid mutation issues
        import copy
        progress = copy.deepcopy(current_user.get_onboarding_progress())
        if 'steps' not in progress:
            progress['steps'] = {}
        
        # Update each step based on checkbox values
        from datetime import datetime
        for step_def in all_steps:
            step_id = step_def.step_id
            checkbox_name = f'step_{step_id}'
            is_checked = request.form.get(checkbox_name) == '1'
            
            # Initialize step if not exists
            if step_id not in progress['steps']:
                progress['steps'][step_id] = {}
            
            # Update completion status
            if is_checked and not progress['steps'][step_id].get('completed', False):
                # User just marked it complete
                progress['steps'][step_id]['completed'] = True
                progress['steps'][step_id]['completed_at'] = datetime.utcnow().isoformat()
            elif not is_checked and progress['steps'][step_id].get('completed', False):
                # User unchecked it
                progress['steps'][step_id]['completed'] = False
                if 'completed_at' in progress['steps'][step_id]:
                    del progress['steps'][step_id]['completed_at']
        
        # Save progress - flag as modified for SQLAlchemy JSON column
        current_user.onboarding_progress = progress
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(current_user, 'onboarding_progress')
        
        # Check if all required steps are complete
        all_required_complete = all(
            progress['steps'].get(s.step_id, {}).get('completed', False)
            for s in all_steps if s.required
        )
        
        if all_required_complete and not current_user.onboarding_completed:
            current_user.onboarding_completed = True
            flash('Congratulations! You have completed all required onboarding steps.', 'success')
        elif not all_required_complete and current_user.onboarding_completed:
            current_user.onboarding_completed = False
        
        db.session.commit()
        
        flash('Onboarding progress updated.', 'success')
        return redirect(url_for('business_auth.onboarding_progress'))
        
    except Exception as e:
        logger.error(f"Error updating onboarding progress: {e}")
        db.session.rollback()
        flash('Error updating progress. Please try again.', 'error')
        return redirect(url_for('business_auth.onboarding_progress'))


@business_auth_bp.route('/onboarding/<step>')
@require_business_auth
def onboarding_step(step):
    """Display specific onboarding step"""
    try:
        business_user_id = session.get('business_user_id')
        current_user = BusinessAccountUser.query.get(business_user_id)
        
        if not current_user:
            flash('Authentication required.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Check if user needs onboarding
        if not current_user.requires_onboarding():
            return redirect(url_for('business_auth.admin_panel'))
        
        # Get license type for flow configuration
        from license_service import LicenseService
        license_info = LicenseService.get_license_info(current_user.business_account_id)
        license_type = license_info.get('license_type', 'core')
        
        # Import onboarding configuration
        from onboarding_config import OnboardingFlowManager
        
        # Get step definition
        step_definition = OnboardingFlowManager.get_step_definition(step)
        if not step_definition:
            flash('Invalid onboarding step.', 'error')
            return redirect(url_for('business_auth.onboarding'))
        
        # Validate step access
        progress = current_user.get_onboarding_progress()
        if not OnboardingFlowManager.validate_step_access(step, progress, license_type):
            flash('Please complete previous steps first.', 'error')
            return redirect(url_for('business_auth.onboarding'))
        
        # Get all steps for progress tracking
        all_steps = OnboardingFlowManager.get_steps_for_license(license_type)
        progress_percentage = OnboardingFlowManager.get_progress_percentage(progress, license_type)
        
        # Get existing data for pre-populating forms
        context_data = {}
        
        if step == 'smtp':
            # Pre-populate SMTP configuration if exists
            from models import EmailConfiguration
            email_config = EmailConfiguration.query.filter_by(
                business_account_id=current_user.business_account_id
            ).first()
            if email_config:
                context_data['email_config'] = email_config
                
        elif step == 'users':
            # Get existing users for display
            existing_users = BusinessAccountUser.query.filter_by(
                business_account_id=current_user.business_account_id
            ).filter(BusinessAccountUser.id != current_user.id).all()
            context_data['existing_users'] = existing_users
        
        return render_template(f'business_auth/{step_definition.template}',
                             step=step_definition,
                             progress=progress,
                             progress_percentage=progress_percentage,
                             all_steps=all_steps,
                             current_step_index=next((i for i, s in enumerate(all_steps) if s.step_id == step), 0),
                             business_account=current_user.business_account,
                             current_user=current_user,
                             **context_data)
        
    except Exception as e:
        logger.error(f"Error displaying onboarding step '{step}': {e}")
        flash('Error loading onboarding step. Please try again.', 'error')
        return redirect(url_for('business_auth.onboarding'))


@business_auth_bp.route('/onboarding/<step>/complete', methods=['POST'])
@require_business_auth
def complete_onboarding_step(step):
    """Complete an onboarding step"""
    try:
        business_user_id = session.get('business_user_id')
        current_user = BusinessAccountUser.query.get(business_user_id)
        
        if not current_user:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        # Check if user needs onboarding
        if not current_user.requires_onboarding():
            return jsonify({'success': True, 'redirect': url_for('business_auth.admin_panel')})
        
        # Get license type for flow configuration
        from license_service import LicenseService
        license_info = LicenseService.get_license_info(current_user.business_account_id)
        license_type = license_info.get('license_type', 'core')
        
        # Import onboarding configuration
        from onboarding_config import OnboardingFlowManager, OnboardingValidation
        
        # Get step definition
        step_definition = OnboardingFlowManager.get_step_definition(step)
        if not step_definition:
            return jsonify({'success': False, 'error': 'Invalid onboarding step'}), 400
        
        # Validate step completion
        form_data = request.form.to_dict()
        validation_method = step_definition.validation_method
        
        is_valid = True
        validation_message = "Step completed successfully"
        
        if validation_method:
            validator = OnboardingValidation.get_validator(validation_method)
            if validator:
                is_valid, validation_message = validator(current_user, form_data)
        
        if not is_valid:
            return jsonify({'success': False, 'error': validation_message}), 400
        
        # Mark step as completed
        current_user.complete_onboarding_step(step)
        db.session.commit()
        
        # Check if all onboarding is complete
        if current_user.onboarding_completed:
            return jsonify({
                'success': True, 
                'completed': True,
                'message': 'Onboarding completed successfully!',
                'redirect': url_for('business_auth.admin_panel')
            })
        
        # Get next step
        next_step = OnboardingFlowManager.get_next_step(step, license_type)
        if next_step:
            return jsonify({
                'success': True,
                'message': validation_message,
                'redirect': url_for('business_auth.onboarding_step', step=next_step)
            })
        else:
            # This shouldn't happen, but handle gracefully
            current_user.complete_onboarding()
            db.session.commit()
            return jsonify({
                'success': True,
                'completed': True,
                'message': 'Onboarding completed successfully!',
                'redirect': url_for('business_auth.admin_panel')
            })
        
    except Exception as e:
        logger.error(f"Error completing onboarding step '{step}': {e}")
        return jsonify({'success': False, 'error': 'Failed to complete step. Please try again.'}), 500


@business_auth_bp.route('/activate/<token>')
def activate_account(token):
    """Account activation page for business account admin users"""
    try:
        # Find user by invitation token
        user = BusinessAccountUser.query.filter_by(invitation_token=token).first()
        
        if not user:
            flash('Invalid activation link.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Check if token is valid and not expired
        if not user.is_invitation_valid():
            flash('Activation link has expired. Please contact support for a new invitation.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Check if already activated
        if user.is_activated():
            flash('Account already activated. Please log in.', 'info')
            return redirect(url_for('business_auth.login'))
        
        return render_template('business_auth/activate_account.html',
                             user=user,
                             business_account=user.business_account,
                             token=token)
    
    except Exception as e:
        logger.error(f"Error loading activation page: {e}")
        flash('Error loading activation page.', 'error')
        return redirect(url_for('business_auth.login'))


@business_auth_bp.route('/activate/<token>', methods=['POST'])
def process_account_activation(token):
    """Process account activation with password setup"""
    try:
        # Find user by invitation token
        user = BusinessAccountUser.query.filter_by(invitation_token=token).first()
        
        if not user:
            flash('Invalid activation link.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Check if token is valid and not expired
        if not user.is_invitation_valid():
            flash('Activation link has expired. Please contact support for a new invitation.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Check if already activated
        if user.is_activated():
            flash('Account already activated. Please log in.', 'info')
            return redirect(url_for('business_auth.login'))
        
        # Get form data
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validate password
        if not password:
            flash('Password is required.', 'error')
            return render_template('business_auth/activate_account.html',
                                 user=user,
                                 business_account=user.business_account,
                                 token=token)
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('business_auth/activate_account.html',
                                 user=user,
                                 business_account=user.business_account,
                                 token=token)
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('business_auth/activate_account.html',
                                 user=user,
                                 business_account=user.business_account,
                                 token=token)
        
        # Activate account
        user.activate_account(password)
        db.session.commit()
        
        logger.info(f"Business account user {user.email} activated successfully")
        flash(f'Welcome, {user.get_full_name()}! Your account has been activated successfully.', 'success')
        
        # Audit log the activation
        try:
            from audit_utils import queue_audit_log
            queue_audit_log(
                business_account_id=user.business_account_id,
                action_type='user_account_activated',
                resource_type='business_account_user',
                details={
                    'user_email': user.email,
                    'user_name': user.get_full_name(),
                    'business_account_name': user.business_account.name
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to log user activation audit: {audit_error}")
        
        # Redirect to login page
        return redirect(url_for('business_auth.login'))
        
    except Exception as e:
        logger.error(f"Error processing account activation: {e}")
        flash('Failed to activate account. Please try again.', 'error')
        return render_template('business_auth/activate_account.html',
                             user=None,
                             business_account=None,
                             token=token)


# ==== AUTHENTICATION ROUTES ====

@business_auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Business account login page and handler"""
    if request.method == 'GET':
        # Clear non-authentication flash messages to prevent message leakage from other pages
        # Only preserve authentication-related messages
        auth_keywords = ['log in', 'login', 'session', 'authentication', 'password', 'account', 'suspended', 'active', 'token']
        
        # Get all flash messages
        flashed_messages = get_flashed_messages(with_categories=True)
        
        # Filter and re-flash only authentication-related messages
        for category, message in flashed_messages:
            message_lower = message.lower()
            if any(keyword in message_lower for keyword in auth_keywords):
                flash(message, category)
        
        # Show login form
        return render_template('business_auth/login.html')
    
    # Handle login submission
    try:
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
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
        session_duration = 168  # Always 7 days (improved user experience)
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
        session['business_user_name'] = user.get_full_name()  # User's actual name for display
        session['user_role'] = user.role
        session.permanent = True  # 7-day session lifetime for all users (configured in app.py)
        
        # Load user's language preference into session (persistent across devices)
        user_language = user.get_language_preference()
        if user_language:
            session['language'] = user_language
        
        logger.info(f"Business account user {email} logged in successfully")
        flash(f'Welcome back, {user.get_full_name()}!', 'success')
        
        # Audit log successful login
        try:
            from audit_utils import audit_user_login
            audit_user_login(
                user_email=user.email,
                user_name=user.get_full_name(),
                business_account_id=user.business_account_id,
                ip_address=request.environ.get('HTTP_X_FORWARDED_FOR', 
                                             request.environ.get('REMOTE_ADDR', ''))[:45]
            )
        except Exception as audit_error:
            logger.error(f"Failed to audit login for {email}: {audit_error}")
        
        # Redirect to admin panel
        return redirect(url_for('business_auth.admin_panel'))
        
    except Exception as e:
        logger.error(f"Business login error: {e}")
        flash('Login failed. Please try again.', 'error')
        return render_template('business_auth/login.html')


@business_auth_bp.route('/logout')
def logout():
    """Business account logout"""
    # Capture user info before clearing session
    user_email = None
    user_name = None
    business_account_id = session.get('business_account_id')
    
    try:
        # Get user info for audit before clearing session
        user_id = session.get('business_user_id')
        if user_id:
            user = BusinessAccountUser.query.get(user_id)
            if user:
                user_email = user.email
                user_name = user.get_full_name()
    except Exception as e:
        logger.warning(f"Could not get user info for logout audit: {e}")
    
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
        
        # Audit log successful logout
        if user_email and business_account_id:
            try:
                from audit_utils import audit_user_logout
                audit_user_logout(
                    user_email=user_email,
                    user_name=user_name,
                    business_account_id=business_account_id,
                    ip_address=request.environ.get('HTTP_X_FORWARDED_FOR', 
                                                 request.environ.get('REMOTE_ADDR', ''))[:45]
                )
            except Exception as audit_error:
                logger.error(f"Failed to audit logout for {user_email}: {audit_error}")
        
    except Exception as e:
        logger.error(f"Business logout error: {e}")
        # Even on error, clear flash messages to prevent accumulation
        from flask import get_flashed_messages
        get_flashed_messages()
        flash('Logout completed. Please log in again if needed.', 'info')
    
    return redirect(url_for('business_auth.login'))


# ==== PASSWORD RESET ROUTES ====

@business_auth_bp.route('/forgot-password', methods=['GET'])
def forgot_password():
    """Forgot password page - request password reset"""
    return render_template('business_auth/forgot_password.html')


@business_auth_bp.route('/forgot-password/request', methods=['POST'])
@rate_limit(limit=3)  # 3 requests per minute per IP
def forgot_password_request():
    """Handle password reset request and send email"""
    try:
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Please enter your email address.', 'error')
            return redirect(url_for('business_auth.forgot_password'))
        
        # Find user by email
        user = BusinessAccountUser.query.filter_by(email=email).first()
        
        # Always show success message (security: don't reveal if email exists)
        flash('If an account exists with that email, you will receive a password reset link shortly.', 'success')
        
        if user and user.is_active_user:
            # Generate password reset token
            reset_token = user.generate_password_reset_token()
            db.session.commit()
            
            # Send password reset email
            from email_service import email_service
            result = email_service.send_password_reset_email(
                user_email=user.email,
                user_first_name=user.first_name,
                user_last_name=user.last_name,
                reset_token=reset_token,
                business_account_id=user.business_account_id
            )
            
            if result['success']:
                logger.info(f"Password reset email sent to {email}")
            else:
                logger.error(f"Failed to send password reset email to {email}: {result.get('error')}")
        else:
            # Log attempt for inactive or non-existent users
            logger.warning(f"Password reset requested for non-existent or inactive user: {email}")
        
        return redirect(url_for('business_auth.login'))
        
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('business_auth.forgot_password'))


@business_auth_bp.route('/reset-password/<token>', methods=['GET'])
def reset_password(token):
    """Reset password page with token validation"""
    try:
        # Find user by reset token
        user = BusinessAccountUser.query.filter_by(password_reset_token=token).first()
        
        if not user:
            flash('Invalid or expired password reset link.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Validate token
        if not user.validate_password_reset_token(token):
            flash('This password reset link has expired. Please request a new one.', 'error')
            return redirect(url_for('business_auth.forgot_password'))
        
        # Show reset password form
        return render_template('business_auth/reset_password.html', token=token)
        
    except Exception as e:
        logger.error(f"Reset password page error: {e}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('business_auth.login'))


@business_auth_bp.route('/reset-password/<token>/confirm', methods=['POST'])
@rate_limit(limit=5)  # 5 attempts per minute per IP
def reset_password_confirm(token):
    """Handle password reset confirmation"""
    try:
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate inputs
        if not password or not confirm_password:
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('business_auth.reset_password', token=token))
        
        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'error')
            return redirect(url_for('business_auth.reset_password', token=token))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return redirect(url_for('business_auth.reset_password', token=token))
        
        # Find user by reset token
        user = BusinessAccountUser.query.filter_by(password_reset_token=token).first()
        
        if not user:
            flash('Invalid or expired password reset link.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Validate token
        if not user.validate_password_reset_token(token):
            flash('This password reset link has expired. Please request a new one.', 'error')
            return redirect(url_for('business_auth.forgot_password'))
        
        # Reset password
        user.reset_password(password)
        db.session.commit()
        
        # Audit log password reset
        try:
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
            queue_audit_log(
                business_account_id=user.business_account_id,
                action_type='password_reset',
                user_email=user.email,
                user_name=user.get_full_name(),
                ip_address=client_ip,
                details={
                    'method': 'self_service_reset',
                    'via': 'forgot_password_flow'
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to audit password reset for {user.email}: {audit_error}")
        
        logger.info(f"Password reset successful for user {user.email}")
        flash('Your password has been reset successfully. Please log in with your new password.', 'success')
        
        return redirect(url_for('business_auth.login'))
        
    except Exception as e:
        logger.error(f"Password reset confirmation error: {e}")
        db.session.rollback()
        flash('An error occurred while resetting your password. Please try again.', 'error')
        return redirect(url_for('business_auth.reset_password', token=token))


# ==== UI VERSION TOGGLE (PHASE 2B FEATURE FLAGS) ====

@business_auth_bp.route('/toggle-ui-version', methods=['POST'])
@require_business_auth
def toggle_ui_version():
    """Toggle between v1 (current) and v2 (sidebar) UI versions"""
    from feature_flags import feature_flags
    
    try:
        # Check if toggling is enabled
        if not feature_flags.can_user_toggle():
            logger.warning(f"User {session.get('business_user_id')} attempted UI toggle when disabled")
            if request.is_json:
                return jsonify({'success': False, 'error': 'UI toggling is not enabled'}), 403
            else:
                flash('UI version switching is currently disabled.', 'error')
                return redirect(request.referrer or url_for('business_auth.admin_panel'))
        
        # Safely get requested version from JSON or form data
        requested_version = None
        json_data = request.get_json(silent=True)  # Returns None for malformed JSON
        if json_data:
            requested_version = json_data.get('version')
        elif request.form:
            requested_version = request.form.get('version')
        
        current_version = feature_flags.get_ui_version()
        
        if not requested_version:
            # Toggle: v1 → v2, v2 → v1
            requested_version = 'v2' if current_version == 'v1' else 'v1'
        
        # Validate and set preference
        if feature_flags.set_user_ui_preference(requested_version):
            logger.info(f"User {session.get('business_user_id')} toggled UI to {requested_version}")
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'ui_version': requested_version,
                    'message': f'Switched to UI version {requested_version}'
                })
            else:
                flash(f'UI switched to version {requested_version}. Page will reload.', 'success')
                # Redirect to same page but strip ?ui parameter so session preference takes effect
                from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
                redirect_url = request.referrer or url_for('business_auth.admin_panel')
                
                # Parse URL and remove 'ui' parameter
                parsed = urlparse(redirect_url)
                query_params = parse_qs(parsed.query)
                query_params.pop('ui', None)  # Remove ui parameter
                
                # Rebuild URL without ui parameter
                new_query = urlencode(query_params, doseq=True)
                redirect_url = urlunparse((
                    parsed.scheme, parsed.netloc, parsed.path,
                    parsed.params, new_query, parsed.fragment
                ))
                
                return redirect(redirect_url)
        else:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Invalid UI version'}), 400
            else:
                flash('Failed to switch UI version.', 'error')
                return redirect(request.referrer or url_for('business_auth.admin_panel'))
    
    except Exception as e:
        logger.error(f"UI toggle error: {e}")
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        else:
            flash('Error toggling UI version.', 'error')
            return redirect(request.referrer or url_for('business_auth.admin_panel'))


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
        
        # PERFORMANCE: Pass business_account to avoid duplicate query
        from license_service import LicenseService
        is_platform_admin = current_business_user.is_platform_admin() if current_business_user else False
        license_info = LicenseService.get_license_info(
            business_account.id, 
            business_account=business_account,
            is_platform_admin=is_platform_admin
        )
        
        # Load admin panel data for all account types (security enforced by decorators)
        from models import Campaign, SurveyResponse, Participant, CampaignParticipant, EmailDelivery
        from email_service import email_service
        
        # Get campaigns for this business account
        campaigns = Campaign.query.filter_by(
            business_account_id=business_account.id
        ).order_by(Campaign.created_at.desc()).limit(5).all()
        
        # Get recent responses (properly scoped to business account)
        recent_responses = SurveyResponse.query.join(Campaign).filter(
            Campaign.business_account_id == business_account.id
        ).order_by(SurveyResponse.created_at.desc()).limit(10).all()
        
        # OPTIMIZATION: Consolidate stats into 3 batch queries instead of 7 separate COUNTs
        from sqlalchemy import func
        
        # Query 1: Get email stats grouped by status (replaces 4 COUNT queries)
        email_stats_raw = db.session.query(
            EmailDelivery.status,
            func.count(EmailDelivery.id)
        ).filter(
            EmailDelivery.business_account_id == business_account.id,
            EmailDelivery.email_type == 'participant_invitation'
        ).group_by(EmailDelivery.status).all()
        
        email_stats_dict = dict(email_stats_raw)
        total_invitations = sum(email_stats_dict.values())
        sent_invitations = email_stats_dict.get('sent', 0)
        failed_invitations = email_stats_dict.get('failed', 0)
        pending_invitations = email_stats_dict.get('pending', 0)
        
        # Query 2: Get basic entity counts (replaces 2 COUNT queries)
        total_campaigns = Campaign.query.filter_by(
            business_account_id=business_account.id
        ).count()
        
        total_participants = Participant.query.filter_by(
            business_account_id=business_account.id
        ).count()
        
        # Query 3: Get response count
        total_responses = SurveyResponse.query.join(Campaign).filter(
            Campaign.business_account_id == business_account.id
        ).count()
        
        # OPTIMIZATION: Pre-compute all campaign metrics in batch queries (eliminates N+1)
        campaign_ids = [c.id for c in campaigns]
        
        # Batch query: Get participant counts for all campaigns
        participant_counts = dict(
            db.session.query(
                CampaignParticipant.campaign_id,
                func.count(CampaignParticipant.id)
            ).filter(
                CampaignParticipant.campaign_id.in_(campaign_ids),
                CampaignParticipant.business_account_id == business_account.id
            ).group_by(CampaignParticipant.campaign_id).all()
        ) if campaign_ids else {}
        
        # Batch query: Get invitation stats for all campaigns grouped by campaign_id and status
        invitation_stats_raw = db.session.query(
            EmailDelivery.campaign_id,
            EmailDelivery.status,
            func.count(EmailDelivery.id)
        ).filter(
            EmailDelivery.campaign_id.in_(campaign_ids),
            EmailDelivery.business_account_id == business_account.id,
            EmailDelivery.email_type == 'participant_invitation'
        ).group_by(EmailDelivery.campaign_id, EmailDelivery.status).all() if campaign_ids else []
        
        # Build invitation stats lookup: {campaign_id: {'sent': X, 'failed': Y, 'pending': Z}}
        invitation_stats_by_campaign = {}
        for campaign_id, status, count in invitation_stats_raw:
            if campaign_id not in invitation_stats_by_campaign:
                invitation_stats_by_campaign[campaign_id] = {}
            invitation_stats_by_campaign[campaign_id][status] = count
        
        # Build active campaigns list using pre-computed data
        active_campaigns = []
        for campaign in campaigns:
            if campaign.is_active():
                participant_count = participant_counts.get(campaign.id, 0)
                campaign_inv_stats = invitation_stats_by_campaign.get(campaign.id, {})
                
                campaign_sent = campaign_inv_stats.get('sent', 0)
                campaign_failed = campaign_inv_stats.get('failed', 0)
                campaign_pending = campaign_inv_stats.get('pending', 0)
                campaign_invitations = campaign_sent + campaign_failed + campaign_pending
                
                campaign_data = campaign.to_dict(response_count=0)  # No query needed for admin panel
                campaign_data.update({
                    'participant_count': participant_count,
                    'invitation_stats': {
                        'total': campaign_invitations,
                        'sent': campaign_sent,
                        'pending': campaign_pending,
                        'can_send_invitations': participant_count > 0 and email_service.is_configured()
                    }
                })
                active_campaigns.append(campaign_data)
        
        # Get primary active campaign for analytics link
        primary_active_campaign_id = None
        if active_campaigns:
            primary_active_campaign_id = active_campaigns[0]['id']
        
        # OPTIMIZATION: Serialize all campaigns once without response_count to avoid N+1
        all_campaigns_data = [c.to_dict(response_count=0) for c in campaigns]
        
        # Get scheduler stats and campaign counts for Settings Hub
        from task_queue import task_queue
        scheduler_stats = task_queue.get_stats()
        campaign_counts = {
            'draft': Campaign.query.filter_by(business_account_id=business_account.id, status='draft').count(),
            'ready': Campaign.query.filter_by(business_account_id=business_account.id, status='ready').count(),
            'active': Campaign.query.filter_by(business_account_id=business_account.id, status='active').count(),
            'completed': Campaign.query.filter_by(business_account_id=business_account.id, status='completed').count()
        }
        
        # Build unified admin data for all account types
        admin_data = {
            'account_type': business_account.account_type,
            'campaigns': all_campaigns_data,
            'active_campaigns': active_campaigns,
            'recent_responses': [r.to_dict() for r in recent_responses],
            'primary_active_campaign_id': primary_active_campaign_id,
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
            'email_configured': email_service.is_configured(),
            'license_info': license_info,
            'scheduler_stats': scheduler_stats,
            'campaign_counts': campaign_counts
        }
        
        # Determine UI version (respects FORCE_V2_FOR_BUSINESS_USERS and SIDEBAR_ROLLOUT_PERCENTAGE)
        ui_version = feature_flags.get_ui_version(user_id=user_id)
        template_name = 'business_auth/admin_panel.html'
        if ui_version == 'v2':
            template_name = 'business_auth/admin_panel_v2.html'
            logger.info(f"Admin panel v2 for user {current_business_user.email} (ui_version={ui_version})")
        
        return render_template(template_name,
                             business_account=business_account,
                             current_user=current_business_user,
                             admin_data=admin_data)
        
    except Exception as e:
        logger.error(f"Admin panel error: {e}")
        flash('Error loading admin panel.', 'error')
        return redirect(url_for('business_auth.login'))


@business_auth_bp.route('/admin/business-analytics-hub')
@require_platform_admin
def business_analytics_hub():
    """Platform admin dashboard with system-wide metrics and management"""
    try:
        # Import required modules first
        from license_service import LicenseService
        from datetime import datetime, timedelta
        from models import BusinessAccount, BusinessAccountUser, Campaign, SurveyResponse, Participant
        
        # Get current user
        user_id = session.get('business_user_id')
        current_user = BusinessAccountUser.query.get(user_id)
        
        if not current_user:
            flash('User session invalid.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Import additional models for comprehensive metrics
        from sqlalchemy import func
        from models import CampaignParticipant
        
        # === BUSINESS ACCOUNT INTELLIGENCE ===
        total_accounts = BusinessAccount.query.count()
        active_accounts = BusinessAccount.query.filter_by(is_active=True).count() if hasattr(BusinessAccount, 'is_active') else total_accounts
        trial_accounts = BusinessAccount.query.filter_by(account_type='trial').count()
        customer_accounts = BusinessAccount.query.filter_by(account_type='customer').count()
        demo_accounts = BusinessAccount.query.filter_by(account_type='demo').count()
        platform_owner_accounts = BusinessAccount.query.filter_by(account_type='platform_owner').count()
        
        # === USER ENGAGEMENT ===
        total_users = BusinessAccountUser.query.count()
        total_active_users = BusinessAccountUser.query.filter_by(is_active_user=True).count()
        total_inactive_users = total_users - total_active_users
        avg_users_per_account = round(total_users / max(total_accounts, 1), 1)
        
        # === CAMPAIGN PERFORMANCE ===
        total_campaigns = Campaign.query.count()
        draft_campaigns = Campaign.query.filter_by(status='draft').count()
        ready_campaigns = Campaign.query.filter_by(status='ready').count()
        active_campaigns = Campaign.query.filter_by(status='active').count()
        completed_campaigns = Campaign.query.filter_by(status='completed').count()
        cancelled_campaigns = Campaign.query.filter_by(status='cancelled').count()
        
        # Time-based metrics
        current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        campaigns_this_month = Campaign.query.filter(Campaign.created_at >= current_month_start).count()
        
        # === PARTICIPANT INTELLIGENCE ===
        total_participants = Participant.query.count()
        
        # Participants per business account
        participant_counts = db.session.query(
            Participant.business_account_id,
            func.count(Participant.id).label('participant_count')
        ).group_by(Participant.business_account_id).all()
        
        avg_participants_per_account = round(total_participants / max(total_accounts, 1), 1)
        
        # Campaign-participant assignments
        total_assignments = CampaignParticipant.query.count()
        avg_participants_per_campaign = round(total_assignments / max(total_campaigns, 1), 1)
        
        # === SURVEY & RESPONSE ANALYTICS ===
        total_responses = SurveyResponse.query.count()
        responses_this_month = SurveyResponse.query.filter(SurveyResponse.created_at >= current_month_start).count()
        
        # Calculate completion rate (responses vs total assignments)
        completion_rate = round((total_responses / max(total_assignments, 1)) * 100, 1)
        
        # === LICENSE UTILIZATION ===
        license_summary = {
            'total_licensed_accounts': 0,
            'high_usage_accounts': [],
            'accounts_by_license_type': {
                'trial': 0, 'core': 0, 'plus': 0, 'pro': 0, 'enterprise': 0
            }
        }
        
        all_accounts = BusinessAccount.query.filter(BusinessAccount.account_type.in_(['trial', 'customer'])).all()
        
        for account in all_accounts:
            try:
                license_info = LicenseService.get_license_info(account.id)
                license_type = license_info.get('license_type', 'trial')
                license_summary['accounts_by_license_type'][license_type] = license_summary['accounts_by_license_type'].get(license_type, 0) + 1
                license_summary['total_licensed_accounts'] += 1
                
                # Check for high usage (over 80% of limits)
                users_usage = (license_info.get('users_used', 0) / max(license_info.get('users_limit', 1), 1)) * 100
                campaigns_usage = (license_info.get('campaigns_used', 0) / max(license_info.get('campaigns_limit', 1), 1)) * 100
                
                if users_usage > 80 or campaigns_usage > 80:
                    license_summary['high_usage_accounts'].append({
                        'account': account,
                        'users_usage': round(users_usage, 1),
                        'campaigns_usage': round(campaigns_usage, 1),
                        'license_type': license_type
                    })
            except Exception as e:
                logger.warning(f"Error getting license info for account {account.id}: {e}")
                continue
        
        # === RECENT ACTIVITY ===
        recent_accounts = BusinessAccount.query.order_by(BusinessAccount.created_at.desc()).limit(5).all()
        
        # Most active accounts by campaign volume
        most_active_accounts = db.session.query(
            Campaign.business_account_id,
            BusinessAccount.name,
            func.count(Campaign.id).label('campaign_count')
        ).join(
            BusinessAccount, Campaign.business_account_id == BusinessAccount.id
        ).group_by(
            Campaign.business_account_id, BusinessAccount.name
        ).order_by(
            func.count(Campaign.id).desc()
        ).limit(5).all()
        
        # Platform admin count for template compatibility
        platform_admin_count = BusinessAccountUser.query.filter_by(role='platform_admin').count()
        
        # === BUILD DASHBOARD DATA (Compatible with existing template) ===
        dashboard_data = {
            'overview_metrics': {
                'total_accounts': total_accounts,
                'active_accounts': active_accounts,
                'trial_accounts': trial_accounts,
                'customer_accounts': customer_accounts,
                'demo_accounts': demo_accounts,
                'platform_owner_accounts': platform_owner_accounts,
                'total_active_users': total_active_users,
                'platform_admin_count': platform_admin_count,
                'campaigns_this_month': campaigns_this_month,
                'active_campaigns': active_campaigns,
                'responses_this_month': responses_this_month
            },
            'recent_accounts': [account.to_dict() for account in recent_accounts],
            'high_usage_accounts': license_summary['high_usage_accounts'][:10],  # Top 10 high usage accounts
            
            # Extended metrics for comprehensive platform insights
            'detailed_metrics': {
                'business_intelligence': {
                    'total_accounts': total_accounts,
                    'active_accounts': active_accounts,
                    'trial_accounts': trial_accounts,
                    'customer_accounts': customer_accounts,
                    'demo_accounts': demo_accounts,
                    'platform_owner_accounts': platform_owner_accounts
                },
                'user_engagement': {
                    'total_users': total_users,
                    'total_active_users': total_active_users,
                    'total_inactive_users': total_inactive_users,
                    'avg_users_per_account': avg_users_per_account
                },
                'campaign_performance': {
                    'total_campaigns': total_campaigns,
                    'draft_campaigns': draft_campaigns,
                    'ready_campaigns': ready_campaigns,
                    'active_campaigns': active_campaigns,
                    'completed_campaigns': completed_campaigns,
                    'cancelled_campaigns': cancelled_campaigns,
                    'campaigns_this_month': campaigns_this_month
                },
                'participant_intelligence': {
                    'total_participants': total_participants,
                    'avg_participants_per_account': avg_participants_per_account,
                    'total_assignments': total_assignments,
                    'avg_participants_per_campaign': avg_participants_per_campaign
                },
                'survey_analytics': {
                    'total_responses': total_responses,
                    'responses_this_month': responses_this_month,
                    'completion_rate': completion_rate
                },
                'license_utilization': license_summary,
                'recent_activity': {
                    'recent_accounts': [account.to_dict() for account in recent_accounts],
                    'most_active_accounts': [
                        {
                            'business_name': acc.name,
                            'campaign_count': acc.campaign_count
                        } for acc in most_active_accounts
                    ]
                }
            }
        }
        
        # === USER DIRECTORY: Optimized query with eager loading ===
        from sqlalchemy.orm import selectinload
        
        # Fetch top 20 recent business accounts with their users in 2 queries (optimized)
        accounts_with_users = BusinessAccount.query\
            .options(selectinload(BusinessAccount.users))\
            .order_by(BusinessAccount.created_at.desc())\
            .limit(20)\
            .all()
        
        # Prepare user directory data
        user_directory = []
        for account in accounts_with_users:
            user_list = []
            for user in account.users:
                user_list.append({
                    'id': user.id,
                    'full_name': user.get_full_name(),
                    'email': user.email,
                    'role': user.role,
                    'is_active': user.is_active_user,
                    'last_login': user.last_login_at.strftime('%Y-%m-%d %H:%M') if user.last_login_at else 'Never'
                })
            
            user_directory.append({
                'account_id': account.id,
                'account_name': account.name,
                'account_type': account.account_type,
                'user_count': len(user_list),
                'users': user_list
            })
        
        dashboard_data['user_directory'] = user_directory
        
        logger.info(f"Platform admin {current_user.email} accessed platform dashboard")
        
        return render_template('business_auth/platform_dashboard.html',
                             current_user=current_user,
                             dashboard_data=dashboard_data)
    
    except Exception as e:
        logger.error(f"Platform dashboard error: {e}")
        flash('Error loading platform dashboard.', 'error')
        return redirect(url_for('business_auth.admin_panel'))



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
        # Set active status
        admin_user.is_active_user = True
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
def force_scheduler_run():
    """Force immediate scheduler run (admin only) for testing purposes"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            if request.is_json:
                return jsonify({'error': 'Business account context not found'}), 400
            flash(_('Business account context not found.'), 'error')
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
            # Provide more helpful error message
            message = "The scheduler is currently running or was recently executed. Please wait a moment and try again."
            if request.is_json:
                return jsonify({
                    'error': message,
                    'info': 'The scheduler uses locks to prevent concurrent execution. This ensures data consistency.'
                }), 409  # 409 Conflict status code
            flash(message, 'warning')
        
        return redirect(url_for('business_auth.admin_panel'))
        
    except Exception as e:
        logger.error(f"Error forcing scheduler run: {e}")
        if request.is_json:
            return jsonify({'error': 'Failed to execute scheduler'}), 500
        flash('Failed to execute scheduler. Please try again.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@business_auth_bp.route('/admin/scheduler/status')
@require_business_auth
def scheduler_status():
    """Get scheduler status and statistics (admin only)"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            # Check if JSON response is requested (via Content-Type or Accept header)
            wants_json = request.is_json or 'application/json' in request.headers.get('Accept', '')
            if wants_json:
                return jsonify({'error': 'Business account context not found'}), 400
            flash(_('Business account context not found.'), 'error')
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
        
        # Check if JSON response is requested (via Content-Type or Accept header)
        wants_json = request.is_json or 'application/json' in request.headers.get('Accept', '')
        
        if wants_json:
            return jsonify({
                'scheduler_stats': scheduler_stats,
                'campaign_counts': campaign_counts,
                'business_account': {
                    'id': current_account.id,
                    'name': current_account.name
                }
            })
        
        # For HTML requests, show dedicated scheduler status page
        return render_template('business_auth/scheduler_status.html',
                             scheduler_stats=scheduler_stats,
                             campaign_counts=campaign_counts,
                             business_account=current_account)
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        # Check if JSON response is requested (via Content-Type or Accept header)
        wants_json = request.is_json or 'application/json' in request.headers.get('Accept', '')
        if wants_json:
            return jsonify({'error': 'Failed to get scheduler status'}), 500
        flash('Failed to get scheduler status.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


# ==== AUDIT LOGS ROUTES ====

@business_auth_bp.route('/admin/audit-logs')
@require_business_auth
def audit_logs():
    """Audit logs viewing page"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        # Get filter parameters
        action_type = request.args.get('action_type', '')
        user_email = request.args.get('user_email', '')
        days_back = int(request.args.get('days_back', '30'))
        page = int(request.args.get('page', '1'))
        per_page = 20
        offset = (page - 1) * per_page
        
        # Get audit logs for this business account
        from models import AuditLog
        audit_logs = AuditLog.get_business_audit_logs(
            business_account_id=current_account.id,
            action_type=action_type if action_type else None,
            user_email=user_email if user_email else None,
            days_back=days_back,
            limit=per_page,
            offset=offset
        )
        
        # Get audit statistics
        audit_stats = AuditLog.get_audit_stats(
            business_account_id=current_account.id,
            days_back=days_back
        )
        
        # Get available filter options
        from sqlalchemy import distinct
        available_actions = [row[0] for row in db.session.query(
            distinct(AuditLog.action_type)
        ).filter_by(business_account_id=current_account.id).all()]
        
        available_users = [row[0] for row in db.session.query(
            distinct(AuditLog.user_email)
        ).filter_by(business_account_id=current_account.id).filter(
            AuditLog.user_email.isnot(None)
        ).all()]
        
        # Calculate pagination info
        total_count = AuditLog.query.filter_by(business_account_id=current_account.id).count()
        has_next = total_count > (offset + per_page)
        has_prev = page > 1
        
        return render_template('business_auth/audit_logs.html',
                             audit_logs=[log.to_dict() for log in audit_logs],
                             audit_stats=audit_stats,
                             available_actions=sorted(available_actions),
                             available_users=sorted(available_users),
                             current_filters={
                                 'action_type': action_type,
                                 'user_email': user_email,
                                 'days_back': days_back
                             },
                             pagination={
                                 'page': page,
                                 'per_page': per_page,
                                 'has_next': has_next,
                                 'has_prev': has_prev,
                                 'next_page': page + 1 if has_next else None,
                                 'prev_page': page - 1 if has_prev else None
                             },
                             business_account=current_account)
    
    except Exception as e:
        logger.error(f"Error loading audit logs: {e}")
        flash('Failed to load audit logs.', 'error')
        return redirect(url_for('business_auth.admin_panel'))

# Test audit logs route removed for production security
# @business_auth_bp.route('/admin/audit-logs/test')
# @require_business_auth
# @rate_limit(limit=10)  # 10 test entries per minute
# def test_audit_logs():
    """Create test audit log entries for demo purposes"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account context not found'}), 400
        
        # Import audit utilities
        from audit_utils import queue_audit_log
        from datetime import datetime, timedelta
        import random
        
        # Create several test audit entries
        test_entries = [
            {
                'action_type': 'user_login',
                'resource_name': None,
                'user_email': 'test.user@company.com',
                'user_name': 'Test User',
                'details': {'login_time': datetime.utcnow().isoformat()}
            },
            {
                'action_type': 'campaign_created',
                'resource_type': 'campaign',
                'resource_name': 'Demo Survey Q1 2025',
                'resource_id': '999',
                'user_email': 'admin@company.com',
                'user_name': 'Admin User',
                'details': {'start_date': '2025-01-01', 'end_date': '2025-03-31'}
            },
            {
                'action_type': 'participants_uploaded',
                'resource_type': 'campaign',
                'resource_name': 'Demo Survey Q1 2025',
                'user_email': 'admin@company.com',
                'user_name': 'Admin User',
                'details': {'count': 150, 'source': 'CSV upload'}
            },
            {
                'action_type': 'email_config_saved',
                'resource_type': 'email_config',
                'user_email': 'admin@company.com',
                'user_name': 'Admin User',
                'details': {'fields_changed': ['smtp_server', 'sender_name']}
            },
            {
                'action_type': 'survey_invitations_sent',
                'resource_type': 'campaign',
                'resource_name': 'Demo Survey Q1 2025',
                'user_email': 'admin@company.com',
                'user_name': 'Admin User',
                'details': {'count': 150, 'batch_id': 'batch_001'}
            }
        ]
        
        # Add test entries to queue
        created_count = 0
        for entry in test_entries:
            try:
                queue_audit_log(
                    business_account_id=current_account.id,
                    **entry
                )
                created_count += 1
            except Exception as e:
                logger.error(f"Failed to create test audit entry: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Created {created_count} test audit log entries',
            'created_count': created_count
        })
    
    except Exception as e:
        logger.error(f"Error creating test audit logs: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to create test audit logs: {str(e)}'
        }), 500


# ==== EMAIL CONFIGURATION ROUTES ====

@business_auth_bp.route('/admin/email-config')
@require_business_auth
def email_config():
    """Email configuration management page"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            logger.error("No current account found in email config route")
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        # Get existing email configuration if any
        email_config = current_account.get_email_configuration()
        
        return render_template('business_auth/email_config.html',
                             email_config=email_config,
                             business_account=current_account)
    
    except Exception as e:
        logger.error(f"Error loading email configuration: {e}")
        flash('Failed to load email configuration.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@business_auth_bp.route('/admin/email-config/save', methods=['POST'])
@require_business_auth
def save_email_config():
    """Save email configuration"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        # Get form data
        email_provider = request.form.get('email_provider', 'smtp').strip()
        aws_region = request.form.get('aws_region', '').strip() if email_provider == 'aws_ses' else None
        smtp_server = request.form.get('smtp_server', '').strip()
        smtp_port = request.form.get('smtp_port', '587')
        smtp_username = request.form.get('smtp_username', '').strip()
        smtp_password = request.form.get('smtp_password', '').strip()
        use_tls = request.form.get('use_tls') == 'on'
        use_ssl = request.form.get('use_ssl') == 'on'
        sender_name = request.form.get('sender_name', '').strip()
        sender_email = request.form.get('sender_email', '').strip()
        reply_to_email = request.form.get('reply_to_email', '').strip()
        admin_emails = request.form.get('admin_emails', '').strip()
        
        # Parse admin emails
        admin_email_list = []
        if admin_emails:
            admin_email_list = [email.strip() for email in admin_emails.split(',') if email.strip()]
        
        # Validate port
        try:
            smtp_port = int(smtp_port)
            if not (1 <= smtp_port <= 65535):
                raise ValueError("Port must be between 1 and 65535")
        except ValueError:
            flash('Invalid SMTP port. Please enter a number between 1 and 65535.', 'error')
            return redirect(url_for('business_auth.email_config'))
        
        # Get or create email configuration
        email_config = current_account.get_email_configuration()
        if not email_config:
            email_config = EmailConfiguration(business_account_id=current_account.id)
        
        # Update configuration
        email_config.email_provider = email_provider
        email_config.aws_region = aws_region
        
        # For standard SMTP, use the provided server; for AWS SES, it will be auto-generated
        if email_provider == 'smtp':
            email_config.smtp_server = smtp_server
        else:
            # Auto-generate SMTP server for AWS SES based on region
            email_config.ensure_ses_smtp_server()
        
        email_config.smtp_port = smtp_port
        email_config.smtp_username = smtp_username
        email_config.use_tls = use_tls
        email_config.use_ssl = use_ssl
        email_config.sender_name = sender_name
        email_config.sender_email = sender_email
        email_config.reply_to_email = reply_to_email if reply_to_email else None
        email_config.set_admin_emails(admin_email_list)
        
        # Custom email content
        use_custom_content = request.form.get('use_custom_content') == 'on'
        email_config.use_custom_content = use_custom_content
        
        if use_custom_content:
            email_config.custom_subject_template = request.form.get('custom_subject_template', '').strip() or None
            email_config.custom_intro_message = request.form.get('custom_intro_message', '').strip() or None
            email_config.custom_cta_text = request.form.get('custom_cta_text', '').strip() or None
            email_config.custom_closing_message = request.form.get('custom_closing_message', '').strip() or None
            email_config.custom_footer_note = request.form.get('custom_footer_note', '').strip() or None
        
        # Update password only if provided
        if smtp_password:
            email_config.set_smtp_password(smtp_password)
        
        # Validate configuration
        validation_errors = email_config.validate_configuration()
        if validation_errors:
            for error in validation_errors:
                flash(error, 'error')
            return redirect(url_for('business_auth.email_config'))
        
        # Validate custom content if enabled
        content_errors = email_config.validate_custom_content()
        if content_errors:
            for error in content_errors:
                flash(error, 'error')
            return redirect(url_for('business_auth.email_config'))
        
        # Save to database
        if email_config.id is None:
            db.session.add(email_config)
        
        db.session.commit()
        
        # Audit log email configuration save
        try:
            from audit_utils import audit_email_config_change
            changed_fields = []
            
            # Determine which fields were changed (simple approach for now)
            if email_provider: changed_fields.append('email_provider')
            if aws_region: changed_fields.append('aws_region')
            if smtp_server: changed_fields.append('smtp_server')
            if sender_name: changed_fields.append('sender_name')
            if sender_email: changed_fields.append('sender_email')
            if smtp_password: changed_fields.append('smtp_password')
            if reply_to_email: changed_fields.append('reply_to_email')
            if admin_email_list: changed_fields.append('admin_emails')
            
            audit_email_config_change(
                business_account_id=current_account.id,
                config_fields_changed=changed_fields
            )
        except Exception as audit_error:
            logger.error(f"Failed to audit email config save: {audit_error}")
        
        flash('Email configuration saved successfully!', 'success')
        return redirect(url_for('business_auth.email_config'))
    
    except Exception as e:
        logger.error(f"Error saving email configuration: {e}")
        db.session.rollback()
        flash('Failed to save email configuration. Please try again.', 'error')
        return redirect(url_for('business_auth.email_config'))


@business_auth_bp.route('/admin/email-config/test', methods=['POST'])
@require_business_auth
@rate_limit(limit=10)  # 10 tests per minute per IP to prevent abuse
def test_email_config():
    """Test email configuration"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account context not found'}), 400
        
        # Import email service
        from email_service import email_service
        
        # Test the configuration using tenant-specific settings
        test_result = email_service.test_connection_for_account(current_account.id)
        
        # Update EmailConfiguration with test result if it exists
        email_config = current_account.get_email_configuration()
        if email_config:
            email_config.set_test_result(test_result)
            db.session.commit()
        
        # Audit log email configuration test
        try:
            from audit_utils import queue_audit_log
            queue_audit_log(
                business_account_id=current_account.id,
                action_type='email_config_tested',
                resource_type='email_config',
                details={
                    'test_success': test_result.get('success', False),
                    'smtp_server': email_config.smtp_server if email_config else 'unknown'
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to audit email config test: {audit_error}")
        
        return jsonify(test_result)
    
    except Exception as e:
        logger.error(f"Error testing email configuration: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to test email configuration: {str(e)}'
        }), 500


@business_auth_bp.route('/admin/email-config/send-test', methods=['POST'])
@require_business_auth
@rate_limit(limit=5)  # 5 test emails per minute per IP to prevent spam
def send_test_email():
    """Send test email"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account context not found'}), 400
        
        # Get test email address from request
        # Get test email address from request with proper None handling
        if request.is_json and request.json is not None:
            test_email = request.json.get('test_email', '').strip()
        else:
            test_email = request.form.get('test_email', '').strip()
        
        # Enhanced email validation
        if not test_email:
            return jsonify({'error': 'Test email address is required'}), 400
        
        # Validate email format with regex
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(test_email):
            return jsonify({'error': 'Please enter a valid email address format'}), 400
        
        # Additional security: prevent potential injection
        if len(test_email) > 320:  # RFC 5321 limit
            return jsonify({'error': 'Email address too long'}), 400
        
        # Import email service
        from email_service import email_service
        
        # Prepare test email content
        subject = f"Test Email - {current_account.name} VOÏA Configuration"
        text_body = f"""
Hello,

This is a test email to verify the email configuration for {current_account.name}.

If you received this email, your SMTP configuration is working correctly!

Configuration Details:
- Business Account: {current_account.name}
- Test Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

Best regards,
VOÏA System
"""
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>VOÏA Test Email</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .success {{ color: #28a745; font-weight: bold; }}
        .details {{ background: #e9ecef; padding: 15px; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>✅ VOÏA Email Configuration Test</h2>
        <p class="success">Configuration test successful!</p>
    </div>
    
    <p>Hello,</p>
    
    <p>This is a test email to verify the email configuration for <strong>{current_account.name}</strong>.</p>
    
    <p>If you received this email, your SMTP configuration is working correctly!</p>
    
    <div class="details">
        <strong>Configuration Details:</strong><br>
        • Business Account: {current_account.name}<br>
        • Test Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
    </div>
    
    <p>Best regards,<br>
    VOÏA System</p>
</body>
</html>
"""
        
        # Send test email
        result = email_service.send_email(
            to_emails=test_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            business_account_id=current_account.id
        )
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to send test email: {str(e)}'
        }), 500


@business_auth_bp.route('/admin/email-config/preview', methods=['POST'])
@require_business_auth
def preview_email_content():
    """Preview email content with custom or default templates"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account context not found'}), 400
        
        # Get custom content from request
        data = request.get_json()
        use_custom = data.get('use_custom', False)
        
        # Sample data for preview
        sample_participant_name = "John Doe"
        sample_campaign_name = "Q4 Customer Feedback Survey"
        sample_business_name = current_account.name
        
        # Build content based on custom vs default
        if use_custom and (data.get('subject') or data.get('intro') or data.get('cta_text') or data.get('closing') or data.get('footer')):
            # Use custom content from form
            subject = data.get('subject') or "Your feedback is requested: {campaign_name}"
            intro = data.get('intro') or "{business_account_name} is requesting your valuable feedback through our Voice of Client system."
            cta_text = data.get('cta_text') or "Complete Your Survey"
            closing = data.get('closing') or "Your feedback helps improve services and experiences. The survey should take just a few minutes to complete.\n\nThank you for your time and valuable insights!"
            footer = data.get('footer') or "This is an automated message. If you have any questions, please contact the organization that sent this survey."
        else:
            # Use defaults
            subject = "Your feedback is requested: {campaign_name}"
            intro = "{business_account_name} is requesting your valuable feedback through our Voice of Client system."
            cta_text = "Complete Your Survey"
            closing = "Your feedback helps improve services and experiences. The survey should take just a few minutes to complete.\n\nThank you for your time and valuable insights!"
            footer = "This is an automated message. If you have any questions, please contact the organization that sent this survey."
        
        # Substitute variables
        subject = subject.replace('{participant_name}', sample_participant_name).replace('{campaign_name}', sample_campaign_name).replace('{business_account_name}', sample_business_name)
        intro = intro.replace('{participant_name}', sample_participant_name).replace('{campaign_name}', sample_campaign_name).replace('{business_account_name}', sample_business_name)
        closing = closing.replace('{participant_name}', sample_participant_name).replace('{campaign_name}', sample_campaign_name).replace('{business_account_name}', sample_business_name)
        
        # Get branding
        from models import BrandingConfig
        branding_config = BrandingConfig.query.filter_by(business_account_id=current_account.id).first()
        company_name = branding_config.get_company_display_name() if branding_config else 'VOÏA - Voice Of Client'
        tagline = 'AI Powered Client Insights'
        logo_html = ""
        if branding_config and branding_config.get_logo_url():
            logo_url = branding_config.get_logo_url()
            logo_html = f'<img src="{logo_url}" alt="{company_name}" style="max-height: 60px; margin-bottom: 10px; display: block; margin-left: auto; margin-right: auto;">'
        
        # Build HTML preview
        html_preview = f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f8f9fa; padding: 20px;">
    <div style="background-color: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <div style="text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #E13A44;">
            {logo_html}
            <div style="font-size: 24px; font-weight: bold; color: #E13A44; margin-bottom: 5px;">{company_name}</div>
            <div style="font-size: 14px; color: #666; font-style: italic;">{tagline}</div>
        </div>
        
        <h2 style="color: #333; font-size: 20px;">Hello {sample_participant_name},</h2>
        
        <p style="color: #333; line-height: 1.6;">{intro}</p>
        
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #E13A44; margin: 20px 0; font-weight: 500;">
            <strong>Campaign:</strong> {sample_campaign_name}
        </div>
        
        <div style="text-align: center; margin: 20px 0;">
            <a href="#" style="display: inline-block; background-color: #E13A44; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: 500;">{cta_text}</a>
        </div>
        
        <div style="background-color: #e7f3ff; padding: 10px; border-radius: 5px; font-size: 14px; margin: 15px 0;">
            <strong>🔒 Security Note:</strong> This personalized link is secure and will expire in 72 hours.
        </div>
        
        <p style="color: #333; line-height: 1.6; white-space: pre-line;">{closing}</p>
        
        <p style="color: #333;">Best regards,<br>
        The {company_name} Team</p>
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; text-align: center;">
            {footer}
        </div>
    </div>
</div>
"""
        
        return jsonify({
            'success': True,
            'html': html_preview,
            'subject': subject
        })
    
    except Exception as e:
        logger.error(f"Error generating email preview: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to generate preview: {str(e)}'
        }), 500


# ==== PLATFORM EMAIL SETTINGS ROUTES ====

@business_auth_bp.route('/admin/platform-email-settings')
@require_business_auth
@require_platform_admin
def platform_email_settings():
    """Platform-wide AWS SES configuration page (Platform Admin Only)"""
    try:
        current_user = BusinessAccountUser.query.get(session.get('business_user_id'))
        
        # Get existing platform email settings if any
        from models import PlatformEmailSettings
        platform_settings = PlatformEmailSettings.query.first()
        
        return render_template('business_auth/platform_email_settings.html',
                             platform_settings=platform_settings,
                             current_user=current_user)
    
    except Exception as e:
        logger.error(f"Error loading platform email settings: {e}")
        flash('Failed to load platform email settings.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@business_auth_bp.route('/admin/platform-email-settings/save', methods=['POST'])
@require_business_auth
@require_platform_admin
def save_platform_email_settings():
    """Save platform-wide AWS SES configuration (Platform Admin Only)"""
    try:
        current_user = BusinessAccountUser.query.get(session.get('business_user_id'))
        if not current_user:
            flash('User session invalid.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get form data
        aws_region = request.form.get('aws_region', '').strip()
        smtp_server = request.form.get('smtp_server', '').strip()
        smtp_port = request.form.get('smtp_port', '587')
        smtp_username = request.form.get('smtp_username', '').strip()
        smtp_password = request.form.get('smtp_password', '').strip()
        use_tls = request.form.get('use_tls') == 'on'
        use_ssl = request.form.get('use_ssl') == 'on'
        
        # Validate required fields
        if not all([aws_region, smtp_server, smtp_username]):
            flash('AWS Region, SMTP Server, and SMTP Username are required.', 'error')
            return redirect(url_for('business_auth.platform_email_settings'))
        
        # Validate port
        try:
            smtp_port = int(smtp_port)
            if not (1 <= smtp_port <= 65535):
                raise ValueError("Port must be between 1 and 65535")
        except ValueError:
            flash('Invalid SMTP port. Please enter a number between 1 and 65535.', 'error')
            return redirect(url_for('business_auth.platform_email_settings'))
        
        # Get or create platform email settings (singleton)
        from models import PlatformEmailSettings
        platform_settings = PlatformEmailSettings.query.first()
        
        if not platform_settings:
            platform_settings = PlatformEmailSettings()
            db.session.add(platform_settings)
        
        # Update settings
        platform_settings.aws_region = aws_region
        platform_settings.smtp_server = smtp_server
        platform_settings.smtp_port = smtp_port
        platform_settings.smtp_username = smtp_username
        platform_settings.use_tls = use_tls
        platform_settings.use_ssl = use_ssl
        platform_settings.configured_by_user_id = current_user.id
        platform_settings.updated_at = datetime.utcnow()
        
        # Update password only if provided (allows updating other fields without re-entering password)
        if smtp_password:
            platform_settings.set_smtp_password(smtp_password)
        
        # Validation passed but not yet tested
        platform_settings.is_verified = False
        
        db.session.commit()
        
        # Queue audit log
        queue_audit_log(
            business_account_id=session.get('business_account_id'),
            action_type='platform_email_settings_update',
            resource_type='platform_email_settings',
            resource_id=platform_settings.id,
            user_name=current_user.get_full_name(),
            details={
                'aws_region': aws_region,
                'smtp_server': smtp_server,
                'smtp_port': smtp_port,
                'smtp_username': smtp_username,
                'use_tls': use_tls,
                'use_ssl': use_ssl
            }
        )
        
        flash('Platform email settings saved successfully. Please test the connection to verify.', 'success')
        return redirect(url_for('business_auth.platform_email_settings'))
    
    except Exception as e:
        logger.error(f"Error saving platform email settings: {e}")
        db.session.rollback()
        flash(f'Failed to save platform email settings: {str(e)}', 'error')
        return redirect(url_for('business_auth.platform_email_settings'))


@business_auth_bp.route('/admin/platform-email-settings/test', methods=['POST'])
@require_business_auth
@require_platform_admin
@rate_limit(limit=10)
def test_platform_email_settings():
    """Test platform email configuration connection (Platform Admin Only)"""
    try:
        from models import PlatformEmailSettings
        platform_settings = PlatformEmailSettings.query.first()
        
        if not platform_settings:
            return jsonify({
                'success': False,
                'error': 'No platform email settings configured'
            }), 400
        
        # Get password
        smtp_password = platform_settings.get_smtp_password()
        if not smtp_password:
            return jsonify({
                'success': False,
                'error': 'SMTP password not configured'
            }), 400
        
        # Test SMTP connection
        import smtplib
        from email.mime.text import MIMEText
        
        try:
            # Create SMTP connection
            if platform_settings.use_ssl:
                server = smtplib.SMTP_SSL(platform_settings.smtp_server, platform_settings.smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(platform_settings.smtp_server, platform_settings.smtp_port, timeout=10)
                if platform_settings.use_tls:
                    server.starttls()
            
            # Authenticate
            server.login(platform_settings.smtp_username, smtp_password)
            server.quit()
            
            # Update verification status
            platform_settings.is_verified = True
            platform_settings.last_test_at = datetime.utcnow()
            platform_settings.last_test_result = json.dumps({
                'status': 'success',
                'message': 'Connection successful',
                'timestamp': datetime.utcnow().isoformat()
            })
            db.session.commit()
            
            # Queue audit log
            current_user = BusinessAccountUser.query.get(session.get('business_user_id'))
            queue_audit_log(
                business_account_id=session.get('business_account_id'),
                action_type='platform_email_settings_test',
                resource_type='platform_email_settings',
                resource_id=platform_settings.id,
                user_name=current_user.get_full_name() if current_user else 'Unknown',
                details={'result': 'success'}
            )
            
            return jsonify({
                'success': True,
                'message': 'SMTP connection successful! Platform email settings verified.'
            })
        
        except smtplib.SMTPAuthenticationError as e:
            error_msg = 'Authentication failed. Please check your SMTP username and password.'
            platform_settings.is_verified = False
            platform_settings.last_test_at = datetime.utcnow()
            platform_settings.last_test_result = json.dumps({
                'status': 'error',
                'message': error_msg,
                'error_type': 'authentication',
                'timestamp': datetime.utcnow().isoformat()
            })
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        except Exception as smtp_error:
            error_msg = f'Connection failed: {str(smtp_error)}'
            platform_settings.is_verified = False
            platform_settings.last_test_at = datetime.utcnow()
            platform_settings.last_test_result = json.dumps({
                'status': 'error',
                'message': error_msg,
                'timestamp': datetime.utcnow().isoformat()
            })
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
    
    except Exception as e:
        logger.error(f"Error testing platform email settings: {e}")
        return jsonify({
            'success': False,
            'error': f'Test failed: {str(e)}'
        }), 500


# ==== PLATFORM EMAIL DOMAIN MANAGEMENT ROUTES ====

@business_auth_bp.route('/admin/platform-email-domains')
@require_business_auth
@require_platform_admin
def platform_email_domains():
    """Platform-wide domain management page (Platform Admin Only)"""
    try:
        current_user = BusinessAccountUser.query.get(session.get('business_user_id'))
        
        # Get all verified domains across all business accounts
        from models import EmailConfiguration, BusinessAccount
        
        # Get all email configurations that use platform email (VOÏA-managed)
        domains = EmailConfiguration.query.filter_by(use_platform_email=True).all()
        
        # Get all business accounts for dropdown
        business_accounts = BusinessAccount.query.filter_by(status='active').order_by(BusinessAccount.name).all()
        
        # Convert domains to dictionaries for JSON serialization in template
        domains_data = [domain.to_dict() for domain in domains]
        
        return render_template('business_auth/platform_email_domains.html',
                             domains=domains,
                             domains_data=domains_data,
                             business_accounts=business_accounts,
                             current_user=current_user)
    
    except Exception as e:
        logger.error(f"Error loading platform email domains: {e}")
        flash('Failed to load platform email domains.', 'error')
        return redirect(url_for('business_auth.platform_email_settings'))


@business_auth_bp.route('/admin/platform-email-domains/add', methods=['POST'])
@require_business_auth
@require_platform_admin
def add_platform_email_domain():
    """Add a new verified domain (Platform Admin Only)"""
    try:
        current_user = BusinessAccountUser.query.get(session.get('business_user_id'))
        if not current_user:
            flash('User session invalid.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get form data
        business_account_id = request.form.get('business_account_id')
        sender_domain = request.form.get('sender_domain', '').strip().lower()
        domain_verified = request.form.get('domain_verified') == 'on'
        
        # DKIM records
        dkim_record_1_name = request.form.get('dkim_record_1_name', '').strip()
        dkim_record_1_value = request.form.get('dkim_record_1_value', '').strip()
        dkim_record_2_name = request.form.get('dkim_record_2_name', '').strip()
        dkim_record_2_value = request.form.get('dkim_record_2_value', '').strip()
        dkim_record_3_name = request.form.get('dkim_record_3_name', '').strip()
        dkim_record_3_value = request.form.get('dkim_record_3_value', '').strip()
        
        # Validate required fields
        if not business_account_id or not sender_domain:
            flash('Business Account and Domain Name are required.', 'error')
            return redirect(url_for('business_auth.platform_email_domains'))
        
        # Validate business account exists
        from models import BusinessAccount
        business_account = BusinessAccount.query.get(business_account_id)
        if not business_account:
            flash('Invalid business account selected.', 'error')
            return redirect(url_for('business_auth.platform_email_domains'))
        
        # Check if domain already exists for this business account
        from models import EmailConfiguration
        existing_domain = EmailConfiguration.query.filter_by(
            business_account_id=business_account_id,
            sender_domain=sender_domain,
            use_platform_email=True
        ).first()
        
        if existing_domain:
            flash(f'Domain {sender_domain} already exists for {business_account.name}.', 'error')
            return redirect(url_for('business_auth.platform_email_domains'))
        
        # Create new email configuration for this domain
        email_config = EmailConfiguration.query.filter_by(business_account_id=business_account_id).first()
        
        # Guaranteed fallback values (never None or empty)
        default_sender_name = (business_account.name if business_account.name else f"Team {sender_domain}").strip() or f"Team {sender_domain}"
        default_sender_email = f"noreply@{sender_domain}"
        default_reply_to = (business_account.contact_email if business_account.contact_email and '@' in business_account.contact_email else f"support@{sender_domain}").strip() or f"support@{sender_domain}"
        
        if not email_config:
            # Create new email configuration with guaranteed non-null defaults
            email_config = EmailConfiguration(
                business_account_id=business_account_id,
                sender_name=default_sender_name,
                sender_email=default_sender_email,
                reply_to_email=default_reply_to
            )
            db.session.add(email_config)
        else:
            # Update sender defaults if not already set
            if not email_config.sender_name or not email_config.sender_name.strip():
                email_config.sender_name = default_sender_name
            if not email_config.sender_email or not email_config.sender_email.strip():
                email_config.sender_email = default_sender_email
            if not email_config.reply_to_email or not email_config.reply_to_email.strip():
                email_config.reply_to_email = default_reply_to
        
        # Update with platform email settings
        email_config.use_platform_email = True
        email_config.sender_domain = sender_domain
        email_config.domain_verified = domain_verified
        email_config.domain_verified_at = datetime.utcnow() if domain_verified else None
        
        # Set DKIM records
        email_config.dkim_record_1_name = dkim_record_1_name if dkim_record_1_name else None
        email_config.dkim_record_1_value = dkim_record_1_value if dkim_record_1_value else None
        email_config.dkim_record_2_name = dkim_record_2_name if dkim_record_2_name else None
        email_config.dkim_record_2_value = dkim_record_2_value if dkim_record_2_value else None
        email_config.dkim_record_3_name = dkim_record_3_name if dkim_record_3_name else None
        email_config.dkim_record_3_value = dkim_record_3_value if dkim_record_3_value else None
        
        db.session.commit()
        
        # Audit log
        queue_audit_log(
            business_account_id=business_account_id,
            action_type='platform_email_domain_add',
            resource_type='email_configuration',
            resource_id=email_config.id,
            user_name=current_user.get_full_name(),
            details={
                'domain': sender_domain,
                'verified': domain_verified,
                'business_account': business_account.name
            }
        )
        
        flash(f'Domain {sender_domain} added successfully for {business_account.name}. Sender defaults applied - business account can customize sender identity in Email Settings.', 'success')
        return redirect(url_for('business_auth.platform_email_domains'))
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding platform email domain: {e}")
        flash(f'Failed to add domain: {str(e)}', 'error')
        return redirect(url_for('business_auth.platform_email_domains'))


@business_auth_bp.route('/admin/platform-email-domains/edit/<int:config_id>', methods=['POST'])
@require_business_auth
@require_platform_admin
def edit_platform_email_domain(config_id):
    """Edit an existing verified domain (Platform Admin Only)"""
    try:
        current_user = BusinessAccountUser.query.get(session.get('business_user_id'))
        if not current_user:
            flash('User session invalid.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get email configuration
        from models import EmailConfiguration
        email_config = EmailConfiguration.query.get(config_id)
        
        if not email_config:
            flash('Domain configuration not found.', 'error')
            return redirect(url_for('business_auth.platform_email_domains'))
        
        # Get form data
        domain_verified = request.form.get('domain_verified') == 'on'
        
        # DKIM records
        dkim_record_1_name = request.form.get('dkim_record_1_name', '').strip()
        dkim_record_1_value = request.form.get('dkim_record_1_value', '').strip()
        dkim_record_2_name = request.form.get('dkim_record_2_name', '').strip()
        dkim_record_2_value = request.form.get('dkim_record_2_value', '').strip()
        dkim_record_3_name = request.form.get('dkim_record_3_name', '').strip()
        dkim_record_3_value = request.form.get('dkim_record_3_value', '').strip()
        
        # Update domain verification status
        was_verified = email_config.domain_verified
        email_config.domain_verified = domain_verified
        
        if domain_verified and not was_verified:
            email_config.domain_verified_at = datetime.utcnow()
        elif not domain_verified and was_verified:
            email_config.domain_verified_at = None
        
        # Update DKIM records
        email_config.dkim_record_1_name = dkim_record_1_name if dkim_record_1_name else None
        email_config.dkim_record_1_value = dkim_record_1_value if dkim_record_1_value else None
        email_config.dkim_record_2_name = dkim_record_2_name if dkim_record_2_name else None
        email_config.dkim_record_2_value = dkim_record_2_value if dkim_record_2_value else None
        email_config.dkim_record_3_name = dkim_record_3_name if dkim_record_3_name else None
        email_config.dkim_record_3_value = dkim_record_3_value if dkim_record_3_value else None
        
        db.session.commit()
        
        # Audit log
        queue_audit_log(
            business_account_id=email_config.business_account_id,
            action_type='platform_email_domain_update',
            resource_type='email_configuration',
            resource_id=email_config.id,
            user_name=current_user.get_full_name(),
            details={
                'domain': email_config.sender_domain,
                'verified': domain_verified,
                'verification_changed': was_verified != domain_verified
            }
        )
        
        flash(f'Domain {email_config.sender_domain} updated successfully.', 'success')
        return redirect(url_for('business_auth.platform_email_domains'))
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error editing platform email domain: {e}")
        flash(f'Failed to update domain: {str(e)}', 'error')
        return redirect(url_for('business_auth.platform_email_domains'))


@business_auth_bp.route('/admin/platform-email-domains/delete/<int:config_id>', methods=['POST'])
@require_business_auth
@require_platform_admin
def delete_platform_email_domain(config_id):
    """Delete a verified domain (Platform Admin Only)"""
    try:
        current_user = BusinessAccountUser.query.get(session.get('business_user_id'))
        if not current_user:
            flash('User session invalid.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get email configuration
        from models import EmailConfiguration
        email_config = EmailConfiguration.query.get(config_id)
        
        if not email_config:
            flash('Domain configuration not found.', 'error')
            return redirect(url_for('business_auth.platform_email_domains'))
        
        domain_name = email_config.sender_domain
        business_account_id = email_config.business_account_id
        
        # Safety check: Only allow deletion if not actively used
        # For now, we'll allow deletion and just reset to client-managed mode
        email_config.use_platform_email = False
        email_config.sender_domain = None
        email_config.domain_verified = False
        email_config.domain_verified_at = None
        email_config.dkim_record_1_name = None
        email_config.dkim_record_1_value = None
        email_config.dkim_record_2_name = None
        email_config.dkim_record_2_value = None
        email_config.dkim_record_3_name = None
        email_config.dkim_record_3_value = None
        
        db.session.commit()
        
        # Audit log
        queue_audit_log(
            business_account_id=business_account_id,
            action_type='platform_email_domain_delete',
            resource_type='email_configuration',
            resource_id=email_config.id,
            user_name=current_user.get_full_name(),
            details={
                'domain': domain_name
            }
        )
        
        flash(f'Domain {domain_name} removed successfully.', 'success')
        return redirect(url_for('business_auth.platform_email_domains'))
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting platform email domain: {e}")
        flash(f'Failed to delete domain: {str(e)}', 'error')
        return redirect(url_for('business_auth.platform_email_domains'))


# ==== INDUSTRY TOPIC HINTS MANAGEMENT (Platform Admin Only) ====

@business_auth_bp.route('/admin/industry-hints')
@require_business_auth
@require_platform_admin
def industry_hints_config():
    """Industry topic hints configuration page (Platform Admin Only)"""
    try:
        current_user = BusinessAccountUser.query.get(session.get('business_user_id'))
        
        # Load current configuration from the Python file
        import industry_topic_hints_config
        import json
        
        # Convert to pretty-printed JSON for editing
        hints_json = json.dumps(industry_topic_hints_config.INDUSTRY_TOPIC_HINTS, indent=2, ensure_ascii=False)
        
        return render_template('business_auth/industry_hints_config.html',
                             hints_json=hints_json,
                             current_user=current_user)
    
    except Exception as e:
        logger.error(f"Error loading industry hints configuration: {e}")
        flash('Failed to load industry hints configuration.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@business_auth_bp.route('/admin/industry-hints/save', methods=['POST'])
@require_business_auth
@require_platform_admin
def save_industry_hints_config():
    """Save industry topic hints configuration (Platform Admin Only)"""
    try:
        current_user = BusinessAccountUser.query.get(session.get('business_user_id'))
        if not current_user:
            flash('User session invalid.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get JSON from form
        hints_json = request.form.get('hints_json', '').strip()
        
        if not hints_json:
            flash('Configuration data is required.', 'error')
            return redirect(url_for('business_auth.industry_hints_config'))
        
        # Validate JSON
        import json
        try:
            hints_data = json.loads(hints_json)
        except json.JSONDecodeError as e:
            flash(f'Invalid JSON format: {str(e)}', 'error')
            return redirect(url_for('business_auth.industry_hints_config'))
        
        # Basic validation - ensure it's a dict with industry keys
        if not isinstance(hints_data, dict):
            flash('Configuration must be a JSON object (dictionary).', 'error')
            return redirect(url_for('business_auth.industry_hints_config'))
        
        # Validate that each industry has topic hints
        for industry, topics in hints_data.items():
            if not isinstance(topics, dict):
                flash(f'Industry "{industry}" must have a dictionary of topic hints.', 'error')
                return redirect(url_for('business_auth.industry_hints_config'))
        
        # Write to file
        config_content = f'''"""
Industry-Specific Topic Hints Configuration

This module defines platform-wide default hints for conversational survey questions,
mapped by industry and survey topic. These hints customize AI prompts to ask more
relevant, industry-specific questions.

Architecture:
- Platform admin maintains this file (default hints library)
- BusinessAccount.industry_topic_hints JSON can override specific hints
- Campaign inherits from BusinessAccount or uses platform defaults

Usage in PromptTemplateService:
- Inject hints into topic descriptions to guide GPT-4o question generation
- Example: "Product Quality (focus on: defects, throughput, line reliability)"
"""

INDUSTRY_TOPIC_HINTS = {json.dumps(hints_data, indent=4, ensure_ascii=False)}


def get_available_industries():
    """
    Get list of available industries for UI selection
    
    Returns:
        list: Industry names sorted alphabetically, with Generic last
    """
    industries = sorted([k for k in INDUSTRY_TOPIC_HINTS.keys() if k != "Generic"])
    industries.append("Generic")
    return industries


def get_industry_hints(industry):
    """
    Get topic hints for a specific industry
    
    Args:
        industry (str): Industry name
    
    Returns:
        dict: Topic hints mapping, or Generic hints if industry not found
    """
    return INDUSTRY_TOPIC_HINTS.get(industry, INDUSTRY_TOPIC_HINTS["Generic"])


def get_topic_hint(industry, topic):
    """
    Get hint for a specific industry and topic
    
    Args:
        industry (str): Industry name
        topic (str): Survey topic name
    
    Returns:
        str: Hint keywords or empty string if not found
    """
    hints = get_industry_hints(industry)
    return hints.get(topic, "")


def merge_custom_hints(industry, custom_hints):
    """
    Merge custom business account hints with platform defaults
    
    Args:
        industry (str): Industry name
        custom_hints (dict): Custom hints from BusinessAccount.industry_topic_hints
    
    Returns:
        dict: Merged hints (custom overrides platform defaults)
    """
    platform_hints = get_industry_hints(industry).copy()
    
    if custom_hints and isinstance(custom_hints, dict):
        platform_hints.update(custom_hints)
    
    return platform_hints
'''
        
        # Write to file
        with open('industry_topic_hints_config.py', 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        # Reload the module to apply changes immediately
        import importlib
        import industry_topic_hints_config
        importlib.reload(industry_topic_hints_config)
        
        # Audit log
        queue_audit_log(
            business_account_id=current_user.business_account_id,
            action_type='industry_hints_update',
            resource_type='platform_config',
            resource_id=None,
            user_name=current_user.get_full_name(),
            details={
                'industries_count': len(hints_data),
                'industries': list(hints_data.keys())
            }
        )
        
        flash('Industry topic hints configuration updated successfully.', 'success')
        return redirect(url_for('business_auth.industry_hints_config'))
    
    except Exception as e:
        logger.error(f"Error saving industry hints configuration: {e}")
        flash(f'Failed to save configuration: {str(e)}', 'error')
        return redirect(url_for('business_auth.industry_hints_config'))


# ==== EMAIL DELIVERY CONFIGURATION ROUTES (Business Account) ====

def _get_email_delivery_data(business_account_id):
    """Get email delivery configuration data (cached for 6 hours to avoid expensive SES API calls).
    
    Returns a dict with:
        - email_config: EmailConfiguration object or None
        - available_domains: List of verified domains for VOÏA-Managed mode
    
    This function caches only the DATA, not the rendered HTML, to preserve CSRF tokens.
    """
    from app import cache
    from models import EmailConfiguration, BusinessAccount
    
    cache_key = f'email_delivery_data_{business_account_id}'
    
    # Try to get from cache
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.debug(f"Serving email delivery data from cache: {cache_key}")
        return cached_data
    
    # Cache miss - fetch from database
    logger.debug(f"Cache miss for email delivery data: {cache_key}")
    
    business_account = BusinessAccount.query.get(business_account_id)
    if not business_account:
        return None
    
    # Get existing email configuration if any
    email_config = business_account.get_email_configuration()
    
    # Get available verified domains for this business account (for VOÏA-Managed mode)
    available_domains = EmailConfiguration.query.filter_by(
        business_account_id=business_account_id,
        use_platform_email=True,
        domain_verified=True
    ).all()
    
    data = {
        'email_config': email_config,
        'available_domains': available_domains
    }
    
    # Cache for 6 hours (21600 seconds)
    cache.set(cache_key, data, timeout=21600)
    logger.debug(f"Cached email delivery data: {cache_key}")
    
    return data

@business_auth_bp.route('/admin/email-delivery-config')
@require_business_auth
def email_delivery_config():
    """Email delivery configuration page - dual-mode: VOÏA-Managed or Client-Managed (Business Admin)
    
    Data is cached for 6 hours to avoid expensive SES API calls on every page load.
    Template is rendered fresh on each request to preserve CSRF tokens.
    """
    try:
        current_account = get_current_business_account()
        if not current_account:
            logger.error("No current account found in email delivery config route")
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        # Get cached data (includes email_config and available_domains)
        data = _get_email_delivery_data(current_account.id)
        if not data:
            logger.error(f"Failed to retrieve email delivery data for account {current_account.id}")
            flash(_('Failed to load email delivery configuration.'), 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        # Render template fresh on each request to preserve CSRF tokens
        return render_template('business_auth/email_delivery_config.html',
                             email_config=data['email_config'],
                             available_domains=data['available_domains'],
                             business_account=current_account)
    
    except Exception as e:
        logger.error(f"Error loading email delivery configuration: {e}")
        flash('Failed to load email delivery configuration.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@business_auth_bp.route('/admin/email-delivery-config/save', methods=['POST'])
@require_business_auth
def save_email_delivery_config():
    """Save email delivery configuration (dual-mode support)
    
    Invalidates cache after successful save to ensure fresh data on next load.
    """
    from app import cache
    
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        # Get email delivery mode
        email_mode = request.form.get('email_mode', 'client_managed').strip()  # 'voïa_managed' or 'client_managed'
        
        # Get or create email configuration
        email_config = current_account.get_email_configuration()
        if not email_config:
            email_config = EmailConfiguration(business_account_id=current_account.id)
            db.session.add(email_config)
        
        # Set the email delivery mode
        if email_mode == 'voïa_managed':
            # VOÏA-Managed Mode: Use platform AWS SES
            email_config.use_platform_email = True
            
            # Get selected domain
            selected_domain_id = request.form.get('selected_domain_id')
            if not selected_domain_id:
                flash('Please select a verified domain for VOÏA-Managed email delivery.', 'error')
                return redirect(url_for('business_auth.email_delivery_config'))
            
            # Verify the domain belongs to this business account and is verified
            from models import EmailConfiguration as EC
            selected_domain_config = EC.query.filter_by(
                id=selected_domain_id,
                business_account_id=current_account.id,
                use_platform_email=True,
                domain_verified=True
            ).first()
            
            if not selected_domain_config:
                flash('Invalid or unverified domain selected.', 'error')
                return redirect(url_for('business_auth.email_delivery_config'))
            
            # Copy domain configuration to email_config
            email_config.sender_domain = selected_domain_config.sender_domain
            email_config.domain_verified = True
            email_config.domain_verified_at = selected_domain_config.domain_verified_at
            email_config.dkim_record_1_name = selected_domain_config.dkim_record_1_name
            email_config.dkim_record_1_value = selected_domain_config.dkim_record_1_value
            email_config.dkim_record_2_name = selected_domain_config.dkim_record_2_name
            email_config.dkim_record_2_value = selected_domain_config.dkim_record_2_value
            email_config.dkim_record_3_name = selected_domain_config.dkim_record_3_name
            email_config.dkim_record_3_value = selected_domain_config.dkim_record_3_value
            
            # Get sender configuration (still required for "From" name and email)
            sender_name = request.form.get('sender_name', '').strip()
            sender_email = request.form.get('sender_email', '').strip()
            
            if not sender_name or not sender_email:
                flash('Sender name and email are required.', 'error')
                return redirect(url_for('business_auth.email_delivery_config'))
            
            # Validate sender email domain matches selected domain
            if '@' in sender_email:
                sender_email_domain = sender_email.split('@')[1].lower()
                if sender_email_domain != email_config.sender_domain:
                    flash(f'Sender email must use the verified domain: {email_config.sender_domain}', 'error')
                    return redirect(url_for('business_auth.email_delivery_config'))
            
            email_config.sender_name = sender_name
            email_config.sender_email = sender_email
            email_config.reply_to_email = request.form.get('reply_to_email', '').strip() or None
            
            # Clear client-managed SMTP fields
            email_config.smtp_server = None
            email_config.smtp_port = 587  # Keep default
            email_config.smtp_username = None
            email_config.smtp_password_encrypted = None
            email_config.use_tls = True
            email_config.use_ssl = False
            
        else:
            # Client-Managed Mode: Use their own SMTP credentials
            email_config.use_platform_email = False
            
            # Get SMTP configuration
            email_provider = request.form.get('email_provider', 'smtp').strip()
            smtp_server = request.form.get('smtp_server', '').strip()
            smtp_port = request.form.get('smtp_port', '587')
            smtp_username = request.form.get('smtp_username', '').strip()
            smtp_password = request.form.get('smtp_password', '').strip()
            use_tls = request.form.get('use_tls') == 'on'
            use_ssl = request.form.get('use_ssl') == 'on'
            sender_name = request.form.get('sender_name', '').strip()
            sender_email = request.form.get('sender_email', '').strip()
            reply_to_email = request.form.get('reply_to_email', '').strip()
            
            # Validate required fields
            if not smtp_server or not sender_name or not sender_email:
                flash('SMTP server, sender name, and sender email are required for client-managed mode.', 'error')
                return redirect(url_for('business_auth.email_delivery_config'))
            
            # Validate port
            try:
                smtp_port = int(smtp_port)
                if not (1 <= smtp_port <= 65535):
                    raise ValueError("Port must be between 1 and 65535")
            except ValueError:
                flash('Invalid SMTP port. Please enter a number between 1 and 65535.', 'error')
                return redirect(url_for('business_auth.email_delivery_config'))
            
            # Update configuration
            email_config.email_provider = email_provider
            email_config.smtp_server = smtp_server
            email_config.smtp_port = smtp_port
            email_config.smtp_username = smtp_username
            email_config.use_tls = use_tls
            email_config.use_ssl = use_ssl
            email_config.sender_name = sender_name
            email_config.sender_email = sender_email
            email_config.reply_to_email = reply_to_email if reply_to_email else None
            
            # Update password only if provided
            if smtp_password:
                email_config.set_smtp_password(smtp_password)
            
            # Clear VOÏA-managed fields
            email_config.sender_domain = None
            email_config.domain_verified = False
            email_config.domain_verified_at = None
            email_config.dkim_record_1_name = None
            email_config.dkim_record_1_value = None
            email_config.dkim_record_2_name = None
            email_config.dkim_record_2_value = None
            email_config.dkim_record_3_name = None
            email_config.dkim_record_3_value = None
        
        # Save to database
        db.session.commit()
        
        # Invalidate data cache to ensure fresh data on next load
        cache_key = f'email_delivery_data_{current_account.id}'
        cache.delete(cache_key)
        logger.debug(f"Invalidated email delivery data cache: {cache_key}")
        
        # Audit log
        from audit_utils import queue_audit_log
        queue_audit_log(
            business_account_id=current_account.id,
            action_type='email_delivery_config_updated',
            resource_type='email_configuration',
            resource_id=email_config.id,
            user_name=session.get('business_user_name', 'Unknown'),
            details={
                'mode': 'VOÏA-Managed' if email_mode == 'voïa_managed' else 'Client-Managed',
                'domain': email_config.sender_domain if email_mode == 'voïa_managed' else None
            }
        )
        
        flash('Email delivery configuration saved successfully!', 'success')
        return redirect(url_for('business_auth.email_delivery_config'))
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving email delivery configuration: {e}")
        flash(f'Failed to save email delivery configuration: {str(e)}', 'error')
        return redirect(url_for('business_auth.email_delivery_config'))


@business_auth_bp.route('/admin/email-delivery-config/test', methods=['POST'])
@require_business_auth
@rate_limit(limit=3)  # 3 test emails per hour to prevent abuse
def test_email_delivery_config():
    """Send test email to verify business account email configuration"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.email_delivery_config'))
        
        # Get test recipient email (default to current user's email)
        current_user = BusinessAccountUser.query.get(session.get('business_user_id'))
        test_recipient = request.form.get('test_email', '').strip()
        
        if not test_recipient:
            if current_user:
                test_recipient = current_user.email
            else:
                flash(_('Please provide a test email address.'), 'error')
                return redirect(url_for('business_auth.email_delivery_config'))
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, test_recipient):
            flash(_('Please provide a valid email address.'), 'error')
            return redirect(url_for('business_auth.email_delivery_config'))
        
        # Get email configuration
        email_config = current_account.get_email_configuration()
        if not email_config:
            flash(_('Email configuration not found. Please configure your email settings first.'), 'error')
            return redirect(url_for('business_auth.email_delivery_config'))
        
        # Validate configuration based on mode
        if email_config.use_platform_email:
            # VOÏA-Managed mode validation
            if not email_config.domain_verified:
                flash(_('Your domain is not yet verified. Please contact the platform administrator.'), 'error')
                return redirect(url_for('business_auth.email_delivery_config'))
            
            if not email_config.sender_domain or not email_config.sender_email:
                flash(_('Please complete your VOÏA-Managed email configuration (domain and sender email required).'), 'error')
                return redirect(url_for('business_auth.email_delivery_config'))
            
            # Check platform settings exist
            from models import PlatformEmailSettings
            platform_settings = PlatformEmailSettings.query.first()
            if not platform_settings or not platform_settings.is_verified:
                flash(_('Platform email settings are not configured. Please contact the platform administrator.'), 'error')
                return redirect(url_for('business_auth.email_delivery_config'))
        else:
            # Client-Managed mode validation
            if not email_config.smtp_server or not email_config.sender_email:
                flash(_('Please complete your Client-Managed email configuration (SMTP server and sender email required).'), 'error')
                return redirect(url_for('business_auth.email_delivery_config'))
        
        # Send test email
        from email_service import email_service
        
        email_mode = 'VOÏA-Managed' if email_config.use_platform_email else 'Client-Managed'
        subject = f'Test Email from {current_account.name}'
        text_body = f"""This is a test email from your VOÏA email configuration.

Configuration Mode: {email_mode}
Business Account: {current_account.name}
Sender Email: {email_config.sender_email}
Test Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

If you received this email, your email configuration is working correctly!

---
This is an automated test message from VOÏA - Voice Of Client"""
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #dc3545;">Test Email from VOÏA</h2>
                <p>This is a test email from your VOÏA email configuration.</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 5px 0;"><strong>Configuration Mode:</strong> {email_mode}</p>
                    <p style="margin: 5px 0;"><strong>Business Account:</strong> {current_account.name}</p>
                    <p style="margin: 5px 0;"><strong>Sender Email:</strong> {email_config.sender_email}</p>
                    <p style="margin: 5px 0;"><strong>Test Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                </div>
                
                <p style="color: #28a745; font-weight: bold;">✓ If you received this email, your email configuration is working correctly!</p>
                
                <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                <p style="font-size: 12px; color: #6c757d;">This is an automated test message from VOÏA - Voice Of Client</p>
            </div>
        </body>
        </html>
        """
        
        result = email_service.send_email(
            to_emails=[test_recipient],
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            business_account_id=current_account.id
        )
        
        # Audit log
        from audit_utils import queue_audit_log
        queue_audit_log(
            business_account_id=current_account.id,
            action_type='email_delivery_config_test',
            resource_type='email_configuration',
            resource_id=email_config.id,
            user_name=session.get('business_user_name', 'Unknown'),
            details={
                'test_recipient': test_recipient,
                'mode': email_mode,
                'success': result.get('success', False),
                'error': result.get('error') if not result.get('success') else None
            }
        )
        
        # Show result to user
        if result.get('success'):
            flash(_('Test email sent successfully to %(email)s! Please check your inbox.', email=test_recipient), 'success')
        else:
            error_msg = result.get('error', _('Unknown error occurred'))
            flash(_('Failed to send test email: %(error)s', error=error_msg), 'error')
        
        return redirect(url_for('business_auth.email_delivery_config'))
    
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        flash(_('Failed to send test email: %(error)s', error=str(e)), 'error')
        return redirect(url_for('business_auth.email_delivery_config'))


# ==== BRANDING CONFIGURATION ROUTES ====

@business_auth_bp.route('/admin/brand-config')
@require_business_auth
def brand_config():
    """Branding configuration management page"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            logger.error("No current account found in brand config route")
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        # Get existing branding configuration if any
        from models import BrandingConfig
        branding_config = BrandingConfig.get_or_create_for_business_account(current_account.id)
        
        return render_template('business_auth/brand_config.html',
                             branding_config=branding_config,
                             business_account=current_account)
    
    except Exception as e:
        logger.error(f"Error loading branding configuration: {e}")
        flash('Failed to load branding configuration.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@business_auth_bp.route('/admin/brand-config/save', methods=['POST'])
@require_business_auth
def save_brand_config():
    """Save branding configuration with secure logo upload and image processing"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        # Get form data
        company_display_name = request.form.get('company_display_name', '').strip()
        
        # Get color palette data
        primary_color = request.form.get('primary_color', '#dc3545').strip()
        secondary_color = request.form.get('secondary_color', '#6c757d').strip()
        accent_color = request.form.get('accent_color', '#28a745').strip()
        text_color = request.form.get('text_color', '#212529').strip()
        background_color = request.form.get('background_color', '#ffffff').strip()
        
        # Server-side validation: Validate hex color format
        import re
        hex_color_pattern = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')
        
        colors_to_validate = {
            'Primary Color': primary_color,
            'Secondary Color': secondary_color,
            'Accent Color': accent_color,
            'Text Color': text_color,
            'Background Color': background_color
        }
        
        for color_name, color_value in colors_to_validate.items():
            if not hex_color_pattern.match(color_value):
                flash(f'Invalid {color_name} format. Please use a valid hex color (e.g., #FF0000).', 'error')
                return redirect(url_for('business_auth.brand_config'))
        
        # Get or create branding configuration
        from models import BrandingConfig
        branding_config = BrandingConfig.get_or_create_for_business_account(current_account.id)
        
        # Update configuration
        branding_config.company_display_name = company_display_name if company_display_name else None
        branding_config.primary_color = primary_color
        branding_config.secondary_color = secondary_color
        branding_config.accent_color = accent_color
        branding_config.text_color = text_color
        branding_config.background_color = background_color
        
        # Handle logo upload
        if 'logo_file' in request.files:
            logo_file = request.files['logo_file']
            if logo_file.filename:
                try:
                    # Process and validate the uploaded logo
                    processed_filename = _process_logo_upload(logo_file, current_account.id, branding_config.logo_filename)
                    if processed_filename:
                        branding_config.logo_filename = processed_filename
                except ValueError as ve:
                    flash(str(ve), 'error')
                    return redirect(url_for('business_auth.brand_config'))
                except Exception as e:
                    logger.error(f"Logo upload processing error: {e}")
                    flash('Failed to process logo upload. Please try again with a different image.', 'error')
                    return redirect(url_for('business_auth.brand_config'))
        
        # Save to database
        if branding_config not in db.session:
            db.session.add(branding_config)
        
        db.session.commit()
        
        logger.info(f"Branding configuration updated for business account: {current_account.name}")
        flash('Branding configuration saved successfully!', 'success')
        
        # Audit log configuration update
        try:
            from audit_utils import queue_audit_log
            queue_audit_log(
                business_account_id=current_account.id,
                action_type='branding_config_updated',
                resource_type='branding_config',
                details={
                    'company_display_name': company_display_name,
                    'logo_updated': 'logo_file' in request.files and request.files['logo_file'].filename != '',
                    'colors_updated': {
                        'primary_color': primary_color,
                        'secondary_color': secondary_color,
                        'accent_color': accent_color,
                        'text_color': text_color,
                        'background_color': background_color
                    }
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to audit branding config update: {audit_error}")
        
        return redirect(url_for('business_auth.brand_config'))
    
    except Exception as e:
        logger.error(f"Error saving branding configuration: {e}")
        db.session.rollback()
        flash('Failed to save branding configuration. Please try again.', 'error')
        return redirect(url_for('business_auth.brand_config'))


@business_auth_bp.route('/admin/license-info')
@require_business_auth
def license_info():
    """Display comprehensive license information for the business account"""
    try:
        # Get current business account
        business_account = get_current_business_account()
        if not business_account:
            flash('Business account not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get comprehensive license information using LicenseService
        from license_service import LicenseService
        license_data = LicenseService.get_license_info(business_account.id)
        
        # Add business account object to the context
        license_data['business_account'] = business_account
        
        # Get active campaign information for display
        try:
            from models import Campaign, CampaignParticipant
            active_campaign = Campaign.query.filter(
                Campaign.business_account_id == business_account.id,
                Campaign.status == 'active'
            ).first()
            
            active_participants = 0
            if active_campaign:
                active_participants = CampaignParticipant.query.filter_by(
                    campaign_id=active_campaign.id
                ).count()
                
            license_data.update({
                'active_campaign': active_campaign,
                'active_participants': active_participants
            })
        except Exception as e:
            logger.warning(f"Could not fetch active campaign participants: {e}")
            license_data.update({
                'active_campaign': None,
                'active_participants': 0
            })
        
        return render_template('business_auth/license_info.html', **license_data)
        
    except Exception as e:
        logger.error(f"License info page error: {e}")
        flash('Failed to load license information. Please try again.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


def _process_logo_upload(logo_file, business_account_id, old_logo_filename=None):
    """
    Process and validate logo upload with secure handling and image resizing
    
    Args:
        logo_file: FileStorage object from request
        business_account_id: ID of the business account
        old_logo_filename: Previous logo filename to clean up
    
    Returns:
        str: New filename of the processed logo
    
    Raises:
        ValueError: For validation errors that should be shown to user
        Exception: For system errors
    """
    import os
    import io
    from werkzeug.utils import secure_filename
    from PIL import Image, ImageOps
    
    # Validate file size first (5MB limit)
    logo_file.seek(0, 2)  # Seek to end
    file_size = logo_file.tell()
    logo_file.seek(0)  # Reset to beginning
    
    if file_size > 5 * 1024 * 1024:
        raise ValueError('File too large. Please upload a file smaller than 5MB.')
    
    if file_size == 0:
        raise ValueError('File is empty. Please select a valid image file.')
    
    # Read file content for validation
    file_content = logo_file.read()
    logo_file.seek(0)  # Reset for later use
    
    # Allowed formats - only safe raster image formats
    allowed_formats = {'PNG', 'JPEG', 'GIF', 'WEBP'}
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Get file extension
    if '.' not in logo_file.filename:
        raise ValueError('File must have a valid extension.')
    
    file_extension = logo_file.filename.rsplit('.', 1)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise ValueError('Invalid file type. Please upload PNG, JPG, JPEG, GIF, or WEBP files only.')
    
    # Validate image using Pillow - more secure than imghdr
    try:
        file_stream = io.BytesIO(file_content)
        image = Image.open(file_stream)
        
        # Verify the image can be loaded and get format
        detected_format = image.format
        image.verify()  # Verify the image integrity
        
        # Reset stream for processing
        file_stream.seek(0)
        image = Image.open(file_stream)
        
    except Exception as e:
        raise ValueError('Invalid or corrupted image file. Please upload a valid image.')
    
    # Validate format is in allowed list
    if detected_format not in allowed_formats:
        raise ValueError(f'Unsupported image format: {detected_format}. Please upload PNG, JPG, JPEG, GIF, or WEBP files only.')
    
    # Additional security check - ensure detected format matches extension
    format_extension_map = {
        'PNG': ['png'],
        'JPEG': ['jpg', 'jpeg'],
        'GIF': ['gif'],
        'WEBP': ['webp']
    }
    
    if file_extension not in format_extension_map.get(detected_format, []):
        raise ValueError(f'File extension .{file_extension} does not match the actual file format ({detected_format}).')
    
    try:
        # Image already loaded and verified above, continue processing
        
        # Convert to RGB if necessary (for JPEG output)
        if image.mode in ('RGBA', 'P'):
            # Keep transparency for PNG, convert to RGB for others
            if detected_format == 'png':
                # Keep as RGBA for PNG
                pass
            else:
                # Convert to RGB for other formats
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = rgb_image
        
        # Get original dimensions
        original_width, original_height = image.size
        
        # Target dimensions for email compatibility
        max_width = 300
        max_height = 100
        
        # Calculate new dimensions maintaining aspect ratio
        width_ratio = max_width / original_width
        height_ratio = max_height / original_height
        ratio = min(width_ratio, height_ratio)
        
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)
        
        # Only resize if image is larger than target dimensions
        if ratio < 1:
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"Logo resized from {original_width}x{original_height} to {new_width}x{new_height}")
        
        # Create upload directory
        upload_dir = os.path.join('static', 'uploads', 'logos', str(business_account_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate secure filename - always save as PNG for consistency
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        base_filename = secure_filename(logo_file.filename)
        # Remove extension and add .png
        if '.' in base_filename:
            base_filename = base_filename.rsplit('.', 1)[0]
        filename = f"{timestamp}_{base_filename}.png"
        file_path = os.path.join(upload_dir, filename)
        
        # Save the processed image as PNG
        image.save(file_path, 'PNG', optimize=True)
        
        # Clean up old file
        _cleanup_old_logo(upload_dir, old_logo_filename)
        
        logger.info(f"Logo uploaded and processed successfully: {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"Image processing error: {e}")
        raise Exception(f"Failed to process image: {str(e)}")


def _cleanup_old_logo(upload_dir, old_logo_filename):
    """Clean up old logo file"""
    import os
    
    if old_logo_filename:
        old_file_path = os.path.join(upload_dir, old_logo_filename)
        if os.path.exists(old_file_path):
            try:
                os.remove(old_file_path)
                logger.info(f"Old logo file removed: {old_logo_filename}")
            except Exception as e:
                logger.warning(f"Failed to remove old logo file {old_logo_filename}: {e}")


# ==== SURVEY CUSTOMIZATION CONFIGURATION ROUTES ====

@business_auth_bp.route('/admin/survey-config')
@require_business_auth
def survey_config():
    """Survey customization configuration management page"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            logger.error("No current account found in survey config route")
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        # Allow demo accounts to access survey customization for testing
        
        # Import industry topic hints config for industry verticalization (Phase 2)
        from industry_topic_hints_config import get_available_industries, INDUSTRY_TOPIC_HINTS
        import json
        
        # Define available options for dropdowns
        available_industries = get_available_industries()  # Phase 2: Platform-managed industry list
        
        tone_options = [
            'professional', 'warm', 'casual', 'formal'
        ]
        
        # Topic options must match industry_topic_hints_config.py exactly (8 topics)
        topic_options = [
            'Product Quality', 'Support Experience', 'Service Rating', 
            'NPS Score', 'Pricing Value', 'User Experience',
            'Satisfaction', 'Improvement Suggestions'
        ]
        
        return render_template('business_auth/survey_config.html',
                             business_account=current_account,
                             available_industries=available_industries,
                             industry_topic_hints_json=json.dumps(INDUSTRY_TOPIC_HINTS),
                             tone_options=tone_options,
                             topic_options=topic_options,
                             ENABLE_PROMPT_PREVIEW=os.getenv('ENABLE_PROMPT_PREVIEW') == 'true')
    
    except Exception as e:
        logger.error(f"Error loading survey configuration: {e}")
        flash(_('Failed to load survey configuration.'), 'error')
        return redirect(url_for('business_auth.admin_panel'))


@business_auth_bp.route('/admin/survey-config/save', methods=['POST'])
@require_business_auth
def save_survey_config():
    """Save survey customization configuration"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        # Allow demo accounts to save survey customization for testing
        
        # Get form data
        industry = request.form.get('industry', '').strip()
        company_description = request.form.get('company_description', '').strip()
        product_description = request.form.get('product_description', '').strip()
        target_clients_description = request.form.get('target_clients_description', '').strip()
        conversation_tone = request.form.get('conversation_tone', '').strip()
        custom_end_message = request.form.get('custom_end_message', '').strip()
        
        # Survey control parameters
        max_questions = request.form.get('max_questions', type=int)
        max_duration_seconds = request.form.get('max_duration_seconds', type=int)
        max_follow_ups_per_topic = request.form.get('max_follow_ups_per_topic', type=int)
        
        # Multi-select fields
        prioritized_topics = request.form.getlist('prioritized_topics')
        optional_topics = request.form.getlist('optional_topics')
        
        # Validation
        errors = []
        
        # Validate text fields lengths
        if company_description and len(company_description) > 500:
            errors.append("Company description must be 500 characters or less.")
        if product_description and len(product_description) > 500:
            errors.append("Product description must be 500 characters or less.")
        if target_clients_description and len(target_clients_description) > 300:
            errors.append("Target customers description must be 300 characters or less.")
        if custom_end_message and len(custom_end_message) > 1000:
            errors.append("Custom end message must be 1000 characters or less.")
        
        # Validate numeric ranges
        if max_questions is not None and (max_questions < 3 or max_questions > 15):
            errors.append("Maximum questions must be between 3 and 15.")
        if max_duration_seconds is not None and (max_duration_seconds < 60 or max_duration_seconds > 300):
            errors.append("Maximum duration must be between 60 and 300 seconds.")
        if max_follow_ups_per_topic is not None and (max_follow_ups_per_topic < 1 or max_follow_ups_per_topic > 3):
            errors.append("Maximum follow-ups per topic must be between 1 and 3.")
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return redirect(url_for('business_auth.survey_config'))
        
        # Capture BEFORE values for audit trail
        before_values = {
            'industry': current_account.industry,
            'company_description': current_account.company_description,
            'product_description': current_account.product_description,
            'target_clients_description': current_account.target_clients_description,
            'conversation_tone': current_account.conversation_tone,
            'custom_end_message': current_account.custom_end_message,
            'max_questions': current_account.max_questions,
            'max_duration_seconds': current_account.max_duration_seconds,
            'max_follow_ups_per_topic': current_account.max_follow_ups_per_topic,
            'prioritized_topics': current_account.prioritized_topics,
            'optional_topics': current_account.optional_topics
        }
        
        # Update business account with survey customization fields
        current_account.industry = industry if industry else None
        current_account.company_description = company_description if company_description else None
        current_account.product_description = product_description if product_description else None
        current_account.target_clients_description = target_clients_description if target_clients_description else None
        current_account.conversation_tone = conversation_tone if conversation_tone else 'professional'
        current_account.custom_end_message = custom_end_message if custom_end_message else None
        
        # Survey control parameters
        current_account.max_questions = max_questions if max_questions is not None else 8
        current_account.max_duration_seconds = max_duration_seconds if max_duration_seconds is not None else 120
        current_account.max_follow_ups_per_topic = max_follow_ups_per_topic if max_follow_ups_per_topic is not None else 2
        
        # JSON fields
        current_account.prioritized_topics = prioritized_topics if prioritized_topics else None
        current_account.optional_topics = optional_topics if optional_topics else None
        
        # Capture AFTER values for audit trail
        after_values = {
            'industry': current_account.industry,
            'company_description': current_account.company_description,
            'product_description': current_account.product_description,
            'target_clients_description': current_account.target_clients_description,
            'conversation_tone': current_account.conversation_tone,
            'custom_end_message': current_account.custom_end_message,
            'max_questions': current_account.max_questions,
            'max_duration_seconds': current_account.max_duration_seconds,
            'max_follow_ups_per_topic': current_account.max_follow_ups_per_topic,
            'prioritized_topics': current_account.prioritized_topics,
            'optional_topics': current_account.optional_topics
        }
        
        # Identify changed fields
        changed_fields = []
        for field in before_values.keys():
            if before_values[field] != after_values[field]:
                changed_fields.append(field)
        
        # Update timestamp
        current_account.updated_at = datetime.utcnow()
        
        # Save to database
        db.session.commit()
        
        # Audit log with before/after values
        queue_audit_log(
            business_account_id=current_account.id,
            action_type='survey_config_updated',
            resource_type='business_account',
            resource_id=current_account.id,
            resource_name=current_account.name,
            details={
                'fields_changed': changed_fields,
                'changes_count': len(changed_fields),
                'before': before_values,
                'after': after_values
            }
        )
        
        logger.info(f"Survey configuration updated for business account: {current_account.name} - {len(changed_fields)} fields changed")
        flash('Survey configuration saved successfully! Your changes will be reflected in new survey sessions.', 'success')
        return redirect(url_for('business_auth.survey_config'))
        
    except Exception as e:
        logger.error(f"Error saving survey configuration: {e}")
        db.session.rollback()
        flash('Échec de l’enregistrement de la configuration de l’enquête. Veuillez réessayer.', 'error')
        return redirect(url_for('business_auth.survey_config'))



# ==== DEVELOPMENT-ONLY ROUTES ====

def _sanitize_config_overrides(overrides):
    """
    Validate and sanitize survey config overrides from client
    Prevents injection attacks and ensures data types are correct
    """
    import re
    
    sanitized = {}
    
    # Text fields - strip HTML/script tags, limit length
    text_fields = {
        'industry': 100,
        'conversation_tone': 50,
        'company_description': 500,
        'product_description': 500,
        'target_clients_description': 300,
        'custom_end_message': 1000,
        'custom_system_prompt': 5000
    }
    
    for field, max_length in text_fields.items():
        if field in overrides:
            value = str(overrides[field])
            # Strip script tags
            value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
            # Limit length
            value = value[:max_length]
            sanitized[field] = value
    
    # Numeric fields - ensure integers within valid ranges
    numeric_fields = {
        'max_questions': (3, 15, 8),
        'max_duration_seconds': (60, 300, 120),
        'max_follow_ups_per_topic': (1, 5, 2)
    }
    
    for field, (min_val, max_val, default) in numeric_fields.items():
        if field in overrides:
            try:
                value = int(overrides[field])
                # Clamp to valid range
                value = max(min_val, min(max_val, value))
                sanitized[field] = value
            except (ValueError, TypeError):
                sanitized[field] = default
    
    # Array fields - ensure they're lists of strings
    array_fields = ['survey_goals', 'prioritized_topics', 'optional_topics']
    
    for field in array_fields:
        if field in overrides:
            if isinstance(overrides[field], list):
                # Filter out non-strings and limit to 20 items
                sanitized[field] = [str(item)[:100] for item in overrides[field] if item][:20]
            else:
                sanitized[field] = []
    
    return sanitized

@business_auth_bp.route('/dev/prompt-preview', methods=['GET', 'POST'])
@require_business_auth
def prompt_preview():
    """
    Development-only endpoint for previewing AI survey prompts
    Requires ENABLE_PROMPT_PREVIEW=true environment variable
    Multi-tenant safe: Always uses session business account, validates campaign ownership
    
    Supports both GET (DB values) and POST (form override values) for pre-save validation
    """
    import os
    
    # Guard: Only available when environment variable is enabled
    if not os.getenv('ENABLE_PROMPT_PREVIEW') == 'true':
        return jsonify({'error': 'Not available'}), 404
    
    try:
        # CRITICAL: Always use session's business account (ignore user-supplied account_id to prevent tenant leakage)
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Not authenticated'}), 401
        
        business_account_id = current_account.id
        
        # Get optional campaign_id (from query string for GET, from body for POST)
        campaign_id = None
        config_overrides = None
        
        if request.method == 'POST':
            # Extract data from JSON body
            data = request.get_json() or {}
            # Note: dict.get doesn't support type parameter (unlike request.args.get)
            # Safely parse campaign_id with try/except to handle malformed inputs
            campaign_id = None
            if 'campaign_id' in data and data['campaign_id']:
                try:
                    campaign_id = int(data['campaign_id'])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid campaign_id in preview request: {data.get('campaign_id')}")
                    campaign_id = None
            
            config_overrides = data.get('config_overrides', {})
            
            # Validate and sanitize overrides
            if config_overrides:
                config_overrides = _sanitize_config_overrides(config_overrides)
        else:
            # GET request - use query params (legacy support)
            campaign_id = request.args.get('campaign_id', type=int)
        
        # Validate campaign ownership if campaign_id provided
        if campaign_id:
            from models import Campaign
            campaign = Campaign.query.filter_by(
                id=campaign_id,
                business_account_id=business_account_id  # Enforce tenant ownership
            ).first()
            
            if not campaign:
                return jsonify({'error': 'Campaign not found or access denied'}), 404
        
        # Generate preview using helper (with optional overrides)
        from prompt_preview_helper import build_preview_prompt
        
        preview_data = build_preview_prompt(
            business_account_id=business_account_id,
            campaign_id=campaign_id,
            config_overrides=config_overrides
        )
        
        # Return preview data as JSON
        return jsonify({
            'success': True,
            'prompt': preview_data['system_prompt'],
            'config': preview_data['config'],
            'metadata': preview_data['metadata'],
            'sample_context': preview_data['sample_context']
        })
    
    except Exception as e:
        logger.error(f"Error generating prompt preview: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==== LICENSE MANAGEMENT ROUTES ====

# Business account license overview routes (for regular business users)
@business_auth_bp.route('/admin/licenses/overview')
@require_business_auth
def business_license_overview():
    """View license overview for current business account"""
    try:
        # Get current business account
        business_account = get_current_business_account()
        if not business_account:
            flash('Business account not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get filter parameter
        filter_type = request.args.get('filter', 'overview').lower()
        
        # Get license information for current business account only
        from license_service import LicenseService
        
        try:
            current_license = LicenseService.get_current_license(business_account.id)
            license_info = LicenseService.get_license_info(business_account.id)
            
            # Get usage statistics
            campaigns_used = LicenseService.get_campaigns_used_in_current_period(business_account.id)
            users_count = getattr(business_account, 'current_users_count', 0)
            
            account_data = {
                'id': business_account.id,
                'name': business_account.name,
                'account_type': business_account.account_type,
                'status': business_account.status,
                'current_license': current_license,
                'license_type': license_info.get('license_type', 'trial'),
                'license_status': license_info.get('license_status', 'trial'),
                'license_start': license_info.get('license_start'),
                'license_end': license_info.get('license_end'),
                'campaigns_used': campaigns_used,
                'campaigns_limit': license_info.get('campaigns_limit', 4),
                'users_count': users_count,
                'users_limit': license_info.get('users_limit', 5),
                'expires_soon': license_info.get('expires_soon', False),
                'days_remaining': license_info.get('days_remaining', 0)
            }
            
            # Set page context based on filter
            page_title = "License Overview"
            if filter_type == 'usage':
                page_title = "License Usage Details"
            elif filter_type == 'expiring':
                page_title = "License Expiration Information"
            
            return render_template('business_auth/license_overview.html',
                                 account_data=account_data,
                                 filter_type=filter_type,
                                 page_title=page_title)
        
        except Exception as license_error:
            logger.error(f"Error retrieving license info for business account {business_account.id}: {license_error}")
            flash('Failed to load license information. Please try again.', 'error')
            return redirect(url_for('business_auth.admin_panel'))
    
    except Exception as e:
        logger.error(f"Error loading business license overview: {e}")
        flash('Failed to load license overview. Please try again.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


# Platform admin license management routes (for platform admins only)
@business_auth_bp.route('/admin/licenses/')
@require_platform_admin
def admin_licenses():
    """List all business accounts with current license status (Platform Admin Only)"""
    try:
        # Get filter parameter
        filter_type = request.args.get('filter', 'all').lower()
        
        # Use bulk optimization method to fetch all license data efficiently
        bulk_license_data = LicenseService.get_bulk_license_data()
        
        # Transform bulk data to match original format
        licenses_data = []
        for account_id, data in bulk_license_data.items():
            account = data['account']
            license_info = data['license_info']
            
            # Check if there's an unactivated admin user (check both 'admin' and legacy 'business_account_admin')
            unactivated_admin = BusinessAccountUser.query.filter(
                BusinessAccountUser.business_account_id == account.id,
                BusinessAccountUser.role.in_(['admin', 'business_account_admin']),
                BusinessAccountUser.email_verified == False
            ).first()
            
            # Get active campaign count for parallel campaigns toggle validation
            from models import Campaign
            active_campaigns_count = Campaign.query.filter_by(
                business_account_id=account.id,
                status='active'
            ).count()
            
            account_data = {
                'id': account.id,
                'name': account.name,
                'account_type': account.account_type,
                'status': account.status,
                'current_license': license_info.get('current_license'),
                'license_type': license_info.get('license_type', 'trial'),
                'license_status': license_info.get('license_status', 'trial'),
                'license_start': license_info.get('license_start'),
                'license_end': license_info.get('license_end'),
                'campaigns_used': license_info.get('campaigns_used', 0),
                'campaigns_limit': license_info.get('campaigns_limit', 4),
                'users_count': license_info.get('users_used', 0),
                'users_limit': license_info.get('users_limit', 5),
                'expires_soon': license_info.get('expires_soon', False),
                'days_remaining': license_info.get('days_remaining', 0),
                'total_respondents': license_info.get('total_respondents', 0),
                'total_invitations': license_info.get('total_invitations', 0),
                'has_unactivated_admin': unactivated_admin is not None,
                'unactivated_admin_id': unactivated_admin.id if unactivated_admin else None,
                'unactivated_admin_email': unactivated_admin.email if unactivated_admin else None,
                'allow_parallel_campaigns': getattr(account, 'allow_parallel_campaigns', False),
                'active_campaigns_count': active_campaigns_count
            }
            licenses_data.append(account_data)
        
        # Apply filtering based on filter_type
        filtered_data = licenses_data
        page_title = "All Business Accounts"
        
        if filter_type == 'expiring':
            filtered_data = [data for data in licenses_data if data.get('expires_soon', False)]
            page_title = "Expiring Licenses"
        elif filter_type == 'trial':
            filtered_data = [data for data in licenses_data if data.get('license_type') == 'trial']
            page_title = "Trial Accounts"
        elif filter_type == 'usage':
            # Show accounts with high usage (>80% of limits)
            filtered_data = [data for data in licenses_data 
                           if (data.get('campaigns_used', 0) / max(data.get('campaigns_limit', 1), 1) > 0.8) or
                              (data.get('users_count', 0) / max(data.get('users_limit', 1), 1) > 0.8)]
            page_title = "High Usage Accounts"
        
        return render_template('business_auth/admin_licenses.html',
                             licenses_data=filtered_data,
                             total_accounts=len(licenses_data),
                             filter_type=filter_type,
                             page_title=page_title)
        
    except Exception as e:
        logger.error(f"Error loading admin licenses page: {e}")
        flash('Failed to load license information. Please try again.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@business_auth_bp.route('/admin/licenses/assign/<int:business_id>')
@require_platform_admin
def license_assignment_form(business_id):
    """Show license assignment form for specific business account (Platform Admin Only)"""
    try:
        # Validate business account access (platform admin is allowed)
        is_valid, business_account, message = validate_business_account_access(business_id, allow_platform_admin=True)
        if not is_valid:
            logger.warning(f"Unauthorized license assignment form access attempt: {message}")
            flash('Access denied. You cannot access this business account.', 'error')
            return redirect(url_for('business_auth.admin_licenses'))
        
        if not business_account:
            flash('Business account not found.', 'error')
            return redirect(url_for('business_auth.admin_licenses'))
        
        # Get current license information with error handling
        try:
            current_license = LicenseService.get_current_license(business_id)
            license_info = LicenseService.get_license_info(business_id)
        except Exception as license_error:
            logger.error(f"Error retrieving license info for business_id {business_id}: {license_error}")
            current_license = None
            license_info = {'license_type': 'trial', 'license_status': 'error'}
        
        # Get available license types
        try:
            available_types = LicenseService.get_available_license_types()
        except Exception as types_error:
            logger.error(f"Error retrieving available license types: {types_error}")
            available_types = ['core', 'plus', 'pro']  # Fallback
        
        # Get current usage statistics with error handling
        try:
            campaigns_used = LicenseService.get_campaigns_used_in_current_period(business_id)
            users_count = getattr(business_account, 'current_users_count', 0)
        except Exception as usage_error:
            logger.error(f"Error retrieving usage statistics for business_id {business_id}: {usage_error}")
            campaigns_used = 0
            users_count = 0
        
        # Get license templates with pricing information
        from license_templates import LicenseTemplateManager
        try:
            core_template = LicenseTemplateManager.get_template('core')
            plus_template = LicenseTemplateManager.get_template('plus')
            pro_template = LicenseTemplateManager.get_template('pro')
        except Exception as template_error:
            logger.error(f"Error retrieving license templates: {template_error}")
            core_template = None
            plus_template = None
            pro_template = None
        
        # Defensive data sanitization
        template_data = {
            'business_account': business_account,
            'current_license': current_license,
            'license_info': license_info,
            'available_types': available_types,
            'campaigns_used': max(0, campaigns_used),  # Ensure non-negative
            'users_count': max(0, users_count),  # Ensure non-negative
            'usage_stats': {
                'users_count': max(0, users_count),
                'campaigns_count': max(0, campaigns_used),
                'responses_count': 0  # TODO: Add response count when available
            },
            # License templates with pricing
            'core_template': core_template,
            'plus_template': plus_template,
            'pro_template': pro_template
        }
        
        # Log platform admin access for audit
        current_user = BusinessAccountUser.query.get(session.get('business_user_id'))
        logger.info(f"Platform admin {current_user.email if current_user else 'unknown'} accessed license assignment form for business_id {business_id} ({business_account.name})")
        
        return render_template('business_auth/licenses/assignment_form.html', **template_data)
        
    except Exception as e:
        logger.error(f"Error loading license assignment form for business_id {business_id}: {e}")
        flash('Failed to load assignment form. Please try again.', 'error')
        return redirect(url_for('business_auth.admin_licenses'))


@business_auth_bp.route('/admin/licenses/assign', methods=['POST'])
@require_platform_admin
def process_license_assignment():
    """Process license assignment form submission (Platform Admin Only)"""
    try:
        # Get form data with validation
        business_id_str = request.form.get('business_id', '').strip()
        license_type = request.form.get('license_type', '').strip().lower()
        
        # Comprehensive input validation
        if not business_id_str or not license_type:
            flash('Business account and license type are required.', 'error')
            return redirect(url_for('business_auth.admin_licenses'))
        
        # Validate business_id is numeric
        try:
            business_id = int(business_id_str)
            if business_id <= 0:
                raise ValueError("Business ID must be positive")
        except ValueError:
            logger.warning(f"Invalid business_id provided in license assignment: '{business_id_str}'")
            flash('Invalid business account ID.', 'error')
            return redirect(url_for('business_auth.admin_licenses'))
        
        # Validate license type
        valid_license_types = ['core', 'plus', 'pro', 'trial']
        if license_type not in valid_license_types:
            logger.warning(f"Invalid license_type provided: '{license_type}'")
            flash('Invalid license type selected.', 'error')
            return redirect(url_for('business_auth.admin_licenses'))
        
        # Validate business account access (platform admin is allowed)
        is_valid, business_account, message = validate_business_account_access(business_id, allow_platform_admin=True)
        if not is_valid:
            logger.warning(f"Unauthorized license assignment attempt: {message} for business_id {business_id}")
            flash('Access denied. You cannot assign licenses to this business account.', 'error')
            return redirect(url_for('business_auth.admin_licenses'))
        
        if not business_account:
            flash('Business account not found.', 'error')
            return redirect(url_for('business_auth.admin_licenses'))
        
        # Get current user for audit trail
        current_user = BusinessAccountUser.query.get(session.get('business_user_id'))
        if not current_user:
            logger.error("License assignment attempted without valid user session")
            flash('Invalid user session. Please log in again.', 'error')
            return redirect(url_for('business_auth.login'))
        
        created_by = current_user.get_full_name()
        
        # Handle custom configuration for Pro licenses with comprehensive validation
        custom_config = None
        if license_type == 'pro':
            custom_config = {}
            
            # Get and validate custom limits from form
            try:
                campaigns_limit = request.form.get('max_campaigns_per_year', '').strip()
                users_limit = request.form.get('max_users', '').strip()
                participants_limit = request.form.get('max_participants_per_campaign', '').strip()
                
                if campaigns_limit:
                    campaigns_value = int(campaigns_limit)
                    if campaigns_value < 1 or campaigns_value > 1000:
                        flash('Maximum campaigns per year must be between 1 and 1000.', 'error')
                        return redirect(url_for('business_auth.license_assignment_form', business_id=business_id))
                    custom_config['max_campaigns_per_year'] = campaigns_value
                
                if users_limit:
                    users_value = int(users_limit)
                    if users_value < 1 or users_value > 10000:
                        flash('Maximum users must be between 1 and 10,000.', 'error')
                        return redirect(url_for('business_auth.license_assignment_form', business_id=business_id))
                    custom_config['max_users'] = users_value
                
                if participants_limit:
                    participants_value = int(participants_limit)
                    if participants_value < 1 or participants_value > 1000000:
                        flash('Maximum target responses per campaign must be between 1 and 1,000,000.', 'error')
                        return redirect(url_for('business_auth.license_assignment_form', business_id=business_id))
                    custom_config['max_participants_per_campaign'] = participants_value
                
                invitations_limit = request.form.get('max_invitations_per_campaign', '').strip()
                if invitations_limit:
                    invitations_value = int(invitations_limit)
                    if invitations_value < 1 or invitations_value > 5000000:
                        flash('Maximum invitations per campaign must be between 1 and 5,000,000.', 'error')
                        return redirect(url_for('business_auth.license_assignment_form', business_id=business_id))
                    custom_config['max_invitations_per_campaign'] = invitations_value
                    
            except ValueError:
                flash('Custom limit values must be valid positive numbers.', 'error')
                return redirect(url_for('business_auth.license_assignment_form', business_id=business_id))
        
        # Additional security: Re-validate the business account hasn't changed
        fresh_business_account = BusinessAccount.query.get(business_id)
        if not fresh_business_account or fresh_business_account.name != business_account.name:
            logger.error(f"Business account validation failed during license assignment for business_id {business_id}")
            flash('Business account validation failed. Please try again.', 'error')
            return redirect(url_for('business_auth.admin_licenses'))
        
        # Transcript upload is now universally available to all license tiers
        # No add-on configuration needed - usage bounded by participant response limits
        transcript_addon_config = None
        
        # Log the assignment attempt for audit
        logger.info(f"Platform admin {current_user.email} attempting to assign {license_type} license to business_id {business_id} ({business_account.name})")
        
        # Call LicenseService to assign license
        success, license_record, message = LicenseService.assign_license_to_business(
            business_id=business_id,
            license_type=license_type,
            custom_config=custom_config,
            created_by=created_by,
            transcript_addon_config=transcript_addon_config
        )
        
        if success:
            flash(f'License assigned successfully: {message}', 'success')
            logger.info(f"License {license_type} successfully assigned to business_id {business_id} by {current_user.email}")
            
            # Audit log successful assignment
            try:
                from audit_utils import audit_license_assignment
                audit_license_assignment(
                    admin_email=current_user.email,
                    admin_name=created_by,
                    business_account_id=business_id,
                    business_account_name=business_account.name,
                    license_type=license_type,
                    custom_config=custom_config,
                    success=True
                )
            except Exception as audit_error:
                logger.error(f"Failed to audit license assignment: {audit_error}")
        else:
            flash(f'Failed to assign license: {message}', 'error')
            logger.error(f"Failed to assign license {license_type} to business_id {business_id}: {message}")
        
        return redirect(url_for('business_auth.admin_licenses'))
        
    except Exception as e:
        logger.error(f"Error processing license assignment: {e}")
        flash('Failed to process license assignment. Please try again.', 'error')
        return redirect(url_for('business_auth.admin_licenses'))


@business_auth_bp.route('/admin/licenses/<int:business_id>/toggle-parallel-campaigns', methods=['POST'])
@require_platform_admin
def toggle_parallel_campaigns(business_id):
    """Toggle allow_parallel_campaigns setting for a business account (Platform Admin Only)
    
    Implements downgrade protection: cannot disable parallel campaigns when 2+ campaigns are active.
    This prevents data inconsistency where multiple active campaigns exist but parallel mode is off.
    """
    try:
        from models import BusinessAccount, Campaign
        
        # Validate business account access (platform admin is allowed)
        is_valid, business_account, message = validate_business_account_access(business_id, allow_platform_admin=True)
        if not is_valid:
            logger.warning(f"Unauthorized parallel campaigns toggle attempt: {message}")
            if request.is_json:
                return jsonify({'success': False, 'error': 'Access denied'}), 403
            flash('Access denied. You cannot modify this business account.', 'error')
            return redirect(url_for('business_auth.admin_licenses'))
        
        if not business_account:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Business account not found'}), 404
            flash('Business account not found.', 'error')
            return redirect(url_for('business_auth.admin_licenses'))
        
        # Get current user for audit trail
        current_user = BusinessAccountUser.query.get(session.get('business_user_id'))
        if not current_user:
            logger.error("Parallel campaigns toggle attempted without valid user session")
            if request.is_json:
                return jsonify({'success': False, 'error': 'Invalid session'}), 401
            flash('Invalid user session. Please log in again.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get current state
        current_state = business_account.allow_parallel_campaigns
        new_state = not current_state
        
        # DOWNGRADE PROTECTION: If disabling, check for 2+ active campaigns
        if current_state and not new_state:
            active_campaign_count = Campaign.query.filter_by(
                business_account_id=business_id,
                status='active'
            ).count()
            
            if active_campaign_count >= 2:
                error_msg = f'Cannot disable parallel campaigns: {active_campaign_count} campaigns are currently active. Complete or cancel campaigns until only 1 remains.'
                logger.warning(f"Parallel campaigns downgrade blocked for business_id {business_id}: {active_campaign_count} active campaigns")
                
                if request.is_json:
                    return jsonify({
                        'success': False, 
                        'error': error_msg,
                        'active_campaign_count': active_campaign_count
                    }), 409
                flash(error_msg, 'error')
                return redirect(url_for('business_auth.admin_licenses'))
        
        # Update the setting
        business_account.allow_parallel_campaigns = new_state
        db.session.commit()
        
        action = 'enabled' if new_state else 'disabled'
        logger.info(f"Platform admin {current_user.email} {action} parallel campaigns for business_id {business_id} ({business_account.name})")
        
        # Audit log the change
        try:
            from models import AuditLog
            audit_entry = AuditLog(
                action='parallel_campaigns_toggle',
                entity_type='business_account',
                entity_id=business_id,
                user_id=current_user.id,
                user_email=current_user.email,
                details=f"Parallel campaigns {action} for {business_account.name}",
                metadata={
                    'business_account_id': business_id,
                    'business_account_name': business_account.name,
                    'previous_state': current_state,
                    'new_state': new_state,
                    'admin_email': current_user.email
                }
            )
            db.session.add(audit_entry)
            db.session.commit()
        except Exception as audit_error:
            logger.error(f"Failed to audit parallel campaigns toggle: {audit_error}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'new_state': new_state,
                'message': f'Parallel campaigns {action}'
            })
        
        flash(f'Parallel campaigns {action} for {business_account.name}.', 'success')
        return redirect(url_for('business_auth.admin_licenses'))
        
    except Exception as e:
        logger.error(f"Error toggling parallel campaigns for business_id {business_id}: {e}")
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'error': 'Internal server error'}), 500
        flash('Failed to toggle parallel campaigns. Please try again.', 'error')
        return redirect(url_for('business_auth.admin_licenses'))


@business_auth_bp.route('/admin/licenses/history/<int:business_id>')
@require_platform_admin
def license_history(business_id):
    """Show license history timeline for specific business account (Platform Admin Only)"""
    try:
        # Validate business account access (platform admin is allowed)
        is_valid, business_account, message = validate_business_account_access(business_id, allow_platform_admin=True)
        if not is_valid:
            logger.warning(f"Unauthorized license history access attempt: {message}")
            flash('Access denied. You cannot view this business account license history.', 'error')
            return redirect(url_for('business_auth.admin_licenses'))
        
        if not business_account:
            flash('Business account not found.', 'error')
            return redirect(url_for('business_auth.admin_licenses'))
        
        # Get license history with error handling
        try:
            license_history_records = LicenseService.get_license_history(business_id)
            if not license_history_records:
                license_history_records = []  # Ensure we have an empty list instead of None
        except Exception as history_error:
            logger.error(f"Error retrieving license history for business_id {business_id}: {history_error}")
            license_history_records = []
        
        # Get current license for comparison with error handling
        try:
            current_license = LicenseService.get_current_license(business_id)
        except Exception as current_error:
            logger.error(f"Error retrieving current license for business_id {business_id}: {current_error}")
            current_license = None
        
        # Sanitize and validate history records
        safe_history = []
        for record in license_history_records:
            try:
                # Ensure the record belongs to the correct business account
                if hasattr(record, 'business_account_id') and record.business_account_id == business_id:
                    safe_history.append(record)
                else:
                    logger.warning(f"License history record {getattr(record, 'id', 'unknown')} does not belong to business_id {business_id}")
            except Exception as record_error:
                logger.error(f"Error processing license history record: {record_error}")
                continue
        
        template_data = {
            'business_account': business_account,
            'license_history': safe_history,
            'current_license': current_license,
            'history_count': len(safe_history)
        }
        
        # Log platform admin access for audit
        current_user = BusinessAccountUser.query.get(session.get('business_user_id'))
        logger.info(f"Platform admin {current_user.email if current_user else 'unknown'} accessed license history for business_id {business_id} ({business_account.name})")
        
        return render_template('business_auth/licenses/history.html', **template_data)
        
    except Exception as e:
        logger.error(f"Error loading license history for business_id {business_id}: {e}")
        flash('Failed to load license history. Please try again.', 'error')
        return redirect(url_for('business_auth.admin_licenses'))


@business_auth_bp.route('/admin/licenses/dashboard')
@require_platform_admin
def license_dashboard():
    """License management dashboard with overview statistics and quick actions (Platform Admin Only)"""
    try:
        # Log platform admin access for audit
        current_user = BusinessAccountUser.query.get(session.get('business_user_id'))
        logger.info(f"Platform admin {current_user.email if current_user else 'unknown'} accessed license dashboard")
        
        # Pass user context to template
        is_platform_admin = current_user.is_platform_admin() if current_user else False
        
        # Get overall statistics with error handling (exclude platform owner ID 10)
        try:
            total_accounts = BusinessAccount.query.filter(BusinessAccount.id != 10).count()
            if total_accounts < 0:
                total_accounts = 0
        except Exception as count_error:
            logger.error(f"Error counting business accounts: {count_error}")
            total_accounts = 0
        
        # Initialize statistics with safe defaults
        license_distribution = {}
        active_licenses = 0
        expired_licenses = 0
        trial_accounts = 0
        total_campaigns_this_month = 0
        total_users = 0
        accounts_expiring_soon = []
        accounts_processed = 0
        accounts_with_errors = 0
        
        # Process customer business accounts only (exclude platform owner accounts)
        try:
            business_accounts = BusinessAccount.query.filter(BusinessAccount.id != 10).all()
        except Exception as query_error:
            logger.error(f"Error querying business accounts: {query_error}")
            business_accounts = []
        
        # PERFORMANCE: Pre-calculate campaign counts to avoid N+1 queries
        from sqlalchemy import func
        account_ids = [account.id for account in business_accounts]
        campaigns_by_account = {}
        
        if account_ids:
            try:
                # Batch query: Get all campaign counts grouped by business_account_id
                # This replaces N individual queries with a single batch query
                for account_id in account_ids:
                    try:
                        campaigns_by_account[account_id] = LicenseService.get_campaigns_used_in_current_period(account_id)
                    except Exception as count_error:
                        campaigns_by_account[account_id] = 0
            except Exception as batch_error:
                logger.warning(f"Error pre-calculating campaign counts: {batch_error}")
        
        for account in business_accounts:
            try:
                # Validate account data
                if not account or not hasattr(account, 'id'):
                    logger.warning(f"Invalid account object encountered during dashboard processing")
                    accounts_with_errors += 1
                    continue
                
                accounts_processed += 1
                
                # PERFORMANCE: Pass account object to avoid duplicate query
                # Use bypass_admin_override=True to get actual license data for analytics
                try:
                    license_info = LicenseService.get_license_info(
                        account.id, 
                        business_account=account,
                        bypass_admin_override=True
                    )
                    license_type = license_info.get('license_type', 'trial')
                    license_status = license_info.get('license_status', 'trial')
                    
                    # Validate license type and status values
                    valid_license_types = ['core', 'plus', 'pro', 'trial']
                    valid_license_statuses = ['active', 'expired', 'trial', 'suspended', 'unlimited']
                    
                    if license_type not in valid_license_types:
                        logger.warning(f"Invalid license_type '{license_type}' for account {account.id}")
                        license_type = 'trial'
                    
                    if license_status not in valid_license_statuses:
                        logger.warning(f"Invalid license_status '{license_status}' for account {account.id}")
                        license_status = 'trial'
                    
                except Exception as license_error:
                    logger.error(f"Error getting license info for account {account.id}: {license_error}")
                    license_type = 'trial'
                    license_status = 'trial'
                    license_info = {'license_type': 'trial', 'license_status': 'trial'}
                
                # Count license types safely
                license_distribution[license_type] = license_distribution.get(license_type, 0) + 1
                
                # Count license statuses
                if license_status == 'active':
                    active_licenses += 1
                elif license_status == 'expired':
                    expired_licenses += 1
                elif license_status == 'trial':
                    trial_accounts += 1
                
                # Check for accounts expiring soon with validation
                try:
                    if license_info.get('expires_soon', False):
                        days_remaining = license_info.get('days_remaining', 0)
                        if isinstance(days_remaining, (int, float)) and days_remaining >= 0:
                            accounts_expiring_soon.append({
                                'id': account.id,
                                'name': getattr(account, 'name', f'Account {account.id}'),
                                'days_remaining': int(days_remaining),
                                'license_type': license_type
                            })
                except Exception as expiry_error:
                    logger.warning(f"Error processing expiry info for account {account.id}: {expiry_error}")
                
                # PERFORMANCE: Use pre-fetched campaign count
                try:
                    campaigns_used = campaigns_by_account.get(account.id, 0)
                    campaigns_used = max(0, int(campaigns_used)) if campaigns_used is not None else 0
                    total_campaigns_this_month += campaigns_used
                    
                    users_count = getattr(account, 'current_users_count', 0)
                    users_count = max(0, int(users_count)) if users_count is not None else 0
                    total_users += users_count
                    
                except Exception as usage_error:
                    logger.warning(f"Error getting usage statistics for account {account.id}: {usage_error}")
                
            except Exception as account_error:
                logger.error(f"Error processing account {getattr(account, 'id', 'unknown')} for dashboard: {account_error}")
                accounts_with_errors += 1
                # Count as trial account if error
                trial_accounts += 1
        
        # Get available license types for quick assignment with fallback
        try:
            available_types = LicenseService.get_available_license_types()
            if not available_types:
                available_types = ['core', 'plus', 'pro']  # Safe fallback
        except Exception as types_error:
            logger.error(f"Error getting available license types: {types_error}")
            available_types = ['core', 'plus', 'pro']  # Safe fallback
        
        # Sanitize accounts_expiring_soon (limit to prevent UI issues)
        accounts_expiring_soon = accounts_expiring_soon[:50]  # Limit to 50 entries
        
        # Structure data to match template expectations
        license_stats = {
            'total_accounts': max(0, total_accounts),
            'core_licenses': license_distribution.get('core', 0),
            'plus_licenses': license_distribution.get('plus', 0),
            'pro_licenses': license_distribution.get('pro', 0),
            'trial_accounts': trial_accounts,  # Use STATUS counter (not TYPE) to show accounts actively trialing
            'expiring_soon': len(accounts_expiring_soon),
            'account_growth': 0  # Could calculate this from historical data later
        }
        
        dashboard_data = {
            'license_stats': license_stats,
            'total_accounts': max(0, total_accounts),
            'active_licenses': max(0, active_licenses),
            'expired_licenses': max(0, expired_licenses),
            'trial_accounts': max(0, trial_accounts),
            'license_distribution': license_distribution,
            'total_campaigns_this_month': max(0, total_campaigns_this_month),
            'total_users': max(0, total_users),
            'accounts_expiring_soon': accounts_expiring_soon,
            'available_types': available_types,
            'accounts_processed': accounts_processed,
            'accounts_with_errors': accounts_with_errors,
            'alerts': [],  # Add empty alerts for now
            'recent_activities': [],  # Add empty activities for now
            'is_platform_admin': is_platform_admin  # Platform admin status for conditional links
        }
        
        return render_template('business_auth/licenses/dashboard.html', needs_charts=True, **dashboard_data)
        
    except Exception as e:
        logger.error(f"Error loading license dashboard: {e}")
        flash('Failed to load license dashboard. Please try again.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


# ==== EXECUTIVE REPORT API ROUTES ====

@business_auth_bp.route('/api/campaigns/<int:campaign_id>/executive-reports', methods=['GET'])
@require_business_auth
def get_executive_reports(campaign_id):
    """Get executive reports for a campaign"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account context not found'}), 401
        
        # Verify campaign belongs to current business account
        from models import Campaign
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Get executive reports for this campaign
        from models import ExecutiveReport
        reports = ExecutiveReport.query.filter_by(
            campaign_id=campaign_id,
            business_account_id=current_account.id
        ).order_by(ExecutiveReport.created_at.desc()).all()
        
        return jsonify({
            'executive_reports': [report.to_dict() for report in reports]
        })
        
    except Exception as e:
        logger.error(f"Error getting executive reports for campaign {campaign_id}: {e}")
        return jsonify({'error': 'Failed to get executive reports'}), 500


@business_auth_bp.route('/api/campaigns/<int:campaign_id>/executive-reports/download', methods=['GET'])
@require_business_auth
def download_executive_report(campaign_id):
    """Download executive report for a campaign"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account context not found'}), 401
        
        # Verify campaign belongs to current business account
        from models import Campaign
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Get executive report for this campaign
        from models import ExecutiveReport
        report = ExecutiveReport.query.filter_by(
            campaign_id=campaign_id,
            business_account_id=current_account.id,
            status='completed'
        ).order_by(ExecutiveReport.created_at.desc()).first()
        
        if not report:
            return jsonify({'error': 'Executive report not found or not ready'}), 404
        
        # Check if file exists
        import os
        if not os.path.exists(report.file_path):
            return jsonify({'error': 'Report file not found on disk'}), 404
        
        # Update download count
        report.download_count += 1
        db.session.commit()
        
        # Log the download in audit trail
        try:
            from audit_utils import queue_audit_log
            queue_audit_log(
                business_account_id=current_account.id,
                action_type='executive_report_downloaded',
                resource_type='campaign',
                resource_id=campaign_id,
                resource_name=campaign.name,
                details={
                    'report_id': report.id,
                    'file_name': f"Executive_Report_{campaign.name}_{report.generated_at.strftime('%Y%m%d')}.pdf",
                    'report_generated_at': report.generated_at.isoformat() if report.generated_at else None,
                    'download_count': report.download_count
                }
            )
        except Exception as e:
            logger.error(f"Failed to log executive report download audit event: {e}")
        
        # Serve the file
        from flask import send_file
        filename = f"Executive_Report_{campaign.name}_{report.generated_at.strftime('%Y%m%d')}.pdf"
        
        return send_file(
            report.file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Error downloading executive report for campaign {campaign_id}: {e}")
        return jsonify({'error': 'Failed to download executive report'}), 500


@business_auth_bp.route('/api/campaigns/<int:campaign_id>/executive-reports/generate', methods=['POST'])
@require_business_auth
def generate_executive_report_manually(campaign_id):
    """Manually trigger executive report generation for a campaign"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account context not found'}), 401
        
        # Verify campaign belongs to current business account and user has admin permission
        from models import Campaign
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Check if campaign is completed
        if campaign.status != 'completed':
            return jsonify({'error': 'Campaign must be completed to generate executive report'}), 400
        
        # Check if user has admin permission
        business_user_id = session.get('business_user_id')
        from models import BusinessAccountUser
        user = BusinessAccountUser.query.get(business_user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin permission required'}), 403
        
        # Queue executive report generation with lazy import to avoid circular imports
        from task_queue import task_queue
        task_queue.add_task('executive_report', data_id=campaign.id, task_data={
            'campaign_id': campaign.id,
            'business_account_id': current_account.id,
            'user_id': user.id,
            'user_email': user.email,
            'user_name': user.get_full_name()
        })
        
        logger.info(f"Manual executive report generation queued for campaign {campaign.id} by user {user.email}")
        
        return jsonify({
            'message': 'Executive report generation started',
            'campaign_id': campaign.id
        })
        
    except Exception as e:
        logger.error(f"Error generating executive report for campaign {campaign_id}: {e}")
        return jsonify({'error': 'Failed to start executive report generation'}), 500


@business_auth_bp.route('/api/campaigns/<int:campaign_id>/executive-reports/regenerate', methods=['POST'])
@require_business_auth
def regenerate_executive_report(campaign_id):
    """Regenerate an existing executive report for a campaign"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account context not found'}), 401
        
        # Verify campaign belongs to current business account
        from models import Campaign
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Check if campaign is completed
        if campaign.status != 'completed':
            return jsonify({'error': 'Campaign must be completed to regenerate executive report'}), 400
        
        # Check if user has admin permission
        business_user_id = session.get('business_user_id')
        from models import BusinessAccountUser
        user = BusinessAccountUser.query.get(business_user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin permission required'}), 403
        
        # Check if existing report exists
        from models import ExecutiveReport
        existing_report = ExecutiveReport.query.filter_by(
            campaign_id=campaign_id,
            business_account_id=current_account.id
        ).order_by(ExecutiveReport.created_at.desc()).first()
        
        if not existing_report:
            return jsonify({'error': 'No existing report found to regenerate. Please generate a new report instead.'}), 404
        
        # Prevent duplicate regeneration requests
        if existing_report.status == 'processing':
            return jsonify({'message': 'Report regeneration already in progress'}), 200
        
        # Update report status to processing
        existing_report.status = 'processing'
        existing_report.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Queue executive report regeneration
        from task_queue import task_queue
        task_queue.add_task('executive_report', data_id=campaign.id, task_data={
            'campaign_id': campaign.id,
            'business_account_id': current_account.id,
            'regenerating': True,
            'report_id': existing_report.id,
            'user_id': user.id,
            'user_email': user.email,
            'user_name': user.get_full_name()
        })
        
        logger.info(f"Executive report regeneration queued for campaign {campaign.id} by user {user.email}")
        
        return jsonify({
            'message': 'Executive report regeneration started',
            'campaign_id': campaign.id
        })
        
    except Exception as e:
        logger.error(f"Error regenerating executive report for campaign {campaign_id}: {e}")
        return jsonify({'error': 'Failed to start executive report regeneration'}), 500


# ==== TRANSCRIPT ANALYSIS ROUTES ====

@business_auth_bp.route('/api/campaigns/<int:campaign_id>/transcripts/upload', methods=['POST'])
@require_business_auth
def upload_transcript(campaign_id):
    """Upload and process transcript for a campaign"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account context not found'}), 401
        
        # Check if user has admin permission
        business_user_id = session.get('business_user_id')
        from models import BusinessAccountUser
        user = BusinessAccountUser.query.get(business_user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin permission required'}), 403
        
        # Verify campaign belongs to current business account
        from models import Campaign
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Check if campaign is active (only active campaigns can receive transcript uploads)
        if campaign.status != 'active':
            return jsonify({'error': 'Transcript upload only allowed for active campaigns'}), 400
        
        # Check for uploaded file
        if 'transcript_file' not in request.files:
            return jsonify({'error': 'No transcript file provided'}), 400
        
        file = request.files['transcript_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file extension
        if not file.filename.lower().endswith('.txt'):
            return jsonify({'error': 'Only .txt files are supported'}), 400
        
        # Validate file size (max 1MB)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > 1024 * 1024:  # 1MB
            return jsonify({'error': 'File size must be less than 1MB'}), 400
        
        # Read transcript content
        try:
            transcript_content = file.read().decode('utf-8').strip()
        except UnicodeDecodeError:
            return jsonify({'error': 'File must be valid UTF-8 text'}), 400
        
        if not transcript_content:
            return jsonify({'error': 'Transcript file is empty'}), 400
        
        # Get participant details from form
        participant_name = request.form.get('participant_name', '').strip()
        participant_email = request.form.get('participant_email', '').strip()
        participant_company = request.form.get('participant_company', '').strip()
        
        if not all([participant_name, participant_email, participant_company]):
            return jsonify({'error': 'Participant name, email, and company are required'}), 400
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, participant_email):
            return jsonify({'error': 'Invalid email address format'}), 400
        
        # Check for duplicate transcript (by hash)
        import hashlib
        transcript_hash = hashlib.sha256(transcript_content.encode()).hexdigest()
        
        from models import SurveyResponse
        existing_response = SurveyResponse.query.filter_by(
            campaign_id=campaign_id,
            transcript_hash=transcript_hash
        ).first()
        
        if existing_response:
            return jsonify({'error': 'This transcript has already been processed for this campaign'}), 409
        
        # Queue transcript for AI analysis processing
        from task_queue import task_queue
        task_queue.add_task('transcript_analysis', data_id=campaign_id, task_data={
            'campaign_id': campaign_id,
            'business_account_id': current_account.id,
            'transcript_content': transcript_content,
            'transcript_hash': transcript_hash,
            'transcript_filename': file.filename,
            'participant_name': participant_name,
            'participant_email': participant_email,
            'participant_company': participant_company,
            'uploaded_by_user_id': user.id
        })
        
        logger.info(f"Transcript analysis queued for campaign {campaign_id} by user {user.email}")
        
        return jsonify({
            'success': True,
            'message': 'Transcript uploaded successfully and queued for analysis',
            'campaign_id': campaign_id,
            'participant_name': participant_name
        })
        
    except Exception as e:
        logger.error(f"Error uploading transcript for campaign {campaign_id}: {e}")
        return jsonify({'error': 'Failed to upload transcript'}), 500


@business_auth_bp.route('/api/campaigns/<int:campaign_id>/transcripts', methods=['GET'])
@require_business_auth
def get_campaign_transcripts(campaign_id):
    """Get list of transcript-sourced responses for a campaign"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account context not found'}), 401
        
        # Verify campaign belongs to current business account
        from models import Campaign
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Get transcript responses for this campaign
        from models import SurveyResponse
        transcript_responses = SurveyResponse.query.filter_by(
            campaign_id=campaign_id,
            source_type='transcript'
        ).order_by(SurveyResponse.created_at.desc()).all()
        
        responses_data = []
        for response in transcript_responses:
            responses_data.append({
                'id': response.id,
                'participant_name': response.respondent_name,
                'participant_email': response.respondent_email,
                'participant_company': response.company_name,
                'transcript_filename': response.transcript_filename,
                'nps_score': response.nps_score,
                'nps_category': response.nps_category,
                'sentiment_label': response.sentiment_label,
                'created_at': response.created_at.isoformat() if response.created_at else None,
                'analyzed_at': response.analyzed_at.isoformat() if response.analyzed_at else None
            })
        
        return jsonify({
            'transcripts': responses_data,
            'count': len(responses_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting transcripts for campaign {campaign_id}: {e}")
        return jsonify({'error': 'Failed to get transcripts'}), 500


@business_auth_bp.route('/api/transcripts/<int:response_id>/download', methods=['GET'])
@require_business_auth
def download_transcript(response_id):
    """Download original transcript file"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account context not found'}), 401
        
        # Get transcript response and verify access
        from models import SurveyResponse, Campaign
        response = SurveyResponse.query.join(Campaign).filter(
            SurveyResponse.id == response_id,
            SurveyResponse.source_type == 'transcript',
            Campaign.business_account_id == current_account.id
        ).first()
        
        if not response:
            return jsonify({'error': 'Transcript not found'}), 404
        
        if not response.transcript_content:
            return jsonify({'error': 'Transcript content not available'}), 404
        
        # Create file-like response
        from flask import Response
        filename = response.transcript_filename or f"transcript_{response.id}.txt"
        
        return Response(
            response.transcript_content,
            mimetype='text/plain',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'text/plain; charset=utf-8'
            }
        )
        
    except Exception as e:
        logger.error(f"Error downloading transcript {response_id}: {e}")
        return jsonify({'error': 'Failed to download transcript'}), 500


@business_auth_bp.route('/analytics')
@require_business_auth
def business_analytics():
    """Analytics dashboard for business account users"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash(_('Business account context not found.'), 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get company NPS data - will be filtered by business account in API calls
        from data_storage import get_company_nps_data
        company_nps_data = get_company_nps_data()
        
        # Get current business user for branding context
        current_business_user = get_current_business_user()
        is_business_authenticated = current_business_user is not None
        business_user_name = f"{current_business_user.first_name} {current_business_user.last_name}" if current_business_user else None
        
        # Get branding context for the business account
        branding_context = get_branding_context(current_account.id)
        
        # Pass business account context for template
        return render_template('dashboard.html', 
                             company_nps_data=company_nps_data, 
                             user_email=None,  # Business users don't show email in public template
                             business_account=current_account,
                             is_business_authenticated=is_business_authenticated,
                             business_user_name=business_user_name,
                             branding_context=branding_context)
        
    except Exception as e:
        logger.error(f"Error loading business analytics for account {current_account.id if current_account else 'unknown'}: {e}")
        flash('Error loading analytics dashboard.', 'error')
        return redirect(url_for('business_auth.admin_panel'))

# ==== TRANSLATION REVIEW TOOL ROUTES ====

@business_auth_bp.route('/translation-review')
@require_platform_admin
def translation_review_tool():
    """Translation string review tool for platform administrators"""
    try:
        # Serve the review tool HTML
        return send_file('review_tool.html')
    except Exception as e:
        logger.error(f"Error loading translation review tool: {e}")
        flash('Error loading review tool.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@business_auth_bp.route('/translation-review/data')
@require_platform_admin
def translation_review_data():
    """Serve the review queue JSON data"""
    try:
        import os
        if os.path.exists('yellow_review_queue.json'):
            return send_file('yellow_review_queue.json', mimetype='application/json')
        else:
            return jsonify({'error': 'Review queue not found'}), 404
    except Exception as e:
        logger.error(f"Error loading review data: {e}")
        return jsonify({'error': str(e)}), 500


@business_auth_bp.route('/translation-review/save', methods=['POST'])
@require_platform_admin
def save_translation_decisions():
    """Save manual review decisions"""
    try:
        decisions = request.get_json()
        
        if not decisions:
            return jsonify({'error': 'No decisions provided'}), 400
        
        # Save to file
        import json
        with open('manual_review_decisions.json', 'w', encoding='utf-8') as f:
            json.dump(decisions, f, indent=2)
        
        logger.info(f"Saved {len(decisions)} translation review decisions")
        
        return jsonify({
            'success': True,
            'message': f'Saved {len(decisions)} decisions',
            'count': len(decisions)
        })
        
    except Exception as e:
        logger.error(f"Error saving translation decisions: {e}")
        return jsonify({'error': str(e)}), 500


@business_auth_bp.route('/translation-review/upload')
@require_platform_admin
def upload_decisions_form():
    """Upload form for review decisions"""
    try:
        return send_file('upload_decisions.html')
    except Exception as e:
        logger.error(f"Error loading upload form: {e}")
        return jsonify({'error': str(e)}), 500
