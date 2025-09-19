#!/usr/bin/env python3
"""
Debug script to examine a single account in detail to understand the data inconsistency.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import BusinessAccount, LicenseHistory
from license_service import LicenseService
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_account(account_id):
    """Debug a single account to understand the data inconsistency."""
    
    with app.app_context():
        # Get account details
        account = BusinessAccount.query.get(account_id)
        if not account:
            logger.error(f"Account {account_id} not found")
            return
            
        logger.info(f"=== DEBUGGING ACCOUNT {account_id} ({account.name}) ===")
        logger.info(f"Account current_users_count: {getattr(account, 'current_users_count', 'N/A')}")
        
        # Get current license directly
        current_license = LicenseService.get_current_license(account_id)
        if current_license:
            logger.info(f"Current license: {current_license.license_type}")
            logger.info(f"License max_users: {current_license.max_users}")
            logger.info(f"License status: {current_license.status}")
            logger.info(f"License activated_at: {current_license.activated_at}")
            logger.info(f"License expires_at: {current_license.expires_at}")
        else:
            logger.info("No current license found")
        
        # Get individual license info
        logger.info("=== INDIVIDUAL GET_LICENSE_INFO ===")
        individual_info = LicenseService.get_license_info(account_id)
        logger.info(f"Individual users_used: {individual_info.get('users_used')}")
        logger.info(f"Individual users_limit: {individual_info.get('users_limit')}")
        logger.info(f"Individual users_remaining: {individual_info.get('users_remaining')}")
        logger.info(f"Individual license_type: {individual_info.get('license_type')}")
        logger.info(f"Individual current_license: {individual_info.get('current_license')}")
        
        # Get bulk license info
        logger.info("=== BULK GET_LICENSE_DATA ===")
        bulk_results = LicenseService.get_bulk_license_data([account_id])
        bulk_data = bulk_results.get(account_id)
        if bulk_data:
            bulk_info = bulk_data.get('license_info', {})
            logger.info(f"Bulk users_used: {bulk_info.get('users_used')}")
            logger.info(f"Bulk users_limit: {bulk_info.get('users_limit')}")
            logger.info(f"Bulk users_remaining: {bulk_info.get('users_remaining')}")
            logger.info(f"Bulk license_type: {bulk_info.get('license_type')}")
            logger.info(f"Bulk current_license: {bulk_info.get('current_license')}")
        else:
            logger.error("No bulk data found")

if __name__ == "__main__":
    # Debug account 3 first as it showed issues
    debug_account(3)