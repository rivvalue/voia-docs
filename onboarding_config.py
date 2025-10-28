"""
Onboarding Configuration System
Defines mandatory onboarding flows for different license types
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Callable
import logging

logger = logging.getLogger(__name__)


@dataclass
class OnboardingStep:
    """Configuration for a single onboarding step"""
    step_id: str
    name: str
    description: str
    template: str
    required: bool = True
    validation_method: Optional[str] = None
    next_step: Optional[str] = None
    license_types: Optional[List[str]] = None  # If None, applies to all licenses


class OnboardingFlowManager:
    """Manages onboarding flows for different license types"""
    
    # Step definitions - extensible configuration
    STEP_DEFINITIONS = {
        'welcome': OnboardingStep(
            step_id='welcome',
            name='Welcome to VOÏA',
            description='Introduction to your VOÏA platform setup',
            template='onboarding/welcome.html',
            required=True,
            validation_method='validate_welcome_step'
        ),
        'smtp': OnboardingStep(
            step_id='smtp',
            name='Email Configuration',
            description='Configure SMTP settings for survey invitations',
            template='onboarding/smtp.html',
            required=True,
            validation_method='validate_smtp_configuration',
            next_step='brand'
        ),
        'brand': OnboardingStep(
            step_id='brand',
            name='Brand Configuration',
            description='Customize your logo and brand colors (optional)',
            template='onboarding/brand.html',
            required=False,
            validation_method='validate_brand_configuration',
            next_step='users'
        ),
        'users': OnboardingStep(
            step_id='users',
            name='Add Team Members',
            description='Add campaign managers to your team',
            template='onboarding/users.html',
            required=True,
            validation_method='validate_user_creation',
            next_step='complete'
        ),
        'complete': OnboardingStep(
            step_id='complete',
            name='Setup Complete',
            description='Your VOÏA platform is ready to use',
            template='onboarding/complete.html',
            required=True
        )
    }
    
    # License-specific flow configurations
    ONBOARDING_FLOWS = {
        'core': {
            'steps': ['welcome', 'smtp', 'brand', 'users', 'complete'],
            'mandatory': True,
            'description': 'Essential setup for Core license holders'
        },
        'plus': {
            'steps': ['welcome', 'smtp', 'brand', 'users', 'complete'],
            'mandatory': True,
            'description': 'Enhanced setup for Plus license holders'
        },
        'pro': {
            'steps': [],  # Pro licenses skip onboarding
            'mandatory': False,
            'description': 'Pro license holders have optional onboarding'
        },
        'trial': {
            'steps': ['welcome', 'smtp', 'brand', 'users', 'complete'],
            'mandatory': True,
            'description': 'Trial setup to explore VOÏA features'
        }
    }
    
    @classmethod
    def get_flow_for_license(cls, license_type: str) -> Dict:
        """Get onboarding flow configuration for license type"""
        return cls.ONBOARDING_FLOWS.get(license_type.lower(), cls.ONBOARDING_FLOWS['core'])
    
    @classmethod
    def get_step_definition(cls, step_id: str) -> Optional[OnboardingStep]:
        """Get step definition by step ID"""
        return cls.STEP_DEFINITIONS.get(step_id)
    
    @classmethod
    def get_steps_for_license(cls, license_type: str) -> List[OnboardingStep]:
        """Get ordered list of steps for license type"""
        flow = cls.get_flow_for_license(license_type)
        steps = []
        
        for step_id in flow.get('steps', []):
            step_def = cls.get_step_definition(step_id)
            if step_def:
                steps.append(step_def)
        
        return steps
    
    @classmethod
    def is_onboarding_required(cls, license_type: str) -> bool:
        """Check if onboarding is mandatory for license type"""
        flow = cls.get_flow_for_license(license_type)
        return flow.get('mandatory', False)
    
    @classmethod
    def get_next_step(cls, current_step: str, license_type: str) -> Optional[str]:
        """Get next step in the flow"""
        steps = cls.get_steps_for_license(license_type)
        step_ids = [step.step_id for step in steps]
        
        try:
            current_index = step_ids.index(current_step)
            if current_index + 1 < len(step_ids):
                return step_ids[current_index + 1]
        except ValueError:
            logger.warning(f"Current step '{current_step}' not found in flow for license '{license_type}'")
        
        return None
    
    @classmethod
    def get_previous_step(cls, current_step: str, license_type: str) -> Optional[str]:
        """Get previous step in the flow"""
        steps = cls.get_steps_for_license(license_type)
        step_ids = [step.step_id for step in steps]
        
        try:
            current_index = step_ids.index(current_step)
            if current_index > 0:
                return step_ids[current_index - 1]
        except ValueError:
            logger.warning(f"Current step '{current_step}' not found in flow for license '{license_type}'")
        
        return None
    
    @classmethod
    def validate_step_access(cls, step_id: str, user_progress: Dict, license_type: str) -> bool:
        """Validate if user can access a specific step"""
        steps = cls.get_steps_for_license(license_type)
        step_ids = [step.step_id for step in steps]
        
        # Allow access to first step
        if step_id == step_ids[0]:
            return True
        
        try:
            current_index = step_ids.index(step_id)
            # Check if all previous steps are completed
            for i in range(current_index):
                prev_step_id = step_ids[i]
                if not user_progress.get('steps', {}).get(prev_step_id, {}).get('completed', False):
                    return False
            return True
        except ValueError:
            return False
    
    @classmethod
    def get_progress_percentage(cls, user_progress: Dict, license_type: str) -> float:
        """Calculate onboarding progress percentage"""
        steps = cls.get_steps_for_license(license_type)
        if not steps:
            return 100.0
        
        completed_steps = 0
        for step in steps:
            if user_progress.get('steps', {}).get(step.step_id, {}).get('completed', False):
                completed_steps += 1
        
        return (completed_steps / len(steps)) * 100.0
    
    @classmethod
    def add_step_to_flow(cls, license_type: str, step_definition: OnboardingStep, position: Optional[int] = None):
        """Add a new step to an existing flow (for future extensibility)"""
        if license_type not in cls.ONBOARDING_FLOWS:
            logger.error(f"License type '{license_type}' not found")
            return False
        
        # Add step definition
        cls.STEP_DEFINITIONS[step_definition.step_id] = step_definition
        
        # Add to flow
        flow_steps = cls.ONBOARDING_FLOWS[license_type]['steps']
        if position is None:
            # Insert before 'complete' step
            if 'complete' in flow_steps:
                insert_position = flow_steps.index('complete')
                flow_steps.insert(insert_position, step_definition.step_id)
            else:
                flow_steps.append(step_definition.step_id)
        else:
            flow_steps.insert(position, step_definition.step_id)
        
        logger.info(f"Added step '{step_definition.step_id}' to {license_type} license flow")
        return True


# Validation methods for onboarding steps
class OnboardingValidation:
    """Validation methods for onboarding steps"""
    
    @staticmethod
    def validate_welcome_step(user, form_data):
        """Validate welcome step completion"""
        # Welcome step just needs acknowledgment
        return True, "Welcome step completed"
    
    @staticmethod
    def validate_smtp_configuration(user, form_data):
        """Validate SMTP configuration step"""
        try:
            from models import EmailConfiguration
            
            # Check if business account has valid SMTP configuration
            email_config = EmailConfiguration.query.filter_by(
                business_account_id=user.business_account_id
            ).first()
            
            if not email_config:
                return False, "SMTP configuration is required"
            
            # Validate required fields
            if not all([email_config.smtp_server, email_config.smtp_port, 
                       email_config.smtp_username, email_config.encrypted_password]):
                return False, "Complete SMTP configuration is required"
            
            return True, "SMTP configuration validated"
            
        except Exception as e:
            logger.error(f"SMTP validation error: {e}")
            return False, "Failed to validate SMTP configuration"
    
    @staticmethod
    def validate_brand_configuration(user, form_data):
        """Validate brand configuration step - optional/skippable"""
        try:
            # Check if user wants to skip
            if form_data.get('skip_brand'):
                return True, "Brand configuration skipped"
            
            # Check if user self-confirmed completion
            if form_data.get('brand_confirmed'):
                return True, "Brand configuration confirmed"
            
            # No strict validation - this step is optional
            return True, "Brand configuration step completed"
            
        except Exception as e:
            logger.error(f"Brand validation error: {e}")
            return True, "Brand configuration step completed (with errors)"
    
    @staticmethod
    def validate_user_creation(user, form_data):
        """Validate user creation step"""
        try:
            from models import BusinessAccountUser
            
            # Check if at least one campaign manager has been added
            users = BusinessAccountUser.query.filter_by(
                business_account_id=user.business_account_id
            ).filter(
                BusinessAccountUser.role.in_(['manager', 'admin', 'business_account_admin'])
            ).filter(
                BusinessAccountUser.id != user.id  # Exclude current user
            ).count()
            
            if users < 1:
                return False, "At least one campaign manager must be added"
            
            return True, f"Team setup completed with {users} member(s)"
            
        except Exception as e:
            logger.error(f"User creation validation error: {e}")
            return False, "Failed to validate team setup"
    
    @classmethod
    def get_validator(cls, validation_method: str) -> Optional[Callable]:
        """Get validation method by name"""
        return getattr(cls, validation_method, None)