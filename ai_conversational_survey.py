import os
import json
import uuid
from typing import Dict, Any, List
from openai import OpenAI

def normalize_company_name(company_name):
    """Normalize company name for case-insensitive comparison"""
    if not company_name:
        return company_name
    # Convert to title case for consistent display (first letter caps, rest lowercase)
    return company_name.strip().title()

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
        # CRITICAL FIX: Preserve any pre-populated extracted_data (like tenure from form)
        # The extracted_data might already be set by start_ai_conversational_survey
        existing_extracted_data = self.extracted_data.copy() if hasattr(self, 'extracted_data') and self.extracted_data else {}
        
        print(f"CRITICAL DEBUG: Pre-conversation extracted_data: {existing_extracted_data}")
        
        self.survey_data = {
            'company_name': company_name,
            'respondent_name': respondent_name,
            'conversation_history': [],
            'extracted_data': existing_extracted_data  # Preserve the pre-populated data
        }
        
        # CRITICAL: Keep reference to extracted_data intact
        self.extracted_data = self.survey_data['extracted_data']
        
        # Debug logging
        print(f"STARTUP DEBUG: After initialization, extracted_data: {self.extracted_data}")
        
        welcome_message = self._generate_welcome_message(company_name, respondent_name)
        
        self.conversation_history.append({
            'sender': 'Voxa',
            'message': welcome_message,
            'timestamp': 'now'
        })
        
        return {
            'message': welcome_message,
            'message_type': 'welcome',
            'step': 'welcome',
            'progress': 10,
            'is_complete': False,
            'conversation_id': str(uuid.uuid4()),
            'extracted_data': self.extracted_data  # Include initial extracted data
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
        
        # Track what was just extracted for debugging - but PREVENT overwrites of existing data
        newly_extracted = {}
        for key, value in extracted.items():
            if value is not None:
                # CRITICAL: Only update if we don't already have this data to prevent overwrites
                if self.extracted_data.get(key) is None:
                    newly_extracted[key] = value
                    self.extracted_data[key] = value
                    print(f"LOCKED DATA: {key} = {value} (first time captured)")
                else:
                    # Data already exists, don't overwrite - log the attempt
                    existing_value = self.extracted_data.get(key)
                    print(f"DATA PROTECTION: Prevented overwrite of {key}. Keeping existing: {existing_value}, AI suggested: {value}")
        
        self.survey_data['extracted_data'] = self.extracted_data
        
        # Increment step count BEFORE generating next question
        self.step_count += 1
        
        print(f"Step {self.step_count}: Extracted data: {newly_extracted}")
        print(f"Total extracted so far: {self.extracted_data}")
        
        # Debug print
        print(f"Step {self.step_count}: User said: '{user_input}'")
        print(f"Extracted data: {extracted}")
        print(f"Full extracted data: {self.extracted_data}")
        
        # ANTI-LOOP PROTECTION: Prevent infinite loops but allow service questions
        if self.step_count > 8:
            print("LOOP PROTECTION: Forcing completion after 8 steps")
            self.is_complete = True
            return {
                'message': "Thank you so much for your detailed feedback about Archelo Group! Your insights are very valuable.",
                'message_type': 'completion',
                'step': 'forced_complete',
                'progress': 100,
                'is_complete': True
            }
        
        # Check if we have enough data to complete
        if self._check_completion_criteria():
            next_question = {
                'message': "Thank you so much for taking the time to share your detailed feedback about Archelo Group! Your insights are incredibly valuable and will help us improve our service delivery. Have a wonderful day!",
                'message_type': 'completion',
                'step': 'complete',
                'progress': 100,
                'is_complete': True
            }
            self.is_complete = True
        else:
            # Generate next AI question using updated data
            next_question = self._generate_ai_question(user_input, context)
        
        # Add AI response to conversation history
        if not next_question.get('is_complete', False):
            self.conversation_history.append({
                'sender': 'Voxa',
                'message': next_question['message'],
                'timestamp': 'now'
            })
        
        # Debug logging
        print(f"Step {self.step_count}: Extracted data: {self.extracted_data}")
        print(f"Next question: {next_question.get('message', '')}")
        
        # Add extracted_data to response for frontend state sync
        next_question['extracted_data'] = self.extracted_data
        return next_question
    
    def _generate_welcome_message(self, company_name: str, respondent_name: str) -> str:
        """Generate personalized welcome message with Archelo Group introduction"""
        # Always use the new Archelo Group introduction and go directly to NPS
        return f"Hi {respondent_name}, we'd love to hear from you.\n\nArchelo is on a mission to make workplace tools less painful, and your feedback makes us better.\n\nThis short conversation will help us understand what's working, what's not, and how to improve your experience with ArcheloFlow.\n\nOn a scale of 0-10, how likely are you to recommend Archelo Group to a friend or colleague?"
    
    def _extract_survey_data_with_ai(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured survey data from natural language using OpenAI"""
        try:
            # Get list of already captured data to prevent overwrites
            locked_fields = [key for key, value in self.extracted_data.items() if value is not None]
            
            prompt = f"""Extract survey data from this customer response: "{user_input}"

Context of conversation:
- Company: {context.get('company_name', 'Unknown')}
- Current extracted data: {json.dumps(self.extracted_data, indent=2)}
- Conversation step: {self.step_count}
- ALREADY CAPTURED (DO NOT RE-EXTRACT): {locked_fields}

CRITICAL INSTRUCTION: Only extract NEW information from this specific response. 
DO NOT re-extract or change data that was already captured in previous responses.

Extract any of the following data present in the response:
- Tenure with Archelo Group: Look for duration mentions like "6 months", "2 years", "less than 6 months", etc.
- NPS score (0-10): Look for numbers, recommendations, likelihood scores
- Satisfaction level (1-5): Look for satisfaction, happiness, contentment indicators
- Service quality rating (1-5): Look for professional services, service delivery ratings
- Product value rating (1-5): Look for product quality, solution value, deliverable satisfaction
- Pricing rating (1-5): Look for pricing value, cost appreciation, pricing satisfaction
- Support rating (1-5): Look for customer service, support quality, help desk ratings
- Improvement suggestions: Any feedback about what could be better
- Compliments: What they liked or appreciated
- Complaints: What they didn't like or found problematic
- Reasons: Why they gave their rating or recommendation
- Additional comments: Any other relevant feedback

Return ONLY JSON in this format:
{{
    "tenure_with_archelo": string or null,
    "nps_score": number or null,
    "nps_category": "Promoter/Passive/Detractor" or null,
    "satisfaction_rating": number or null,
    "service_rating": number or null,
    "product_value_rating": number or null,
    "pricing_rating": number or null,
    "support_rating": number or null,
    "improvement_feedback": "text" or null,
    "compliment_feedback": "text" or null,
    "complaint_feedback": "text" or null,
    "nps_reasoning": "text" or null,
    "additional_comments": "text" or null
}}

Only include fields that are clearly present in the response. If a field is not mentioned, use null.

IMPORTANT: If data was already captured (listed in ALREADY CAPTURED above), return null for those fields to prevent overwrites."""

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
        
        # Extract NPS score - only if we're in the NPS collection step and don't have it yet
        import re
        
        # Extract NPS score if we don't have it yet and input looks like a number
        if not self.extracted_data.get('nps_score') and re.search(r'\b([0-9]|10)\b', user_input):
            print(f"Attempting NPS extraction at step {self.step_count} for input: '{user_input}'")
            nps_patterns = [
                r'(?:score|rating|give|rate).*?(10|[0-9])',  # Fixed: 10 before single digits
                r'^(10|[0-9])(?:\s|$|/|,|\.)',
                r'(10|[0-9])\s*(?:out of 10|/10)',
                r'(?:i.*d.*say|i.*d.*give|i.*d.*rate).*?(10|[0-9])',  # Fixed order
                r'(?:probably|maybe|around|about).*?(10|[0-9])',
                r'\b(10|[0-9])\b(?!\d)',  # Fixed: Check for 10 first
                r'(10|[0-9])',  # Fixed order
                r'(?:is|was|would be|rating|score).*?(10|[0-9])',
                r'(10|[0-9])(?:\s*(?:stars?|points?|rating))?'  # Fixed order
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
                        print(f"FIRST TIME NPS CAPTURE (FALLBACK): {score} - LOCKED")
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
        
        # Service quality rating keywords
        service_keywords = {
            5: ['excellent service', 'outstanding service', 'perfect service', 'amazing service', 'superb service'],
            4: ['good service', 'great service', 'quality service', 'professional service', 'solid service'],
            3: ['average service', 'okay service', 'standard service', 'fair service', 'decent service'],
            2: ['poor service', 'bad service', 'lacking service', 'subpar service', 'disappointing service'],
            1: ['terrible service', 'awful service', 'horrible service', 'worst service', 'unacceptable service']
        }
        
        # Product value keywords
        product_keywords = {
            5: ['excellent product', 'outstanding product', 'amazing product', 'perfect solution', 'superb deliverables'],
            4: ['good product', 'quality product', 'solid solution', 'valuable deliverables', 'great outcome'],
            3: ['average product', 'okay solution', 'standard deliverables', 'fair outcome', 'decent product'],
            2: ['poor product', 'lacking solution', 'disappointing deliverables', 'subpar outcome', 'weak product'],
            1: ['terrible product', 'awful solution', 'horrible deliverables', 'worst outcome', 'useless product']
        }
        
        # Pricing appreciation keywords
        pricing_keywords = {
            5: ['excellent value', 'outstanding value', 'great value', 'fantastic value', 'amazing value', 'perfect price'],
            4: ['good value', 'fair value', 'reasonable price', 'worth it', 'good price'],
            3: ['fair price', 'average price', 'okay price', 'standard pricing', 'acceptable price'],
            2: ['expensive', 'pricey', 'costly', 'overpriced', 'high price'],
            1: ['very expensive', 'too expensive', 'way overpriced', 'ridiculously expensive', 'unaffordable']
        }
        
        # Support services keywords
        support_keywords = {
            5: ['excellent support', 'outstanding support', 'amazing support', 'perfect support', 'superb support'],
            4: ['good support', 'helpful support', 'responsive support', 'quality support', 'solid support'],
            3: ['average support', 'okay support', 'standard support', 'fair support', 'decent support'],
            2: ['poor support', 'slow support', 'unhelpful support', 'lacking support', 'bad support'],
            1: ['terrible support', 'awful support', 'horrible support', 'worst support', 'no support']
        }
        
        for rating, keywords in satisfaction_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                extracted['satisfaction_rating'] = rating
                break
        
        # Extract service quality ratings
        for rating, keywords in service_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                extracted['service_rating'] = rating
                break
        
        # Extract product value ratings
        for rating, keywords in product_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                extracted['product_value_rating'] = rating
                break
        
        # Extract pricing ratings
        for rating, keywords in pricing_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                extracted['pricing_rating'] = rating
                break
        
        # Extract support ratings
        for rating, keywords in support_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                extracted['support_rating'] = rating
                break
        
        # Extract tenure information - only if we're answering the tenure question (step_count will be 1 when processing tenure response)
        if not self.extracted_data.get('tenure_with_archelo') and self.step_count == 1:
            tenure_patterns = {
                'Less than 6 months': ['less than 6 months', 'under 6 months', 'few months', '3 months', '4 months', '5 months'],
                '6 months - 1 year': ['6 months', 'seven months', '8 months', '9 months', '10 months', '11 months', 'about a year'],
                '1-2 years': ['1 year', '2 years', 'one year', 'two years', '18 months', 'year and half'],
                '2-3 years': ['2 years', '3 years', 'two years', 'three years', '30 months'],
                '3-5 years': ['3 years', '4 years', '5 years', 'three years', 'four years', 'five years'],
                '5-10 years': ['5 years', '6 years', '7 years', '8 years', '9 years', '10 years', 'decade'],
                'More than 10 years': ['more than 10 years', 'over 10 years', '11 years', '15 years', '20 years', 'decades']
            }
            
            for tenure_option, patterns in tenure_patterns.items():
                if any(pattern in text_lower for pattern in patterns):
                    extracted['tenure_with_archelo'] = tenure_option
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
        
        # Store reasoning if it seems like reasoning OR if it's any substantive response
        reasoning_indicators = ['because', 'since', 'due to', 'reason', 'why', 'that\'s why', 'good', 'bad', 'great', 'poor', 'like', 'dislike', 'satisfied', 'happy', 'disappointed']
        if any(indicator in text_lower for indicator in reasoning_indicators) or len(user_input.strip()) > 5:
            extracted['nps_reasoning'] = user_input
        
        # Always store as additional comments for context
        extracted['additional_comments'] = user_input
        
        return extracted
    
    def _check_completion_criteria(self) -> bool:
        """Check if we have enough data to complete the survey"""
        # Core requirements
        has_nps = self.extracted_data.get('nps_score') is not None
        has_reasoning = self.extracted_data.get('nps_reasoning') is not None or self.extracted_data.get('compliment_feedback') is not None or self.extracted_data.get('complaint_feedback') is not None or self.extracted_data.get('additional_comments') is not None
        has_tenure = self.extracted_data.get('tenure_with_archelo') is not None
        
        # Additional data points
        has_satisfaction = self.extracted_data.get('satisfaction_rating') is not None
        has_service = self.extracted_data.get('service_rating') is not None
        has_improvement = self.extracted_data.get('improvement_feedback') is not None
        
        # BALANCED COMPLETION LOGIC: Get key data but prevent loops
        # Core data: NPS + tenure + reasoning  
        has_core = has_nps and has_tenure and has_reasoning
        
        # Prefer to get at least one service rating
        has_service_feedback = has_satisfaction or has_service or has_improvement
        
        # BALANCED APPROACH: Try to get service feedback but don't loop forever
        has_sufficient_data = has_core and has_service_feedback
        
        # Progressive completion thresholds
        enough_steps = self.step_count >= 5  # Allow a bit more time for service questions
        force_complete = self.step_count >= 7  # Still force completion to prevent loops
        
        # Complete if we have sufficient data OR enough steps OR force
        completion_ready = has_sufficient_data or enough_steps or force_complete
        
        print(f"COMPLETION CHECK: NPS={has_nps}, Tenure={has_tenure}, Reasoning={has_reasoning}, Service={has_service_feedback}, Steps={self.step_count}, Ready={completion_ready}")
        
        return completion_ready
    
    def _get_next_question_priority(self) -> str:
        """Determine what question should be asked next based on collected data"""
        data = self.extracted_data
        
        # Check what we have and what we need
        if not data.get('tenure_with_archelo'):
            return "Ask about business relationship tenure with Archelo Group (how long working together)"
        elif not data.get('nps_score'):
            return "Ask for NPS score (0-10 likelihood to recommend Archelo Group)"
        elif not data.get('nps_reasoning'):
            return "Ask WHY they gave that NPS score - what's their reasoning about Archelo Group"
        elif not data.get('satisfaction_rating'):
            return "Ask for overall satisfaction rating (1-5) with Archelo Group"
        elif not data.get('service_rating'):
            return "Ask for professional services quality rating (1-5) from Archelo Group"
        elif not data.get('improvement_feedback'):
            return "Ask what Archelo Group could do better or improve"
        else:
            return "Wrap up the conversation - you have enough information"
    
    def _generate_ai_question(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate next question using OpenAI"""
        try:
            # Format conversation history for context
            history_text = self._format_conversation_history()
            
            prompt = f"""You are conducting a customer feedback survey about Archelo Group (the supplier company). Focus on Archelo Group's service delivery, support quality, and business relationship aspects.

CONVERSATION HISTORY:
{history_text}

CUSTOMER'S LATEST RESPONSE: "{user_input}"

SURVEY DATA COLLECTED SO FAR:
{json.dumps(self.extracted_data, indent=2)}

CONVERSATION STEP: {self.step_count}

NEXT LOGICAL QUESTION PRIORITY:
{self._get_next_question_priority()}

YOUR ROLE: You are a helpful customer feedback specialist having a natural conversation. Your goal is to collect feedback about Archelo Group:
1. Business relationship tenure - How long working with Archelo Group
2. NPS score (0-10) - How likely to recommend Archelo Group
3. Reason for their NPS score about Archelo Group
4. Satisfaction level (1-5) - Overall satisfaction with Archelo Group
5. Professional services quality rating (1-5) - Quality of Archelo Group's professional services
6. Product value rating (1-5) - Value and quality of Archelo Group's products/solutions
7. Pricing appreciation rating (1-5) - How they feel about Archelo Group's pricing value
8. Support services rating (1-5) - Quality of Archelo Group's support and customer service
9. Improvement suggestions - What could Archelo Group do better
10. Additional feedback - Any other comments about Archelo Group

GUIDELINES:
- Keep the conversation natural and engaging
- Ask ONE question at a time
- CRITICALLY IMPORTANT: DON'T ask for information you already have (check SURVEY DATA COLLECTED SO FAR)
- If tenure_with_archelo is already known, NEVER ask about it again
- Look at what you have already collected and ask for what's missing logically
- If you have NPS score but no reasoning, ask WHY they gave that score
- If you have tenure but no satisfaction rating, ask about satisfaction
- Reference their previous responses to show you're listening
- If they mention specific issues, ask thoughtful follow-ups
- If they seem rushed, be more direct
- If they're chatty, engage with their details
- Move through the survey logically: tenure → NPS → reasoning → ratings → improvements
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
        print(f"Current extracted data: {self.extracted_data}")
        print(f"Tenure from extracted_data: {self.extracted_data.get('tenure_with_archelo')}")
        print(f"NPS from extracted_data: {self.extracted_data.get('nps_score')}")
        
        # FIXED: Special case handling without step manipulation
        if (self.extracted_data.get('tenure_with_archelo') is not None and 
            self.extracted_data.get('nps_score') is not None and 
            not self.extracted_data.get('nps_reasoning') and
            self.step_count <= 4):
            score = self.extracted_data['nps_score']
            if score >= 9:
                return {
                    'message': f"Wonderful! A {score} is fantastic. What specifically about Archelo Group made your experience so great?",
                    'message_type': 'ai_question',
                    'step': 'nps_reasoning',
                    'progress': 40,
                    'is_complete': False
                }
            elif score >= 7:
                return {
                    'message': f"Thanks for the {score}! What would it take to make you even more likely to recommend Archelo Group?",
                    'message_type': 'ai_question',
                    'step': 'nps_reasoning',
                    'progress': 40,
                    'is_complete': False
                }
            else:
                return {
                    'message': f"I appreciate your honesty with the {score}. What are the main issues that are holding you back from recommending Archelo Group?",
                    'message_type': 'ai_question',
                    'step': 'nps_reasoning',
                    'progress': 40,
                    'is_complete': False
                }
        
        # Use step-based progression but check if we already have tenure data
        if self.step_count == 1:
            # First question: Ask for tenure with Archelo Group ONLY if we don't have it
            if self.extracted_data.get('tenure_with_archelo') is None:
                return {
                    'message': "How long have you been working with Archelo Group? Please choose from: Less than 6 months, 6 months - 1 year, 1-2 years, 2-3 years, 3-5 years, 5-10 years, or More than 10 years.",
                    'message_type': 'ai_question',
                    'step': 'tenure_collection',
                    'progress': 15,
                    'is_complete': False
                }
            else:
                # We already have tenure, skip to NPS question
                # Don't manipulate step count - let natural progression continue
                return {
                    'message': "On a scale of 0-10, how likely are you to recommend Archelo Group to a friend or colleague?",
                    'message_type': 'ai_question',
                    'step': 'nps_collection',
                    'progress': 25,
                    'is_complete': False
                }

        if self.step_count == 2:
            # Second question: Ask for NPS about Archelo Group (the supplier) ONLY if we don't have it
            if self.extracted_data.get('nps_score') is None:
                return {
                    'message': "On a scale of 0-10, how likely are you to recommend Archelo Group to a friend or colleague?",
                    'message_type': 'ai_question',
                    'step': 'nps_collection',
                    'progress': 25,
                    'is_complete': False
                }
            else:
                # We already have NPS score from previous data, go to step 3 logic
                pass  # Fall through to step 3 logic
        
        if self.step_count == 3:
            # Check if we just got NPS score and need to ask reasoning question
            if extracted.get('nps_score') is not None or self.extracted_data.get('nps_score') is not None:
                # We just got the NPS score, ask for reasoning
                score = extracted.get('nps_score') or self.extracted_data.get('nps_score')
                if score >= 9:
                    return {
                        'message': f"Wonderful! A {score} is fantastic. What specifically about Archelo Group made your experience so great?",
                        'message_type': 'ai_question',
                        'step': 'nps_reasoning',
                        'progress': 40,
                        'is_complete': False
                    }
                elif score >= 7:
                    return {
                        'message': f"Thanks for the {score}! What would it take to make you even more likely to recommend Archelo Group?",
                        'message_type': 'ai_question',
                        'step': 'nps_reasoning',
                        'progress': 40,
                        'is_complete': False
                    }
                else:
                    return {
                        'message': f"I appreciate your honesty with the {score}. What are the main issues that are holding you back from recommending Archelo Group?",
                        'message_type': 'ai_question',
                        'step': 'nps_reasoning',
                        'progress': 40,
                        'is_complete': False
                    }
            else:
                # Third question: We should have already asked the NPS reasoning question
                # This response is the user's answer to the NPS reasoning question
                # Move to satisfaction question
                return {
                    'message': "How would you describe your overall satisfaction with Archelo Group's service? Very satisfied, satisfied, neutral, dissatisfied, or very dissatisfied?",
                    'message_type': 'ai_question',
                    'step': 'satisfaction',
                    'progress': 40,
                    'is_complete': False
                }
        
        elif self.step_count == 4:
            # Fourth question: Overall satisfaction rating
            return {
                'message': "How would you describe your overall satisfaction with Archelo Group's service? Very satisfied, satisfied, neutral, dissatisfied, or very dissatisfied?",
                'message_type': 'ai_question',
                'step': 'satisfaction',
                'progress': 45,
                'is_complete': False
            }
        
        elif self.step_count == 5:
            # Fifth question: Professional services quality rating
            return {
                'message': "How would you rate the quality of Archelo Group's professional services? Excellent, good, average, poor, or very poor?",
                'message_type': 'ai_question',
                'step': 'service_quality',
                'progress': 50,
                'is_complete': False
            }
        
        elif self.step_count == 6:
            # Sixth question: Product value rating
            return {
                'message': "How would you rate the value and quality of Archelo Group's products or solutions? Excellent, good, average, poor, or very poor?",
                'message_type': 'ai_question',
                'step': 'product_value',
                'progress': 55,
                'is_complete': False
            }
        
        elif self.step_count == 7:
            # Seventh question: Pricing appreciation rating
            return {
                'message': "How do you feel about Archelo Group's pricing? Do you find it excellent value, good value, fair, expensive, or very expensive?",
                'message_type': 'ai_question',
                'step': 'pricing_value',
                'progress': 65,
                'is_complete': False
            }
        
        elif self.step_count == 8:
            # Eighth question: Support services rating
            return {
                'message': "How would you rate Archelo Group's support and customer service? Excellent, good, average, poor, or very poor?",
                'message_type': 'ai_question',
                'step': 'support_quality',
                'progress': 75,
                'is_complete': False
            }
        
        elif self.step_count == 9:
            # Ninth question: Improvement suggestions
            if extracted.get('nps_score', 0) < 7:
                return {
                    'message': "What specific changes would make the biggest difference in improving your experience with Archelo Group?",
                    'message_type': 'ai_question',
                    'step': 'improvement',
                    'progress': 85,
                    'is_complete': False
                }
            else:
                return {
                    'message': "Is there anything Archelo Group could do even better to enhance your experience?",
                    'message_type': 'ai_question',
                    'step': 'improvement',
                    'progress': 85,
                    'is_complete': False
                }
        
        # Step 10 or higher: Complete the survey
        else:
            return {
                'message': "Thank you so much for sharing your valuable feedback about Archelo Group! Your insights help improve their service for everyone.",
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
            'company_name': normalize_company_name(context.get('company_name')),
            'respondent_name': context.get('respondent_name'),
            'respondent_email': context.get('respondent_email'),
            'tenure_with_archelo': extracted.get('tenure_with_archelo'),
            'nps_score': nps_score,
            'nps_category': nps_category,
            'satisfaction_rating': extracted.get('satisfaction_rating'),
            'service_rating': extracted.get('support_rating') or extracted.get('service_rating'),  # Support questions map to service_rating
            'pricing_rating': extracted.get('pricing_rating'),
            'product_value_rating': extracted.get('product_value_rating'),  # Product value rating
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

def start_ai_conversational_survey(company_name: str, respondent_name: str, tenure_with_archelo: str = None) -> Dict[str, Any]:
    """Start a new AI-powered conversational survey session"""
    conversation_id = str(uuid.uuid4())
    ai_survey = AIConversationalSurvey()
    
    # If tenure data is provided from the form, pre-populate it
    if tenure_with_archelo:
        ai_survey.extracted_data['tenure_with_archelo'] = tenure_with_archelo
        print(f"Pre-populated tenure from form: {tenure_with_archelo}")
    
    result = ai_survey.start_conversation(company_name, respondent_name)
    result['conversation_id'] = conversation_id
    
    # Store instance for session persistence
    ai_conversation_instances[conversation_id] = ai_survey
    
    return result

def process_ai_conversation_response(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Process user's conversational response with AI"""
    conversation_id = context.get('conversation_id')
    
    print(f"DEBUG: Processing conversation_id: {conversation_id}")
    print(f"DEBUG: Available instances: {list(ai_conversation_instances.keys())}")
    print(f"DEBUG: Context keys: {list(context.keys())}")
    
    if conversation_id and conversation_id in ai_conversation_instances:
        ai_survey = ai_conversation_instances[conversation_id]
        print(f"DEBUG: Found existing instance with step {ai_survey.step_count}, extracted data: {ai_survey.extracted_data}")
        return ai_survey.process_user_response(user_input, context)
    else:
        print(f"WARNING: No instance found for conversation_id {conversation_id}, recreating from context")
        print(f"AVAILABLE INSTANCES: {ai_conversation_instances}")
        
        # RECOVERY: Recreate the conversation instance from context data
        ai_survey = AIConversationalSurvey()
        
        # Restore survey data from context
        company_name = context.get('company_name', '')
        respondent_name = context.get('respondent_name', '')
        
        # Initialize the survey data with context
        ai_survey.survey_data = {
            'company_name': company_name,
            'respondent_name': respondent_name,
            'conversation_history': context.get('conversation_history', []),
            'extracted_data': context.get('extracted_data', {})
        }
        
        # Set extracted data from context
        ai_survey.extracted_data = ai_survey.survey_data['extracted_data']
        
        # Try to restore step count from context or estimate it
        ai_survey.step_count = context.get('step_count', len(context.get('conversation_history', [])) // 2)
        
        print(f"RECOVERY: Recreated instance with step {ai_survey.step_count}, extracted data: {ai_survey.extracted_data}")
        
        # Store the recreated instance
        if conversation_id:
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
        
        raw_company_name = context.get('company_name') or survey_data.get('company_name')
        return {
            'company_name': normalize_company_name(raw_company_name),
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