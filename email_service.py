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
from models import EmailDelivery, EmailConfiguration, BrandingConfig

logger = logging.getLogger(__name__)

class EmailService:
    """Centralized email service for VOÏA system with multi-tenant support"""
    
    def __init__(self):
        # System-wide default configuration
        self.default_smtp_server = None
        self.default_smtp_port = None  
        self.default_smtp_username = None
        self.default_smtp_password = None
        self.default_admin_emails = []
        self._load_default_config()
    
    def _load_default_config(self):
        """Load default SMTP configuration from environment variables"""
        try:
            self.default_smtp_server = os.environ.get('SMTP_SERVER')
            self.default_smtp_port = int(os.environ.get('SMTP_PORT', 587))
            self.default_smtp_username = os.environ.get('SMTP_USERNAME')  
            self.default_smtp_password = os.environ.get('SMTP_PASSWORD')
            
            # Parse admin emails
            admin_emails_str = os.environ.get('ADMIN_EMAILS', '')
            if admin_emails_str:
                self.default_admin_emails = [email.strip() for email in admin_emails_str.split(',')]
            
            logger.info(f"Default email service configured: Server={self.default_smtp_server}, Port={self.default_smtp_port}")
            if self.default_admin_emails:
                logger.info(f"Default admin emails configured: {len(self.default_admin_emails)} recipients")
                
        except Exception as e:
            logger.error(f"Failed to load default email configuration: {e}")
            self.default_smtp_server = None
    
    def _get_email_config(self, business_account_id: Optional[int] = None) -> Dict:
        """Get email configuration for a business account or fall back to defaults"""
        config = {
            'smtp_server': self.default_smtp_server,
            'smtp_port': self.default_smtp_port,
            'smtp_username': self.default_smtp_username,
            'smtp_password': self.default_smtp_password,
            'use_tls': True,
            'use_ssl': False,
            'sender_name': 'VOÏA Team',
            'sender_email': self.default_smtp_username,
            'reply_to_email': None,
            'admin_emails': self.default_admin_emails,
            'source': 'system_default'
        }
        
        # Try to get business account specific configuration
        if business_account_id:
            try:
                email_config = EmailConfiguration.get_for_business_account(business_account_id)
                logger.debug(f"EmailConfiguration.get_for_business_account({business_account_id}) returned: {email_config is not None}")
                
                if email_config:
                    # Test is_valid() step by step
                    validation_errors = email_config.validate_configuration()
                    logger.debug(f"Basic validation errors: {validation_errors}")
                    
                    if len(validation_errors) == 0:
                        decrypted_password = email_config.get_smtp_password()
                        logger.debug(f"Password decryption result: {decrypted_password is not None} (length: {len(decrypted_password) if decrypted_password else 0})")
                        is_valid_result = email_config.is_valid()
                        logger.debug(f"Final is_valid() result: {is_valid_result}")
                    else:
                        logger.error(f"CRITICAL: Basic validation failed for business_account_id {business_account_id}: {validation_errors}")
                        is_valid_result = False
                else:
                    logger.error(f"CRITICAL: No EmailConfiguration record found for business_account_id {business_account_id}")
                    is_valid_result = False
                
                if email_config and is_valid_result:
                    config.update({
                        'smtp_server': email_config.smtp_server,
                        'smtp_port': email_config.smtp_port,
                        'smtp_username': email_config.smtp_username,
                        'smtp_password': email_config.get_smtp_password(),
                        'use_tls': email_config.use_tls,
                        'use_ssl': email_config.use_ssl,
                        'sender_name': email_config.sender_name,
                        'sender_email': email_config.sender_email,
                        'reply_to_email': email_config.reply_to_email,
                        'admin_emails': email_config.get_admin_emails(),
                        'source': 'business_account'
                    })
                    logger.debug(f"SUCCESS: Using business account email configuration for account {business_account_id}")
                else:
                    logger.error(f"FAILED: Invalid business account email configuration for account {business_account_id}, falling back to system defaults")
            except Exception as e:
                logger.error(f"EXCEPTION: Failed to load business account email configuration for account {business_account_id}: {e}")
                logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                logger.debug("Falling back to system default email configuration")
        
        return config
    
    def _get_branding_config(self, business_account_id: Optional[int] = None) -> Dict:
        """Get branding configuration for a business account with fallbacks"""
        branding = {
            'company_name': 'VOÏA - Voice Of Client',
            'logo_url': None,
            'tagline': 'AI Powered Client Insights',
            'has_custom_branding': False
        }
        
        if business_account_id:
            try:
                branding_config = BrandingConfig.query.filter_by(business_account_id=business_account_id).first()
                if branding_config:
                    # Get company display name with fallback
                    company_name = branding_config.get_company_display_name()
                    if company_name and company_name != 'Unknown Company':
                        branding['company_name'] = company_name
                        branding['has_custom_branding'] = True
                    
                    # Get logo URL if available
                    logo_url = branding_config.get_logo_url()
                    if logo_url:
                        branding['logo_url'] = logo_url
                        branding['has_custom_branding'] = True
                        
                    logger.debug(f"Loaded branding config for business account {business_account_id}: {company_name}")
                else:
                    logger.debug(f"No branding config found for business account {business_account_id}, using defaults")
            except Exception as e:
                logger.error(f"Failed to load branding configuration for business account {business_account_id}: {e}")
                logger.debug("Falling back to default VOÏA branding")
        
        return branding
    
    def is_configured(self, business_account_id: Optional[int] = None) -> bool:
        """Check if email service is properly configured for a business account or system default"""
        logger.debug(f"is_configured() called with business_account_id={business_account_id}")
        config = self._get_email_config(business_account_id)
        logger.debug(f"is_configured() got config with source: {config.get('source', 'unknown')}")
        logger.debug(f"is_configured() SMTP settings: server={bool(config['smtp_server'])}, port={bool(config['smtp_port'])}, username={bool(config['smtp_username'])}, password={bool(config['smtp_password'])}")
        
        result = all([
            config['smtp_server'],
            config['smtp_port'],
            config['smtp_username'],
            config['smtp_password']
        ])
        logger.debug(f"is_configured() returning: {result}")
        return result
    
    def send_email(self, 
                   to_emails: Union[str, List[str]], 
                   subject: str,
                   text_body: str,
                   html_body: Optional[str] = None,
                   from_email: Optional[str] = None,
                   email_delivery_id: Optional[int] = None,
                   business_account_id: Optional[int] = None) -> Dict:
        """
        Send email with text and optional HTML content using tenant-specific or default configuration
        
        Args:
            to_emails: Recipient email(s)
            subject: Email subject
            text_body: Plain text body
            html_body: Optional HTML body
            from_email: Optional sender email (defaults to configuration)
            email_delivery_id: Optional EmailDelivery record ID for tracking
            business_account_id: Optional business account ID for tenant-specific configuration
            
        Returns:
            Dict with success status and details
        """
        recipients: List[str] = []
        email_delivery = None
        
        # Get email configuration for this business account
        email_config = self._get_email_config(business_account_id)
        
        # Get EmailDelivery record if provided
        if email_delivery_id:
            try:
                email_delivery = EmailDelivery.query.get(email_delivery_id)
            except Exception as e:
                logger.error(f"Failed to retrieve EmailDelivery {email_delivery_id}: {e}")
        
        # Check configuration using the SAME config object we just loaded (avoid double-call to _get_email_config)
        config_check = all([
            email_config['smtp_server'],
            email_config['smtp_port'], 
            email_config['smtp_username'],
            email_config['smtp_password']
        ])
        
        if not config_check:
            config_source = email_config.get('source', 'unknown')
            error_msg = f'Email service not configured - missing SMTP settings (using {config_source} configuration)'
            logger.error(f"CRITICAL: send_email config check failed for business_account_id={business_account_id}. Config source: {config_source}, server: {bool(email_config['smtp_server'])}, port: {bool(email_config['smtp_port'])}, username: {bool(email_config['smtp_username'])}, password: {bool(email_config['smtp_password'])}")
            if email_delivery:
                email_delivery.mark_failed(error_msg, is_permanent=True)
                db.session.commit()
            return {
                'success': False,
                'error': error_msg
            }
        
        # Additional safety checks for type assertions
        if not all([email_config['smtp_server'], email_config['smtp_port'], 
                   email_config['smtp_username'], email_config['smtp_password']]):
            config_source = email_config.get('source', 'unknown')
            error_msg = f'Email service configuration incomplete (using {config_source} configuration)'
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
            
            # Set sender email - use business configuration or fall back to provided/default
            sender = from_email or email_config['sender_email'] or email_config['smtp_username']
            sender_name = email_config.get('sender_name', 'VOÏA Team')
            
            # Create message with proper sender formatting
            if sender_name and sender_name != sender:
                formatted_sender = f"{sender_name} <{sender}>"
            else:
                formatted_sender = sender
            
            # Create message
            if html_body:
                # Multipart message with both text and HTML
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = formatted_sender
                msg['To'] = ', '.join(recipients)
                
                # Add Reply-To if configured
                if email_config.get('reply_to_email'):
                    msg['Reply-To'] = email_config['reply_to_email']
                
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
                msg['From'] = formatted_sender
                msg['To'] = ', '.join(recipients)
                msg.set_content(text_body)
                
                # Add Reply-To if configured
                if email_config.get('reply_to_email'):
                    msg['Reply-To'] = email_config['reply_to_email']
            
            # Send email with type-safe values using tenant configuration
            context = ssl.create_default_context()
            smtp_port = email_config['smtp_port'] or 587  # Default port fallback
            
            # Determine connection type
            if email_config.get('use_ssl', False):
                # Use SSL connection
                with smtplib.SMTP_SSL(str(email_config['smtp_server']), smtp_port, context=context) as server:
                    server.login(str(email_config['smtp_username']), str(email_config['smtp_password']))
                    server.send_message(msg)
            else:
                # Use TLS connection (default)
                with smtplib.SMTP(str(email_config['smtp_server']), smtp_port) as server:
                    if email_config.get('use_tls', True):
                        server.starttls(context=context)
                    server.login(str(email_config['smtp_username']), str(email_config['smtp_password']))
                    server.send_message(msg)
            
            # Mark as successfully sent if we have a delivery record
            if email_delivery:
                email_delivery.mark_sent()
                db.session.commit()
            
            config_source = email_config.get('source', 'unknown')
            logger.info(f"Email sent successfully to {len(recipients)} recipients: {subject} (using {config_source} configuration)")
            
            return {
                'success': True,
                'recipients': recipients,
                'subject': subject,
                'sent_at': datetime.utcnow().isoformat(),
                'email_delivery_id': email_delivery_id,
                'config_source': config_source
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

    def test_configuration(self, business_account_id: Optional[int] = None) -> Dict:
        """
        Test email configuration for a business account or system default
        
        Args:
            business_account_id: Optional business account ID for tenant-specific configuration
            
        Returns:
            Dict with test results
        """
        email_config = self._get_email_config(business_account_id)
        config_source = email_config.get('source', 'unknown')
        
        if not self.is_configured(business_account_id):
            return {
                'success': False,
                'error': f'Email service not configured - missing SMTP settings (using {config_source} configuration)',
                'configured': False,
                'config_source': config_source
            }
        
        try:
            # Test SMTP connection
            context = ssl.create_default_context()
            smtp_port = email_config['smtp_port'] or 587
            
            if email_config.get('use_ssl', False):
                # Test SSL connection
                with smtplib.SMTP_SSL(str(email_config['smtp_server']), smtp_port, context=context) as server:
                    server.login(str(email_config['smtp_username']), str(email_config['smtp_password']))
            else:
                # Test TLS connection
                with smtplib.SMTP(str(email_config['smtp_server']), smtp_port) as server:
                    if email_config.get('use_tls', True):
                        server.starttls(context=context)
                    server.login(str(email_config['smtp_username']), str(email_config['smtp_password']))
            
            logger.info(f"Email configuration test successful (using {config_source} configuration)")
            
            return {
                'success': True,
                'message': 'Email configuration test successful',
                'configured': True,
                'config_source': config_source,
                'smtp_server': email_config['smtp_server'],
                'smtp_port': email_config['smtp_port'],
                'use_tls': email_config.get('use_tls', True),
                'use_ssl': email_config.get('use_ssl', False)
            }
            
        except Exception as e:
            error_msg = f"Email configuration test failed (using {config_source} configuration): {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'configured': True,
                'config_source': config_source,
                'smtp_server': email_config['smtp_server'],
                'smtp_port': email_config['smtp_port']
            }

    def send_participant_invitation(self, 
                                    participant_email: str,
                                    participant_name: str,
                                    campaign_name: str,
                                    survey_token: str,
                                    business_account_name: str,
                                    email_delivery_id: Optional[int] = None,
                                    business_account_id: Optional[int] = None) -> Dict:
        """
        Send survey invitation to a participant using tenant-specific configuration
        
        Args:
            participant_email: Participant's email
            participant_name: Participant's name
            campaign_name: Campaign name
            survey_token: JWT token for survey access
            business_account_name: Business account name
            email_delivery_id: Optional EmailDelivery record ID for tracking
            business_account_id: Optional business account ID for tenant-specific configuration
            
        Returns:
            Dict with success status and details
        """
        
        try:
            # Get branding configuration for this business account
            branding = self._get_branding_config(business_account_id)
            
            # Generate survey URL (using the correct 'survey' route)
            survey_url = url_for('survey', token=survey_token, _external=True)
            
            # Email subject
            subject = f"Your feedback is requested: {campaign_name}"
            
            # Text body with branding support
            text_body = f"""
Hello {participant_name},

{business_account_name} is requesting your valuable feedback through our Voice of Client system.

Campaign: {campaign_name}

Please click the link below to complete your survey:
{survey_url}

This personalized link is secure and will expire in 72 hours.

Your feedback helps improve services and experiences. The survey should take just a few minutes to complete.

Thank you for your time and valuable insights!

Best regards,
The {branding['company_name']} Team
{branding['tagline']}

---
This is an automated message. If you have any questions, please contact the organization that sent this survey.
"""
            
            # HTML body with branding support
            logo_html = ""
            if branding['logo_url']:
                logo_url = branding['logo_url']
                company_name = branding['company_name']
                logo_html = f'<img src="{logo_url}" alt="{company_name}" style="max-height: 60px; margin-bottom: 10px; display: block; margin-left: auto; margin-right: auto;">'
            
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
        .logo-image {{
            max-height: 60px;
            margin-bottom: 10px;
            display: block;
            margin-left: auto;
            margin-right: auto;
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
            {logo_html}
            <div class="logo">{branding['company_name']}</div>
            <div class="tagline">{branding['tagline']}</div>
        </div>
        
        <h2>Hello {participant_name},</h2>
        
        <p><strong>{business_account_name}</strong> is requesting your valuable feedback through our Voice of Client system.</p>
        
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
        The {branding['company_name']} Team</p>
        
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
                email_delivery_id=email_delivery_id,
                business_account_id=business_account_id
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

    def send_business_account_invitation(self, 
                                         user_email: str,
                                         user_first_name: str,
                                         user_last_name: str,
                                         business_account_name: str,
                                         invitation_token: str,
                                         email_delivery_id: Optional[int] = None,
                                         business_account_id: Optional[int] = None) -> Dict:
        """
        Send business account activation invitation using business account's SMTP configuration
        
        Args:
            user_email: New business user's email
            user_first_name: User's first name
            user_last_name: User's last name
            business_account_name: Name of the business account
            invitation_token: Secure UUID token for account activation
            email_delivery_id: Optional EmailDelivery record ID for tracking
            business_account_id: Business account ID to use their SMTP configuration
            
        Returns:
            Dict with success status and details
        """
        
        try:
            # Use business account's SMTP configuration if provided, otherwise fall back to platform-level
            email_config = self._get_email_config(business_account_id)
            branding = self._get_branding_config(business_account_id)
            
            # Generate activation URL
            from flask import url_for
            activation_url = url_for('business_auth.activate_account', token=invitation_token, _external=True)
            
            # Email subject
            subject = f"Welcome to {branding['company_name']} - Activate Your Business Account"
            
            # User's full name
            user_full_name = f"{user_first_name} {user_last_name}"
            
            # Text body for business account invitation
            text_body = f"""
Welcome to {branding['company_name']}!

Dear {user_full_name},

You have been invited to join {business_account_name} on our Voice of Client (VOÏA) platform as a business account administrator.

To activate your account and set up your password, please click the link below:
{activation_url}

This secure activation link will expire in 24 hours for security purposes.

Once activated, you'll have access to:
• Create and manage feedback campaigns
• Analyze client responses and insights
• Configure your business account settings
• Manage participant lists and invitations

If you have any questions or need assistance, please contact our support team.

Welcome aboard!

Best regards,
The {branding['company_name']} Team
{branding['tagline']}

---
This is an automated system message. Please do not reply to this email.
If you did not expect this invitation, please ignore this message.
"""
            
            # HTML body for business account invitation
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Welcome to {branding['company_name']}</title>
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
            font-size: 28px;
            font-weight: bold;
            color: #E13A44;
            margin-bottom: 5px;
        }}
        .tagline {{
            font-size: 14px;
            color: #666;
            font-style: italic;
        }}
        .welcome-message {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            border-left: 4px solid #28a745;
            margin: 20px 0;
        }}
        .business-account {{
            background-color: #e7f3ff;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #007bff;
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
            text-align: center;
            font-weight: bold;
            font-size: 16px;
        }}
        .cta-button:hover {{
            background-color: #c12e38;
        }}
        .features {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .feature-list {{
            list-style: none;
            padding: 0;
        }}
        .feature-list li {{
            padding: 8px 0;
            padding-left: 25px;
            position: relative;
        }}
        .feature-list li:before {{
            content: "✓";
            position: absolute;
            left: 0;
            color: #28a745;
            font-weight: bold;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            font-size: 12px;
            color: #666;
        }}
        .security-notice {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 4px;
            padding: 10px;
            margin: 15px 0;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">{branding['company_name']}</div>
            <div class="tagline">{branding['tagline']}</div>
        </div>
        
        <div class="welcome-message">
            <h2 style="margin-top: 0; color: #28a745;">Welcome to the Team!</h2>
            <p>Dear <strong>{user_full_name}</strong>,</p>
            <p>You have been invited to join <strong>{business_account_name}</strong> on our Voice of Client (VOÏA) platform as a business account administrator.</p>
        </div>
        
        <div class="business-account">
            <strong>Business Account:</strong> {business_account_name}
        </div>
        
        <p style="text-align: center;">
            <a href="{activation_url}" class="cta-button">Activate Your Account</a>
        </p>
        
        <div class="security-notice">
            <strong>Security Notice:</strong> This activation link will expire in 24 hours for your security.
        </div>
        
        <div class="features">
            <h3 style="margin-top: 0;">What You Can Do:</h3>
            <ul class="feature-list">
                <li>Create and manage feedback campaigns</li>
                <li>Analyze client responses and insights</li>
                <li>Configure your business account settings</li>
                <li>Manage participant lists and invitations</li>
                <li>Access comprehensive reporting dashboards</li>
                <li>Customize survey workflows and branding</li>
            </ul>
        </div>
        
        <div style="margin: 30px 0; padding: 20px; background-color: #e7f3ff; border-radius: 5px;">
            <p style="margin: 0;"><strong>Need Help?</strong></p>
            <p style="margin: 5px 0 0 0;">Our support team is here to help you get started. Contact us anytime with questions.</p>
        </div>
        
        <div class="footer">
            <p>Best regards,<br>
            The {branding['company_name']} Team</p>
            <hr style="margin: 15px 0;">
            <p><em>This is an automated system message. Please do not reply to this email.<br>
            If you did not expect this invitation, please ignore this message.</em></p>
        </div>
    </div>
</body>
</html>
"""
            
            # Send email using platform-level configuration (business_account_id=None ensures platform SMTP)
            result = self.send_email(
                to_emails=user_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                email_delivery_id=email_delivery_id,
                business_account_id=None  # Force platform-level configuration
            )
            
            # Add invitation-specific metadata
            if result['success']:
                result.update({
                    'email_type': 'business_account_invitation',
                    'user_email': user_email,
                    'user_name': user_full_name,
                    'business_account_name': business_account_name,
                    'invitation_token': invitation_token,
                    'activation_url': activation_url
                })
                
                logger.info(f"Business account invitation sent successfully to {user_email} for {business_account_name}")
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to send business account invitation to {user_email}: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'email_type': 'business_account_invitation',
                'user_email': user_email,
                'business_account_name': business_account_name
            }

    def send_campaign_notification(self,
                                   notification_type: str,
                                   campaign_name: str,
                                   campaign_id: int,
                                   business_account_name: str,
                                   additional_data: Optional[Dict] = None,
                                   email_delivery_id: Optional[int] = None,
                                   business_account_id: Optional[int] = None) -> Dict:
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
            # Get branding configuration for this business account
            branding = self._get_branding_config(business_account_id)
            
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
{branding['company_name']} Campaign Management System
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
{branding['company_name']} Campaign Management System
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
{branding['company_name']} Campaign Management System
"""
            
            else:
                return {
                    'success': False,
                    'error': f'Unknown notification type: {notification_type}'
                }
            
            # Send to all admin emails
            email_config = self._get_email_config(business_account_id)
            admin_emails = email_config.get('admin_emails', [])
            if not admin_emails:
                return {
                    'success': False,
                    'error': 'No admin emails configured for notifications'
                }
            
            result = self.send_email(
                to_emails=admin_emails,
                subject=subject,
                text_body=text_body,
                email_delivery_id=email_delivery_id,
                business_account_id=business_account_id
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
        Test SMTP connection and configuration using instance settings
        
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
            # Get default email configuration
            email_config = self._get_email_config()
            
            # Additional safety checks for type assertions  
            if not all([email_config['smtp_server'], email_config['smtp_port'], email_config['smtp_username'], email_config['smtp_password']]):
                return {
                    'success': False,
                    'error': 'Email service configuration incomplete',
                    'configured': True
                }
            
            # Test SMTP connection
            context = ssl.create_default_context()
            smtp_port = email_config['smtp_port'] or 587  # Default port fallback
            
            with smtplib.SMTP(str(email_config['smtp_server']), smtp_port) as server:
                if email_config.get('use_tls', True):
                    server.starttls(context=context)
                server.login(str(email_config['smtp_username']), str(email_config['smtp_password']))
                
                logger.info("Email service connection test successful")
                
                return {
                    'success': True,
                    'configured': True,
                    'smtp_server': email_config['smtp_server'],
                    'smtp_port': email_config['smtp_port'],
                    'admin_emails_count': len(email_config.get('admin_emails', [])),
                    'test_time': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            error_msg = f"Email service connection test failed: {str(e)}"
            logger.error(error_msg)
            
            email_config = self._get_email_config()
            return {
                'success': False,
                'error': error_msg,
                'configured': True,
                'smtp_server': email_config.get('smtp_server'),
                'smtp_port': email_config.get('smtp_port')
            }

    def test_connection_for_account(self, business_account_id: Optional[int] = None) -> Dict:
        """
        Test SMTP connection for a specific business account
        
        Args:
            business_account_id: Optional business account ID for tenant-specific configuration
        
        Returns:
            Dict with connection test results
        """
        
        if not self.is_configured(business_account_id):
            return {
                'success': False,
                'error': 'Email service not configured - missing SMTP settings',
                'configured': False
            }
        
        # Get the configuration for this business account
        config = self._get_email_config(business_account_id)
        
        try:
            # Validate required settings
            required_settings = ['smtp_server', 'smtp_port', 'smtp_username', 'smtp_password']
            missing_settings = [key for key in required_settings if not config.get(key)]
            
            if missing_settings:
                return {
                    'success': False,
                    'error': f'Email service configuration incomplete - missing: {", ".join(missing_settings)}',
                    'configured': True,
                    'config_source': config.get('source', 'unknown')
                }
            
            # Test SMTP connection with account-specific settings
            context = ssl.create_default_context()
            smtp_port = config['smtp_port'] or 587  # Default port fallback
            
            with smtplib.SMTP(str(config['smtp_server']), smtp_port) as server:
                if config.get('use_tls', True):
                    server.starttls(context=context)
                server.login(str(config['smtp_username']), str(config['smtp_password']))
                
                logger.info(f"Email service connection test successful for business account {business_account_id}")
                
                return {
                    'success': True,
                    'configured': True,
                    'config_source': config['source'],
                    'smtp_server': config['smtp_server'],
                    'smtp_port': config['smtp_port'],
                    'sender_email': config.get('sender_email'),
                    'admin_emails_count': len(config.get('admin_emails', [])),
                    'test_time': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            error_msg = f"Email service connection test failed: {str(e)}"
            logger.error(f"Connection test failed for business account {business_account_id}: {error_msg}")
            
            return {
                'success': False,
                'error': error_msg,
                'configured': True,
                'config_source': config.get('source', 'unknown'),
                'smtp_server': config.get('smtp_server'),
                'smtp_port': config.get('smtp_port')
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