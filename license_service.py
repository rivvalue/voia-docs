"""
LicenseService: Comprehensive license management service for VOÏ Voice of Insight
Author: System Migration Agent
Created: September 17, 2025

This service replaces all direct BusinessAccount license field access with the new 
license_history table system. It provides centralized license management with:
- Current license lookup and validation
- License period calculations with edge case handling
- Campaign, user, and participant limit enforcement
- Historical license tracking and migration support
- Comprehensive error handling and audit logging

The service maintains API compatibility with existing BusinessAccount methods while
providing enhanced functionality through the license_history table structure.
"""

from datetime import datetime, date, timedelta
from typing import Optional, Tuple, Dict, List, Any
import logging
from models import LicenseHistory, BusinessAccount, Campaign, db
from sqlalchemy import and_, func

logger = logging.getLogger(__name__)

class LicenseService:
    """
    Comprehensive license management service that replaces direct BusinessAccount license field access
    with license_history table operations.
    
    This service provides:
    - Centralized license validation and enforcement
    - Backward compatibility with existing BusinessAccount methods
    - Enhanced historical tracking and audit capabilities  
    - Graceful handling of trial accounts and edge cases
    - Performance-optimized license lookups
    """
    
    # ==== CORE LICENSE LOOKUP METHODS ====
    
    @staticmethod
    def get_current_license(business_account_id: int) -> Optional[LicenseHistory]:
        """
        Get the current active license for a business account.
        
        Args:
            business_account_id: Business account ID to look up
            
        Returns:
            LicenseHistory: Current active license or None if no active license
            
        Note:
            This method uses database indexes for optimal performance and includes
            comprehensive validation of license status and date ranges.
        """
        try:
            return LicenseHistory.get_current_license(business_account_id)
        except Exception as e:
            logger.error(f"Failed to get current license for business_account_id {business_account_id}: {e}")
            return None
    
    @staticmethod
    def get_license_for_date(business_account_id: int, reference_date: date) -> Optional[LicenseHistory]:
        """
        Get the license that was active on a specific date.
        
        Args:
            business_account_id: Business account ID to look up
            reference_date: Date to check license for
            
        Returns:
            LicenseHistory: License active on the specified date or None
        """
        try:
            return LicenseHistory.get_license_for_date(business_account_id, reference_date)
        except Exception as e:
            logger.error(f"Failed to get license for date {reference_date} for business_account_id {business_account_id}: {e}")
            return None
    
    @staticmethod
    def get_license_period(business_account_id: int, reference_date: Optional[date] = None) -> Tuple[Optional[date], Optional[date]]:
        """
        Calculate license period boundaries for a business account.
        
        Replaces BusinessAccount.get_license_period() with license_history table lookup.
        Maintains backward compatibility including trial account fallback behavior.
        
        Args:
            business_account_id: Business account ID to get license period for
            reference_date: Date to check (defaults to today)
            
        Returns:
            tuple: (period_start_date, period_end_date) or (None, None) if no valid license
            
        Backward Compatibility:
            - Maintains same edge case handling as original method
            - Supports trial account fallback to calendar year
            - Handles leap year date calculations properly
        """
        if reference_date is None:
            reference_date = date.today()
        
        try:
            # Try to get license for the reference date
            license_record = LicenseService.get_license_for_date(business_account_id, reference_date)
            
            if license_record:
                # Convert datetime to date for consistency with original method
                start_date = license_record.activated_at.date() if hasattr(license_record.activated_at, 'date') else license_record.activated_at
                end_date = license_record.expires_at.date() if hasattr(license_record.expires_at, 'date') else license_record.expires_at
                
                logger.debug(f"Found license period for business_account_id {business_account_id}: {start_date} to {end_date}")
                return start_date, end_date
            
            # No license found - check if this account exists and needs migration
            business_account = BusinessAccount.query.get(business_account_id)
            if not business_account:
                logger.warning(f"Business account {business_account_id} not found")
                return None, None
            
            # For trial accounts or accounts without license_history records,
            # fall back to original BusinessAccount method for backward compatibility
            logger.info(f"No license_history found for business_account_id {business_account_id}, falling back to legacy method")
            return business_account.get_license_period(reference_date)
            
        except Exception as e:
            logger.error(f"Failed to get license period for business_account_id {business_account_id}: {e}")
            
            # Try fallback to legacy method
            try:
                business_account = BusinessAccount.query.get(business_account_id)
                if business_account:
                    logger.info(f"Using legacy fallback for license period lookup for business_account_id {business_account_id}")
                    return business_account.get_license_period(reference_date)
            except Exception as fallback_error:
                logger.error(f"Legacy fallback also failed for business_account_id {business_account_id}: {fallback_error}")
            
            return None, None
    
    # ==== CAMPAIGN LIMIT ENFORCEMENT ====
    
    @staticmethod
    def can_activate_campaign(business_account_id: int) -> bool:
        """
        Check if business account can activate another campaign based on current license limits.
        
        Replaces BusinessAccount.can_activate_campaign() with license_history table lookup.
        Maintains backward compatibility including trial account behavior.
        
        Args:
            business_account_id: Business account ID to check
            
        Returns:
            bool: True if account can activate another campaign, False otherwise
            
        Backward Compatibility:
            - Uses same logic as original method (4 campaigns per license period)
            - Falls back to calendar year for trial accounts without license history
            - Counts ALL campaigns that started in current period regardless of status
        """
        try:
            # Get current license period boundaries
            period_start, period_end = LicenseService.get_license_period(business_account_id)
            
            # Get current license to check limits
            current_license = LicenseService.get_current_license(business_account_id)
            max_campaigns = current_license.max_campaigns_per_year if current_license else 4
            
            # If no valid license period, fall back to calendar year (trial behavior)
            if not period_start or not period_end:
                logger.info(f"No valid license period for business_account_id {business_account_id}, using calendar year fallback")
                current_year = date.today().year
                period_start = date(current_year, 1, 1)
                period_end = date(current_year, 12, 31)
            
            # Count ALL campaigns that started in current license period (same as original logic)
            campaigns_this_period = LicenseService.get_campaigns_used_in_current_period(
                business_account_id, period_start, period_end
            )
            
            can_activate = campaigns_this_period < max_campaigns
            
            logger.debug(f"Campaign limit check for business_account_id {business_account_id}: "
                        f"{campaigns_this_period}/{max_campaigns} campaigns used, can_activate={can_activate}")
            
            return can_activate
            
        except Exception as e:
            logger.error(f"Failed to check campaign activation limit for business_account_id {business_account_id}: {e}")
            
            # Fallback to legacy method for safety
            try:
                business_account = BusinessAccount.query.get(business_account_id)
                if business_account:
                    return business_account.can_activate_campaign()
            except Exception as fallback_error:
                logger.error(f"Legacy fallback failed for campaign limit check: {fallback_error}")
            
            # Default to allowing campaigns if all checks fail (fail-safe behavior)
            logger.warning(f"All license checks failed for business_account_id {business_account_id}, defaulting to allow campaign")
            return True
    
    @staticmethod
    def get_campaigns_used_in_current_period(business_account_id: int, period_start: Optional[date] = None, period_end: Optional[date] = None) -> int:
        """
        Count campaigns used in the current license period.
        
        Args:
            business_account_id: Business account ID to check
            period_start: Start of period to check (defaults to current license period)
            period_end: End of period to check (defaults to current license period)
            
        Returns:
            int: Number of campaigns started in the period
        """
        try:
            # Get period dates if not provided
            if period_start is None or period_end is None:
                period_start, period_end = LicenseService.get_license_period(business_account_id)
                
                if not period_start or not period_end:
                    # Fallback to calendar year
                    current_year = date.today().year
                    period_start = date(current_year, 1, 1) 
                    period_end = date(current_year, 12, 31)
            
            # Count campaigns that started in this period (regardless of status)
            campaigns_count = Campaign.query.filter(
                Campaign.business_account_id == business_account_id,
                Campaign.start_date >= period_start,
                Campaign.start_date <= period_end
            ).count()
            
            logger.debug(f"Found {campaigns_count} campaigns for business_account_id {business_account_id} "
                        f"in period {period_start} to {period_end}")
            
            return campaigns_count
            
        except Exception as e:
            logger.error(f"Failed to count campaigns for business_account_id {business_account_id}: {e}")
            return 0
    
    # ==== USER AND PARTICIPANT LIMIT ENFORCEMENT ====
    
    @staticmethod
    def can_add_user(business_account_id: int) -> bool:
        """
        Check if business account can add another user based on current license limits.
        
        Args:
            business_account_id: Business account ID to check
            
        Returns:
            bool: True if account can add another user, False otherwise
        """
        try:
            # Get current license limits
            current_license = LicenseService.get_current_license(business_account_id)
            max_users = current_license.max_users if current_license else 5
            
            # Get current user count
            business_account = BusinessAccount.query.get(business_account_id)
            if not business_account:
                logger.warning(f"Business account {business_account_id} not found")
                return False
            
            current_users = business_account.current_users_count
            can_add = current_users < max_users
            
            logger.debug(f"User limit check for business_account_id {business_account_id}: "
                        f"{current_users}/{max_users} users, can_add={can_add}")
            
            return can_add
            
        except Exception as e:
            logger.error(f"Failed to check user limit for business_account_id {business_account_id}: {e}")
            return False
    
    @staticmethod
    def can_add_participants(business_account_id: int, campaign_id: int, additional_count: int) -> bool:
        """
        Check if campaign can add more participants based on current license limits.
        
        Args:
            business_account_id: Business account ID to check
            campaign_id: Campaign ID to check
            additional_count: Number of additional participants to add
            
        Returns:
            bool: True if campaign can add the participants, False otherwise
        """
        try:
            # Get current license limits
            current_license = LicenseService.get_current_license(business_account_id)
            max_participants = current_license.max_participants_per_campaign if current_license else 500
            
            # Get current participant count for this campaign
            from models import CampaignParticipant
            current_count = CampaignParticipant.query.filter_by(
                campaign_id=campaign_id,
                business_account_id=business_account_id
            ).count()
            
            can_add = (current_count + additional_count) <= max_participants
            
            logger.debug(f"Participant limit check for campaign {campaign_id}: "
                        f"{current_count}+{additional_count}/{max_participants} participants, can_add={can_add}")
            
            return can_add
            
        except Exception as e:
            logger.error(f"Failed to check participant limit for campaign {campaign_id}: {e}")
            return False
    
    # ==== LICENSE INFORMATION AND STATUS ====
    
    @staticmethod
    def get_license_info(business_account_id: int) -> Dict[str, Any]:
        """
        Get comprehensive license information for admin UI display.
        
        Replaces the license info logic from business_auth_routes.py with enhanced
        license_history table data and maintains backward compatibility.
        
        Args:
            business_account_id: Business account ID to get info for
            
        Returns:
            dict: Comprehensive license information including:
                - current_license: LicenseHistory object or None
                - license_type: Type of current license
                - license_status: Current status
                - license_start: License activation date
                - license_end: License expiration date
                - days_remaining: Days until expiration
                - days_since_expired: Days since expiration
                - campaigns_used: Campaigns used in current period
                - campaigns_limit: Maximum campaigns allowed
                - campaigns_remaining: Campaigns remaining
                - users_used: Current users count
                - users_limit: Maximum users allowed
                - users_remaining: Users remaining
                - can_activate_campaign: Whether new campaign can be activated
                - can_add_user: Whether new user can be added
                - expires_soon: Whether license expires within 30 days
        """
        try:
            # Get current license
            current_license = LicenseService.get_current_license(business_account_id)
            
            # Get business account for user count
            business_account = BusinessAccount.query.get(business_account_id)
            if not business_account:
                logger.warning(f"Business account {business_account_id} not found")
                return LicenseService._get_empty_license_info()
            
            # Initialize default values
            license_info = {
                'current_license': current_license,
                'license_type': 'trial',
                'license_status': 'trial',
                'license_start': None,
                'license_end': None,
                'days_remaining': 0,
                'days_since_expired': 0,
                'expires_soon': False,
                'campaigns_used': 0,
                'campaigns_limit': 4,
                'campaigns_remaining': 4,
                'users_used': business_account.current_users_count,
                'users_limit': 5,
                'users_remaining': max(0, 5 - business_account.current_users_count),
                'participants_limit': 500,
                'can_activate_campaign': True,
                'can_add_user': True
            }
            
            if current_license:
                # Update with actual license data
                license_info.update({
                    'license_type': current_license.license_type,
                    'license_status': current_license.status,
                    'license_start': current_license.activated_at.date() if hasattr(current_license.activated_at, 'date') else current_license.activated_at,
                    'license_end': current_license.expires_at.date() if hasattr(current_license.expires_at, 'date') else current_license.expires_at,
                    'days_remaining': current_license.days_remaining(),
                    'days_since_expired': current_license.days_since_expired(),
                    'campaigns_limit': current_license.max_campaigns_per_year,
                    'users_limit': current_license.max_users,
                    'participants_limit': current_license.max_participants_per_campaign,
                    'expires_soon': current_license.days_remaining() <= 30 and current_license.is_active()
                })
            else:
                # No current license - try to get period from legacy fields for backward compatibility
                period_start, period_end = LicenseService.get_license_period(business_account_id)
                if period_start and period_end:
                    license_info.update({
                        'license_start': period_start,
                        'license_end': period_end,
                        'license_status': business_account.license_status or 'trial'
                    })
                    
                    # Calculate days remaining for legacy license
                    today = date.today()
                    if period_end > today:
                        license_info['days_remaining'] = (period_end - today).days
                        license_info['expires_soon'] = license_info['days_remaining'] <= 30
                    else:
                        license_info['days_since_expired'] = (today - period_end).days
            
            # Calculate campaign usage
            campaigns_used = LicenseService.get_campaigns_used_in_current_period(business_account_id)
            license_info.update({
                'campaigns_used': campaigns_used,
                'campaigns_remaining': max(0, license_info['campaigns_limit'] - campaigns_used)
            })
            
            # Update capability checks
            license_info.update({
                'can_activate_campaign': LicenseService.can_activate_campaign(business_account_id),
                'can_add_user': LicenseService.can_add_user(business_account_id)
            })
            
            logger.debug(f"Generated license info for business_account_id {business_account_id}: "
                        f"type={license_info['license_type']}, status={license_info['license_status']}, "
                        f"campaigns={campaigns_used}/{license_info['campaigns_limit']}")
            
            return license_info
            
        except Exception as e:
            logger.error(f"Failed to get license info for business_account_id {business_account_id}: {e}")
            return LicenseService._get_empty_license_info()
    
    @staticmethod
    def _get_empty_license_info() -> Dict[str, Any]:
        """Get default/empty license info for error cases."""
        return {
            'current_license': None,
            'license_type': 'trial',
            'license_status': 'trial',
            'license_start': None,
            'license_end': None,
            'days_remaining': 0,
            'days_since_expired': 0,
            'expires_soon': False,
            'campaigns_used': 0,
            'campaigns_limit': 4,
            'campaigns_remaining': 4,
            'users_used': 0,
            'users_limit': 5,
            'users_remaining': 5,
            'participants_limit': 500,
            'can_activate_campaign': True,
            'can_add_user': True
        }
    
    # ==== LICENSE HISTORY AND AUDIT ====
    
    @staticmethod
    def get_license_history(business_account_id: int) -> List[LicenseHistory]:
        """
        Get complete license history for a business account.
        
        Args:
            business_account_id: Business account ID to get history for
            
        Returns:
            List[LicenseHistory]: All license records ordered by activation date (newest first)
        """
        try:
            return LicenseHistory.query.filter_by(
                business_account_id=business_account_id
            ).order_by(LicenseHistory.activated_at.desc()).all()
        except Exception as e:
            logger.error(f"Failed to get license history for business_account_id {business_account_id}: {e}")
            return []
    
    @staticmethod
    def get_license_usage_summary(business_account_id: int) -> Dict[str, Any]:
        """
        Get comprehensive license usage summary for reporting and analytics.
        
        Args:
            business_account_id: Business account ID to analyze
            
        Returns:
            dict: Usage summary including:
                - current_period_campaigns: Campaigns in current license period
                - historical_usage: Usage across all license periods
                - utilization_rates: Percentage utilization of limits
                - trend_analysis: Usage trends over time
        """
        try:
            # Get current license info
            license_info = LicenseService.get_license_info(business_account_id)
            
            # Get historical data
            license_history = LicenseService.get_license_history(business_account_id)
            
            # Calculate utilization rates
            campaign_utilization = (license_info['campaigns_used'] / license_info['campaigns_limit'] * 100) if license_info['campaigns_limit'] > 0 else 0
            user_utilization = (license_info['users_used'] / license_info['users_limit'] * 100) if license_info['users_limit'] > 0 else 0
            
            summary = {
                'business_account_id': business_account_id,
                'current_license': license_info,
                'campaign_utilization_pct': round(campaign_utilization, 1),
                'user_utilization_pct': round(user_utilization, 1),
                'total_license_periods': len(license_history),
                'license_history': [license.to_dict() for license in license_history],
                'generated_at': datetime.utcnow().isoformat()
            }
            
            logger.debug(f"Generated usage summary for business_account_id {business_account_id}: "
                        f"campaign_util={campaign_utilization:.1f}%, user_util={user_utilization:.1f}%")
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate usage summary for business_account_id {business_account_id}: {e}")
            return {'error': str(e), 'business_account_id': business_account_id}
    
    # ==== LICENSE VALIDATION AND HEALTH CHECKS ====
    
    @staticmethod
    def validate_license_integrity(business_account_id: int) -> Dict[str, Any]:
        """
        Validate license integrity and identify potential issues.
        
        Args:
            business_account_id: Business account ID to validate
            
        Returns:
            dict: Validation results including:
                - is_valid: Overall validation status
                - issues: List of identified issues
                - recommendations: Suggested actions
                - current_status: Current license status summary
        """
        validation_result = {
            'business_account_id': business_account_id,
            'is_valid': True,
            'issues': [],
            'recommendations': [],
            'current_status': None,
            'validated_at': datetime.utcnow().isoformat()
        }
        
        try:
            # Get current license
            current_license = LicenseService.get_current_license(business_account_id)
            business_account = BusinessAccount.query.get(business_account_id)
            
            if not business_account:
                validation_result['is_valid'] = False
                validation_result['issues'].append('Business account not found')
                return validation_result
            
            validation_result['current_status'] = LicenseService.get_license_info(business_account_id)
            
            # Check for missing current license
            if not current_license:
                validation_result['issues'].append('No active license found')
                validation_result['recommendations'].append('Create or activate a license for this account')
                
                # Check if migration is needed
                if business_account.license_activated_at or business_account.license_expires_at:
                    validation_result['recommendations'].append('Consider migrating legacy license data to license_history table')
            
            # Check for expired license
            if current_license and current_license.is_expired():
                validation_result['issues'].append('Current license is expired')
                validation_result['recommendations'].append('Renew license to maintain service')
            
            # Check for approaching expiration
            if current_license and current_license.days_remaining() <= 30 and current_license.days_remaining() > 0:
                validation_result['issues'].append(f'License expires in {current_license.days_remaining()} days')
                validation_result['recommendations'].append('Plan license renewal')
            
            # Check for overlapping licenses
            license_history = LicenseService.get_license_history(business_account_id)
            active_licenses = [l for l in license_history if l.status == 'active']
            if len(active_licenses) > 1:
                validation_result['issues'].append(f'Multiple active licenses found ({len(active_licenses)})')
                validation_result['recommendations'].append('Deactivate duplicate licenses')
            
            # Set overall validation status
            validation_result['is_valid'] = len(validation_result['issues']) == 0
            
            logger.debug(f"License validation for business_account_id {business_account_id}: "
                        f"valid={validation_result['is_valid']}, issues={len(validation_result['issues'])}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Failed to validate license integrity for business_account_id {business_account_id}: {e}")
            validation_result['is_valid'] = False
            validation_result['issues'].append(f'Validation error: {str(e)}')
            return validation_result
    
    # ==== UTILITY METHODS ====
    
    @staticmethod
    def create_trial_license(business_account_id: int, activated_at: Optional[datetime] = None, created_by: str = 'license_service') -> Optional[LicenseHistory]:
        """
        Create a new trial license for a business account.
        
        Args:
            business_account_id: Business account ID to create license for
            activated_at: License activation date (defaults to now)
            created_by: Who created the license (for audit trail)
            
        Returns:
            LicenseHistory: Created license record or None if failed
        """
        try:
            license_record = LicenseHistory.create_trial_license(
                business_account_id=business_account_id,
                activated_at=activated_at,
                created_by=created_by
            )
            
            db.session.add(license_record)
            db.session.commit()
            
            logger.info(f"Created trial license for business_account_id {business_account_id}")
            return license_record
            
        except Exception as e:
            logger.error(f"Failed to create trial license for business_account_id {business_account_id}: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def migrate_legacy_license(business_account_id: int, created_by: str = 'license_service_migration') -> Optional[LicenseHistory]:
        """
        Migrate legacy BusinessAccount license fields to license_history table.
        
        Args:
            business_account_id: Business account ID to migrate
            created_by: Who performed the migration (for audit trail)
            
        Returns:
            LicenseHistory: Migrated license record or None if failed
        """
        try:
            business_account = BusinessAccount.query.get(business_account_id)
            if not business_account:
                logger.warning(f"Business account {business_account_id} not found for migration")
                return None
            
            # Check if already has license history
            existing_license = LicenseService.get_current_license(business_account_id)
            if existing_license:
                logger.info(f"Business account {business_account_id} already has license history, skipping migration")
                return existing_license
            
            # Create migrated license record
            license_record = LicenseHistory.migrate_from_business_account(
                business_account=business_account,
                created_by=created_by
            )
            
            db.session.add(license_record)
            db.session.commit()
            
            logger.info(f"Migrated legacy license for business_account_id {business_account_id}")
            return license_record
            
        except Exception as e:
            logger.error(f"Failed to migrate legacy license for business_account_id {business_account_id}: {e}")
            db.session.rollback()
            return None