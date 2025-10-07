"""
Audit Utilities - Client-visible audit logging system for VOÏA
Provides decorator-based audit logging with client-friendly descriptions
"""

import json
import logging
from datetime import datetime
from functools import wraps
from flask import session, request, g
from models import AuditLog, BusinessAccountUser
from app import db
import task_queue

# Configure logging
logger = logging.getLogger(__name__)

# Action type mappings for client-friendly descriptions
ACTION_DESCRIPTIONS = {
    'user_login': 'User logged in',
    'user_logout': 'User logged out', 
    'campaign_created': 'Campaign created',
    'campaign_updated': 'Campaign updated',
    'campaign_status_changed': 'Campaign status changed',
    'campaign_deleted': 'Campaign deleted',
    'participant_created': 'Participant created',
    'participant_deleted': 'Participant deleted',
    'participant_token_regenerated': 'Participant access token regenerated',
    'participants_added': 'Participants added',
    'participants_uploaded': 'Participants uploaded via CSV',
    'participants_removed': 'Participants removed',
    'survey_invitations_sent': 'Survey invitations sent',
    'email_config_saved': 'Email settings updated',
    'email_config_tested': 'Email configuration tested',
    'account_settings_updated': 'Account settings updated',
    'user_added': 'New user added to account',
    'user_removed': 'User removed from account',
    'scheduler_run': 'Campaign scheduler executed',
    'executive_report_downloaded': 'Executive report downloaded'
}

def get_current_user_context():
    """Extract current user context from Flask session/request"""
    user_email = None
    user_name = None
    business_account_id = None
    ip_address = None
    
    try:
        # Get IP address
        if request:
            ip_address = request.environ.get('HTTP_X_FORWARDED_FOR')
            if not ip_address:
                ip_address = request.environ.get('REMOTE_ADDR')
        
        # Get user context from session
        if hasattr(g, 'current_user') and g.current_user:
            # Business user context
            user_email = g.current_user.email
            user_name = g.current_user.get_full_name()
            business_account_id = g.current_user.business_account_id
        elif session and 'business_user_id' in session:
            # Fallback: get from business session
            try:
                user = BusinessAccountUser.query.get(session['business_user_id'])
                if user:
                    user_email = user.email
                    user_name = user.get_full_name()
                    business_account_id = user.business_account_id
                # Also check session directly for business account
                if not business_account_id and 'business_account_id' in session:
                    business_account_id = session['business_account_id']
            except:
                pass
                
    except Exception as e:
        logger.warning(f"Error getting user context for audit: {e}")
    
    return {
        'user_email': user_email,
        'user_name': user_name,
        'business_account_id': business_account_id,
        'ip_address': ip_address
    }

def sanitize_audit_details(details):
    """Remove sensitive information from audit details"""
    if not details:
        return details
    
    # List of sensitive keys to remove or mask
    sensitive_keys = [
        'password', 'smtp_password', 'token', 'secret', 'key', 
        'api_key', 'auth_token', 'session_id', 'csrf_token'
    ]
    
    if isinstance(details, dict):
        sanitized = {}
        for key, value in details.items():
            key_lower = key.lower()
            
            # Remove sensitive keys completely
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                continue
            
            # Recursively sanitize nested dictionaries
            if isinstance(value, dict):
                sanitized[key] = sanitize_audit_details(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    return details

def create_audit_description(action_type, resource_name=None, details=None):
    """Create client-friendly audit description"""
    base_description = ACTION_DESCRIPTIONS.get(action_type, action_type.replace('_', ' ').title())
    
    if resource_name:
        if action_type == 'campaign_created':
            return f"Campaign '{resource_name}' created"
        elif action_type == 'campaign_status_changed':
            old_status = details.get('old_status', 'unknown') if details else 'unknown'
            new_status = details.get('new_status', 'unknown') if details else 'unknown'
            return f"Campaign '{resource_name}' status changed from {old_status} to {new_status}"
        elif action_type == 'participants_added':
            count = details.get('count', 1) if details else 1
            return f"{count} participant{'s' if count != 1 else ''} added to campaign '{resource_name}'"
        elif action_type == 'participants_uploaded':
            count = details.get('count', 0) if details else 0
            return f"{count} participants uploaded via CSV to campaign '{resource_name}'"
        elif action_type == 'survey_invitations_sent':
            count = details.get('count', 0) if details else 0
            return f"Survey invitations sent to {count} participant{'s' if count != 1 else ''}"
        elif action_type == 'executive_report_downloaded':
            return f"Executive report downloaded for campaign '{resource_name}'"
        else:
            return f"{base_description} - {resource_name}"
    
    return base_description

async def write_audit_log_async(audit_data):
    """Write audit log entry asynchronously via task queue"""
    try:
        # Get the global task queue instance
        from main import app
        
        with app.app_context():
            # Create audit log entry
            audit = AuditLog.create_audit_entry(**audit_data)
            db.session.add(audit)
            db.session.commit()
            
            logger.debug(f"Audit log created: {audit.action_description}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")
        return False

def queue_audit_log(business_account_id, action_type, resource_name=None, 
                   resource_type=None, resource_id=None, details=None,
                   user_email=None, user_name=None, ip_address=None):
    """Queue audit log entry for async processing"""
    try:
        # Auto-detect user context if not provided
        if not user_email or not business_account_id:
            context = get_current_user_context()
            user_email = user_email or context['user_email']
            user_name = user_name or context['user_name'] 
            business_account_id = business_account_id or context['business_account_id']
            ip_address = ip_address or context['ip_address']
        
        # Skip audit if we can't identify the business account
        if not business_account_id:
            logger.warning(f"Skipping audit log - no business account context for action: {action_type}")
            return
        
        # Sanitize details
        sanitized_details = sanitize_audit_details(details)
        
        # Create description
        description = create_audit_description(action_type, resource_name, sanitized_details)
        
        # Prepare audit data
        audit_data = {
            'business_account_id': business_account_id,
            'user_email': user_email,
            'user_name': user_name,
            'action_type': action_type,
            'action_description': description,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'resource_name': resource_name,
            'details': sanitized_details,
            'ip_address': ip_address
        }
        
        # Add to task queue for async processing
        task_queue_instance = getattr(g, 'task_queue', None)
        if task_queue_instance:
            task_queue_instance.add_task(
                task_type='audit_log',
                task_data=audit_data,
                priority=3  # Lower priority than critical business operations
            )
        else:
            # Fallback: Write directly (synchronous)
            logger.warning("Task queue not available, writing audit log synchronously")
            write_audit_log_sync(audit_data)
            
    except Exception as e:
        logger.error(f"Failed to queue audit log: {e}")
        # Don't let audit failures break main functionality

def write_audit_log_sync(audit_data):
    """Write audit log entry synchronously (fallback)"""
    try:
        audit = AuditLog.create_audit_entry(**audit_data)
        db.session.add(audit)
        db.session.commit()
        logger.debug(f"Audit log created synchronously: {audit.action_description}")
        return True
    except Exception as e:
        logger.error(f"Failed to write audit log synchronously: {e}")
        return False

def audit_action(action_type, resource_type=None, get_resource_name=None, capture_details=None):
    """
    Decorator for client-visible audit logging
    
    Args:
        action_type (str): Type of action being performed (e.g., 'campaign_created')
        resource_type (str): Type of resource being acted upon (e.g., 'campaign')
        get_resource_name (callable): Function to extract resource name from function args/result
        capture_details (callable): Function to extract additional details from function args/result
    
    Usage:
        @audit_action('campaign_created', resource_type='campaign')
        def create_campaign(name, description):
            # ... campaign creation logic
            return campaign
            
        @audit_action('participants_uploaded', 
                     resource_type='campaign',
                     get_resource_name=lambda args, result: result.get('campaign_name'),
                     capture_details=lambda args, result: {'count': result.get('count', 0)})
        def upload_participants(campaign_id, csv_file):
            # ... upload logic
            return {'campaign_name': 'Q1 Survey', 'count': 100}
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Execute the original function first
            try:
                result = func(*args, **kwargs)
                success = True
                error_message = None
            except Exception as e:
                result = None
                success = False
                error_message = str(e)
                # Re-raise the exception after audit logging
                
            try:
                # Extract resource information
                resource_name = None
                if get_resource_name:
                    try:
                        resource_name = get_resource_name(args, result)
                    except:
                        pass
                
                # Extract additional details
                details = {}
                if capture_details:
                    try:
                        details = capture_details(args, result) or {}
                    except:
                        pass
                
                # Add success/failure information
                details['success'] = success
                if error_message:
                    details['error'] = error_message
                
                # Extract resource ID if possible
                resource_id = None
                if result and isinstance(result, dict):
                    resource_id = result.get('id') or result.get('campaign_id') or result.get('participant_id')
                elif hasattr(result, 'id'):
                    resource_id = result.id
                
                # Queue audit log
                queue_audit_log(
                    business_account_id=None,  # Will be auto-detected
                    action_type=action_type,
                    resource_name=resource_name,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details=details
                )
                
            except Exception as audit_error:
                logger.error(f"Audit logging failed for {func.__name__}: {audit_error}")
                # Continue execution even if audit fails
            
            # Re-raise original exception if function failed
            if not success:
                raise Exception(error_message)
                
            return result
        return wrapper
    return decorator

# Convenience functions for common audit scenarios
def audit_user_login(user_email, user_name, business_account_id, ip_address=None):
    """Audit user login event"""
    queue_audit_log(
        business_account_id=business_account_id,
        action_type='user_login',
        user_email=user_email,
        user_name=user_name,
        ip_address=ip_address,
        details={'login_time': datetime.utcnow().isoformat()}
    )

def audit_user_logout(user_email, user_name, business_account_id, ip_address=None):
    """Audit user logout event"""
    queue_audit_log(
        business_account_id=business_account_id,
        action_type='user_logout',
        user_email=user_email,
        user_name=user_name,
        ip_address=ip_address,
        details={'logout_time': datetime.utcnow().isoformat()}
    )

def audit_campaign_status_change(campaign_id, campaign_name, old_status, new_status, business_account_id=None):
    """Audit campaign status change"""
    queue_audit_log(
        business_account_id=business_account_id,
        action_type='campaign_status_changed',
        resource_type='campaign',
        resource_id=campaign_id,
        resource_name=campaign_name,
        details={'old_status': old_status, 'new_status': new_status}
    )

def audit_email_config_change(business_account_id, config_fields_changed):
    """Audit email configuration changes"""
    queue_audit_log(
        business_account_id=business_account_id,
        action_type='email_config_saved',
        resource_type='email_config',
        details={'fields_changed': config_fields_changed}
    )