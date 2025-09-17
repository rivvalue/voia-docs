"""
License Template System for VOÏ Voice of Insight
Author: System Integration Agent
Created: September 17, 2025

This module provides a standardized license template system for creating and managing
different license types (Core, Plus, Pro) with predefined configurations and validation.

The template system integrates with the LicenseHistory model to provide:
- Standardized license configurations
- Validation of license parameters
- Support for custom Pro configurations
- Easy application of templates to create license records
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import calendar

logger = logging.getLogger(__name__)

def add_months(start_date: datetime, months: int) -> datetime:
    """
    Safely add months to a datetime, handling month-end rollover cases.
    
    This function handles edge cases like:
    - Jan 31 + 1 month = Feb 28 (or Feb 29 in leap years)
    - Mar 31 + 1 month = Apr 30
    - Dec 31 + 1 month = Jan 31 (next year)
    
    Args:
        start_date: The starting datetime
        months: Number of months to add (can be negative)
        
    Returns:
        datetime: New datetime with months added safely
        
    Examples:
        >>> add_months(datetime(2025, 1, 31), 1)  # Jan 31 -> Feb 28
        datetime(2025, 2, 28, 0, 0)
        >>> add_months(datetime(2025, 3, 31), 1)  # Mar 31 -> Apr 30
        datetime(2025, 4, 30, 0, 0)
        >>> add_months(datetime(2024, 1, 31), 1)  # Jan 31 -> Feb 29 (leap year)
        datetime(2024, 2, 29, 0, 0)
    """
    if months == 0:
        return start_date
    
    # Calculate target year and month
    total_months = start_date.month + months
    target_year = start_date.year + (total_months - 1) // 12
    target_month = ((total_months - 1) % 12) + 1
    
    # Get the last day of the target month
    last_day_of_target_month = calendar.monthrange(target_year, target_month)[1]
    
    # Clamp the day to the valid range for the target month
    target_day = min(start_date.day, last_day_of_target_month)
    
    # Create the new datetime with the same time components
    return start_date.replace(
        year=target_year,
        month=target_month,
        day=target_day
    )

@dataclass
class LicenseTemplate:
    """
    License template class defining the structure and limits for different license types.
    
    This class provides a standardized way to define license configurations that can be
    applied to create LicenseHistory records with consistent parameters.
    """
    
    # Template Identity
    license_type: str
    display_name: str
    description: str
    
    # License Limits
    max_campaigns_per_year: int
    max_users: int
    max_participants_per_campaign: int
    
    # Template Properties
    is_custom: bool = False
    is_trial: bool = False
    default_duration_months: int = 12
    
    # Additional Features (for future expansion)
    features: Optional[List[str]] = None
    
    def __post_init__(self):
        """Validate template parameters after initialization"""
        if self.features is None:
            self.features = []
        
        # Validate required fields
        if not self.license_type:
            raise ValueError("license_type is required")
        if not self.display_name:
            raise ValueError("display_name is required")
        
        # Validate limits are positive
        if self.max_campaigns_per_year <= 0:
            raise ValueError("max_campaigns_per_year must be positive")
        if self.max_users <= 0:
            raise ValueError("max_users must be positive")
        if self.max_participants_per_campaign <= 0:
            raise ValueError("max_participants_per_campaign must be positive")
        if self.default_duration_months <= 0:
            raise ValueError("default_duration_months must be positive")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary for serialization"""
        return {
            'license_type': self.license_type,
            'display_name': self.display_name,
            'description': self.description,
            'max_campaigns_per_year': self.max_campaigns_per_year,
            'max_users': self.max_users,
            'max_participants_per_campaign': self.max_participants_per_campaign,
            'is_custom': self.is_custom,
            'is_trial': self.is_trial,
            'default_duration_months': self.default_duration_months,
            'features': self.features or []
        }
    
    def validate_custom_config(self, custom_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and merge custom configuration for Pro licenses.
        
        Args:
            custom_config: Dictionary of custom parameters
            
        Returns:
            dict: Validated and merged configuration
            
        Raises:
            ValueError: If custom configuration is invalid
        """
        if not self.is_custom:
            raise ValueError(f"Template {self.license_type} does not support custom configuration")
        
        # Start with template defaults
        config = self.to_dict()
        
        # Validate and apply custom parameters
        if 'max_campaigns_per_year' in custom_config:
            if not isinstance(custom_config['max_campaigns_per_year'], int) or custom_config['max_campaigns_per_year'] <= 0:
                raise ValueError("max_campaigns_per_year must be a positive integer")
            config['max_campaigns_per_year'] = custom_config['max_campaigns_per_year']
        
        if 'max_users' in custom_config:
            if not isinstance(custom_config['max_users'], int) or custom_config['max_users'] <= 0:
                raise ValueError("max_users must be a positive integer")
            config['max_users'] = custom_config['max_users']
        
        if 'max_participants_per_campaign' in custom_config:
            if not isinstance(custom_config['max_participants_per_campaign'], int) or custom_config['max_participants_per_campaign'] <= 0:
                raise ValueError("max_participants_per_campaign must be a positive integer")
            config['max_participants_per_campaign'] = custom_config['max_participants_per_campaign']
        
        if 'duration_months' in custom_config:
            if not isinstance(custom_config['duration_months'], int) or custom_config['duration_months'] <= 0:
                raise ValueError("duration_months must be a positive integer")
            config['default_duration_months'] = custom_config['duration_months']
        
        return config


class LicenseTemplateManager:
    """
    Manager class for license templates providing access to predefined templates
    and template-related operations.
    """
    
    # Predefined License Templates
    CORE_TEMPLATE = LicenseTemplate(
        license_type='core',
        display_name='Core',
        description='Basic license for small teams with essential features',
        max_campaigns_per_year=4,
        max_users=5,
        max_participants_per_campaign=200,
        default_duration_months=12,
        features=['Basic Analytics', 'Email Support', 'Standard Templates']
    )
    
    PLUS_TEMPLATE = LicenseTemplate(
        license_type='plus',
        display_name='Plus',
        description='Enhanced license for growing teams with advanced features',
        max_campaigns_per_year=4,
        max_users=10,
        max_participants_per_campaign=2000,
        default_duration_months=12,
        features=['Advanced Analytics', 'Priority Support', 'Custom Templates', 'API Access']
    )
    
    PRO_TEMPLATE = LicenseTemplate(
        license_type='pro',
        display_name='Pro',
        description='Fully customizable license for enterprise teams',
        max_campaigns_per_year=12,  # Default for Pro, but customizable
        max_users=25,  # Default for Pro, but customizable
        max_participants_per_campaign=10000,  # Default for Pro, but customizable
        is_custom=True,
        default_duration_months=12,
        features=['Custom Analytics', 'Dedicated Support', 'White Label', 'Custom Integrations', 'SLA Guarantee']
    )
    
    TRIAL_TEMPLATE = LicenseTemplate(
        license_type='trial',
        display_name='Trial',
        description='Trial license for evaluation purposes',
        max_campaigns_per_year=1,
        max_users=2,
        max_participants_per_campaign=50,
        is_trial=True,
        default_duration_months=1,
        features=['Basic Features', 'Limited Support']
    )
    
    # Template Registry
    _templates = {
        'core': CORE_TEMPLATE,
        'plus': PLUS_TEMPLATE,
        'pro': PRO_TEMPLATE,
        'trial': TRIAL_TEMPLATE
    }
    
    @classmethod
    def get_template(cls, license_type: str) -> Optional[LicenseTemplate]:
        """
        Get a license template by type.
        
        Args:
            license_type: Type of license template to retrieve
            
        Returns:
            LicenseTemplate: Template object or None if not found
        """
        return cls._templates.get(license_type.lower())
    
    @classmethod
    def get_available_license_types(cls) -> List[Dict[str, Any]]:
        """
        Get list of all available license types with their descriptions.
        
        Returns:
            list: List of dictionaries containing license type information
        """
        return [template.to_dict() for template in cls._templates.values()]
    
    @classmethod
    def get_standard_license_types(cls) -> List[Dict[str, Any]]:
        """
        Get list of standard (non-trial) license types.
        
        Returns:
            list: List of dictionaries containing standard license type information
        """
        return [
            template.to_dict() 
            for template in cls._templates.values() 
            if not template.is_trial
        ]
    
    @classmethod
    def validate_license_type(cls, license_type: str) -> bool:
        """
        Validate if a license type exists.
        
        Args:
            license_type: License type to validate
            
        Returns:
            bool: True if license type exists, False otherwise
        """
        return license_type.lower() in cls._templates
    
    @classmethod
    def create_license_config(cls, license_type: str, custom_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a complete license configuration from template and custom parameters.
        
        Args:
            license_type: Type of license to create
            custom_config: Optional custom configuration for Pro licenses
            
        Returns:
            dict: Complete license configuration
            
        Raises:
            ValueError: If license type is invalid or custom config is invalid
        """
        template = cls.get_template(license_type)
        if not template:
            raise ValueError(f"Invalid license type: {license_type}")
        
        # For Pro licenses with custom config, validate and merge
        if template.is_custom and custom_config:
            return template.validate_custom_config(custom_config)
        
        # For standard templates, return as-is
        return template.to_dict()
    
    @classmethod
    def calculate_license_dates(cls, license_type: str, start_date: Optional[datetime] = None, duration_months: Optional[int] = None) -> tuple[datetime, datetime]:
        """
        Calculate license activation and expiration dates.
        
        Args:
            license_type: Type of license
            start_date: License start date (defaults to now)
            duration_months: License duration in months (defaults to template default)
            
        Returns:
            tuple: (activation_date, expiration_date)
            
        Raises:
            ValueError: If license type is invalid
        """
        template = cls.get_template(license_type)
        if not template:
            raise ValueError(f"Invalid license type: {license_type}")
        
        if start_date is None:
            start_date = datetime.utcnow()
        
        if duration_months is None:
            duration_months = template.default_duration_months
        
        # Calculate expiration date using safe month addition
        expiration_date = add_months(start_date, duration_months)
        
        return start_date, expiration_date
    
    @classmethod
    def get_template_comparison(cls, license_types: List[str]) -> Dict[str, Any]:
        """
        Get a comparison matrix of multiple license templates.
        
        Args:
            license_types: List of license types to compare
            
        Returns:
            dict: Comparison matrix with features and limits
        """
        comparison = {
            'license_types': license_types,
            'features': {},
            'limits': {},
            'templates': {}
        }
        
        # Collect all features across templates
        all_features = set()
        templates = {}
        
        for license_type in license_types:
            template = cls.get_template(license_type)
            if template:
                templates[license_type] = template.to_dict()
                all_features.update(template.features or [])
        
        # Build feature matrix
        for feature in sorted(all_features):
            comparison['features'][feature] = {}
            for license_type in license_types:
                template = cls.get_template(license_type)
                has_feature = template and feature in (template.features or [])
                comparison['features'][feature][license_type] = has_feature
        
        # Build limits comparison
        limit_fields = ['max_campaigns_per_year', 'max_users', 'max_participants_per_campaign']
        for field in limit_fields:
            comparison['limits'][field] = {}
            for license_type in license_types:
                template = cls.get_template(license_type)
                value = getattr(template, field, 0) if template else 0
                comparison['limits'][field][license_type] = value
        
        comparison['templates'] = templates
        
        return comparison


# Convenience functions for easy access
def get_core_template() -> LicenseTemplate:
    """Get Core license template"""
    return LicenseTemplateManager.CORE_TEMPLATE

def get_plus_template() -> LicenseTemplate:
    """Get Plus license template"""
    return LicenseTemplateManager.PLUS_TEMPLATE

def get_pro_template() -> LicenseTemplate:
    """Get Pro license template"""
    return LicenseTemplateManager.PRO_TEMPLATE

def get_trial_template() -> LicenseTemplate:
    """Get Trial license template"""
    return LicenseTemplateManager.TRIAL_TEMPLATE