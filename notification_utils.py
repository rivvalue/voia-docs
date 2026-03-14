"""
Notification Utilities
Provides persistent notification system for important events and background job completions
"""

from models import Notification, db
from flask import session
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


def notify(message, category='info', business_account_id=None, user_id=None, **metadata):
    """
    Create a persistent notification for the user
    
    Args:
        message: Notification message (max 500 chars)
        category: Type of notification ('success', 'error', 'warning', 'info')
        business_account_id: Business account ID (auto-detected from session if not provided)
        user_id: User ID (auto-detected from session if not provided)
        **metadata: Additional context (campaign_id, job_id, etc.) stored as JSON
    
    Returns:
        Notification object if created successfully, None otherwise
    
    Examples:
        notify('Campaign activated successfully', 'success', campaign_id=42)
        notify('Bulk upload: 1,157 participants added', 'success', job_id=123)
        notify('License limit warning', 'warning', usage_percent=95)
    """
    try:
        # Auto-detect business_account_id from session if not provided (only in request context)
        if not business_account_id:
            try:
                from flask import has_request_context
                if has_request_context():
                    business_account_id = session.get('business_account_id')
            except:
                pass
            
            if not business_account_id:
                logger.warning("Cannot create notification: business_account_id not found")
                return None
        
        # Auto-detect user_id from session if not provided (only in request context)
        if not user_id:
            try:
                from flask import has_request_context
                if has_request_context():
                    user_id = session.get('business_user_id')
            except:
                pass
        
        # Validate category
        valid_categories = ['success', 'error', 'warning', 'info']
        if category not in valid_categories:
            logger.warning(f"Invalid notification category '{category}', defaulting to 'info'")
            category = 'info'
        
        # Create notification
        notification = Notification(
            business_account_id=business_account_id,
            user_id=user_id,
            message=message[:500],  # Enforce length limit
            category=category,
            meta_data=json.dumps(metadata) if metadata else None,
            unread=True,
            created_at=datetime.utcnow()
        )
        
        db.session.add(notification)
        db.session.commit()
        
        logger.info(f"Created notification for business_account_id {business_account_id}: {message}")
        return notification
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create notification: {e}")
        return None


def get_unread_count(business_account_id, user_id=None):
    """
    Get count of unread notifications for a business account or user
    
    Args:
        business_account_id: Business account ID
        user_id: Optional user ID for user-specific notifications
    
    Returns:
        int: Count of unread notifications
    """
    try:
        query = Notification.query.filter_by(
            business_account_id=business_account_id,
            unread=True
        )
        
        if user_id:
            query = query.filter(
                (Notification.user_id == user_id) | (Notification.user_id.is_(None))
            )
        
        return query.count()
        
    except Exception as e:
        logger.error(f"Failed to get unread count: {e}")
        return 0


def mark_as_read(notification_id, business_account_id):
    """
    Mark a notification as read
    
    Args:
        notification_id: Notification ID (integer)
        business_account_id: Business account ID (for security validation)
    
    Returns:
        bool: True if marked successfully, False otherwise
    """
    try:
        notification = Notification.query.filter_by(
            id=notification_id,
            business_account_id=business_account_id
        ).first()
        
        if not notification:
            logger.warning(f"Notification {notification_id} not found")
            return False
        
        notification.unread = False
        notification.read_at = datetime.utcnow()
        db.session.commit()
        
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to mark notification as read: {e}")
        return False


def mark_notification_as_read_by_uuid(notification_uuid, business_account_id):
    """
    Mark a notification as read using its UUID.
    
    Args:
        notification_uuid: Notification UUID string
        business_account_id: Business account ID (integer, for security validation)
    
    Returns:
        bool: True if marked successfully, False otherwise
    """
    try:
        notification = Notification.query.filter_by(
            uuid=notification_uuid,
            business_account_id=business_account_id
        ).first()
        
        if not notification:
            logger.warning(f"Notification with uuid {notification_uuid} not found")
            return False
        
        notification.unread = False
        notification.read_at = datetime.utcnow()
        db.session.commit()
        
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to mark notification as read by uuid: {e}")
        return False


def mark_all_as_read(business_account_id, user_id=None):
    """
    Mark all notifications as read for a business account or user
    
    Args:
        business_account_id: Business account ID
        user_id: Optional user ID for user-specific notifications
    
    Returns:
        int: Number of notifications marked as read
    """
    try:
        query = Notification.query.filter_by(
            business_account_id=business_account_id,
            unread=True
        )
        
        if user_id:
            query = query.filter(
                (Notification.user_id == user_id) | (Notification.user_id.is_(None))
            )
        
        count = query.update({
            'unread': False,
            'read_at': datetime.utcnow()
        })
        
        db.session.commit()
        return count
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to mark all notifications as read: {e}")
        return 0


def cleanup_old_notifications(days=90):
    """
    Delete notifications older than specified days
    Should be run as a periodic cleanup job
    
    Args:
        days: Number of days to retain notifications
    
    Returns:
        int: Number of notifications deleted
    """
    try:
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted = Notification.query.filter(
            Notification.created_at < cutoff_date
        ).delete()
        
        db.session.commit()
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old notifications (older than {days} days)")
        
        return deleted
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to cleanup old notifications: {e}")
        return 0
