"""
Email Service Module
Handles all email delivery for the Voice of Client (VOÏA) system
"""

import smtplib
import ssl
import os
import logging
import json
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional, Union
from flask import current_app, url_for, render_template_string
import jwt
from app import db
from models import EmailDelivery

logger = logging.getLogger(__name__)

class EmailService:
    """Centralized email service for VOÏA system"""
    
    def __init__(self):
        self.smtp_server = None
        self.smtp_port = None  
        self.smtp_username = None
        self.smtp_password = None
        self.admin_emails = []
        self._load_config()
    
    def _load_config(self):
        """Load SMTP configuration from environment variables"""
        try:
            self.smtp_server = os.environ.get('SMTP_SERVER')
            self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
            self.smtp_username = os.environ.get('SMTP_USERNAME')  
            self.smtp_password = os.environ.get('SMTP_PASSWORD')
            
            # Parse admin emails
            admin_emails_str = os.environ.get('ADMIN_EMAILS', '')
            if admin_emails_str:
                self.admin_emails = [email.strip() for email in admin_emails_str.split(',')]
            
            logger.info(f"Email service configured: Server={self.smtp_server}, Port={self.smtp_port}")
            if self.admin_emails:
                logger.info(f"Admin emails configured: {len(self.admin_emails)} recipients")
                
        except Exception as e:
            logger.error(f"Failed to load email configuration: {e}")
            self.smtp_server = None
    
    def is_configured(self) -> bool:
        """Check if email service is properly configured"""
        return all([
            self.smtp_server,
            self.smtp_port,
            self.smtp_username,
            self.smtp_password
        ])
    
    def send_email(self, 
                   to_emails: Union[str, List[str]], 
                   subject: str,
                   text_body: str,
                   html_body: Optional[str] = None,
                   from_email: Optional[str] = None,
                   email_delivery_id: Optional[int] = None) -> Dict:
        """
        Send email with text and optional HTML content
        
        Args:
            to_emails: Recipient email(s)
            subject: Email subject
            text_body: Plain text body
            html_body: Optional HTML body
            from_email: Optional sender email (defaults to SMTP_USERNAME)
            email_delivery_id: Optional EmailDelivery record ID for tracking
            
        Returns:
            Dict with success status and details
        """
        recipients: List[str] = []
        email_delivery = None
        
        # Get EmailDelivery record if provided
        if email_delivery_id:
            try:
                email_delivery = EmailDelivery.query.get(email_delivery_id)
            except Exception as e:
                logger.error(f"Failed to retrieve EmailDelivery {email_delivery_id}: {e}")
        
        if not self.is_configured():
            error_msg = 'Email service not configured - missing SMTP settings'
            if email_delivery:
                email_delivery.mark_failed(error_msg, is_permanent=True)
                db.session.commit()
            return {
                'success': False,
                'error': error_msg
            }
        
        # Additional safety checks for type assertions
        if not all([self.smtp_server, self.smtp_port, self.smtp_username, self.smtp_password]):
            error_msg = 'Email service configuration incomplete'
            if email_delivery:
                email_delivery.mark_failed(error_msg, is_permanent=True)
                db.session.commit()
            return {
                'success': False,
                'error': error_msg
            }
        
        try:
            # Normalize recipient list
            if isinstance(to_emails, str):
                recipients = [to_emails]
            else:
                recipients = list(to_emails)
            
            # Mark as sending if we have a delivery record
            if email_delivery:
                email_delivery.mark_sending()
                db.session.commit()
            
            # Set sender email
            sender = from_email or self.smtp_username
            
            # Create message
            if html_body:
                # Multipart message with both text and HTML
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = sender
                msg['To'] = ', '.join(recipients)
                
                # Add text part
                text_part = MIMEText(text_body, 'plain')
                msg.attach(text_part)
                
                # Add HTML part
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
                
            else:
                # Simple text message
                msg = EmailMessage()
                msg['Subject'] = subject
                msg['From'] = sender
                msg['To'] = ', '.join(recipients)
                msg.set_content(text_body)
            
            # Send email with type-safe values
            context = ssl.create_default_context()
            smtp_port = self.smtp_port or 587  # Default port fallback
            
            with smtplib.SMTP(str(self.smtp_server), smtp_port) as server:
                server.starttls(context=context)
                server.login(str(self.smtp_username), str(self.smtp_password))
                
                server.send_message(msg)
                
                # Mark as successfully sent if we have a delivery record
                if email_delivery:
                    email_delivery.mark_sent()
                    db.session.commit()
                
                logger.info(f"Email sent successfully to {len(recipients)} recipients: {subject}")
                
                return {
                    'success': True,
                    'recipients': recipients,
                    'subject': subject,
                    'sent_at': datetime.utcnow().isoformat(),
                    'email_delivery_id': email_delivery_id
                }
                
        except Exception as e:
            error_msg = f"Failed to send email '{subject}': {str(e)}"
            logger.error(error_msg)
            
            # Mark as failed if we have a delivery record
            if email_delivery:
                # Check if this is a permanent failure
                is_permanent = self._is_permanent_email_error(str(e))
                email_delivery.mark_failed(error_msg, is_permanent=is_permanent)
                db.session.commit()
            
            return {
                'success': False,
                'error': error_msg,
                'recipients': recipients,
                'subject': subject,
                'email_delivery_id': email_delivery_id
            }
    
    def _is_permanent_email_error(self, error_message: str) -> bool:
        """
        Determine if an email error is permanent (should not retry) or temporary
        
        Args:
            error_message: The error message from SMTP
            
        Returns:
            True if the error is permanent, False if it should be retried
        """
        error_lower = error_message.lower()
        
        # Permanent failures (5xx SMTP codes and specific conditions)
        permanent_indicators = [
            # User/mailbox doesn't exist
            '550', '551', '553',  # SMTP codes for permanent failure
            'user unknown', 'mailbox unavailable', 'no such user',
            'recipient address rejected', 'user does not exist',
            'invalid recipient', 'undeliverable',
            
            # Domain/DNS issues that are likely permanent
            'domain not found', 'no mail server',
            
            # Authentication issues (configuration problems)
            'authentication failed', 'invalid login',
            'smtp username/password not accepted',
            
            # Content/policy rejections
            'spam', 'blocked', 'blacklisted', 'prohibited content',
            'message rejected', 'policy violation'
        ]
        
        # Check if any permanent indicators are present
        for indicator in permanent_indicators:
            if indicator in error_lower:
                return True
        
        # Temporary failures (4xx codes and connection issues)
        temporary_indicators = [
            '421', '422', '431', '432', '433', '441', '442', '451', '452',  # SMTP 4xx codes
            'temporary failure', 'try again', 'mailbox full',
            'rate limit', 'connection timeout', 'network error',
            'server temporarily unavailable', 'service unavailable'
        ]
        
        # If it's explicitly temporary, return False
        for indicator in temporary_indicators:
            if indicator in error_lower:
                return False
        
        # Default to temporary (retryable) for unknown errors
        return False

    def send_participant_invitation(self, 
                                    participant_email: str,
                                    participant_name: str,
                                    campaign_name: str,
                                    survey_token: str,
                                    business_account_name: str,
                                    email_delivery_id: Optional[int] = None) -> Dict:
        """
        Send survey invitation to a participant
        
        Args:
            participant_email: Participant's email
            participant_name: Participant's name
            campaign_name: Campaign name
            survey_token: JWT token for survey access
            business_account_name: Business account name
            email_delivery_id: Optional EmailDelivery record ID for tracking
            
        Returns:
            Dict with success status and details
        """
        
        try:
            # Generate survey URL (using the correct 'survey' route)
            survey_url = url_for('survey', token=survey_token, _external=True)
            
            # Email subject
            subject = f"Your feedback is requested: {campaign_name}"
            
            # Text body
            text_body = f"""
Hello {participant_name},

{business_account_name} is requesting your valuable feedback through our Voice of Client (VOÏA) system.

Campaign: {campaign_name}

Please click the link below to complete your survey:
{survey_url}

This personalized link is secure and will expire in 72 hours.

Your feedback helps improve services and experiences. The survey should take just a few minutes to complete.

Thank you for your time and valuable insights!

Best regards,
The VOÏA Team
AI Powered Client Insights

---
This is an automated message. If you have any questions, please contact the organization that sent this survey.
"""
            
            # HTML body
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Survey Invitation - {campaign_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .container {{
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #E13A44;
        }}
        .logo {{
            font-size: 24px;
            font-weight: bold;
            color: #E13A44;
            margin-bottom: 5px;
        }}
        .tagline {{
            font-size: 14px;
            color: #666;
            font-style: italic;
        }}
        .campaign-name {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #E13A44;
            margin: 20px 0;
            font-weight: 500;
        }}
        .cta-button {{
            display: inline-block;
            background-color: #E13A44;
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
            font-weight: 500;
            text-align: center;
        }}
        .cta-button:hover {{
            background-color: #c12e3a;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            font-size: 12px;
            color: #666;
            text-align: center;
        }}
        .security-note {{
            background-color: #e7f3ff;
            padding: 10px;
            border-radius: 5px;
            font-size: 14px;
            margin: 15px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">VOÏA - Voice Of Client</div>
            <div class="tagline">AI Powered Client Insights</div>
        </div>
        
        <h2>Hello {participant_name},</h2>
        
        <p><strong>{business_account_name}</strong> is requesting your valuable feedback through our Voice of Client (VOÏA) system.</p>
        
        <div class="campaign-name">
            <strong>Campaign:</strong> {campaign_name}
        </div>
        
        <p>Your feedback helps improve services and experiences. The survey should take just a few minutes to complete.</p>
        
        <div style="text-align: center;">
            <a href="{survey_url}" class="cta-button">Complete Your Survey</a>
        </div>
        
        <div class="security-note">
            <strong>🔒 Security Note:</strong> This personalized link is secure and will expire in 72 hours.
        </div>
        
        <p>Thank you for your time and valuable insights!</p>
        
        <p>Best regards,<br>
        The VOÏA Team</p>
        
        <div class="footer">
            This is an automated message. If you have any questions, please contact the organization that sent this survey.
        </div>
    </div>
</body>
</html>
"""
            
            # Send the email
            result = self.send_email(
                to_emails=participant_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                email_delivery_id=email_delivery_id
            )
            
            # Add invitation-specific metadata
            if result['success']:
                result.update({
                    'email_type': 'participant_invitation',
                    'campaign_name': campaign_name,
                    'participant_name': participant_name,
                    'survey_token': survey_token[:20] + '...'  # Truncated for logging
                })
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to send participant invitation to {participant_email}: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'email_type': 'participant_invitation',
                'participant_email': participant_email
            }

    def send_campaign_notification(self,
                                   notification_type: str,
                                   campaign_name: str,
                                   campaign_id: int,
                                   business_account_name: str,
                                   additional_data: Optional[Dict] = None,
                                   email_delivery_id: Optional[int] = None) -> Dict:
        """
        Send campaign lifecycle notifications to admin emails
        
        Args:
            notification_type: Type of notification ('started', 'completed', 'error')
            campaign_name: Campaign name
            campaign_id: Campaign ID
            business_account_name: Business account name
            additional_data: Optional additional data for notification
            email_delivery_id: Optional EmailDelivery record ID for tracking
            
        Returns:
            Dict with success status and details
        """
        
        if not self.admin_emails:
            return {
                'success': False,
                'error': 'No admin emails configured'
            }
        
        try:
            # Prepare notification content based on type
            if notification_type == 'started':
                subject = f"Campaign Started: {campaign_name}"
                text_body = f"""
Campaign Activation Notification

Campaign: {campaign_name}
Campaign ID: {campaign_id}
Business Account: {business_account_name}
Status: ACTIVE
Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

The campaign has been automatically activated and is now collecting responses.

Dashboard: {url_for('business_auth.admin_panel', _external=True)}

---
VOÏA Campaign Management System
"""
                
            elif notification_type == 'completed':
                subject = f"Campaign Completed: {campaign_name}"
                responses_count = additional_data.get('responses_count', 0) if additional_data else 0
                text_body = f"""
Campaign Completion Notification

Campaign: {campaign_name}
Campaign ID: {campaign_id}
Business Account: {business_account_name}
Status: COMPLETED
Completed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
Total Responses: {responses_count}

The campaign has been automatically completed and final analytics are available.

Dashboard: {url_for('business_auth.admin_panel', _external=True)}

---
VOÏA Campaign Management System
"""
                
            elif notification_type == 'error':
                error_details = additional_data.get('error', 'Unknown error') if additional_data else 'Unknown error'
                subject = f"Campaign Error: {campaign_name}"
                text_body = f"""
Campaign Error Notification

Campaign: {campaign_name}
Campaign ID: {campaign_id}
Business Account: {business_account_name}
Error Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

Error Details: {error_details}

Please check the campaign status and take appropriate action.

Dashboard: {url_for('business_auth.admin_panel', _external=True)}

---
VOÏA Campaign Management System
"""
            
            else:
                return {
                    'success': False,
                    'error': f'Unknown notification type: {notification_type}'
                }
            
            # Send to all admin emails
            result = self.send_email(
                to_emails=self.admin_emails,
                subject=subject,
                text_body=text_body,
                email_delivery_id=email_delivery_id
            )
            
            # Add notification-specific metadata
            if result['success']:
                result.update({
                    'email_type': 'campaign_notification',
                    'notification_type': notification_type,
                    'campaign_id': campaign_id,
                    'campaign_name': campaign_name
                })
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to send campaign notification ({notification_type}) for campaign {campaign_id}: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'email_type': 'campaign_notification',
                'notification_type': notification_type
            }

    def test_connection(self) -> Dict:
        """
        Test SMTP connection and configuration
        
        Returns:
            Dict with connection test results
        """
        
        if not self.is_configured():
            return {
                'success': False,
                'error': 'Email service not configured - missing SMTP settings',
                'configured': False
            }
        
        try:
            # Additional safety checks for type assertions  
            if not all([self.smtp_server, self.smtp_port, self.smtp_username, self.smtp_password]):
                return {
                    'success': False,
                    'error': 'Email service configuration incomplete',
                    'configured': True
                }
            
            # Test SMTP connection
            context = ssl.create_default_context()
            smtp_port = self.smtp_port or 587  # Default port fallback
            
            with smtplib.SMTP(str(self.smtp_server), smtp_port) as server:
                server.starttls(context=context)
                server.login(str(self.smtp_username), str(self.smtp_password))
                
                logger.info("Email service connection test successful")
                
                return {
                    'success': True,
                    'configured': True,
                    'smtp_server': self.smtp_server,
                    'smtp_port': self.smtp_port,
                    'admin_emails_count': len(self.admin_emails),
                    'test_time': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            error_msg = f"Email service connection test failed: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'configured': True,
                'smtp_server': self.smtp_server,
                'smtp_port': self.smtp_port
            }

# Global email service instance
email_service = EmailService()

def send_participant_invitation(participant_email: str,
                                participant_name: str,
                                campaign_name: str,
                                survey_token: str,
                                business_account_name: str) -> Dict:
    """Convenience function for sending participant invitations"""
    return email_service.send_participant_invitation(
        participant_email=participant_email,
        participant_name=participant_name,
        campaign_name=campaign_name,
        survey_token=survey_token,
        business_account_name=business_account_name
    )

def send_campaign_notification(notification_type: str,
                               campaign_name: str,
                               campaign_id: int,
                               business_account_name: str,
                               additional_data: Optional[Dict] = None) -> Dict:
    """Convenience function for sending campaign notifications"""
    return email_service.send_campaign_notification(
        notification_type=notification_type,
        campaign_name=campaign_name,
        campaign_id=campaign_id,
        business_account_name=business_account_name,
        additional_data=additional_data
    )

def test_email_service() -> Dict:
    """Convenience function for testing email service"""
    return email_service.test_connection()