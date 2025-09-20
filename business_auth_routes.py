"""
Phase 2: Business Account Authentication Routes
Provides login/logout routes for business account users without affecting public survey access
"""

from flask import Blueprint, request, render_template, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from models import BusinessAccountUser, UserSession, BusinessAccount, EmailConfiguration, LicenseHistory, db
from rate_limiter import rate_limit
from license_service import LicenseService
import logging
from datetime import datetime, timedelta, date
import json
import re

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
            if not current_account:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('business_auth.login'))
            
            # Check account status - mirror require_business_auth logic
            if current_account.status in ['suspended', 'inactive', 'closed']:
                flash('Account access blocked. Please contact support.', 'error')
                return redirect(url_for('business_auth.login'))
            
            # Allow active and trial accounts to proceed
            if current_account.status == 'trial':
                flash('Your account is in trial mode.', 'info')
            
            # Get current user
            business_user_id = session.get('business_user_id')
            current_user = BusinessAccountUser.query.get(business_user_id)
            
            if not current_user or not current_user.has_permission(permission):
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
        
        # Get license information using LicenseService
        from license_service import LicenseService
        license_info = LicenseService.get_license_info(current_account_id)
        
        # Get all users for this business account
        users = BusinessAccountUser.get_by_business_account(current_account_id)
        users_count = len(users)
        
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
        
        # Validate role
        allowed_roles = ['business_account_admin', 'admin', 'manager', 'viewer']
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
        
        # Send invitation email using platform-level email service
        from email_service import EmailService
        email_service = EmailService()
        
        email_result = email_service.send_business_account_invitation(
            user_email=admin_email,
            user_first_name=admin_first_name,
            user_last_name=admin_last_name,
            business_account_name=business_name,
            invitation_token=invitation_token
        )
        
        if email_result.get('success'):
            logger.info(f"Business account '{business_name}' created successfully with admin user {admin_email}")
            flash(f'Business account "{business_name}" created successfully! Invitation email sent to {admin_email}.', 'success')
            
            # Audit log the creation
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
        session['user_role'] = user.role
        session.permanent = remember_me
        
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
        
        # Get license information for this business account
        from license_service import LicenseService
        license_info = LicenseService.get_license_info(business_account.id)
        
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
                'email_configured': email_service.is_configured(),
                'license_info': license_info
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
                },
                'license_info': license_info
            }
        
        return render_template('business_auth/admin_panel.html',
                             business_account=business_account,
                             current_user=current_business_user,
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
        # Set active status - use setattr to avoid UserMixin property conflict
        setattr(admin_user, 'is_active', True)
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
        
        # For HTML requests, show dedicated scheduler status page
        return render_template('business_auth/scheduler_status.html',
                             scheduler_stats=scheduler_stats,
                             campaign_counts=campaign_counts,
                             business_account=current_account)
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        if request.is_json:
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
            flash('Business account context not found.', 'error')
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
            flash('Business account context not found.', 'error')
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
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        # Get form data
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
        email_config.smtp_server = smtp_server
        email_config.smtp_port = smtp_port
        email_config.smtp_username = smtp_username
        email_config.use_tls = use_tls
        email_config.use_ssl = use_ssl
        email_config.sender_name = sender_name
        email_config.sender_email = sender_email
        email_config.reply_to_email = reply_to_email if reply_to_email else None
        email_config.set_admin_emails(admin_email_list)
        
        # Update password only if provided
        if smtp_password:
            email_config.set_smtp_password(smtp_password)
        
        # Validate configuration
        validation_errors = email_config.validate_configuration()
        if validation_errors:
            for error in validation_errors:
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


# ==== BRANDING CONFIGURATION ROUTES ====

@business_auth_bp.route('/admin/brand-config')
@require_business_auth
def brand_config():
    """Branding configuration management page"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            logger.error("No current account found in brand config route")
            flash('Business account context not found.', 'error')
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
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        # Get form data
        company_display_name = request.form.get('company_display_name', '').strip()
        
        # Get or create branding configuration
        from models import BrandingConfig
        branding_config = BrandingConfig.get_or_create_for_business_account(current_account.id)
        
        # Update configuration
        branding_config.company_display_name = company_display_name if company_display_name else None
        
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
                    'logo_updated': 'logo_file' in request.files and request.files['logo_file'].filename != ''
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
    from datetime import date, timedelta
    
    try:
        # Get current business account
        business_account = get_current_business_account()
        if not business_account:
            flash('Business account not found.', 'error')
            return redirect(url_for('business_auth.login'))
        
        # Get license period information
        license_start, license_end = business_account.get_license_period()
        
        # Calculate usage statistics
        campaigns_used = 0
        campaigns_limit = 4
        if license_start and license_end:
            # Count campaigns in current license period
            from models import Campaign
            campaigns_used = Campaign.query.filter(
                Campaign.business_account_id == business_account.id,
                Campaign.start_date >= license_start,
                Campaign.start_date <= license_end
            ).count()
        
        # Calculate days until expiration and days since activation
        days_until_expiry = None
        days_since_activation = 0
        expires_soon = False
        license_status_display = business_account.license_status.title()
        
        # Calculate days since activation if license_start is available
        if license_start:
            today = date.today()
            days_since_activation = (today - license_start).days
        
        if license_end:
            today = date.today()
            if license_end > today:
                days_until_expiry = (license_end - today).days
                expires_soon = days_until_expiry <= 30
                if expires_soon and business_account.license_status == 'active':
                    license_status_display = f"Active (Expires in {days_until_expiry} days)"
            elif license_end < today:
                license_status_display = "Expired"
                days_until_expiry = 0
        
        # Get user usage statistics with defensive programming
        users_used = getattr(business_account, 'current_users_count', 0)
        users_limit = 5
        
        # Get active campaign participant count if applicable
        active_participants = 0
        active_campaign = None
        try:
            from models import Campaign, CampaignParticipant
            active_campaign = Campaign.query.filter(
                Campaign.business_account_id == business_account.id,
                Campaign.status == 'active'
            ).first()
            
            if active_campaign:
                active_participants = CampaignParticipant.query.filter_by(
                    campaign_id=active_campaign.id
                ).count()
        except Exception as e:
            logger.warning(f"Could not fetch active campaign participants: {e}")
        
        # Prepare template context with defensive programming for optional methods
        license_data = {
            'business_account': business_account,
            'license_start': license_start,
            'license_end': license_end,
            'license_status': license_status_display,
            'expires_soon': expires_soon,
            'days_until_expiry': days_until_expiry,
            'days_since_activation': days_since_activation,
            'campaigns_used': campaigns_used,
            'campaigns_limit': campaigns_limit,
            'campaigns_remaining': max(0, campaigns_limit - campaigns_used),
            'users_used': users_used,
            'users_limit': users_limit,
            'users_remaining': max(0, users_limit - users_used),
            'active_campaign': active_campaign,
            'active_participants': active_participants,
            'can_activate_campaign': getattr(business_account, 'can_activate_campaign', lambda: True)() if hasattr(business_account, 'can_activate_campaign') else True,
            'can_add_user': LicenseService.can_add_user(business_account.id)
        }
        
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
            flash('Business account context not found.', 'error')
            return redirect(url_for('business_auth.admin_panel'))
        
        # Allow demo accounts to access survey customization for testing
        
        # Define available options for dropdowns
        industry_options = [
            'Healthcare', 'SaaS', 'Retail', 'Professional Services', 
            'Restaurant', 'Manufacturing', 'Education', 'Finance', 'Other'
        ]
        
        tone_options = [
            'professional', 'warm', 'casual', 'formal'
        ]
        
        topic_options = [
            'NPS', 'Satisfaction', 'Product Quality', 'Service Rating', 
            'Support Experience', 'Pricing Value', 'Improvement Suggestions'
        ]
        
        return render_template('business_auth/survey_config.html',
                             business_account=current_account,
                             industry_options=industry_options,
                             tone_options=tone_options,
                             topic_options=topic_options)
    
    except Exception as e:
        logger.error(f"Error loading survey configuration: {e}")
        flash('Failed to load survey configuration.', 'error')
        return redirect(url_for('business_auth.admin_panel'))


@business_auth_bp.route('/admin/survey-config/save', methods=['POST'])
@require_business_auth
def save_survey_config():
    """Save survey customization configuration"""
    try:
        current_account = get_current_business_account()
        if not current_account:
            flash('Business account context not found.', 'error')
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
        survey_goals = request.form.getlist('survey_goals')
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
        current_account.survey_goals = survey_goals if survey_goals else None
        current_account.prioritized_topics = prioritized_topics if prioritized_topics else None
        current_account.optional_topics = optional_topics if optional_topics else None
        
        # Update timestamp
        current_account.updated_at = datetime.utcnow()
        
        # Save to database
        db.session.commit()
        
        logger.info(f"Survey configuration updated for business account: {current_account.name}")
        flash('Survey configuration saved successfully! Your changes will be reflected in new survey sessions.', 'success')
        return redirect(url_for('business_auth.survey_config'))
        
    except Exception as e:
        logger.error(f"Error saving survey configuration: {e}")
        db.session.rollback()
        flash('Failed to save survey configuration. Please try again.', 'error')
        return redirect(url_for('business_auth.survey_config'))


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
                'days_remaining': license_info.get('days_remaining', 0)
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
        
        # Defensive data sanitization
        template_data = {
            'business_account': business_account,
            'current_license': current_license,
            'license_info': license_info,
            'available_types': available_types,
            'campaigns_used': max(0, campaigns_used),  # Ensure non-negative
            'users_count': max(0, users_count)  # Ensure non-negative
        }
        
        # Log platform admin access for audit
        current_user = BusinessAccountUser.query.get(session.get('business_user_id'))
        logger.info(f"Platform admin {current_user.email if current_user else 'unknown'} accessed license assignment form for business_id {business_id} ({business_account.name})")
        
        return render_template('business_auth/license_assignment_form.html', **template_data)
        
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
                        flash('Maximum participants per campaign must be between 1 and 1,000,000.', 'error')
                        return redirect(url_for('business_auth.license_assignment_form', business_id=business_id))
                    custom_config['max_participants_per_campaign'] = participants_value
                    
            except ValueError:
                flash('Custom limit values must be valid positive numbers.', 'error')
                return redirect(url_for('business_auth.license_assignment_form', business_id=business_id))
        
        # Additional security: Re-validate the business account hasn't changed
        fresh_business_account = BusinessAccount.query.get(business_id)
        if not fresh_business_account or fresh_business_account.name != business_account.name:
            logger.error(f"Business account validation failed during license assignment for business_id {business_id}")
            flash('Business account validation failed. Please try again.', 'error')
            return redirect(url_for('business_auth.admin_licenses'))
        
        # Log the assignment attempt for audit
        logger.info(f"Platform admin {current_user.email} attempting to assign {license_type} license to business_id {business_id} ({business_account.name})")
        
        # Call LicenseService to assign license
        success, license_record, message = LicenseService.assign_license_to_business(
            business_id=business_id,
            license_type=license_type,
            custom_config=custom_config,
            created_by=created_by
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
        
        return render_template('business_auth/license_history.html', **template_data)
        
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
        
        # Get overall statistics with error handling
        try:
            total_accounts = BusinessAccount.query.count()
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
        
        # Process all business accounts with comprehensive error handling
        try:
            business_accounts = BusinessAccount.query.all()
        except Exception as query_error:
            logger.error(f"Error querying business accounts: {query_error}")
            business_accounts = []
        
        for account in business_accounts:
            try:
                # Validate account data
                if not account or not hasattr(account, 'id'):
                    logger.warning(f"Invalid account object encountered during dashboard processing")
                    accounts_with_errors += 1
                    continue
                
                accounts_processed += 1
                
                # Get license info with error handling
                try:
                    license_info = LicenseService.get_license_info(account.id)
                    license_type = license_info.get('license_type', 'trial')
                    license_status = license_info.get('license_status', 'trial')
                    
                    # Validate license type and status values
                    valid_license_types = ['core', 'plus', 'pro', 'trial']
                    valid_license_statuses = ['active', 'expired', 'trial', 'suspended']
                    
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
                
                # Add to usage statistics with validation
                try:
                    campaigns_used = LicenseService.get_campaigns_used_in_current_period(account.id)
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
            'trial_accounts': license_distribution.get('trial', 0),
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
        
        return render_template('business_auth/licenses/dashboard.html', **dashboard_data)
        
    except Exception as e:
        logger.error(f"Error loading license dashboard: {e}")
        flash('Failed to load license dashboard. Please try again.', 'error')
        return redirect(url_for('business_auth.admin_panel'))