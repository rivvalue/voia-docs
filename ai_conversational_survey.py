import os
import json
import uuid
from typing import Dict, Any, List
from openai import OpenAI

class AIConversationalSurvey:
    """OpenAI-powered conversational survey system with adaptive questioning"""
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        self.conversation_history = []
        self.survey_data = {}
        self.extracted_data = {}
        self.step_count = 0
        self.is_complete = False
        
    def start_conversation(self, company_name: str, respondent_name: str) -> Dict[str, Any]:
        """Start a new AI-powered conversational survey"""
        self.survey_data = {
            'company_name': company_name,
            'respondent_name': respondent_name,
            'conversation_history': [],
            'extracted_data': {}
        }
        
        welcome_message = self._generate_welcome_message(company_name, respondent_name)
        
        self.conversation_history.append({
            'sender': 'VoC Agent',
            'message': welcome_message,
            'timestamp': 'now'
        })
        
        return {
            'message': welcome_message,
            'message_type': 'welcome',
            'step': 'welcome',
            'progress': 10,
            'is_complete': False,
            'conversation_id': str(uuid.uuid4())
        }
    
    def process_user_response(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process user response and generate next AI question"""
        # Add user response to conversation history
        self.conversation_history.append({
            'sender': 'User',
            'message': user_input,
            'timestamp': 'now'
        })
        
        # Extract data from user input
        extracted = self._extract_survey_data_with_ai(user_input, context)
        
        # Update extracted data - merge with existing data
        for key, value in extracted.items():
            if value is not None:  # Only update if we have actual data
                self.extracted_data[key] = value
        
        self.survey_data['extracted_data'] = self.extracted_data
        
        # Increment step count BEFORE generating next question
        self.step_count += 1
        
        # Debug print
        print(f"Step {self.step_count}: User said: '{user_input}'")
        print(f"Extracted data: {extracted}")
        print(f"Full extracted data: {self.extracted_data}")
        
        # Generate next AI question using updated data
        next_question = self._generate_ai_question(user_input, context)
        
        # Add AI response to conversation history
        if not next_question.get('is_complete', False):
            self.conversation_history.append({
                'sender': 'VoC Agent',
                'message': next_question['message'],
                'timestamp': 'now'
            })
        
        # Debug logging
        print(f"Step {self.step_count}: Extracted data: {self.extracted_data}")
        print(f"Next question: {next_question.get('message', '')}")
        
        return next_question
    
    def _generate_welcome_message(self, company_name: str, respondent_name: str) -> str:
        """Generate personalized welcome message"""
        return f"Hi {respondent_name}! I'm here to gather your feedback about FC inc. This will be a quick conversation to understand your experience and help improve their service. Let's start - on a scale of 0-10, how likely are you to recommend FC inc to a friend or colleague?"
    
    def _extract_survey_data_with_ai(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured survey data from natural language using OpenAI"""
        try:
            prompt = f"""Extract survey data from this customer response: "{user_input}"

Context of conversation:
- Company: {context.get('company_name', 'Unknown')}
- Current extracted data: {json.dumps(self.extracted_data, indent=2)}
- Conversation step: {self.step_count}

Extract any of the following data present in the response:
- NPS score (0-10): Look for numbers, recommendations, likelihood scores
- Satisfaction level (1-5): Look for satisfaction, happiness, contentment indicators
- Improvement suggestions: Any feedback about what could be better
- Compliments: What they liked or appreciated
- Complaints: What they didn't like or found problematic
- Reasons: Why they gave their rating or recommendation
- Additional comments: Any other relevant feedback

Return ONLY JSON in this format:
{{
    "nps_score": number or null,
    "nps_category": "Promoter/Passive/Detractor" or null,
    "satisfaction_rating": number or null,
    "improvement_feedback": "text" or null,
    "compliment_feedback": "text" or null,
    "complaint_feedback": "text" or null,
    "nps_reasoning": "text" or null,
    "additional_comments": "text" or null
}}

Only include fields that are clearly present in the response. If a field is not mentioned, use null."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=400,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            if content:
                extracted = json.loads(content)
            else:
                extracted = {}
            
            # Add NPS category if score is provided
            if extracted.get('nps_score') is not None:
                score = extracted['nps_score']
                if score >= 9:
                    extracted['nps_category'] = 'Promoter'
                elif score >= 7:
                    extracted['nps_category'] = 'Passive'
                else:
                    extracted['nps_category'] = 'Detractor'
            
            return extracted
            
        except Exception as e:
            print(f"AI extraction error: {e}")
            # Use robust fallback extraction
            return self._extract_survey_data_fallback(user_input)
    
    def _extract_survey_data_fallback(self, user_input: str) -> Dict[str, Any]:
        """Enhanced rule-based extraction with intelligent pattern matching"""
        extracted = {}
        text_lower = user_input.lower()
        
        # Extract NPS score with improved detection
        import re
        
        # Look for numbers 0-10 in various formats - more comprehensive patterns
        nps_patterns = [
            r'(?:score|rating|give|rate).*?([0-9]|10)',
            r'^([0-9]|10)(?:\s|$|/|,|\.)',
            r'([0-9]|10)\s*(?:out of 10|/10)',
            r'(?:i.*d.*say|i.*d.*give|i.*d.*rate).*?([0-9]|10)',
            r'(?:probably|maybe|around|about).*?([0-9]|10)',
            r'\b([0-9]|10)\b(?!\d)',  # Standalone number not part of larger number
            r'([0-9]|10)',  # Any single digit or 10 in the text
            r'(?:is|was|would be|rating|score).*?([0-9]|10)',
            r'([0-9]|10)(?:\s*(?:stars?|points?|rating))?'  # Number followed by optional unit
        ]
        
        for pattern in nps_patterns:
            matches = re.findall(pattern, user_input, re.IGNORECASE)
            for match in matches:
                score = int(match)
                if 0 <= score <= 10:
                    extracted['nps_score'] = score
                    if score >= 9:
                        extracted['nps_category'] = 'Promoter'
                    elif score >= 7:
                        extracted['nps_category'] = 'Passive'
                    else:
                        extracted['nps_category'] = 'Detractor'
                    break
            if 'nps_score' in extracted:
                break
        
        # Enhanced satisfaction detection
        satisfaction_keywords = {
            5: ['very satisfied', 'extremely satisfied', 'absolutely satisfied', 'completely satisfied', 'love it', 'excellent', 'outstanding', 'perfect'],
            4: ['satisfied', 'happy', 'pleased', 'good', 'great', 'positive', 'content'],
            3: ['neutral', 'okay', 'fine', 'average', 'alright', 'so-so', 'mixed'],
            2: ['dissatisfied', 'unhappy', 'disappointed', 'not good', 'poor', 'below average'],
            1: ['very dissatisfied', 'extremely dissatisfied', 'terrible', 'awful', 'horrible', 'hate', 'worst']
        }
        
        for rating, keywords in satisfaction_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                extracted['satisfaction_rating'] = rating
                break
        
        # Extract improvement suggestions
        improvement_indicators = ['improve', 'better', 'fix', 'change', 'enhance', 'upgrade', 'should', 'could', 'need to', 'would like']
        if any(indicator in text_lower for indicator in improvement_indicators):
            extracted['improvement_feedback'] = user_input
        
        # Extract compliments
        positive_indicators = ['love', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'good job', 'well done', 'appreciate']
        if any(indicator in text_lower for indicator in positive_indicators):
            extracted['compliment_feedback'] = user_input
        
        # Extract complaints
        negative_indicators = ['problem', 'issue', 'difficult', 'hard', 'confusing', 'slow', 'expensive', 'bad', 'worst', 'hate']
        if any(indicator in text_lower for indicator in negative_indicators):
            extracted['complaint_feedback'] = user_input
        
        # Store reasoning if it seems like reasoning
        reasoning_indicators = ['because', 'since', 'due to', 'reason', 'why', 'that\'s why']
        if any(indicator in text_lower for indicator in reasoning_indicators):
            extracted['nps_reasoning'] = user_input
        
        # Always store as additional comments for context
        extracted['additional_comments'] = user_input
        
        return extracted
    
    def _generate_ai_question(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate next question using OpenAI"""
        try:
            # Format conversation history for context
            history_text = self._format_conversation_history()
            
            prompt = f"""You are conducting a customer feedback survey about FC inc (the supplier company). Focus on FC inc's service delivery, support quality, and business relationship aspects.

CONVERSATION HISTORY:
{history_text}

CUSTOMER'S LATEST RESPONSE: "{user_input}"

SURVEY DATA COLLECTED SO FAR:
{json.dumps(self.extracted_data, indent=2)}

CONVERSATION STEP: {self.step_count}

YOUR ROLE: You are a helpful customer feedback specialist having a natural conversation. Your goal is to collect feedback about FC inc:
1. NPS score (0-10) - How likely to recommend FC inc
2. Reason for their NPS score about FC inc
3. Satisfaction level (1-5) - Overall satisfaction with FC inc
4. Improvement suggestions - What could FC inc do better
5. Additional feedback - Any other comments about FC inc

GUIDELINES:
- Keep the conversation natural and engaging
- Ask ONE question at a time
- Reference their previous responses to show you're listening
- If they mention specific issues, ask thoughtful follow-ups
- If they seem rushed, be more direct
- If they're chatty, engage with their details
- End gracefully when you have enough information (usually 4-6 exchanges)

RESPONSE FORMAT - Return JSON:
{{
    "message": "Your next question or closing message",
    "message_type": "ai_question",
    "step": "descriptive_step_name",
    "progress": 0-100,
    "is_complete": true/false
}}

Be conversational, empathetic, and adaptive to their communication style."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=300,
                temperature=0.8
            )
            
            content = response.choices[0].message.content
            if content:
                result = json.loads(content)
            else:
                result = {'message': 'Thank you for your feedback!', 'is_complete': True, 'progress': 100}
            
            # Ensure progress is reasonable
            if result.get('progress', 0) < self.step_count * 15:
                result['progress'] = min(100, self.step_count * 15)
            
            self.is_complete = result.get('is_complete', False)
            
            return result
            
        except Exception as e:
            print(f"AI question generation error: {e}")
            return self._generate_fallback_question(user_input, context)
    
    def _format_conversation_history(self) -> str:
        """Format conversation history for AI context"""
        if not self.conversation_history:
            return "This is the start of the conversation."
        
        formatted = []
        for msg in self.conversation_history[-6:]:  # Last 6 messages for context
            sender = msg.get('sender', 'Unknown')
            message = msg.get('message', '')
            formatted.append(f"{sender}: {message}")
        
        return "\n".join(formatted)
    
    def _generate_fallback_question(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fixed progression logic based on step count and missing data"""
        extracted = self.extracted_data
        company_name = context.get('company_name', 'our service')
        
        print(f"Fallback generation - Step: {self.step_count}, Extracted: {extracted}")
        
        # Use step-based progression but check if we already have NPS data
        if self.step_count == 1:
            # First question: Ask for NPS about FC inc (the supplier) ONLY if we don't have it
            if extracted.get('nps_score') is None:
                return {
                    'message': "On a scale of 0-10, how likely are you to recommend FC inc to a friend or colleague?",
                    'message_type': 'ai_question',
                    'step': 'nps_collection',
                    'progress': 20,
                    'is_complete': False
                }
            else:
                # We already have NPS score from first response, move to step 2 logic
                # But increment step count to 2 so next time it goes to step 3 
                self.step_count = 2
                score = extracted['nps_score']
                if score >= 9:
                    return {
                        'message': f"Wonderful! A {score} is fantastic. What specifically about FC inc made your experience so great?",
                        'message_type': 'ai_question',
                        'step': 'nps_reasoning',
                        'progress': 40,
                        'is_complete': False
                    }
                elif score >= 7:
                    return {
                        'message': f"Thanks for the {score}! What would it take to make you even more likely to recommend FC inc?",
                        'message_type': 'ai_question',
                        'step': 'nps_reasoning',
                        'progress': 40,
                        'is_complete': False
                    }
                else:
                    return {
                        'message': f"I appreciate your honesty with the {score}. What are the main issues that are holding you back from recommending FC inc?",
                        'message_type': 'ai_question',
                        'step': 'nps_reasoning',
                        'progress': 40,
                        'is_complete': False
                    }
        
        elif self.step_count == 2:
            # Second question: We should have already asked the NPS reasoning question
            # This response is the user's answer to the NPS reasoning question
            # Move to satisfaction question
            return {
                'message': "How would you describe your overall satisfaction with FC inc's service? Very satisfied, satisfied, neutral, dissatisfied, or very dissatisfied?",
                'message_type': 'ai_question',
                'step': 'satisfaction',
                'progress': 60,
                'is_complete': False
            }
        
        elif self.step_count == 3:
            # Third question: Satisfaction rating
            return {
                'message': "How would you describe your overall satisfaction with FC inc's service? Very satisfied, satisfied, neutral, dissatisfied, or very dissatisfied?",
                'message_type': 'ai_question',
                'step': 'satisfaction',
                'progress': 60,
                'is_complete': False
            }
        
        elif self.step_count == 4:
            # Fourth question: Improvement suggestions
            if extracted.get('nps_score', 0) < 7:
                return {
                    'message': "What specific changes would make the biggest difference in improving your experience with FC inc?",
                    'message_type': 'ai_question',
                    'step': 'improvement',
                    'progress': 80,
                    'is_complete': False
                }
            else:
                return {
                    'message': "Is there anything FC inc could do even better to enhance your experience?",
                    'message_type': 'ai_question',
                    'step': 'improvement',
                    'progress': 80,
                    'is_complete': False
                }
        
        # Step 5 or higher: Complete the survey
        else:
            return {
                'message': "Thank you so much for sharing your valuable feedback about FC inc! Your insights help improve their service for everyone.",
                'message_type': 'conclusion',
                'step': 'conclusion',
                'progress': 100,
                'is_complete': True
            }
    
    def finalize_survey(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Convert conversational data to structured survey format"""
        extracted = self.extracted_data
        
        # Ensure we have at least minimum required data by analyzing conversation history
        if not extracted.get('nps_score') and self.conversation_history:
            self._extract_missing_data_from_history()
        
        # Combine all feedback text
        feedback_parts = []
        for key in ['nps_reasoning', 'improvement_feedback', 'compliment_feedback', 'complaint_feedback', 'additional_comments']:
            if extracted.get(key):
                feedback_parts.append(extracted[key])
        
        combined_feedback = ' '.join(feedback_parts) if feedback_parts else None
        
        # Ensure required fields have values or reasonable defaults
        nps_score = extracted.get('nps_score')
        if nps_score is None:
            # Try to extract from conversation history as fallback
            nps_score = self._extract_nps_from_history()
        
        # Set default NPS category if score exists
        nps_category = extracted.get('nps_category')
        if nps_score is not None and not nps_category:
            if nps_score >= 9:
                nps_category = 'Promoter'
            elif nps_score >= 7:
                nps_category = 'Passive'
            else:
                nps_category = 'Detractor'
        
        return {
            'company_name': context.get('company_name'),
            'respondent_name': context.get('respondent_name'),
            'respondent_email': context.get('respondent_email'),
            'nps_score': nps_score,
            'nps_category': nps_category,
            'satisfaction_rating': extracted.get('satisfaction_rating'),
            'improvement_feedback': extracted.get('improvement_feedback'),
            'recommendation_reason': extracted.get('nps_reasoning'),
            'additional_comments': combined_feedback,
            'conversation_history': json.dumps(self.conversation_history)
        }
    
    def _extract_missing_data_from_history(self):
        """Extract missing survey data from conversation history as fallback"""
        conversation_text = ' '.join([msg.get('message', '') for msg in self.conversation_history if msg.get('sender') == 'User'])
        
        # Try to extract NPS score using simple pattern matching
        import re
        
        # Look for numbers 0-10 in user responses
        for msg in self.conversation_history:
            if msg.get('sender') == 'User':
                message = msg.get('message', '')
                # Look for standalone numbers 0-10
                numbers = re.findall(r'\b([0-9]|10)\b', message)
                for num_str in numbers:
                    num = int(num_str)
                    if 0 <= num <= 10:
                        self.extracted_data['nps_score'] = num
                        if num >= 9:
                            self.extracted_data['nps_category'] = 'Promoter'
                        elif num >= 7:
                            self.extracted_data['nps_category'] = 'Passive'
                        else:
                            self.extracted_data['nps_category'] = 'Detractor'
                        break
        
        # Extract satisfaction keywords
        text_lower = conversation_text.lower()
        if not self.extracted_data.get('satisfaction_rating'):
            if any(word in text_lower for word in ['very satisfied', 'extremely satisfied']):
                self.extracted_data['satisfaction_rating'] = 5
            elif any(word in text_lower for word in ['satisfied', 'happy', 'pleased']):
                self.extracted_data['satisfaction_rating'] = 4
            elif any(word in text_lower for word in ['neutral', 'okay', 'fine']):
                self.extracted_data['satisfaction_rating'] = 3
            elif any(word in text_lower for word in ['dissatisfied', 'unhappy', 'disappointed']):
                self.extracted_data['satisfaction_rating'] = 2
            elif any(word in text_lower for word in ['very dissatisfied', 'terrible', 'awful']):
                self.extracted_data['satisfaction_rating'] = 1
    
    def _extract_nps_from_history(self):
        """Extract NPS score from conversation history using pattern matching"""
        import re
        
        for msg in self.conversation_history:
            if msg.get('sender') == 'User':
                message = msg.get('message', '')
                # Look for numbers 0-10 in context of recommendation
                numbers = re.findall(r'\b([0-9]|10)\b', message)
                for num_str in numbers:
                    num = int(num_str)
                    if 0 <= num <= 10:
                        return num
        return None


# Global instances for session persistence
ai_conversation_instances = {}

def start_ai_conversational_survey(company_name: str, respondent_name: str) -> Dict[str, Any]:
    """Start a new AI-powered conversational survey session"""
    conversation_id = str(uuid.uuid4())
    ai_survey = AIConversationalSurvey()
    
    result = ai_survey.start_conversation(company_name, respondent_name)
    result['conversation_id'] = conversation_id
    
    # Store instance for session persistence
    ai_conversation_instances[conversation_id] = ai_survey
    
    return result

def process_ai_conversation_response(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Process user's conversational response with AI"""
    conversation_id = context.get('conversation_id')
    
    if conversation_id and conversation_id in ai_conversation_instances:
        ai_survey = ai_conversation_instances[conversation_id]
        return ai_survey.process_user_response(user_input, context)
    else:
        # Fallback - create new instance
        ai_survey = AIConversationalSurvey()
        ai_survey.survey_data = context
        ai_conversation_instances[conversation_id] = ai_survey
        return ai_survey.process_user_response(user_input, context)

def finalize_ai_conversational_survey(context: Dict[str, Any]) -> Dict[str, Any]:
    """Finalize and convert AI conversational survey to structured format"""
    conversation_id = context.get('conversation_id')
    
    print(f"Finalizing conversation {conversation_id}")
    print(f"Available instances: {list(ai_conversation_instances.keys())}")
    
    if conversation_id and conversation_id in ai_conversation_instances:
        ai_survey = ai_conversation_instances[conversation_id]
        
        print(f"Found AI survey instance with extracted data: {ai_survey.extracted_data}")
        
        # Use the extracted data from the AI survey instance
        finalization_context = {
            'company_name': ai_survey.survey_data.get('company_name'),
            'respondent_name': ai_survey.survey_data.get('respondent_name'),
            'respondent_email': context.get('respondent_email')
        }
        
        result = ai_survey.finalize_survey(finalization_context)
        print(f"Finalized result: {result}")
        
        # Clean up the instance
        del ai_conversation_instances[conversation_id]
        return result
    else:
        print("No conversation instance found - using fallback")
        # Enhanced fallback - try to extract from context
        survey_data = context.get('survey_data', {})
        extracted_data = survey_data.get('extracted_data', {})
        
        print(f"Fallback survey_data: {survey_data}")
        print(f"Fallback extracted_data: {extracted_data}")
        
        return {
            'company_name': context.get('company_name') or survey_data.get('company_name'),
            'respondent_name': context.get('respondent_name') or survey_data.get('respondent_name'),
            'respondent_email': context.get('respondent_email'),
            'nps_score': extracted_data.get('nps_score'),
            'nps_category': extracted_data.get('nps_category'),
            'satisfaction_rating': extracted_data.get('satisfaction_rating'),
            'improvement_feedback': extracted_data.get('improvement_feedback'),
            'recommendation_reason': extracted_data.get('nps_reasoning'),
            'additional_comments': extracted_data.get('additional_comments'),
            'conversation_history': context.get('conversation_history', json.dumps([]))
        }