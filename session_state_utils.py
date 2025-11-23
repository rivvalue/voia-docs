"""
Session State Utilities for Deterministic Conversational Survey V2
===================================================================

Provides persistence layer for V2 controller state to/from ActiveConversation table.

Created: November 23, 2025
Feature Flag: DETERMINISTIC_SURVEY_FLOW
"""

from app import db
from models import ActiveConversation
from datetime import datetime
from typing import Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)


# V2 State Schema Constants
V2_STATE_SCHEMA = {
    'current_goal_pointer': None,
    'topic_question_counts': {},
    'last_activity': None,
    'resume_offered': False
}


def initialize_deterministic_state(
    conversation_id: str,
    campaign_id: int,
    participant_id: int,
    business_account_id: int
) -> Dict:
    """
    Initialize new V2 session state structure.
    
    Creates fresh state dict with default values for a new conversational survey.
    This state will be persisted to ActiveConversation table.
    
    Args:
        conversation_id: UUID string for this conversation
        campaign_id: Campaign ID
        participant_id: Participant ID
        business_account_id: Business account ID
    
    Returns:
        Complete V2 state dict ready for persistence
    
    State Structure:
        {
            'conversation_id': str,
            'campaign_id': int,
            'participant_id': int,
            'business_account_id': int,
            'extracted_data': {},                 # Stored in ActiveConversation.extracted_data
            'conversation_history': [],           # Stored in ActiveConversation.conversation_history
            'step_count': 0,                     # Stored in ActiveConversation.step_count
            'current_goal_pointer': None,        # Stored in ActiveConversation.survey_data (V2-specific)
            'topic_question_counts': {},         # Stored in ActiveConversation.survey_data (V2-specific)
            'last_activity': timestamp,          # Stored in ActiveConversation.survey_data (V2-specific)
            'resume_offered': False              # Stored in ActiveConversation.survey_data (V2-specific)
        }
    """
    logger.info(f"Initializing V2 state for conversation {conversation_id}")
    
    state = {
        'conversation_id': conversation_id,
        'campaign_id': campaign_id,
        'participant_id': participant_id,
        'business_account_id': business_account_id,
        'extracted_data': {},
        'conversation_history': [],
        'step_count': 0,
        **V2_STATE_SCHEMA,  # Add V2-specific fields
        'last_activity': datetime.utcnow().isoformat()
    }
    
    logger.debug(f"V2 state initialized with schema: {list(state.keys())}")
    return state


def save_deterministic_state(conversation_id: str, controller_state: Dict) -> bool:
    """
    Save V2 controller state to ActiveConversation table.
    
    Stores state across multiple columns:
    - extracted_data → ActiveConversation.extracted_data (JSON)
    - conversation_history → ActiveConversation.conversation_history (JSON)
    - step_count → ActiveConversation.step_count (int)
    - V2-specific fields → ActiveConversation.survey_data (JSON):
      * current_goal_pointer
      * topic_question_counts
      * last_activity
      * resume_offered
    
    Args:
        conversation_id: UUID string
        controller_state: Full V2 state dict from controller
    
    Returns:
        True if save successful, False on error
    
    Error Handling:
        - Fails gracefully with log warning
        - Rolls back transaction on error
        - Returns False instead of raising exception
    """
    try:
        logger.debug(f"Saving V2 state for conversation {conversation_id}")
        
        # Build V2-specific survey_data payload (only V2 fields)
        v2_survey_data = {
            'current_goal_pointer': controller_state.get('current_goal_pointer'),
            'topic_question_counts': controller_state.get('topic_question_counts', {}),
            'last_activity': controller_state.get('last_activity', datetime.utcnow().isoformat()),
            'resume_offered': controller_state.get('resume_offered', False)
        }
        
        # Check if conversation exists
        existing = ActiveConversation.query.filter_by(conversation_id=conversation_id).first()
        
        if existing:
            # Update existing conversation
            existing.extracted_data = json.dumps(controller_state.get('extracted_data', {}))
            existing.conversation_history = json.dumps(controller_state.get('conversation_history', []))
            existing.survey_data = json.dumps(v2_survey_data)
            existing.step_count = controller_state.get('step_count', 0)
            existing.last_updated = datetime.utcnow()
            
            logger.debug(f"Updated existing conversation {conversation_id}")
        else:
            # Create new conversation record
            new_conversation = ActiveConversation(
                conversation_id=conversation_id,
                business_account_id=controller_state.get('business_account_id'),
                campaign_id=controller_state.get('campaign_id'),
                participant_data=json.dumps(controller_state.get('participant_data')),
                extracted_data=json.dumps(controller_state.get('extracted_data', {})),
                conversation_history=json.dumps(controller_state.get('conversation_history', [])),
                survey_data=json.dumps(v2_survey_data),
                step_count=controller_state.get('step_count', 0)
            )
            db.session.add(new_conversation)
            
            logger.debug(f"Created new conversation {conversation_id}")
        
        db.session.commit()
        logger.info(f"✅ V2 state saved for {conversation_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving V2 state for {conversation_id}: {e}")
        db.session.rollback()
        return False


def load_deterministic_state(conversation_id: str) -> Optional[Dict]:
    """
    Load V2 state from ActiveConversation table.
    
    Retrieves persisted state and reconstructs full V2 state dict.
    
    Args:
        conversation_id: UUID string
    
    Returns:
        Complete V2 state dict, or None if not found
    
    Error Handling:
        - Returns None if conversation not found (graceful)
        - Returns fresh default state if JSON parsing fails (fail-soft)
        - Logs warnings for malformed data
    
    State Recovery:
        If survey_data JSON is malformed, returns defaults:
        - current_goal_pointer = None
        - topic_question_counts = {}
        - last_activity = None
        - resume_offered = False
    """
    try:
        logger.debug(f"Loading V2 state for conversation {conversation_id}")
        
        conversation = ActiveConversation.query.filter_by(conversation_id=conversation_id).first()
        
        if not conversation:
            logger.debug(f"No persisted state found for {conversation_id}")
            return None
        
        # Parse JSON fields with fail-soft defaults
        try:
            extracted_data = json.loads(conversation.extracted_data) if conversation.extracted_data else {}
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Malformed extracted_data for {conversation_id}: {e}")
            extracted_data = {}
        
        try:
            conversation_history = json.loads(conversation.conversation_history) if conversation.conversation_history else []
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Malformed conversation_history for {conversation_id}: {e}")
            conversation_history = []
        
        try:
            participant_data = json.loads(conversation.participant_data) if conversation.participant_data else None
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Malformed participant_data for {conversation_id}: {e}")
            participant_data = None
        
        # Parse V2-specific survey_data (fail-soft with defaults)
        v2_data = V2_STATE_SCHEMA.copy()  # Start with defaults
        try:
            if conversation.survey_data:
                parsed_survey_data = json.loads(conversation.survey_data)
                # Merge parsed data (overwrite defaults with actual values)
                v2_data.update(parsed_survey_data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Malformed survey_data for {conversation_id}, using defaults: {e}")
        
        # Reconstruct full state
        state = {
            'conversation_id': conversation_id,
            'campaign_id': conversation.campaign_id,
            'business_account_id': conversation.business_account_id,
            'participant_data': participant_data,
            'extracted_data': extracted_data,
            'conversation_history': conversation_history,
            'step_count': conversation.step_count,
            **v2_data  # Add V2-specific fields
        }
        
        logger.info(f"✅ V2 state loaded for {conversation_id} (step {state['step_count']})")
        return state
        
    except Exception as e:
        logger.error(f"❌ Error loading V2 state for {conversation_id}: {e}")
        return None


def delete_deterministic_state(conversation_id: str) -> bool:
    """
    Delete conversation state from database after finalization.
    
    Called when survey completes successfully to clean up session state.
    
    Args:
        conversation_id: UUID string
    
    Returns:
        True if deletion successful (or record didn't exist), False on error
    """
    try:
        logger.debug(f"Deleting V2 state for conversation {conversation_id}")
        
        conversation = ActiveConversation.query.filter_by(conversation_id=conversation_id).first()
        
        if conversation:
            db.session.delete(conversation)
            db.session.commit()
            logger.info(f"✅ Deleted V2 state for {conversation_id}")
        else:
            logger.debug(f"No state to delete for {conversation_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error deleting V2 state for {conversation_id}: {e}")
        db.session.rollback()
        return False


def update_last_activity(conversation_id: str) -> bool:
    """
    Update last_activity timestamp for abandonment detection.
    
    Lightweight update that only touches survey_data timestamp.
    
    Args:
        conversation_id: UUID string
    
    Returns:
        True if update successful, False on error
    """
    try:
        conversation = ActiveConversation.query.filter_by(conversation_id=conversation_id).first()
        
        if not conversation:
            logger.warning(f"Cannot update last_activity: conversation {conversation_id} not found")
            return False
        
        # Parse existing survey_data
        try:
            survey_data = json.loads(conversation.survey_data) if conversation.survey_data else {}
        except (json.JSONDecodeError, TypeError):
            survey_data = {}
        
        # Update timestamp
        survey_data['last_activity'] = datetime.utcnow().isoformat()
        conversation.survey_data = json.dumps(survey_data)
        conversation.last_updated = datetime.utcnow()
        
        db.session.commit()
        logger.debug(f"Updated last_activity for {conversation_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating last_activity for {conversation_id}: {e}")
        db.session.rollback()
        return False
