import json
import os
from openai import OpenAI
from typing import Dict, List, Any, Optional

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

class ConversationalSurvey:
    """AI-powered conversational survey system"""
    
    def __init__(self):
        self.conversation_history = []
        self.survey_data = {}
        self.current_step = "welcome"
        self.completed_topics = set()
        
    def start_conversation(self, company_name: str, respondent_name: str) -> Dict[str, Any]:
        """Start a new conversational survey"""
        self.survey_data = {
            'company_name': company_name,
            'respondent_name': respondent_name,
            'conversation_history': [],
            'extracted_data': {}
        }
        
        welcome_message = self._generate_welcome_message(company_name, respondent_name)
        
        return {
            'message': welcome_message,
            'message_type': 'ai_question',
            'step': 'welcome',
            'progress': 0
        }
    
    def process_user_response(self, user_input: str, conversation_context: Dict[str, Any]) -> Dict[str, Any]:
        """Process user response and generate next AI question"""
        try:
            # Add user response to conversation history
            self.conversation_history.append({
                'role': 'user',
                'content': user_input,
                'timestamp': 'now'
            })
            
            # Analyze the response and extract survey data
            extracted_data = self._extract_survey_data(user_input, conversation_context)
            
            # Update survey data and conversation context
            if 'extracted_data' not in conversation_context:
                conversation_context['extracted_data'] = {}
            conversation_context['extracted_data'].update(extracted_data)
            
            self.survey_data['extracted_data'].update(extracted_data)
            
            # Determine next question based on conversation flow
            next_response = self._generate_next_question(user_input, conversation_context)
            
            return next_response
            
        except Exception as e:
            print(f"Error processing user response: {e}")
            return {
                'message': "I apologize, but I'm having trouble processing your response. Could you please try again?",
                'message_type': 'error',
                'step': conversation_context.get('step', 'unknown'),
                'progress': conversation_context.get('progress', 0),
                'is_complete': False
            }
    
    def _generate_welcome_message(self, company_name: str, respondent_name: str) -> str:
        """Generate personalized welcome message"""
        return f"""Hi {respondent_name}! 👋

I'm here to help gather your valuable feedback about your experience with {company_name}. 

Instead of filling out a traditional survey, we'll have a natural conversation. I'll ask you questions, and you can respond in your own words - just like talking to a colleague.

This usually takes about 5-7 minutes, and your insights will help improve the products and services you use.

Let's start with the most important question: **On a scale of 0 to 10, how likely are you to recommend {company_name} to a friend or colleague?**

Feel free to explain your reasoning too!"""
    
    def _extract_survey_data(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured survey data from natural language response using rule-based approach"""
        extracted = {}
        user_input_lower = user_input.lower().strip()
        
        # Extract NPS score (0-10)
        import re
        nps_patterns = [
            r'\b([0-9]|10)\b',  # Direct number
            r'score.*?([0-9]|10)',  # "score is 8"
            r'rate.*?([0-9]|10)',   # "rate it 7"
            r'([0-9]|10).*?out.*?10',  # "8 out of 10"
            r'([0-9]|10)/10'  # "8/10"
        ]
        
        for pattern in nps_patterns:
            nps_match = re.search(pattern, user_input)
            if nps_match:
                try:
                    score = int(nps_match.group(1))
                    if 0 <= score <= 10:
                        extracted['nps_score'] = score
                        if score >= 9:
                            extracted['nps_category'] = 'Promoter'
                        elif score >= 7:
                            extracted['nps_category'] = 'Passive'
                        else:
                            extracted['nps_category'] = 'Detractor'
                        break
                except ValueError:
                    continue
        
        # Extract satisfaction rating (1-5)
        satisfaction_keywords = {
            'very satisfied': 5, 'extremely satisfied': 5, 'excellent': 5, 'outstanding': 5,
            'satisfied': 4, 'good': 4, 'happy': 4, 'pleased': 4,
            'neutral': 3, 'okay': 3, 'average': 3, 'fine': 3,
            'dissatisfied': 2, 'poor': 2, 'bad': 2, 'unhappy': 2,
            'very dissatisfied': 1, 'terrible': 1, 'awful': 1, 'horrible': 1
        }
        
        for keyword, rating in satisfaction_keywords.items():
            if keyword in user_input_lower:
                extracted['satisfaction_rating'] = rating
                break
        
        # Extract improvement feedback
        improvement_indicators = ['improve', 'better', 'fix', 'change', 'enhance', 'suggest', 'wish', 'need', 'should']
        if any(indicator in user_input_lower for indicator in improvement_indicators):
            extracted['improvement_feedback'] = user_input
        
        # Store raw feedback
        extracted['feedback_text'] = user_input
        
        # Extract reasoning if NPS score is provided
        if 'nps_score' in extracted:
            extracted['nps_reasoning'] = user_input
        
        # Debug logging
        print(f"Extracted data from '{user_input}': {extracted}")
        
        return extracted
    
    def _generate_next_question(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the next conversational question using rule-based logic"""
        # Get extracted data and conversation state
        extracted = context.get('extracted_data', {})
        step_count = context.get('step_count', 0)
        
        # Update step count
        step_count += 1
        context['step_count'] = step_count
        
        # Determine what information we still need
        needed_info = self._analyze_missing_information(context)
        
        # Debug logging
        print(f"Question generation - extracted data: {extracted}")
        print(f"Step count: {step_count}")
        
        # Rule-based question generation
        if not extracted.get('nps_score'):
            return {
                'message': "On a scale of 0-10, how likely are you to recommend our service to a friend or colleague?",
                'message_type': 'ai_question',
                'step': 'nps_collection',
                'progress': 20,
                'is_complete': False
            }
        
        elif extracted.get('nps_score') and not extracted.get('nps_reasoning'):
            score = extracted['nps_score']
            if score >= 9:
                return {
                    'message': f"Thank you for the {score}! That's wonderful to hear. What specifically makes you likely to recommend us?",
                    'message_type': 'follow_up',
                    'step': 'nps_reasoning',
                    'progress': 40,
                    'is_complete': False
                }
            elif score >= 7:
                return {
                    'message': f"Thanks for the {score}. What would it take to make you more likely to recommend us?",
                    'message_type': 'follow_up',
                    'step': 'nps_reasoning',
                    'progress': 40,
                    'is_complete': False
                }
            else:
                return {
                    'message': f"I appreciate your honesty with the {score}. Can you tell me what's holding you back from recommending us?",
                    'message_type': 'follow_up',
                    'step': 'nps_reasoning',
                    'progress': 40,
                    'is_complete': False
                }
        
        elif not extracted.get('satisfaction_rating'):
            return {
                'message': "How would you describe your overall satisfaction with our service? Are you very satisfied, satisfied, neutral, dissatisfied, or very dissatisfied?",
                'message_type': 'ai_question',
                'step': 'satisfaction',
                'progress': 60,
                'is_complete': False
            }
        
        elif not extracted.get('improvement_feedback'):
            return {
                'message': "What's one thing we could improve to better serve you?",
                'message_type': 'ai_question',
                'step': 'improvement',
                'progress': 80,
                'is_complete': False
            }
        
        else:
            # Survey is complete
            return {
                'message': "Thank you for sharing your valuable feedback! We really appreciate you taking the time to help us improve our service.",
                'message_type': 'conclusion',
                'step': 'conclusion',
                'progress': 100,
                'is_complete': True
            }
    
    def _analyze_missing_information(self, context: Dict[str, Any]) -> List[str]:
        """Analyze what survey information is still missing"""
        extracted = context.get('extracted_data', {})
        needed = []
        
        if 'nps_score' not in extracted:
            needed.append("NPS score (0-10 recommendation likelihood)")
        
        if 'nps_score' in extracted and 'nps_reasoning' not in extracted:
            needed.append("Reasoning for NPS score")
        
        if 'satisfaction_rating' not in extracted:
            needed.append("Overall satisfaction rating")
        
        if 'improvement_feedback' not in extracted:
            needed.append("Suggestions for improvement")
        
        if not any(key in extracted for key in ['positive_aspects', 'negative_aspects']):
            needed.append("Specific likes and dislikes")
        
        return needed
    
    def finalize_survey(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Convert conversational data to structured survey format"""
        extracted = context.get('extracted_data', {})
        
        # Convert to standard survey format
        survey_response = {
            'company_name': context.get('company_name', ''),
            'respondent_name': context.get('respondent_name', ''),
            'respondent_email': context.get('respondent_email', ''),
            'nps_score': extracted.get('nps_score'),
            'satisfaction_rating': extracted.get('satisfaction_rating'),
            'product_value_rating': extracted.get('product_value_rating'),
            'service_rating': extracted.get('service_rating'),
            'pricing_rating': extracted.get('pricing_rating'),
            'improvement_feedback': extracted.get('improvement_feedback'),
            'recommendation_reason': extracted.get('nps_reasoning'),
            'additional_comments': self._combine_conversational_feedback(extracted),
            'conversation_history': json.dumps(self.conversation_history)
        }
        
        return survey_response
    
    def _combine_conversational_feedback(self, extracted: Dict[str, Any]) -> str:
        """Combine all conversational feedback into structured format"""
        feedback_parts = []
        
        if 'positive_aspects' in extracted:
            feedback_parts.append(f"Positive aspects: {extracted['positive_aspects']}")
        
        if 'negative_aspects' in extracted:
            feedback_parts.append(f"Concerns: {extracted['negative_aspects']}")
        
        if 'additional_comments' in extracted:
            feedback_parts.append(f"Additional feedback: {extracted['additional_comments']}")
        
        return " | ".join(feedback_parts)


# Global conversation instances (keyed by conversation_id)
conversation_instances = {}

def start_conversational_survey(company_name: str, respondent_name: str) -> Dict[str, Any]:
    """Start a new conversational survey session"""
    conversation_survey = ConversationalSurvey()
    response = conversation_survey.start_conversation(company_name, respondent_name)
    
    # Store the instance with a unique ID for this session
    import uuid
    conversation_id = str(uuid.uuid4())
    conversation_instances[conversation_id] = conversation_survey
    
    # Add conversation_id to response
    response['conversation_id'] = conversation_id
    return response

def process_conversation_response(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Process user's conversational response"""
    conversation_id = context.get('conversation_id')
    
    # Get or create conversation instance
    if conversation_id and conversation_id in conversation_instances:
        conversation_survey = conversation_instances[conversation_id]
    else:
        # Fallback: create new instance
        conversation_survey = ConversationalSurvey()
        if conversation_id:
            conversation_instances[conversation_id] = conversation_survey
    
    return conversation_survey.process_user_response(user_input, context)

def finalize_conversational_survey(context: Dict[str, Any]) -> Dict[str, Any]:
    """Finalize and convert conversational survey to structured format"""
    conversation_id = context.get('conversation_id')
    
    if conversation_id and conversation_id in conversation_instances:
        conversation_survey = conversation_instances[conversation_id]
        result = conversation_survey.finalize_survey(context)
        # Clean up the instance
        del conversation_instances[conversation_id]
        return result
    else:
        # Fallback finalization
        conversation_survey = ConversationalSurvey()
        return conversation_survey.finalize_survey(context)