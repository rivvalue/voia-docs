#!/usr/bin/env python3
"""
Resend invitation email for Videotron admin user
Option 2: Generate fresh token and resend invitation email
"""

import sys
import os
sys.path.append('.')

from app import app, db
from models import BusinessAccountUser, BusinessAccount
from email_service import EmailService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def resend_videotron_invitation():
    """Resend invitation email for Videotron admin user"""
    
    with app.app_context():
        try:
            # Find Videotron business account
            videotron_account = BusinessAccount.query.filter(
                BusinessAccount.name.ilike('%videotron%')
            ).first()
            
            if not videotron_account:
                logger.error("Videotron business account not found")
                return False
            
            logger.info(f"Found Videotron account: {videotron_account.name} (ID: {videotron_account.id})")
            
            # Find the admin user for Videotron
            admin_user = BusinessAccountUser.query.filter_by(
                business_account_id=videotron_account.id,
                role='business_account_admin'
            ).first()
            
            if not admin_user:
                logger.error("Videotron admin user not found")
                return False
            
            logger.info(f"Found admin user: {admin_user.email} (ID: {admin_user.id})")
            logger.info(f"Current status: email_verified={admin_user.email_verified}, active={admin_user.is_active_user}")
            
            # Generate fresh invitation token
            logger.info("Generating fresh invitation token...")
            new_token = admin_user.generate_invitation_token()
            db.session.commit()
            
            logger.info(f"New invitation token generated: {new_token}")
            
            # Resend invitation email using business account's SMTP config
            logger.info("Sending invitation email...")
            email_service = EmailService()
            
            email_result = email_service.send_business_account_invitation(
                user_email=admin_user.email,
                user_first_name=admin_user.first_name,
                user_last_name=admin_user.last_name,
                business_account_name=videotron_account.name,
                invitation_token=new_token,
                business_account_id=videotron_account.id
            )
            
            if email_result.get('success'):
                logger.info(f"✅ SUCCESS: Invitation email sent to {admin_user.email}")
                logger.info(f"Business Account: {videotron_account.name}")
                logger.info(f"User: {admin_user.first_name} {admin_user.last_name}")
                logger.info(f"Email Status: {email_result}")
                return True
            else:
                logger.error(f"❌ FAILED: Email sending failed: {email_result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ ERROR: Failed to resend invitation: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = resend_videotron_invitation()
    if success:
        print("\n🎉 VIDEOTRON INVITATION RESENT SUCCESSFULLY!")
        print("The admin user should receive a fresh invitation email.")
    else:
        print("\n❌ FAILED TO RESEND INVITATION")
        print("Check the logs above for error details.")