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
            
            # Update survey data
            self.survey_data['extracted_data'].update(extracted_data)
            
            # Determine next question based on conversation flow
            next_response = self._generate_next_question(user_input, conversation_context)
            
            return next_response
            
        except Exception as e:
            return {
                'message': "I apologize, but I'm having trouble processing your response. Could you please try again?",
                'message_type': 'error',
                'step': conversation_context.get('step', 'unknown'),
                'progress': conversation_context.get('progress', 0)
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
        """Extract structured survey data from natural language response"""
        try:
            system_prompt = """You are a survey data extraction expert. Extract relevant survey information from the user's natural language response.

Based on the conversation context and user input, extract and return JSON with any of these fields that can be determined:
- nps_score: Integer 0-10 if mentioned
- nps_reasoning: String explaining their NPS score
- satisfaction_rating: Integer 1-5 if mentioned 
- product_value_rating: Integer 1-5 if mentioned
- service_rating: Integer 1-5 if mentioned
- pricing_rating: Integer 1-5 if mentioned
- improvement_feedback: String with suggestions for improvement
- positive_aspects: String with things they like
- negative_aspects: String with concerns or issues
- additional_comments: String with any other feedback

Only include fields that can be clearly determined from the input. Return empty object if no clear data can be extracted."""

            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context: {json.dumps(context)}\nUser input: {user_input}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            if content:
                return json.loads(content)
            return {}
            
        except Exception as e:
            print(f"Error extracting survey data: {e}")
            return {}
    
    def _generate_next_question(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the next conversational question based on user response"""
        try:
            # Determine what information we still need
            needed_info = self._analyze_missing_information(context)
            
            system_prompt = f"""You are a friendly, professional survey interviewer for Rivvalue Inc. Your goal is to gather customer feedback through natural conversation.

Current conversation context: {json.dumps(context)}
Information still needed: {needed_info}
User's last response: {user_input}

Generate the next question or response following these guidelines:
1. Keep it conversational and friendly
2. Ask about one main topic at a time
3. If user gave an NPS score, ask for reasoning if not provided
4. Explore satisfaction with different aspects (product, service, pricing, value)
5. Ask about specific improvements they'd like to see
6. Keep questions open-ended to encourage detailed responses
7. If you have enough information, move toward conclusion

Return JSON with:
- message: The next question or response
- message_type: "ai_question", "follow_up", "clarification", or "conclusion"
- step: Current conversation step
- progress: Percentage complete (0-100)
- is_complete: Boolean if survey is done"""

            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate next question based on: {user_input}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            if content:
                result = json.loads(content)
                
                # Add conversation history
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': result.get('message', ''),
                    'timestamp': 'now'
                })
                
                return result
            
            # Fallback response
            return {
                'message': "Thank you for your feedback! Is there anything else you'd like to share?",
                'message_type': 'ai_question',
                'step': 'conclusion',
                'progress': 90,
                'is_complete': False
            }
            
        except Exception as e:
            print(f"Error generating next question: {e}")
            return {
                'message': "Thank you for your feedback! Is there anything else you'd like to share about your experience?",
                'message_type': 'ai_question',
                'step': 'conclusion',
                'progress': 90,
                'is_complete': False
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


# Global instance for the conversational survey
conversation_survey = ConversationalSurvey()

def start_conversational_survey(company_name: str, respondent_name: str) -> Dict[str, Any]:
    """Start a new conversational survey session"""
    return conversation_survey.start_conversation(company_name, respondent_name)

def process_conversation_response(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Process user's conversational response"""
    return conversation_survey.process_user_response(user_input, context)

def finalize_conversational_survey(context: Dict[str, Any]) -> Dict[str, Any]:
    """Finalize and convert conversational survey to structured format"""
    return conversation_survey.finalize_survey(context)