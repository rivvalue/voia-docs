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
from email.utils import formataddr
from typing import List, Dict, Optional, Union
from flask import current_app, url_for, render_template_string
import jwt
from app import db
from models import EmailDelivery, EmailConfiguration, BrandingConfig, PlatformEmailSettings

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
        """Get email configuration for a business account or fall back to defaults
        
        Supports dual-mode email delivery:
        - VOÏA-Managed: Uses platform AWS SES credentials + business account verified domain
        - Client-Managed: Uses business account's own SMTP credentials
        """
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
            'source': 'system_default',
            'email_mode': 'system_default'
        }
        
        logger.info(f"_get_email_config called with business_account_id={business_account_id}")
        
        # Try to get business account specific configuration
        if business_account_id:
            try:
                email_config = EmailConfiguration.get_for_business_account(business_account_id)
                logger.info(f"EmailConfiguration.get_for_business_account({business_account_id}) returned: {email_config is not None}")
                
                if email_config:
                    # Check if business account uses VOÏA-managed email (platform AWS SES)
                    if email_config.use_platform_email:
                        logger.info(f"Business account {business_account_id} uses VOÏA-managed email delivery")
                        
                        # Load platform AWS SES credentials
                        platform_settings = PlatformEmailSettings.query.first()
                        
                        if platform_settings and platform_settings.is_verified:
                            # Validate business account has verified domain
                            if not email_config.domain_verified:
                                logger.error(f"Business account {business_account_id} domain not verified for VOÏA-managed mode")
                                raise ValueError("Domain verification required for VOÏA-managed email delivery")
                            
                            if not email_config.sender_domain or not email_config.sender_email:
                                logger.error(f"Business account {business_account_id} missing sender domain/email")
                                raise ValueError("Sender domain and email required for VOÏA-managed email delivery")
                            
                            # Use platform AWS SES credentials + business account sender info
                            config.update({
                                'smtp_server': platform_settings.smtp_server,
                                'smtp_port': platform_settings.smtp_port,
                                'smtp_username': platform_settings.smtp_username,
                                'smtp_password': platform_settings.get_smtp_password(),
                                'use_tls': platform_settings.use_tls,
                                'use_ssl': platform_settings.use_ssl,
                                'sender_name': email_config.sender_name,
                                'sender_email': email_config.sender_email,  # Business account's verified domain email
                                'reply_to_email': email_config.reply_to_email,
                                'admin_emails': email_config.get_admin_emails(),
                                'source': 'voia_managed',
                                'email_mode': 'voia_managed',
                                'sender_domain': email_config.sender_domain,
                                'aws_region': platform_settings.aws_region
                            })
                            
                            logger.info(f"SUCCESS: Using VOÏA-managed email for business account {business_account_id} (Domain: {email_config.sender_domain}, Region: {platform_settings.aws_region})")
                        else:
                            logger.error("Platform AWS SES credentials not configured or not verified")
                            raise ValueError("Platform email settings not available")
                    
                    else:
                        # Client-Managed mode: Use business account's own SMTP credentials
                        logger.info(f"Business account {business_account_id} uses client-managed email delivery")
                        
                        # Validate client-managed configuration
                        validation_errors = email_config.validate_configuration()
                        logger.info(f"Validation errors for business_account_id {business_account_id}: {validation_errors}")
                        
                        if len(validation_errors) == 0:
                            decrypted_password = email_config.get_smtp_password()
                            is_valid_result = email_config.is_valid()
                            logger.info(f"is_valid() result for business_account_id {business_account_id}: {is_valid_result}")
                        else:
                            logger.error(f"CRITICAL: Basic validation failed for business_account_id {business_account_id}: {validation_errors}")
                            is_valid_result = False
                        
                        if is_valid_result:
                            # Auto-generate SMTP server for AWS SES if needed
                            email_config.ensure_ses_smtp_server()
                            
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
                                'email_provider': email_config.email_provider if hasattr(email_config, 'email_provider') else 'smtp',
                                'aws_region': email_config.aws_region if hasattr(email_config, 'aws_region') else None,
                                'source': 'business_account',
                                'email_mode': 'client_managed'
                            })
                            
                            provider_info = f"AWS SES ({email_config.aws_region})" if email_config.is_aws_ses() else "SMTP"
                            logger.info(f"SUCCESS: Using client-managed email configuration for account {business_account_id} (Provider: {provider_info})")
                        else:
                            logger.error(f"FAILED: Invalid client-managed email configuration for account {business_account_id}, falling back to system defaults")
                else:
                    logger.error(f"CRITICAL: No EmailConfiguration record found for business_account_id {business_account_id}")
                    
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
    
    def _get_email_content(self, business_account_id: Optional[int] = None, campaign=None) -> Dict:
        """Get email content configuration with 3-tier fallback: campaign → email_config → defaults
        
        Args:
            business_account_id: Optional business account ID
            campaign: Optional Campaign object for campaign-specific content
            
        Returns:
            Dict with subject, intro, cta_text, closing, footer
        """
        # Default templates (tier 3)
        defaults = {
            'subject': "Votre avis est sollicité : {campaign_name}",
            'intro': "{business_account_name} sollicite votre précieux retour d'expérience via notre système Voice of Client.",
            'cta_text': "Complétez votre enquête",
            'closing': "Your feedback helps improve services and experiences. The survey should take just a few minutes to complete.\n\nThank you for your time and valuable insights!",
            'footer': "Ceci est un message automatique. Si vous avez des questions, veuillez contacter l'organisation qui vous a envoyé cette enquête."
        }
        
        # Try campaign-specific content first (tier 1)
        if campaign and campaign.use_custom_email_content:
            try:
                campaign_content = campaign.get_email_content()
                # Build result, falling back to tier 2/3 for empty fields
                result = {
                    'subject': campaign_content.get('subject_template') or None,
                    'intro': campaign_content.get('intro_message') or None,
                    'cta_text': campaign_content.get('cta_text') or None,
                    'closing': campaign_content.get('closing_message') or None,
                    'footer': campaign_content.get('footer_note') or None
                }
                
                # If all campaign fields are set, return immediately
                if all(result.values()):
                    return result
                
                # Otherwise, continue to tier 2 to fill in gaps
            except Exception as e:
                logger.error(f"Failed to load campaign-specific email content: {e}")
                result = {k: None for k in defaults.keys()}
        else:
            result = {k: None for k in defaults.keys()}
        
        # Try business account email config (tier 2)
        if business_account_id:
            try:
                email_config = EmailConfiguration.get_for_business_account(business_account_id)
                if email_config:
                    account_content = email_config.get_email_content()
                    # Fill in any None values from campaign tier
                    for key in result.keys():
                        if result[key] is None:
                            result[key] = account_content.get(key)
            except Exception as e:
                logger.error(f"Failed to load email content for business account {business_account_id}: {e}")
        
        # Fill in any remaining None values with defaults (tier 3)
        for key in result.keys():
            if result[key] is None:
                result[key] = defaults[key]
        
        return result
    
    def _substitute_variables(self, template: str, variables: Dict) -> str:
        """Substitute template variables with values
        
        Args:
            template: Template string with {variable} placeholders
            variables: Dict of variable names to values
            
        Returns:
            String with variables substituted
        """
        result = template
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))
        return result
    
    def _build_invitation_email_html(self, 
                                     participant_name: str,
                                     campaign_name: str,
                                     survey_url: str,
                                     intro_text: str,
                                     closing_text: str,
                                     footer_text: str,
                                     branding: Dict,
                                     email_content: Dict) -> str:
        """Build invitation email HTML template.
        
        Shared helper used by both send_participant_invitation and preview_campaign_email
        to ensure templates are identical.
        
        Args:
            participant_name: Name of participant
            campaign_name: Campaign name
            survey_url: Survey access URL
            intro_text: Introduction text (variable-substituted)
            closing_text: Closing text (variable-substituted)
            footer_text: Footer text (variable-substituted)
            branding: Branding configuration dict
            email_content: Email content dict with cta_text
            
        Returns:
            HTML string for invitation email
        """
        # Build logo HTML
        logo_html = ""
        if branding['logo_url']:
            logo_url = branding['logo_url']
            company_name = branding['company_name']
            logo_html = f'<img src="{logo_url}" alt="{company_name}" style="max-height: 60px; margin-bottom: 10px; display: block; margin-left: auto; margin-right: auto;">'
        
        return f"""
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
        
        <p>{intro_text}</p>
        
        <div class="campaign-name">
            <strong>Campaign:</strong> {campaign_name}
        </div>
        
        <div style="text-align: center;">
            <a href="{survey_url}" class="cta-button">{email_content['cta_text']}</a>
        </div>
        
        <div class="security-note">
            <strong>🔒 Security Note:</strong> This personalized link is secure and will expire in 72 hours.
        </div>
        
        <p style="white-space: pre-line;">{closing_text}</p>
        
        <p>Best regards,<br>
        The {branding['company_name']} Team</p>
        
        <div class="footer">
            {footer_text}
        </div>
    </div>
</body>
</html>
"""
    
    def _build_reminder_email_html(self,
                                   participant_name: str,
                                   campaign_name: str,
                                   survey_url: str,
                                   intro_text: str,
                                   closing_text: str,
                                   footer_text: str,
                                   branding: Dict,
                                   email_content: Dict,
                                   reminder_badge_text: str = "⏰ Friendly Reminder") -> str:
        """Build reminder email HTML template.
        
        Shared helper used by both send_participant_reminder and preview_campaign_email
        to ensure templates are identical.
        
        Args:
            participant_name: Name of participant
            campaign_name: Campaign name
            survey_url: Survey access URL
            intro_text: Introduction text (variable-substituted)
            closing_text: Closing text (variable-substituted)
            footer_text: Footer text (variable-substituted)
            branding: Branding configuration dict
            email_content: Email content dict with cta_text
            reminder_badge_text: Badge text (e.g., "⏰ Friendly Reminder" or "⏰ Midpoint Reminder")
            
        Returns:
            HTML string for reminder email
        """
        # Build logo HTML
        logo_html = ""
        if branding['logo_url']:
            logo_url = branding['logo_url']
            company_name = branding['company_name']
            logo_html = f'<img src="{logo_url}" alt="{company_name}" style="max-height: 60px; margin-bottom: 10px; display: block; margin-left: auto; margin-right: auto;">'
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Survey Reminder - {campaign_name}</title>
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
        .reminder-badge {{
            background-color: #fff3cd;
            color: #856404;
            padding: 8px 16px;
            border-radius: 20px;
            display: inline-block;
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 20px;
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
        
        <div style="text-align: center;">
            <span class="reminder-badge">{reminder_badge_text}</span>
        </div>
        
        <h2>Hello {participant_name},</h2>
        
        <p>We wanted to remind you about an opportunity to share your feedback with us.</p>
        
        <p>{intro_text}</p>
        
        <div class="campaign-name">
            <strong>Campaign:</strong> {campaign_name}
        </div>
        
        <p>If you haven't already completed the survey, please take a few moments to share your thoughts.</p>
        
        <div style="text-align: center;">
            <a href="{survey_url}" class="cta-button">{email_content['cta_text']}</a>
        </div>
        
        <div class="security-note">
            <strong>🔒 Security Note:</strong> This personalized link is secure and will remain active until the campaign ends.
        </div>
        
        <p>Your input is valuable to us, and we appreciate you taking the time to participate.</p>
        
        <p style="white-space: pre-line;">{closing_text}</p>
        
        <p>Best regards,<br>
        The {branding['company_name']} Team</p>
        
        <div class="footer">
            {footer_text}
        </div>
    </div>
</body>
</html>
"""
    
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
            error_msg = 'Email service not configured - missing SMTP settings'
            logger.warning(f"Email service not configured for business account {business_account_id}, using system defaults")
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
            
            # Set sender email - use business configuration or fall back to provided/default
            sender = from_email or email_config['sender_email'] or email_config['smtp_username']
            sender_name = email_config.get('sender_name', 'VOÏA Team')
            
            # Create message with proper sender formatting using formataddr to handle special characters
            if sender_name and sender_name != sender:
                formatted_sender = formataddr((sender_name, sender))
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
            
            logger.info(f"Sending email via SMTP: server={email_config['smtp_server']}, port={smtp_port}, username={email_config['smtp_username']}, to={recipients}, subject={subject}")
            
            # Determine connection type
            if email_config.get('use_ssl', False):
                # Use SSL connection
                logger.info(f"Using SSL connection to {email_config['smtp_server']}:{smtp_port}")
                with smtplib.SMTP_SSL(str(email_config['smtp_server']), smtp_port, context=context) as server:
                    server.set_debuglevel(1)  # Enable SMTP protocol debugging
                    server.login(str(email_config['smtp_username']), str(email_config['smtp_password']))
                    send_result = server.send_message(msg)
                    logger.info(f"SMTP send_message() returned: {send_result}")
            else:
                # Use TLS connection (default)
                logger.info(f"Using TLS connection to {email_config['smtp_server']}:{smtp_port}")
                with smtplib.SMTP(str(email_config['smtp_server']), smtp_port) as server:
                    server.set_debuglevel(1)  # Enable SMTP protocol debugging
                    if email_config.get('use_tls', True):
                        server.starttls(context=context)
                    server.login(str(email_config['smtp_username']), str(email_config['smtp_password']))
                    send_result = server.send_message(msg)
                    logger.info(f"SMTP send_message() returned: {send_result}")
            
            # Mark as successfully sent if we have a delivery record
            if email_delivery:
                email_delivery.mark_sent()
                db.session.commit()
            
            config_source = email_config.get('source', 'unknown')
            logger.info(f"Email sent successfully to {len(recipients)} recipients: {subject}")
            
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
                'error': 'Email service not configured - missing SMTP settings',
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
            
            logger.info("Email configuration test successful")
            
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
            error_msg = f"Email configuration test failed: {str(e)}"
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
                                    business_account_id: Optional[int] = None,
                                    campaign=None) -> Dict:
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
            campaign: Optional Campaign object for campaign-specific email content
            
        Returns:
            Dict with success status and details
        """
        
        try:
            # Get branding configuration for this business account
            branding = self._get_branding_config(business_account_id)
            
            # Get custom email content with 3-tier fallback (campaign → email_config → defaults)
            email_content = self._get_email_content(business_account_id, campaign=campaign)
            
            # Generate survey URL (using the correct 'survey' route)
            survey_url = url_for('survey', token=survey_token, _external=True)
            
            # Template variables for substitution
            template_vars = {
                'participant_name': participant_name,
                'campaign_name': campaign_name,
                'business_account_name': business_account_name,
                'survey_url': survey_url
            }
            
            # Email subject (with variable substitution)
            subject = self._substitute_variables(email_content['subject'], template_vars)
            
            # Build text body with custom content
            intro_text = self._substitute_variables(email_content['intro'], template_vars)
            closing_text = self._substitute_variables(email_content['closing'], template_vars)
            footer_text = self._substitute_variables(email_content['footer'], template_vars)
            
            text_body = f"""
Hello {participant_name},

{intro_text}

Campaign: {campaign_name}

Please click the link below to complete your survey:
{survey_url}

This personalized link is secure and will expire in 72 hours.

{closing_text}

Best regards,
The {branding['company_name']} Team
{branding['tagline']}

---
{footer_text}
"""
            
            # HTML body using shared template helper
            html_body = self._build_invitation_email_html(
                participant_name=participant_name,
                campaign_name=campaign_name,
                survey_url=survey_url,
                intro_text=intro_text,
                closing_text=closing_text,
                footer_text=footer_text,
                branding=branding,
                email_content=email_content
            )
            
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

    def send_participant_reminder(self, 
                                  participant_email: str,
                                  participant_name: str,
                                  campaign_name: str,
                                  survey_token: str,
                                  business_account_name: str,
                                  email_delivery_id: Optional[int] = None,
                                  business_account_id: Optional[int] = None,
                                  campaign=None) -> Dict:
        """
        Send reminder email to a participant who hasn't completed the survey.
        
        Reuses the same template infrastructure as participant invitations but with
        modified messaging to indicate this is a reminder rather than initial invitation.
        
        Args:
            participant_email: Participant's email
            participant_name: Participant's name
            campaign_name: Campaign name
            survey_token: JWT token for survey access
            business_account_name: Business account name
            email_delivery_id: Optional EmailDelivery record ID for tracking
            business_account_id: Optional business account ID for tenant-specific configuration
            campaign: Optional Campaign object for campaign-specific email content
            
        Returns:
            Dict with success status and details
        """
        
        try:
            # Get branding configuration for this business account
            branding = self._get_branding_config(business_account_id)
            
            # Get custom email content with 3-tier fallback (campaign → email_config → defaults)
            email_content = self._get_email_content(business_account_id, campaign=campaign)
            
            # Generate survey URL (using the correct 'survey' route)
            survey_url = url_for('survey', token=survey_token, _external=True)
            
            # Template variables for substitution
            template_vars = {
                'participant_name': participant_name,
                'campaign_name': campaign_name,
                'business_account_name': business_account_name,
                'survey_url': survey_url
            }
            
            # Email subject with reminder indicator
            subject = f"Reminder: {self._substitute_variables(email_content['subject'], template_vars)}"
            
            # Build text body with reminder-specific messaging
            intro_text = self._substitute_variables(email_content['intro'], template_vars)
            closing_text = self._substitute_variables(email_content['closing'], template_vars)
            footer_text = self._substitute_variables(email_content['footer'], template_vars)
            
            text_body = f"""
Hello {participant_name},

We wanted to remind you about an opportunity to share your feedback with us.

{intro_text}

Campaign: {campaign_name}

If you haven't already completed the survey, please click the link below:
{survey_url}

This personalized link is secure and will remain active until the campaign ends.

Your input is valuable to us, and we appreciate you taking the time to participate.

{closing_text}

Best regards,
The {branding['company_name']} Team
{branding['tagline']}

---
{footer_text}
"""
            
            # HTML body using shared template helper
            html_body = self._build_reminder_email_html(
                participant_name=participant_name,
                campaign_name=campaign_name,
                survey_url=survey_url,
                intro_text=intro_text,
                closing_text=closing_text,
                footer_text=footer_text,
                branding=branding,
                email_content=email_content,
                reminder_badge_text="⏰ Friendly Reminder"
            )
            
            # Send the email
            result = self.send_email(
                to_emails=participant_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                email_delivery_id=email_delivery_id,
                business_account_id=business_account_id
            )
            
            # Add reminder-specific metadata
            if result['success']:
                result.update({
                    'email_type': 'reminder',
                    'campaign_name': campaign_name,
                    'participant_name': participant_name,
                    'survey_token': survey_token[:20] + '...'  # Truncated for logging
                })
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to send participant reminder to {participant_email}: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'email_type': 'reminder',
                'participant_email': participant_email
            }

    def preview_campaign_email(self, campaign, email_type: str = 'invitation') -> Dict:
        """
        Generate email preview HTML for a campaign without sending.
        Reuses the exact same template logic as send_participant_invitation/reminder.
        
        Args:
            campaign: Campaign object
            email_type: Type of email to preview ('invitation', 'reminder_primary', 'reminder_midpoint')
            
        Returns:
            Dict with 'subject', 'html_body', and metadata
        """
        try:
            # Mock participant data for preview
            mock_participant_name = "Jean Dupont"
            mock_participant_email = "example@company.com"
            mock_survey_token = "preview-token-abc123xyz789"
            
            # Get business account info
            business_account = campaign.business_account
            business_account_name = business_account.name if business_account else "Your Organization"
            business_account_id = business_account.id if business_account else None
            
            # Get branding configuration
            branding = self._get_branding_config(business_account_id)
            
            # Get custom email content with 3-tier fallback
            email_content = self._get_email_content(business_account_id, campaign=campaign)
            
            # Generate mock survey URL
            survey_url = url_for('survey', token=mock_survey_token, _external=True)
            
            # Template variables for substitution
            template_vars = {
                'participant_name': mock_participant_name,
                'campaign_name': campaign.name,
                'business_account_name': business_account_name,
                'survey_url': survey_url
            }
            
            # Build email based on type
            if email_type == 'invitation':
                # Email subject
                subject = self._substitute_variables(email_content['subject'], template_vars)
                
                # Build text content
                intro_text = self._substitute_variables(email_content['intro'], template_vars)
                closing_text = self._substitute_variables(email_content['closing'], template_vars)
                footer_text = self._substitute_variables(email_content['footer'], template_vars)
                
                # HTML body using shared template helper
                html_body = self._build_invitation_email_html(
                    participant_name=mock_participant_name,
                    campaign_name=campaign.name,
                    survey_url=survey_url,
                    intro_text=intro_text,
                    closing_text=closing_text,
                    footer_text=footer_text,
                    branding=branding,
                    email_content=email_content
                )
                
            else:  # reminder_primary or reminder_midpoint
                # Email subject with reminder indicator
                subject = f"Reminder: {self._substitute_variables(email_content['subject'], template_vars)}"
                
                # Build text content
                intro_text = self._substitute_variables(email_content['intro'], template_vars)
                closing_text = self._substitute_variables(email_content['closing'], template_vars)
                footer_text = self._substitute_variables(email_content['footer'], template_vars)
                
                # Determine reminder badge text
                if email_type == 'reminder_midpoint':
                    reminder_badge_text = "⏰ Midpoint Reminder"
                else:
                    reminder_badge_text = "⏰ Friendly Reminder"
                
                # HTML body using shared template helper
                html_body = self._build_reminder_email_html(
                    participant_name=mock_participant_name,
                    campaign_name=campaign.name,
                    survey_url=survey_url,
                    intro_text=intro_text,
                    closing_text=closing_text,
                    footer_text=footer_text,
                    branding=branding,
                    email_content=email_content,
                    reminder_badge_text=reminder_badge_text
                )
            
            return {
                'success': True,
                'email_type': email_type,
                'subject': subject,
                'html_body': html_body,
                'mock_participant_name': mock_participant_name,
                'campaign_name': campaign.name
            }
            
        except Exception as e:
            error_msg = f"Failed to generate email preview for campaign {campaign.id}: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'email_type': email_type
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
            
            # Send email using business account SMTP configuration  
            result = self.send_email(
                to_emails=user_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                email_delivery_id=email_delivery_id,
                business_account_id=business_account_id
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

    def send_password_reset_email(self,
                                   user_email: str,
                                   user_first_name: str,
                                   user_last_name: str,
                                   reset_token: str,
                                   email_delivery_id: Optional[int] = None,
                                   business_account_id: Optional[int] = None) -> Dict:
        """
        Send password reset email with secure reset link
        
        Args:
            user_email: User's email address
            user_first_name: User's first name
            user_last_name: User's last name
            reset_token: Secure UUID token for password reset
            email_delivery_id: Optional EmailDelivery record ID for tracking
            business_account_id: Business account ID to use their SMTP configuration
            
        Returns:
            Dict with success status and details
        """
        
        try:
            # Get branding configuration
            branding = self._get_branding_config(business_account_id)
            
            # Generate reset URL
            from flask import url_for
            reset_url = url_for('business_auth.reset_password', token=reset_token, _external=True)
            
            # Email subject
            subject = f"Reset Your Password - {branding['company_name']}"
            
            # User's full name
            user_full_name = f"{user_first_name} {user_last_name}"
            
            # Text body for password reset
            text_body = f"""
Password Reset Request

Dear {user_full_name},

We received a request to reset the password for your {branding['company_name']} business account.

To reset your password, please click the link below:
{reset_url}

This secure password reset link will expire in 24 hours for security purposes.

If you did not request a password reset, please ignore this email. Your password will remain unchanged.

Best regards,
The {branding['company_name']} Team
{branding['tagline']}

---
This is an automated system message. Please do not reply to this email.
If you did not request this password reset, please ignore this message.
"""
            
            # HTML body for password reset
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Password Reset - {branding['company_name']}</title>
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
        .reset-message {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            border-left: 4px solid #E13A44;
            margin: 20px 0;
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
        .warning-box {{
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 4px;
            padding: 15px;
            margin: 20px 0;
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
        
        <div class="reset-message">
            <h2 style="margin-top: 0; color: #E13A44;">Password Reset Request</h2>
            <p>Dear <strong>{user_full_name}</strong>,</p>
            <p>We received a request to reset the password for your business account.</p>
        </div>
        
        <p style="text-align: center;">
            <a href="{reset_url}" class="cta-button">Reset Your Password</a>
        </p>
        
        <div class="security-notice">
            <strong>Security Notice:</strong> This password reset link will expire in 24 hours for your security.
        </div>
        
        <div class="warning-box">
            <strong>Did Not Request This?</strong><br>
            If you did not request a password reset, please ignore this email. Your password will remain unchanged and secure.
        </div>
        
        <div class="footer">
            <p>Best regards,<br>
            The {branding['company_name']} Team</p>
            <hr style="margin: 15px 0;">
            <p><em>This is an automated system message. Please do not reply to this email.<br>
            If you did not request this password reset, please ignore this message.</em></p>
        </div>
    </div>
</body>
</html>
"""
            
            # Send email using business account SMTP configuration
            result = self.send_email(
                to_emails=user_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                email_delivery_id=email_delivery_id,
                business_account_id=business_account_id
            )
            
            # Add password reset-specific metadata
            if result['success']:
                result.update({
                    'email_type': 'password_reset',
                    'user_email': user_email,
                    'user_name': user_full_name,
                    'reset_url': reset_url
                })
                
                logger.info(f"Password reset email sent successfully to {user_email}")
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to send password reset email to {user_email}: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'email_type': 'password_reset',
                'user_email': user_email
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