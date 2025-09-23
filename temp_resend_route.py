#!/usr/bin/env python3
"""
Temporary route to resend Videotron invitation
"""

from flask import current_app
from app import app, db
from models import BusinessAccountUser, BusinessAccount
from email_service import EmailService
import logging

@app.route('/temp/resend-videotron-invitation')
def temp_resend_videotron_invitation():
    """Temporary route to resend Videotron invitation"""
    
    try:
        # Find Videotron admin user
        user = BusinessAccountUser.query.filter_by(
            id=22,
            business_account_id=14
        ).first()
        
        if not user:
            return "ERROR: Videotron admin user not found", 404
        
        # Get business account
        business_account = BusinessAccount.query.get(14)
        if not business_account:
            return "ERROR: Videotron business account not found", 404
        
        # Send invitation email using business account's SMTP config
        email_service = EmailService()
        
        email_result = email_service.send_business_account_invitation(
            user_email=user.email,
            user_first_name=user.first_name,
            user_last_name=user.last_name,
            business_account_name=business_account.name,
            invitation_token=user.invitation_token,
            business_account_id=business_account.id
        )
        
        if email_result.get('success'):
            return f"""
            <h2>✅ SUCCESS: Videotron Invitation Resent!</h2>
            <p><strong>Email sent to:</strong> {user.email}</p>
            <p><strong>Business Account:</strong> {business_account.name}</p>
            <p><strong>User:</strong> {user.first_name} {user.last_name}</p>
            <p><strong>Token:</strong> {user.invitation_token}</p>
            <p><strong>Result:</strong> {email_result}</p>
            <hr>
            <p>The admin user should receive a fresh invitation email shortly.</p>
            """
        else:
            return f"""
            <h2>❌ FAILED: Email sending failed</h2>
            <p><strong>Error:</strong> {email_result.get('error')}</p>
            <p><strong>User:</strong> {user.email}</p>
            <p><strong>Token:</strong> {user.invitation_token}</p>
            """
            
    except Exception as e:
        return f"❌ ERROR: {str(e)}", 500

if __name__ == "__main__":
    print("Temporary route added: /temp/resend-videotron-invitation")