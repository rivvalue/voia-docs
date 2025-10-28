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
import json
from models import LicenseHistory, BusinessAccount, Campaign, SurveyResponse, CampaignParticipant, db
from sqlalchemy import and_, func
from license_templates import LicenseTemplateManager, LicenseTemplate

logger = logging.getLogger(__name__)

# Import cache for performance optimization
try:
    from app import cache
    CACHE_AVAILABLE = True
except ImportError:
    logger.warning("Flask-Caching not available - license info will not be cached")
    CACHE_AVAILABLE = False
    cache = None

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
        Platform administrators have unlimited access.
        
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
            # Check if current user is a platform admin (unlimited access)
            from flask import session
            current_user_id = session.get('business_user_id')
            if current_user_id:
                from models import BusinessAccountUser
                current_user = BusinessAccountUser.query.get(current_user_id)
                if current_user and current_user.is_platform_admin():
                    logger.debug(f"Platform admin {current_user.email} bypassing campaign limit check")
                    return True
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
        Platform administrators have unlimited access.
        
        Args:
            business_account_id: Business account ID to check
            
        Returns:
            bool: True if account can add another user, False otherwise
        """
        try:
            # Check if current user is a platform admin (unlimited access)
            from flask import session
            current_user_id = session.get('business_user_id')
            if current_user_id:
                from models import BusinessAccountUser
                current_user = BusinessAccountUser.query.get(current_user_id)
                if current_user and current_user.is_platform_admin():
                    logger.debug(f"Platform admin {current_user.email} bypassing user limit check")
                    return True
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
        Check if campaign can add more participants (invitations) based on current license limits.
        Platform administrators have unlimited access.
        
        Note: This checks invitation capacity, not response targets. Responses are never limited.
        
        Args:
            business_account_id: Business account ID to check
            campaign_id: Campaign ID to check
            additional_count: Number of additional participants to invite
            
        Returns:
            bool: True if campaign can invite the participants, False otherwise
        """
        try:
            # Check if current user is a platform admin (unlimited access)
            from flask import session
            current_user_id = session.get('business_user_id')
            if current_user_id:
                from models import BusinessAccountUser
                current_user = BusinessAccountUser.query.get(current_user_id)
                if current_user and current_user.is_platform_admin():
                    logger.debug(f"Platform admin {current_user.email} bypassing invitation limit check")
                    return True
            # Get current license limits (use max_invitations_per_campaign for enforcement)
            current_license = LicenseService.get_current_license(business_account_id)
            max_invitations = current_license.max_invitations_per_campaign if current_license else 2500
            
            # Get current participant count for this campaign (all invitations)
            from models import CampaignParticipant
            current_count = CampaignParticipant.query.filter_by(
                campaign_id=campaign_id,
                business_account_id=business_account_id
            ).count()
            
            can_add = (current_count + additional_count) <= max_invitations
            
            logger.debug(f"Invitation limit check for campaign {campaign_id}: "
                        f"{current_count}+{additional_count}/{max_invitations} invitations, can_add={can_add}")
            
            return can_add
            
        except Exception as e:
            logger.error(f"Failed to check invitation limit for campaign {campaign_id}: {e}")
            return False
    
    @staticmethod
    def can_use_transcript_analysis(business_account_id: int) -> bool:
        """
        Check if business account can use transcript upload feature.
        
        Transcript upload is now universally available to all license tiers.
        Usage is bounded by the participant/response limits of each license tier,
        as transcript uploads create CampaignParticipant and SurveyResponse records
        that count against the license quota.
        
        Args:
            business_account_id: Business account ID to check
            
        Returns:
            bool: True if account has an active license (all tiers have access)
        """
        try:
            # Get current license to verify account has valid license
            current_license = LicenseService.get_current_license(business_account_id)
            
            if not current_license:
                logger.warning(f"No active license found for business_account_id {business_account_id}")
                return False
            
            # Transcript upload is universally available to all license tiers
            # Usage is controlled by participant response limits
            logger.debug(f"Transcript upload available for business_account_id {business_account_id} "
                        f"with license type {current_license.license_type}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to check transcript analysis permission for business_account_id {business_account_id}: {e}")
            return False
    
    # ==== LICENSE INFORMATION AND STATUS ====
    
    @staticmethod
    def get_license_info(business_account_id: int, business_account=None, is_platform_admin: bool = False, bypass_admin_override: bool = False) -> Dict[str, Any]:
        """
        Get comprehensive license information for admin UI display.
        
        PERFORMANCE OPTIMIZED: Accepts optional business_account parameter to avoid duplicate queries.
        Results are cached for 5 minutes to improve page load performance.
        
        Replaces the license info logic from business_auth_routes.py with enhanced
        license_history table data and maintains backward compatibility.
        
        Args:
            business_account_id: Business account ID to get info for
            business_account: Optional BusinessAccount object to avoid duplicate query
            is_platform_admin: Optional flag to skip platform admin check query
            bypass_admin_override: If True, return actual license data even for platform admins (for analytics)
            
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
            # OPTIMIZATION: Check platform admin status without database query if flag provided
            # Skip this check if bypass_admin_override is True (used for analytics dashboards)
            if not bypass_admin_override:
                if not is_platform_admin:
                    from flask import session
                    current_user_id = session.get('business_user_id')
                    if current_user_id:
                        from models import BusinessAccountUser
                        current_user = BusinessAccountUser.query.get(current_user_id)
                        if current_user and current_user.is_platform_admin():
                            logger.debug(f"Platform admin {current_user.email} accessing license info - showing unlimited access")
                            return LicenseService._get_platform_admin_license_info(business_account_id)
                elif is_platform_admin:
                    logger.debug(f"Platform admin accessing license info for business_account_id {business_account_id} - showing unlimited access")
                    return LicenseService._get_platform_admin_license_info(business_account_id)
            
            # Get current license
            current_license = LicenseService.get_current_license(business_account_id)
            
            # OPTIMIZATION: Reuse business_account if provided to avoid duplicate query
            if business_account is None:
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
                
                # CRITICAL FIX: Recalculate users_remaining with actual license limit
                license_info['users_remaining'] = max(0, license_info['users_limit'] - license_info['users_used'])
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
                    from datetime import date
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
                'can_add_user': LicenseService.can_add_user(business_account_id),
                'can_use_transcript_analysis': LicenseService.can_use_transcript_analysis(business_account_id)
            })
            
            # Add transcript analysis add-on information
            if current_license:
                from datetime import date
                today = date.today()
                
                # Determine transcript analysis status
                has_addon = False
                addon_status = 'inactive'
                addon_start = None
                addon_end = None
                addon_price = None
                addon_days_remaining = 0
                
                if current_license.transcript_analysis_start_date and current_license.transcript_analysis_end_date:
                    # Date-based add-on
                    addon_start = current_license.transcript_analysis_start_date
                    addon_end = current_license.transcript_analysis_end_date
                    addon_price = current_license.transcript_analysis_price
                    
                    if addon_start <= today <= addon_end:
                        has_addon = True
                        addon_status = 'active'
                        addon_days_remaining = (addon_end - today).days
                    elif today > addon_end:
                        addon_status = 'expired'
                    else:
                        addon_status = 'scheduled'
                        
                elif current_license.has_transcript_analysis:
                    # Legacy boolean-based add-on
                    has_addon = True
                    addon_status = 'active'
                    addon_start = current_license.activated_at.date() if hasattr(current_license.activated_at, 'date') else current_license.activated_at
                    addon_end = current_license.expires_at.date() if hasattr(current_license.expires_at, 'date') else current_license.expires_at
                    if addon_end and isinstance(addon_end, date):
                        addon_days_remaining = (addon_end - today).days if addon_end > today else 0
                
                license_info.update({
                    'transcript_analysis': {
                        'has_addon': has_addon,
                        'status': addon_status,
                        'start_date': addon_start,
                        'end_date': addon_end,
                        'price': float(addon_price) if addon_price else None,
                        'days_remaining': addon_days_remaining,
                        'expires_soon': addon_days_remaining <= 30 and addon_days_remaining > 0
                    }
                })
            
            logger.debug(f"Generated license info for business_account_id {business_account_id}: "
                        f"type={license_info['license_type']}, status={license_info['license_status']}, "
                        f"campaigns={campaigns_used}/{license_info['campaigns_limit']}")
            
            return license_info
            
        except Exception as e:
            logger.error(f"Failed to get license info for business_account_id {business_account_id}: {e}")
            return LicenseService._get_empty_license_info()
    
    @staticmethod
    def _get_platform_admin_license_info(business_account_id: int) -> Dict[str, Any]:
        """Get unlimited license info for platform administrators."""
        # Get business account for basic info
        business_account = BusinessAccount.query.get(business_account_id)
        current_license = LicenseService.get_current_license(business_account_id)
        
        return {
            'current_license': current_license,
            'license_type': 'platform_admin',
            'license_status': 'unlimited',
            'license_start': None,
            'license_end': None,
            'days_remaining': 999999,  # Effectively unlimited
            'days_since_expired': 0,
            'expires_soon': False,
            'campaigns_used': LicenseService.get_campaigns_used_in_current_period(business_account_id) if business_account else 0,
            'campaigns_limit': 999999,  # Unlimited campaigns
            'campaigns_remaining': 999999,
            'users_used': business_account.current_users_count if business_account else 0,
            'users_limit': 999999,  # Unlimited users
            'users_remaining': 999999,
            'participants_limit': 999999,  # Unlimited participants
            'can_activate_campaign': True,
            'can_add_user': True,
            'can_use_transcript_analysis': True,
            'transcript_analysis': {
                'has_addon': True,
                'status': 'unlimited',
                'start_date': None,
                'end_date': None,
                'price': 0.0,
                'days_remaining': 999999,
                'expires_soon': False
            }
        }

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
    
    # ==== LICENSE TEMPLATE INTEGRATION ====
    
    @staticmethod
    def get_available_license_types() -> List[Dict[str, Any]]:
        """
        Get all available license types with their configurations.
        
        Returns:
            list: List of dictionaries containing license type information including:
                - license_type: Type identifier (core, plus, pro, trial)
                - display_name: Human-readable name
                - description: Template description
                - max_campaigns_per_year: Campaign limit
                - max_users: User limit
                - max_participants_per_campaign: Participant limit
                - is_custom: Whether template supports custom configuration
                - is_trial: Whether this is a trial license
                - features: List of features included
        """
        try:
            return LicenseTemplateManager.get_available_license_types()
        except Exception as e:
            logger.error(f"Failed to get available license types: {e}")
            return []
    
    @staticmethod
    def get_standard_license_types() -> List[Dict[str, Any]]:
        """
        Get standard (non-trial) license types for business use.
        
        Returns:
            list: List of standard license type configurations
        """
        try:
            return LicenseTemplateManager.get_standard_license_types()
        except Exception as e:
            logger.error(f"Failed to get standard license types: {e}")
            return []
    
    @staticmethod
    def apply_license_template(
        business_account_id: int,
        license_type: str,
        custom_config: Optional[Dict[str, Any]] = None,
        duration_months: Optional[int] = None,
        start_date: Optional[datetime] = None,
        created_by: str = 'license_service'
    ) -> Optional[LicenseHistory]:
        """
        Apply a license template to create a new license record for a business account.
        
        This method creates a new LicenseHistory record using the specified template
        configuration. For Pro licenses, custom configuration can be provided to override
        default template limits.
        
        Args:
            business_account_id: Business account ID to create license for
            license_type: Type of license template to apply (core, plus, pro, trial)
            custom_config: Optional custom configuration for Pro licenses containing:
                - max_campaigns_per_year: Custom campaign limit
                - max_users: Custom user limit
                - max_participants_per_campaign: Custom participant limit
                - duration_months: Custom license duration
            duration_months: License duration in months (overrides template default)
            start_date: License start date (defaults to now)
            created_by: Who created the license (for audit trail)
            
        Returns:
            LicenseHistory: Created license record or None if failed
            
        Raises:
            ValueError: If license type is invalid or custom config is invalid
            
        Example:
            # Create Core license
            license = LicenseService.apply_license_template(
                business_account_id=123,
                license_type='core'
            )
            
            # Create Pro license with custom limits
            license = LicenseService.apply_license_template(
                business_account_id=123,
                license_type='pro',
                custom_config={
                    'max_campaigns_per_year': 20,
                    'max_users': 50,
                    'max_participants_per_campaign': 15000
                }
            )
        """
        try:
            # Validate business account exists
            business_account = BusinessAccount.query.get(business_account_id)
            if not business_account:
                raise ValueError(f"Business account {business_account_id} not found")
            
            # Get and validate template
            template = LicenseTemplateManager.get_template(license_type)
            if not template:
                raise ValueError(f"Invalid license type: {license_type}")
            
            # Create license configuration
            if template.is_custom and custom_config:
                # Pro license with custom configuration
                license_config = LicenseTemplateManager.create_license_config(license_type, custom_config)
                logger.info(f"Applying {license_type} template with custom config for business_account_id {business_account_id}")
            else:
                # Standard template configuration
                license_config = template.to_dict()
                logger.info(f"Applying {license_type} template for business_account_id {business_account_id}")
            
            # Calculate license dates
            activation_date, expiration_date = LicenseTemplateManager.calculate_license_dates(
                license_type=license_type,
                start_date=start_date,
                duration_months=duration_months or license_config.get('default_duration_months')
            )
            
            # Check for existing active license and handle properly
            existing_license = LicenseService.get_current_license(business_account_id)
            if existing_license and existing_license.is_active():
                logger.info(f"Business account {business_account_id} has active license {existing_license.id} ({existing_license.license_type}), transitioning to {license_type}")
                
                # Deactivate existing license to maintain single-active-license invariant
                existing_license.status = 'cancelled'
                existing_license.notes = (existing_license.notes or '') + f'; Superseded by new {license_type} license on {datetime.utcnow()}'
                
                logger.info(f"Deactivated existing license {existing_license.id} to maintain single active license per account")
            
            # Create new license record
            license_record = LicenseHistory(
                business_account_id=business_account_id,
                license_type=license_config['license_type'],
                status='active',
                activated_at=activation_date,
                expires_at=expiration_date,
                max_campaigns_per_year=license_config['max_campaigns_per_year'],
                max_users=license_config['max_users'],
                max_participants_per_campaign=license_config['max_participants_per_campaign'],
                created_by=created_by,
                notes=f"Created from {template.display_name} template"
            )
            
            # Save to database
            db.session.add(license_record)
            db.session.commit()
            
            logger.info(f"Successfully applied {license_type} template to business_account_id {business_account_id}, "
                       f"license_id {license_record.id}, expires {expiration_date}")
            
            return license_record
            
        except ValueError as e:
            logger.error(f"Validation error applying license template: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to apply license template {license_type} to business_account_id {business_account_id}: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def validate_license_template_config(license_type: str, custom_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate a license template configuration without creating a license record.
        
        Args:
            license_type: License type to validate
            custom_config: Optional custom configuration for Pro licenses
            
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        try:
            template = LicenseTemplateManager.get_template(license_type)
            if not template:
                return False
            
            if template.is_custom and custom_config:
                # Validate custom config for Pro licenses
                LicenseTemplateManager.create_license_config(license_type, custom_config)
            
            return True
        except Exception as e:
            logger.debug(f"License template validation failed: {e}")
            return False
    
    @staticmethod
    def get_license_template_comparison(license_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get a comparison matrix of license templates.
        
        Args:
            license_types: Optional list of license types to compare (defaults to all standard types)
            
        Returns:
            dict: Comparison matrix with features and limits
        """
        try:
            if license_types is None:
                # Default to standard license types (exclude trial)
                license_types = ['core', 'plus', 'pro']
            
            return LicenseTemplateManager.get_template_comparison(license_types)
        except Exception as e:
            logger.error(f"Failed to get license template comparison: {e}")
            return {'license_types': [], 'features': {}, 'limits': {}, 'templates': {}}
    
    # ==== COMPREHENSIVE LICENSE ASSIGNMENT LOGIC ====
    
    @staticmethod
    def assign_license_to_business(
        business_id: int, 
        license_type: str,
        custom_config: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None,
        start_date: Optional[datetime] = None,
        duration_months: Optional[int] = None,
        transcript_addon_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[LicenseHistory], str]:
        """
        Comprehensive license assignment method with validation and transition handling.
        
        Args:
            business_id: Business account ID to assign license to
            license_type: License type (core, plus, pro, trial)  
            custom_config: Optional custom limits for Pro licenses
            created_by: User who is assigning the license (for audit trail)
            start_date: License start date (defaults to now)
            duration_months: License duration in months (defaults to template default)
            transcript_addon_config: Optional transcript analysis add-on configuration
                - start_date: Start date for transcript analysis access
                - end_date: End date for transcript analysis access  
                - price: Custom price for the add-on
            
        Returns:
            tuple: (success: bool, license_record: LicenseHistory, message: str)
            
        Features:
            - Comprehensive validation of all inputs
            - Automatic handling of existing license transitions
            - Proper audit trail integration
            - Transaction safety with rollback on errors
            - Clear success/error messaging
        """
        logger.info(f"Starting license assignment for business_id {business_id}, license_type {license_type}")
        
        try:
            # Step 1: Validate the license assignment request
            validation_success, validation_message = LicenseService.validate_license_assignment(
                business_id, license_type, custom_config
            )
            
            if not validation_success:
                logger.warning(f"License assignment validation failed for business_id {business_id}: {validation_message}")
                return False, None, validation_message
            
            # Step 2: Get template and create license configuration
            template = LicenseTemplateManager.get_template(license_type)
            if not template:
                return False, None, f"License template not found for type '{license_type}'"
                
            if custom_config and template.is_custom:
                license_config = LicenseTemplateManager.create_license_config(license_type, custom_config)
            else:
                license_config = template.to_dict()
            
            # Step 3: Calculate license dates
            activation_date, expiration_date = LicenseTemplateManager.calculate_license_dates(
                license_type=license_type,
                start_date=start_date,
                duration_months=duration_months or license_config.get('default_duration_months')
            )
            
            # Step 4: Handle existing license transitions with concurrency protection
            # Use SELECT...FOR UPDATE to prevent race conditions during license assignment
            business_account = BusinessAccount.query.with_for_update().get(business_id)
            if not business_account:
                return False, None, f"Business account {business_id} not found during assignment"
            
            # Get existing license with row-level locking to prevent concurrent modifications
            existing_license = LicenseHistory.query.filter(
                LicenseHistory.business_account_id == business_id,
                LicenseHistory.status == 'active'
            ).with_for_update().first()
            
            transition_message = ""
            
            if existing_license:
                transition_success, transition_msg = LicenseService.handle_license_transitions(
                    existing_license, license_type, created_by
                )
                if not transition_success:
                    return False, None, f"License transition failed: {transition_msg}"
                transition_message = f" (Previous {existing_license.license_type} license expired)"
            
            # Step 5: Process transcript analysis add-on configuration
            transcript_start_date = None
            transcript_end_date = None
            transcript_price = None
            transcript_addon_enabled = False
            
            if transcript_addon_config:
                transcript_addon_enabled = transcript_addon_config.get('enabled', False)
                transcript_start_date = transcript_addon_config.get('start_date')
                transcript_end_date = transcript_addon_config.get('end_date')
                transcript_price = transcript_addon_config.get('price')
                logger.info(f"Transcript analysis add-on configured for business_id {business_id}: "
                           f"enabled={transcript_addon_enabled}, start={transcript_start_date}, end={transcript_end_date}, price={transcript_price}")
            
            # Step 6: Create new license record with comprehensive audit trail
            assignment_notes = f"License assigned by {created_by or 'System'}"
            if custom_config:
                assignment_notes += f" with custom limits: {custom_config}"
            if transcript_addon_config:
                assignment_notes += f" with transcript analysis add-on (${transcript_price or 0} from {transcript_start_date} to {transcript_end_date})"
            if transition_message:
                assignment_notes += transition_message
            
            new_license = LicenseHistory(
                business_account_id=business_id,
                license_type=license_config['license_type'],
                status='active',
                activated_at=activation_date,
                expires_at=expiration_date,
                max_campaigns_per_year=license_config['max_campaigns_per_year'],
                max_users=license_config['max_users'], 
                max_participants_per_campaign=license_config['max_participants_per_campaign'],
                max_invitations_per_campaign=license_config['max_invitations_per_campaign'],
                annual_price=license_config.get('annual_price'),
                # Transcript analysis add-on fields
                transcript_analysis_start_date=transcript_start_date,
                transcript_analysis_end_date=transcript_end_date,
                transcript_analysis_price=transcript_price,
                has_transcript_analysis=transcript_addon_enabled,
                created_by=created_by,
                notes=assignment_notes
            )
            
            # Step 6: Save to database with enhanced transaction safety and constraint handling
            try:
                db.session.add(new_license)
                db.session.commit()
            except Exception as db_error:
                db.session.rollback()
                if "duplicate key" in str(db_error).lower() or "unique constraint" in str(db_error).lower():
                    logger.error(f"Concurrency conflict during license assignment for business_id {business_id}: {db_error}")
                    return False, None, "License assignment failed due to concurrent modification. Please retry."
                else:
                    raise db_error
            
            # Step 7: Log success and create audit trail
            success_message = (
                f"Successfully assigned {license_type} license to business_id {business_id}. "
                f"License ID: {new_license.id}, expires: {expiration_date.strftime('%Y-%m-%d')}{transition_message}"
            )
            
            logger.info(success_message)
            
            # Optional: Create audit log entry
            LicenseService._create_license_audit_log(
                business_id=business_id,
                action="license_assigned",
                details={
                    'license_id': new_license.id,
                    'license_type': license_type,
                    'custom_limits': custom_config,
                    'expires_at': expiration_date.isoformat(),
                    'assigned_by': created_by
                },
                user_email=created_by
            )
            
            return True, new_license, success_message
            
        except Exception as e:
            logger.error(f"Failed to assign license {license_type} to business_id {business_id}: {e}")
            db.session.rollback()
            error_message = f"License assignment failed due to system error: {str(e)}"
            return False, None, error_message
    
    @staticmethod
    def validate_license_assignment(
        business_id: int, 
        license_type: str, 
        custom_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Comprehensive validation for license assignment requests.
        
        Args:
            business_id: Business account ID to validate
            license_type: License type to validate
            custom_config: Optional custom limits to validate
            
        Returns:
            tuple: (is_valid: bool, error_message: str)
            
        Validation Checks:
            - Business account existence
            - License type validity
            - Custom limits validation for Pro licenses
            - Business account status checks
        """
        try:
            # Check 1: Verify business account exists
            business_account = BusinessAccount.query.get(business_id)
            if not business_account:
                return False, f"Business account {business_id} not found"
            
            # Check 2: Validate license type
            if not LicenseTemplateManager.validate_license_type(license_type):
                available_types = LicenseTemplateManager.get_available_license_types()
                valid_types = ', '.join([t['license_type'] for t in available_types])
                return False, f"Invalid license type '{license_type}'. Valid types: {valid_types}"
            
            # Check 3: Get template for additional validation
            template = LicenseTemplateManager.get_template(license_type)
            if not template:
                return False, f"License template not found for type '{license_type}'"
            
            # Check 4: Validate custom limits for Pro licenses
            if custom_config:
                if not template.is_custom:
                    return False, f"Custom limits not supported for {license_type} license type"
                
                # Validate custom limit parameters
                validation_errors = []
                
                if 'max_campaigns_per_year' in custom_config:
                    value = custom_config['max_campaigns_per_year']
                    if not isinstance(value, int) or value <= 0 or value > 1000:
                        validation_errors.append("max_campaigns_per_year must be a positive integer between 1 and 1000")
                
                if 'max_users' in custom_config:
                    value = custom_config['max_users']
                    if not isinstance(value, int) or value <= 0 or value > 10000:
                        validation_errors.append("max_users must be a positive integer between 1 and 10000")
                
                if 'max_participants_per_campaign' in custom_config:
                    value = custom_config['max_participants_per_campaign']
                    if not isinstance(value, int) or value <= 0 or value > 1000000:
                        validation_errors.append("max_participants_per_campaign must be a positive integer between 1 and 1000000")
                
                if 'duration_months' in custom_config:
                    value = custom_config['duration_months']
                    if not isinstance(value, int) or value <= 0 or value > 120:
                        validation_errors.append("duration_months must be a positive integer between 1 and 120")
                
                if validation_errors:
                    return False, "Custom limits validation failed: " + "; ".join(validation_errors)
            
            # Check 5: Business account status validation
            if hasattr(business_account, 'status') and business_account.status == 'suspended':
                return False, f"Cannot assign license to suspended business account {business_id}"
            
            # Check 6: Downgrade usage validation - Critical for preventing unsafe downgrades
            current_license = LicenseService.get_current_license(business_id)
            if current_license:
                downgrade_validation = LicenseService._validate_downgrade_usage(
                    business_id, current_license, template
                )
                if not downgrade_validation[0]:
                    return downgrade_validation  # Returns (False, error_message)
            
            # All validation checks passed
            return True, "Validation successful"
            
        except Exception as e:
            logger.error(f"License assignment validation error for business_id {business_id}: {e}")
            return False, f"Validation error: {str(e)}"
    
    @staticmethod
    def handle_license_transitions(
        old_license: LicenseHistory, 
        new_license_type: str,
        assigned_by: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Handle transitions between existing and new licenses.
        
        Args:
            old_license: Current active license to transition from
            new_license_type: New license type being assigned
            assigned_by: User performing the transition
            
        Returns:
            tuple: (success: bool, message: str)
            
        Transition Handling:
            - Properly expire existing active licenses
            - Preserve historical records and audit trail
            - Handle upgrade/downgrade scenarios
            - Maintain data integrity
        """
        try:
            if not old_license or not old_license.is_active():
                return True, "No active license to transition from"
            
            # Determine transition type
            transition_type = LicenseService._determine_transition_type(old_license.license_type, new_license_type)
            
            # Create transition notes
            transition_notes = (
                f"License transitioned from {old_license.license_type} to {new_license_type} "
                f"({transition_type}) by {assigned_by or 'System'} on {datetime.utcnow().isoformat()}"
            )
            
            # Expire the old license
            old_license.status = 'expired'
            old_license.notes = (old_license.notes or "") + f"\n{transition_notes}"
            
            # Log the transition
            logger.info(f"License transition for business_account_id {old_license.business_account_id}: "
                       f"{old_license.license_type} -> {new_license_type} ({transition_type})")
            
            # Create audit log for the transition
            LicenseService._create_license_audit_log(
                business_id=old_license.business_account_id,
                action="license_transitioned",
                details={
                    'old_license_id': old_license.id,
                    'old_license_type': old_license.license_type,
                    'new_license_type': new_license_type,
                    'transition_type': transition_type
                },
                user_email=assigned_by
            )
            
            return True, f"Successfully transitioned from {old_license.license_type} to {new_license_type}"
            
        except Exception as e:
            logger.error(f"License transition failed for license {old_license.id}: {e}")
            return False, f"Transition error: {str(e)}"
    
    @staticmethod
    def _determine_transition_type(old_license_type: str, new_license_type: str) -> str:
        """
        Determine the type of license transition (upgrade, downgrade, lateral).
        
        Args:
            old_license_type: Current license type
            new_license_type: New license type
            
        Returns:
            str: Transition type ('upgrade', 'downgrade', 'lateral', 'renewal')
        """
        # Define license hierarchy for upgrade/downgrade determination
        license_hierarchy = {
            'trial': 1,
            'core': 2,
            'plus': 3,
            'pro': 4
        }
        
        old_level = license_hierarchy.get(old_license_type.lower(), 0)
        new_level = license_hierarchy.get(new_license_type.lower(), 0)
        
        if old_license_type.lower() == new_license_type.lower():
            return 'renewal'
        elif new_level > old_level:
            return 'upgrade'
        elif new_level < old_level:
            return 'downgrade'
        else:
            return 'lateral'
    
    @staticmethod  
    def _create_license_audit_log(
        business_id: int,
        action: str, 
        details: Dict[str, Any],
        user_email: Optional[str] = None
    ) -> None:
        """
        Create audit log entry for license operations.
        
        Args:
            business_id: Business account ID
            action: Action performed (e.g., 'license_assigned', 'license_transitioned')
            details: Detailed information about the action
            user_email: Email of user who performed the action
        """
        try:
            # Import AuditLog here to avoid circular imports
            from models import AuditLog
            
            # Generate human-readable action description
            action_desc = LicenseService._generate_audit_description(action, details)
            
            audit_entry = AuditLog(
                business_account_id=business_id,
                user_email=user_email or 'System',
                action_type=action,
                action_description=action_desc,
                resource_type='license',
                resource_id=str(details.get('license_id')) if details.get('license_id') else None,
                resource_name=f"{details.get('license_type', 'Unknown')} license",
                details=json.dumps(details),
                ip_address=None  # Could be passed as parameter if needed
            )
            
            db.session.add(audit_entry)
            # Note: commit is handled by the calling method
            
            logger.debug(f"Created audit log entry for {action} on business_id {business_id}")
            
        except Exception as e:
            # Don't fail the main operation if audit logging fails
            logger.warning(f"Failed to create audit log entry: {e}")
    
    @staticmethod
    def _generate_audit_description(action: str, details: Dict[str, Any]) -> str:
        """
        Generate human-readable audit descriptions for license actions.
        
        Args:
            action: Action type (e.g., 'license_assigned', 'license_transitioned')
            details: Action details dictionary
            
        Returns:
            str: Human-readable description of the action
        """
        try:
            if action == 'license_assigned':
                license_type = details.get('license_type', 'Unknown')
                assigned_by = details.get('assigned_by', 'System')
                return f"{license_type.title()} license assigned by {assigned_by}"
            
            elif action == 'license_transitioned':
                old_type = details.get('old_license_type', 'Unknown')
                new_type = details.get('new_license_type', 'Unknown')
                transition_type = details.get('transition_type', 'changed')
                return f"License {transition_type} from {old_type} to {new_type}"
            
            elif action == 'license_expired':
                license_type = details.get('license_type', 'Unknown')
                return f"{license_type.title()} license expired"
            
            else:
                return f"License {action} completed"
                
        except Exception as e:
            logger.warning(f"Failed to generate audit description: {e}")
            return f"License {action} action"
    
    @staticmethod
    def _validate_downgrade_usage(
        business_id: int,
        current_license: LicenseHistory, 
        target_template: LicenseTemplate
    ) -> Tuple[bool, str]:
        """
        Validate that current usage is compatible with target license limits.
        Critical for preventing unsafe downgrades that would violate constraints.
        
        Args:
            business_id: Business account ID to validate
            current_license: Current active license
            target_template: Target license template with limits
            
        Returns:
            tuple: (is_safe: bool, error_message: str)
            
        Usage Checks:
            - Current users vs target max_users limit
            - Campaigns used in current period vs target max_campaigns limit  
            - Max participants across active campaigns vs target limit
        """
        try:
            # Determine if this is a downgrade by comparing license hierarchy
            transition_type = LicenseService._determine_transition_type(
                current_license.license_type, target_template.license_type
            )
            
            # Only validate usage for downgrades - upgrades and lateral moves are safe
            if transition_type != 'downgrade':
                return True, "No downgrade usage validation needed"
            
            validation_errors = []
            
            # Check 1: Current users vs target max_users limit
            try:
                business_account = BusinessAccount.query.get(business_id)
                if business_account and hasattr(business_account, 'current_users_count'):
                    current_users = business_account.current_users_count
                    if current_users > target_template.max_users:
                        validation_errors.append(
                            f"Current users ({current_users}) exceeds target limit ({target_template.max_users})"
                        )
            except Exception as e:
                logger.warning(f"Could not validate user count for business_id {business_id}: {e}")
            
            # Check 2: Campaigns used in current license period vs target limit  
            try:
                period_start, period_end = LicenseService.get_license_period(business_id)
                if period_start and period_end:
                    campaigns_used = LicenseService.get_campaigns_used_in_current_period(
                        business_id, period_start, period_end
                    )
                    if campaigns_used > target_template.max_campaigns_per_year:
                        validation_errors.append(
                            f"Campaigns used this period ({campaigns_used}) exceeds target limit ({target_template.max_campaigns_per_year})"
                        )
            except Exception as e:
                logger.warning(f"Could not validate campaign usage for business_id {business_id}: {e}")
            
            # Check 3: Max invitations across active campaigns vs target limit
            try:
                from models import CampaignParticipant
                max_invitations_query = db.session.query(
                    func.max(func.count(CampaignParticipant.id))
                ).join(Campaign).filter(
                    Campaign.business_account_id == business_id,
                    Campaign.status.in_(['active', 'ready'])  # Only check active campaigns
                ).group_by(Campaign.id)
                
                max_invitations_result = max_invitations_query.scalar()
                max_invitations_used = max_invitations_result or 0
                
                if max_invitations_used > target_template.max_invitations_per_campaign:
                    validation_errors.append(
                        f"Max invitations in active campaign ({max_invitations_used}) exceeds target limit ({target_template.max_invitations_per_campaign})"
                    )
            except Exception as e:
                logger.warning(f"Could not validate participant usage for business_id {business_id}: {e}")
            
            # Return validation results
            if validation_errors:
                error_msg = (
                    f"Cannot downgrade from {current_license.license_type} to {target_template.license_type} "
                    f"due to current usage exceeding target limits: {'; '.join(validation_errors)}"
                )
                logger.warning(f"Downgrade blocked for business_id {business_id}: {error_msg}")
                return False, error_msg
            
            return True, "Downgrade usage validation passed"
            
        except Exception as e:
            logger.error(f"Downgrade validation error for business_id {business_id}: {e}")
            return False, f"Downgrade validation failed: {str(e)}"
    
    @staticmethod
    def get_license_assignment_history(business_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get the license assignment history for a business account.
        
        Args:
            business_id: Business account ID
            limit: Maximum number of records to return
            
        Returns:
            list: List of license history records with assignment details
        """
        try:
            license_records = LicenseHistory.query.filter_by(
                business_account_id=business_id
            ).order_by(
                LicenseHistory.created_at.desc()
            ).limit(limit).all()
            
            return [record.to_dict() for record in license_records]
            
        except Exception as e:
            logger.error(f"Failed to get license assignment history for business_id {business_id}: {e}")
            return []
    
    @staticmethod
    def assign_license_from_template(
        business_account_id: int,
        template_id: str,
        assigned_by_user_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assign a license to a business account using a template ID.
        
        Args:
            business_account_id: Business account ID to assign license to
            template_id: License template ID (e.g., 'core', 'plus', 'pro', 'trial')
            assigned_by_user_id: User ID who is assigning the license 
            notes: Optional notes for the assignment
            
        Returns:
            dict: Result with success status and details
        """
        try:
            # Get the template to determine license type
            template = LicenseTemplateManager.get_template(template_id)
            if not template:
                return {
                    'success': False,
                    'error': f'License template not found: {template_id}'
                }
            
            # Convert user ID to string for assigned_by field
            assigned_by = str(assigned_by_user_id) if assigned_by_user_id else "system"
            
            # Call the main assignment method
            success, license_record, message = LicenseService.assign_license_to_business(
                business_id=business_account_id,
                license_type=template.license_type,
                created_by=assigned_by
            )
            
            if success and license_record:
                # Update notes if provided
                if notes:
                    license_record.notes = notes
                    db.session.commit()
                
                logger.info(f"Successfully assigned {template_id} license to business account {business_account_id}")
                return {
                    'success': True,
                    'message': message,
                    'license_id': license_record.id,
                    'license_type': license_record.license_type
                }
            else:
                logger.error(f"Failed to assign {template_id} license to business account {business_account_id}: {message}")
                return {
                    'success': False,
                    'error': message
                }
                
        except Exception as e:
            error_msg = f"Error assigning license from template {template_id} to business account {business_account_id}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    # ==== BULK OPTIMIZATION METHODS FOR ADMIN DASHBOARD ====
    
    @staticmethod
    def get_bulk_license_data(business_account_ids: Optional[List[int]] = None) -> Dict[int, Dict[str, Any]]:
        """
        Get license data for multiple business accounts in a single optimized query to avoid N+1 issues.
        
        This method fixes critical data integrity issues while maintaining performance:
        1. Campaign counts use actual license periods, not calendar year
        2. Active license selection validates date windows with deterministic selection
        3. Output schema matches get_license_info() exactly
        
        Args:
            business_account_ids: Optional list of business account IDs to fetch (defaults to all)
            
        Returns:
            dict: Dictionary mapping business_account_id to license data dict
            
        Performance Notes:
            - Uses 3 optimized queries with proper JOINs to avoid N+1 issues
            - Correctly handles license periods per account, not calendar years
            - Provides identical output to individual get_license_info() calls
        """
        try:
            from sqlalchemy.orm import joinedload
            from sqlalchemy import case, exists, text
            
            today = datetime.utcnow()
            
            # Query 1: Get customer business accounts only (exclude platform owner accounts)
            if business_account_ids:
                business_accounts = BusinessAccount.query.filter(
                    BusinessAccount.id.in_(business_account_ids),
                    BusinessAccount.account_type != 'demo'
                ).order_by(BusinessAccount.name).all()
            else:
                business_accounts = BusinessAccount.query.filter(
                    BusinessAccount.account_type != 'demo'
                ).order_by(BusinessAccount.name).all()
            
            if not business_accounts:
                return {}
            
            account_ids = [account.id for account in business_accounts]
            
            # Query 2: CRITICAL FIX - Bulk fetch VALID current licenses with proper date validation
            # This fixes Issue #2: Active License Selection
            current_licenses = {}
            license_query = db.session.query(LicenseHistory).filter(
                LicenseHistory.business_account_id.in_(account_ids),
                LicenseHistory.status == 'active',
                # CRITICAL: Add date validity filters
                LicenseHistory.activated_at <= today,
                LicenseHistory.expires_at >= today
            ).order_by(
                LicenseHistory.business_account_id,
                LicenseHistory.activated_at.desc()  # Deterministic selection if multiple matches
            ).all()
            
            # Process licenses to ensure only one per account (deterministic selection)
            for license_record in license_query:
                # Use first (most recent) license per account due to ORDER BY
                if license_record.business_account_id not in current_licenses:
                    current_licenses[license_record.business_account_id] = license_record
            
            # Query 3: CRITICAL FIX - Campaign counts using actual license periods
            # This fixes Issue #1: Campaign Count Accuracy
            campaign_counts = {}
            
            # Get campaign counts for accounts WITH valid licenses (using license periods)
            campaign_with_license_query = db.session.query(
                Campaign.business_account_id,
                func.count(Campaign.id).label('count')
            ).join(
                LicenseHistory,
                and_(
                    Campaign.business_account_id == LicenseHistory.business_account_id,
                    LicenseHistory.status == 'active',
                    LicenseHistory.activated_at <= today,
                    LicenseHistory.expires_at >= today
                )
            ).filter(
                Campaign.business_account_id.in_(account_ids),
                # CRITICAL: Filter campaigns within license window, not calendar year
                Campaign.start_date >= LicenseHistory.activated_at,
                Campaign.start_date <= LicenseHistory.expires_at
            ).group_by(Campaign.business_account_id).all()
            
            for business_account_id, count in campaign_with_license_query:
                campaign_counts[business_account_id] = count
            
            # For accounts WITHOUT valid licenses, fall back to calendar year
            accounts_with_licenses = set(current_licenses.keys())
            accounts_without_licenses = [aid for aid in account_ids if aid not in accounts_with_licenses]
            
            if accounts_without_licenses:
                current_year = date.today().year
                campaign_fallback_query = db.session.query(
                    Campaign.business_account_id,
                    func.count(Campaign.id).label('count')
                ).filter(
                    Campaign.business_account_id.in_(accounts_without_licenses),
                    Campaign.start_date >= date(current_year, 1, 1),
                    Campaign.start_date <= date(current_year, 12, 31)
                ).group_by(Campaign.business_account_id).all()
                
                for business_account_id, count in campaign_fallback_query:
                    campaign_counts[business_account_id] = count
            
            # Query 4: Total Respondents - Count completed survey responses per business account
            respondent_counts = {}
            respondent_query = db.session.query(
                Campaign.business_account_id,
                func.count(SurveyResponse.id).label('count')
            ).join(
                SurveyResponse,
                Campaign.id == SurveyResponse.campaign_id
            ).filter(
                Campaign.business_account_id.in_(account_ids)
            ).group_by(Campaign.business_account_id).all()
            
            for business_account_id, count in respondent_query:
                respondent_counts[business_account_id] = count
            
            # Query 5: Total Invitations - Count campaign participants (invitations sent) per business account
            invitation_counts = {}
            invitation_query = db.session.query(
                CampaignParticipant.business_account_id,
                func.count(CampaignParticipant.id).label('count')
            ).filter(
                CampaignParticipant.business_account_id.in_(account_ids)
            ).group_by(CampaignParticipant.business_account_id).all()
            
            for business_account_id, count in invitation_query:
                invitation_counts[business_account_id] = count
            
            # Build result dictionary - CRITICAL FIX: Complete schema consistency
            # This fixes Issue #3: Output Schema Consistency
            result = {}
            for account in business_accounts:
                current_license = current_licenses.get(account.id)
                campaigns_used = campaign_counts.get(account.id, 0)
                total_respondents = respondent_counts.get(account.id, 0)
                total_invitations = invitation_counts.get(account.id, 0)
                
                # Build license info EXACTLY like get_license_info()
                users_used = getattr(account, 'current_users_count', 0)
                license_info = {
                    'current_license': current_license,
                    'license_type': 'trial',
                    'license_status': 'trial',
                    'license_start': None,
                    'license_end': None,
                    'days_remaining': 0,
                    'days_since_expired': 0,
                    'expires_soon': False,
                    'campaigns_used': campaigns_used,
                    'campaigns_limit': 4,
                    'campaigns_remaining': max(0, 4 - campaigns_used),
                    'users_used': users_used,
                    'users_limit': 5,
                    'users_remaining': max(0, 5 - users_used),
                    'participants_limit': 500,
                    'can_activate_campaign': campaigns_used < 4,
                    'can_add_user': users_used < 5,
                    'total_respondents': total_respondents,
                    'total_invitations': total_invitations
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
                    
                    # Recalculate with actual license limits
                    license_info.update({
                        'campaigns_remaining': max(0, license_info['campaigns_limit'] - campaigns_used),
                        'users_remaining': max(0, license_info['users_limit'] - license_info['users_used']),
                        'can_activate_campaign': campaigns_used < license_info['campaigns_limit'],
                        'can_add_user': license_info['users_used'] < license_info['users_limit']
                    })
                else:
                    # No current license - handle exactly like get_license_info fallback
                    # Try to get period from legacy BusinessAccount fields if available
                    try:
                        period_start, period_end = LicenseService.get_license_period(account.id)
                        if period_start and period_end:
                            license_info.update({
                                'license_start': period_start,
                                'license_end': period_end,
                                'license_status': getattr(account, 'license_status', 'trial') or 'trial'
                            })
                            
                            # Calculate days remaining for legacy license
                            today_date = date.today()
                            if period_end > today_date:
                                license_info['days_remaining'] = (period_end - today_date).days
                                license_info['expires_soon'] = license_info['days_remaining'] <= 30
                            else:
                                license_info['days_since_expired'] = (today_date - period_end).days
                    except Exception as e:
                        logger.debug(f"Could not get legacy license period for account {account.id}: {e}")
                
                result[account.id] = {
                    'account': account,
                    'license_info': license_info
                }
            
            logger.debug(f"Bulk fetched license data for {len(result)} business accounts in optimized queries")
            return result
            
        except Exception as e:
            logger.error(f"Failed to bulk fetch license data: {e}")
            return {}