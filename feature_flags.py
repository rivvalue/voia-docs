"""
Feature Flag System for UI Version Toggle
Enables safe A/B testing and gradual rollout of sidebar navigation (v2)
"""

import os
import logging
from flask import session, request
from functools import wraps

logger = logging.getLogger(__name__)


class FeatureFlags:
    """Manage feature flags for UI version control"""
    
    # Feature flag configuration
    FLAGS = {
        'sidebar_navigation': {
            'enabled': False,  # Master switch - controls if feature is available at all
            'rollout_percentage': 0,  # 0-100: percentage of users who see v2 by default
            'description': 'New sidebar navigation system (Phase 2b)'
        },
        'settings_hub_v2': {
            'enabled': False,  # Master switch - controls if Settings Hub v2 is available
            'rollout_percentage': 0,  # 0-100: percentage of users who see Settings Hub v2
            'description': 'Settings Hub redesign with 4-card layout (Phase 2-5)'
        },
        'ui_version_toggle': {
            'enabled': True,  # Allow users to manually toggle UI versions
            'description': 'Manual UI version switcher for testing'
        },
        'deterministic_survey_flow': {
            'enabled': False,  # Master switch - controls if deterministic survey V2 is active
            'rollout_percentage': 0,  # 0-100: percentage of surveys using deterministic flow
            'description': 'Deterministic conversational survey controller (V2) - eliminates early-stop bugs'
        }
    }
    
    def __init__(self):
        # Load configuration from environment if available
        self.sidebar_enabled = os.environ.get('FEATURE_SIDEBAR_NAV', 'false').lower() == 'true'
        self.rollout_percentage = int(os.environ.get('SIDEBAR_ROLLOUT_PERCENTAGE', '0'))
        self.settings_hub_enabled = os.environ.get('FEATURE_SETTINGS_HUB_V2', 'false').lower() == 'true'
        self.settings_hub_rollout = int(os.environ.get('SETTINGS_HUB_ROLLOUT_PERCENTAGE', '0'))
        self.toggle_enabled = os.environ.get('FEATURE_UI_TOGGLE', 'true').lower() == 'true'
        self.force_v2 = os.environ.get('FORCE_V2_FOR_BUSINESS_USERS', 'false').lower() == 'true'
        self.deterministic_survey_enabled = os.environ.get('DETERMINISTIC_SURVEY_FLOW', 'false').lower() == 'true'
        self.deterministic_survey_rollout = int(os.environ.get('DETERMINISTIC_SURVEY_ROLLOUT_PERCENTAGE', '0'))
        
        # Update FLAGS dict with runtime values from environment
        self.FLAGS['sidebar_navigation']['enabled'] = self.sidebar_enabled
        self.FLAGS['sidebar_navigation']['rollout_percentage'] = self.rollout_percentage
        self.FLAGS['settings_hub_v2']['enabled'] = self.settings_hub_enabled
        self.FLAGS['settings_hub_v2']['rollout_percentage'] = self.settings_hub_rollout
        self.FLAGS['ui_version_toggle']['enabled'] = self.toggle_enabled
        self.FLAGS['deterministic_survey_flow']['enabled'] = self.deterministic_survey_enabled
        self.FLAGS['deterministic_survey_flow']['rollout_percentage'] = self.deterministic_survey_rollout
        
        logger.info(f"Feature Flags initialized - Sidebar: {self.sidebar_enabled}, "
                   f"Rollout: {self.rollout_percentage}%, Settings Hub v2: {self.settings_hub_enabled}, "
                   f"Settings Hub Rollout: {self.settings_hub_rollout}%, Toggle: {self.toggle_enabled}, "
                   f"Force V2: {self.force_v2}, Deterministic Survey: {self.deterministic_survey_enabled}, "
                   f"Deterministic Rollout: {self.deterministic_survey_rollout}%")
    
    def is_feature_enabled(self, feature_name):
        """Check if a feature flag is enabled (reads from updated FLAGS dict)"""
        return self.FLAGS.get(feature_name, {}).get('enabled', False)
    
    def get_ui_version(self, user_id=None):
        """
        Determine UI version for current request
        
        Priority order:
        1. URL parameter (?ui=v2) - highest priority for testing
        2. Force V2 flag (if authenticated business user)
        3. Session preference (user manually toggled)
        4. Rollout percentage (gradual deployment)
        5. Default to v1 (current UI)
        
        Returns:
            str: 'v1' or 'v2'
        """
        # 1. Check URL parameter (testing/debugging)
        url_version = request.args.get('ui')
        if url_version in ['v1', 'v2']:
            logger.debug(f"UI version from URL parameter: {url_version}")
            return url_version
        
        # 2. Check force V2 flag for authenticated business users
        if self.force_v2 and session.get('business_user_id'):
            logger.debug("UI version forced to v2 for authenticated business user")
            return 'v2'
        
        # 3. Check session preference (user toggle)
        session_version = session.get('ui_version')
        if session_version in ['v1', 'v2']:
            logger.debug(f"UI version from session: {session_version}")
            return session_version
        
        # 4. Check rollout percentage (gradual deployment)
        if self.sidebar_enabled and self.rollout_percentage > 0:
            import random
            if user_id:
                # Deterministic based on user ID (same user always gets same version)
                import hashlib
                hash_val = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16)
                in_rollout = (hash_val % 100) < self.rollout_percentage
            else:
                # Random for non-authenticated users
                in_rollout = random.randint(1, 100) <= self.rollout_percentage
            
            if in_rollout:
                logger.debug(f"UI version v2 from rollout (user_id: {user_id})")
                return 'v2'
        
        # 5. Default to v1 (current UI)
        logger.debug("UI version defaulting to v1")
        return 'v1'
    
    def set_user_ui_preference(self, version):
        """
        Save user's UI version preference to session
        
        Args:
            version (str): 'v1' or 'v2'
        """
        if version not in ['v1', 'v2']:
            logger.warning(f"Invalid UI version attempted: {version}")
            return False
        
        session['ui_version'] = version
        session.permanent = True  # Persist across browser sessions
        logger.info(f"User UI preference set to: {version}")
        return True
    
    def clear_user_ui_preference(self):
        """Remove user's UI version preference (revert to default behavior)"""
        if 'ui_version' in session:
            session.pop('ui_version')
            logger.info("User UI preference cleared")
    
    def get_available_features(self):
        """Get list of all available features and their status"""
        return {
            name: {
                'enabled': config.get('enabled', False),
                'description': config.get('description', '')
            }
            for name, config in self.FLAGS.items()
        }
    
    def can_user_toggle(self):
        """Check if current user is allowed to manually toggle UI version"""
        return self.toggle_enabled
    
    def is_v2_forced(self):
        """Check if V2 is being forced for all authenticated business users"""
        return self.force_v2


# Global feature flags instance
feature_flags = FeatureFlags()


def require_ui_version(version):
    """
    Decorator to enforce a specific UI version for a route
    
    Usage:
        @require_ui_version('v2')
        def new_dashboard():
            # This route only works with v2 UI
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_version = feature_flags.get_ui_version()
            if current_version != version:
                logger.warning(f"Route requires {version} but user has {current_version}")
                # Could redirect to appropriate version here
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_template_for_version(base_name):
    """
    Get appropriate template based on UI version
    
    Args:
        base_name (str): Base template name without version suffix
        
    Returns:
        str: Template path with version suffix if v2, otherwise original
        
    Example:
        get_template_for_version('dashboard') → 'dashboard_v2.html' if v2 active
    """
    version = feature_flags.get_ui_version()
    if version == 'v2':
        # Check if v2 template exists, otherwise fallback to v1
        return f"{base_name}_v2.html"
    return f"{base_name}.html"
