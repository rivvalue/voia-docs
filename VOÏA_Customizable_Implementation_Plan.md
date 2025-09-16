# VOÏA Customizable Survey System - Implementation Plan & Requirements

## Overview

This document outlines the implementation plan for transforming the current hardcoded VOÏA conversational survey system into a fully customizable multi-tenant platform. The new system will maintain the existing trial/demo functionality while enabling enterprise customers to create industry-specific, branded conversational surveys.

## Current State Analysis

### Existing System
- **Hardcoded Company**: Archelo Group / ArcheloFlow
- **Fixed Prompts**: References Archelo Group's professional services and business relationships
- **Single Flow**: All conversations follow same pattern regardless of client
- **Demo Mode**: Public trial using Archelo Group surveys, data aggregated in demo dashboard
- **Analytics**: Robust dashboard and KPI system processing structured survey data

### Trial/Demo Requirements (MUST PRESERVE)
- Public visitors access demo page with consistent "Archelo Group/ArcheloFlow" experience
- All trial surveys link to `business_account.account_type = "demo"`
- Demo dashboard shows aggregated trial data from all public users
- Zero changes to trial user experience during migration

## New VOÏA System Requirements

### 1. Company Profile Customization

#### Required Fields
```
Company Name: [String, 200 chars] - Used throughout conversation
Industry: [Dropdown] - Healthcare, SaaS, Retail, Professional Services, Restaurant, Manufacturing, Education, Finance, Other
Company Description: [Text, 500 chars] - "We provide cloud-based accounting solutions for small businesses"
Product/Service Description: [Text, 500 chars] - "Our flagship product ArcheloFlow helps streamline workflow management"
Target Customers: [Text, 300 chars] - "Small business owners, CFOs, accounting firms"
Conversation Tone: [Dropdown] - Professional, Warm & Friendly, Casual, Formal
Survey Goals: [Multi-select] - NPS, Satisfaction, Product Feedback, Support Quality, Pricing Perception, Custom
```

#### Industry-Specific Defaults
```
Healthcare: Focus on "patient experience", "care quality", "appointment scheduling"
SaaS: Focus on "user onboarding", "feature requests", "API documentation" 
Retail: Focus on "shopping experience", "product quality", "customer service"
Restaurant: Focus on "dining experience", "food quality", "service speed"
```

### 2. Survey Flow Controls

#### Pace & Timing Parameters
```json
{
  "max_questions": {
    "type": "integer",
    "range": [3, 15],
    "default": 8,
    "description": "Absolute hard stop for conversation length"
  },
  "max_duration_seconds": {
    "type": "integer", 
    "range": [60, 300],
    "default": 120,
    "description": "Time limit for entire conversation"
  },
  "max_follow_ups_per_topic": {
    "type": "integer",
    "range": [1, 3], 
    "default": 2,
    "description": "Control topic depth exploration"
  },
  "response_timeout_seconds": {
    "type": "integer",
    "range": [30, 120],
    "default": 60,
    "description": "Individual response timeout"
  }
}
```

#### Topic Prioritization
```json
{
  "prioritized_topics": {
    "type": "array",
    "options": ["NPS", "Satisfaction", "Product Quality", "Service Rating", "Support Experience", "Pricing Value", "Improvement Suggestions"],
    "default": ["NPS", "Product Quality", "Support Experience"],
    "description": "Topics to cover first, in order"
  },
  "optional_topics": {
    "type": "array", 
    "options": ["Pricing Value", "Additional Comments"],
    "default": ["Pricing Value"],
    "description": "Topics to skip if time/questions run out"
  },
  "required_topics": {
    "type": "array",
    "options": ["NPS"],
    "default": ["NPS"],
    "description": "Topics that must be covered"
  }
}
```

### 3. Dynamic Prompt Template System

#### Master Template Structure
```
You are VOÏA, an AI-powered conversational feedback agent. You are conducting a Voice of Client session on behalf of {{company_name}}.

Company Profile:
• Name: {{company_name}}
• Industry: {{industry}}
• Description: {{company_description}}
• Product/Service: {{product_description}}
• Customers: {{target_clients_description}}
• Tone: {{conversation_tone}}
• Survey Goals: {{survey_goals}}

Survey Parameters:
• Maximum Questions: {{max_questions}}
• Time Limit: {{max_duration_seconds}} seconds
• Prioritized Topics: {{prioritized_topics}}
• Optional Topics: {{optional_topics}}
• Follow-ups per Topic: {{max_follow_ups_per_topic}}

Conversation Guidelines:
- Adapt your language to match the {{conversation_tone}} tone
- Focus conversation on {{industry}}-specific terminology and concerns
- Ask about their experience with {{product_description}}
- Reference {{target_clients_description}} context when relevant
- Prioritize {{prioritized_topics}} and skip {{optional_topics}} if time is short
- Keep responses natural and engaging while collecting structured data

Your goal is to collect feedback about {{company_name}} focusing on: {{survey_goals}}
```

#### Industry-Specific Prompt Variations

**Healthcare Template Additions:**
```
Healthcare Context:
- Ask about "patient experience" instead of "user experience"
- Focus on "care quality", "appointment scheduling", "staff professionalism"
- Use respectful, empathetic tone for health-related feedback
- Prioritize patient safety and satisfaction themes
```

**SaaS Template Additions:**
```
SaaS Context:
- Ask about "onboarding experience", "feature usability", "technical support"
- Focus on "product functionality", "integration challenges", "user adoption"
- Use technical terminology appropriately for the user type
- Prioritize product improvement and user success themes
```

**Restaurant Template Additions:**
```
Restaurant Context:
- Ask about "dining experience", "food quality", "service speed", "ambiance"
- Focus on "meal satisfaction", "staff friendliness", "atmosphere"
- Use warm, hospitality-focused language
- Prioritize food quality and service experience themes
```

### 4. Account Type Conditional Logic

#### Demo Mode (account_type = "demo")
```python
# Fixed behavior - NO customization
company_profile = {
    "company_name": "Archelo Group",
    "product_name": "ArcheloFlow", 
    "industry": "Professional Services",
    "tone": "professional",
    "focus": "business relationship and service delivery"
}
# Use existing hardcoded prompts exactly as they are now
```

#### Customer Mode (account_type = "customer")
```python
# Dynamic behavior - FULL customization
company_profile = load_business_account_customization(business_account_id)
if company_profile.is_complete():
    use_custom_template(company_profile)
else:
    use_default_template_with_company_name(business_account.name)
```

### 5. Data Structure Requirements

#### Survey Response Output (UNCHANGED)
The customizable system must produce identical output structure to maintain analytics compatibility:

```json
{
  "company_name": "string",
  "respondent_name": "string", 
  "respondent_email": "string",
  "nps_score": "integer",
  "nps_category": "string",
  "satisfaction_rating": "integer",
  "service_rating": "integer", 
  "pricing_rating": "integer",
  "product_value_rating": "integer",
  "improvement_feedback": "text",
  "recommendation_reason": "text",
  "additional_comments": "text",
  "conversation_history": "json"
}
```

#### Business Account Extensions
```sql
-- Add to existing business_accounts table
ALTER TABLE business_accounts ADD COLUMN industry VARCHAR(100);
ALTER TABLE business_accounts ADD COLUMN company_description TEXT;
ALTER TABLE business_accounts ADD COLUMN product_description TEXT;
ALTER TABLE business_accounts ADD COLUMN target_clients_description TEXT;
ALTER TABLE business_accounts ADD COLUMN conversation_tone VARCHAR(50) DEFAULT 'professional';
ALTER TABLE business_accounts ADD COLUMN survey_goals JSON;
ALTER TABLE business_accounts ADD COLUMN max_questions INTEGER DEFAULT 8;
ALTER TABLE business_accounts ADD COLUMN max_duration_seconds INTEGER DEFAULT 120;
ALTER TABLE business_accounts ADD COLUMN max_follow_ups_per_topic INTEGER DEFAULT 2;
ALTER TABLE business_accounts ADD COLUMN prioritized_topics JSON;
ALTER TABLE business_accounts ADD COLUMN optional_topics JSON;
ALTER TABLE business_accounts ADD COLUMN custom_end_message TEXT;
ALTER TABLE business_accounts ADD COLUMN custom_system_prompt TEXT;
ALTER TABLE business_accounts ADD COLUMN prompt_template_version VARCHAR(10) DEFAULT 'v1.0';
```

## Implementation Plan

### Phase 1: Database Schema Extension (Week 1)

#### Objectives
- Add customization fields to BusinessAccount model
- Ensure demo accounts remain unaffected
- Create safe migration with defaults

#### Tasks
1. Create database migration script with new columns
2. Add NOT NULL constraints with sensible defaults
3. Create indexes for performance (industry, conversation_tone)
4. Test migration on copy of production data
5. Validate demo accounts remain unchanged

#### Acceptance Criteria
- All new fields added with nullable=True
- Demo accounts (`account_type = "demo"`) have NULL customization fields
- Customer accounts get default values
- No disruption to existing functionality

### Phase 2: Dual-Mode Backend Logic (Week 1-2)

#### Objectives
- Create conditional survey system based on account type
- Implement template engine for dynamic prompt generation
- Maintain existing demo behavior exactly

#### Tasks
1. **Account Type Detection System**
   ```python
   def get_survey_mode(business_account):
       if business_account.account_type == "demo":
           return "demo_mode"  # Use hardcoded Archelo prompts
       else:
           return "custom_mode"  # Use customizable templates
   ```

2. **Template Engine Development**
   - Dynamic prompt generation from business account fields
   - Fallback to demo mode if customization incomplete
   - Industry-specific template variations

3. **Conversation Flow Updates**
   - Respect max_questions limits
   - Implement topic prioritization logic
   - Add time-based conversation controls

4. **AI Integration Updates**
   - Modify `_generate_ai_question()` for conditional prompts
   - Update `_extract_survey_data_with_ai()` for custom contexts
   - Maintain same data extraction output format

#### Acceptance Criteria
- Demo accounts use exact current behavior
- Customer accounts can use custom templates
- Fallback logic prevents failures
- Same SurveyResponse data structure maintained

### Phase 3: Frontend UI for Customer Accounts (Week 2-3)

#### Objectives
- Create survey customization interface for customer accounts
- Hide customization from demo accounts
- Provide preview functionality

#### Tasks
1. **Branding Page Extension**
   - Add "Survey Customization" section
   - Company profile form fields
   - Survey control parameters
   - Account type guards (only show to customers)

2. **Form Components**
   ```html
   <!-- Company Profile Section -->
   Industry: <select> options based on predefined list
   Company Description: <textarea maxlength="500">
   Product Description: <textarea maxlength="500">
   Target Customers: <textarea maxlength="300">
   Conversation Tone: <select> Professional/Warm/Casual/Formal
   Survey Goals: <multi-select checkboxes>
   
   <!-- Survey Controls Section -->
   Max Questions: <range slider 3-15>
   Time Limit: <select> 60s/90s/120s/180s/No Limit
   Topic Priorities: <drag-and-drop sortable list>
   Optional Topics: <checkboxes>
   Custom End Message: <textarea>
   ```

3. **Preview System**
   - Show sample conversation with current settings
   - Real-time preview updates as settings change
   - Example questions for selected industry/tone

4. **Validation & Saving**
   - Required field validation
   - Character limit enforcement  
   - AJAX save functionality
   - Success/error feedback

#### Acceptance Criteria
- Only customer accounts see customization options
- Demo accounts see no customization UI
- All form fields have proper validation
- Preview accurately reflects settings
- Changes save successfully to database

### Phase 4: Template System Integration (Week 3-4)

#### Objectives
- Make AI use custom templates seamlessly
- Implement industry-specific conversation logic
- Ensure conversation quality across all customizations

#### Tasks
1. **Dynamic Prompt Generation**
   ```python
   def build_conversation_prompt(business_account, conversation_context):
       if business_account.account_type == "demo":
           return get_demo_prompts()
       
       template = load_industry_template(business_account.industry)
       return template.format(
           company_name=business_account.name,
           industry=business_account.industry,
           company_description=business_account.company_description,
           # ... other customization fields
       )
   ```

2. **Industry-Specific Logic**
   - Healthcare: Focus on patient experience, care quality
   - SaaS: Focus on user onboarding, feature requests
   - Retail: Focus on shopping experience, product quality
   - Restaurant: Focus on dining experience, food quality

3. **Conversation Flow Controls**
   - Question limit enforcement
   - Time limit tracking
   - Topic prioritization implementation
   - Optional topic skipping logic

4. **Quality Assurance**
   - Conversation coherence testing
   - Data extraction accuracy validation
   - Edge case handling (incomplete profiles)

#### Acceptance Criteria
- Custom conversations feel natural and industry-appropriate
- All survey controls work as specified
- Data extraction produces same output format
- Quality maintained across all customization combinations

### Phase 5: Data Migration & Default Population (Week 4)

#### Objectives
- Populate sensible defaults for existing customer accounts
- Preserve demo accounts completely
- Ensure smooth transition for existing users

#### Tasks
1. **Demo Account Protection**
   ```sql
   -- Ensure demo accounts have NO customization data
   UPDATE business_accounts 
   SET industry = NULL, company_description = NULL, conversation_tone = NULL
   WHERE account_type = 'demo';
   ```

2. **Customer Account Defaults**
   - Analyze existing account names for industry hints
   - Set default conversation tone to 'professional'
   - Set standard topic priorities: ["NPS", "Product Quality", "Support Experience"]
   - Set reasonable limits: 8 questions, 120 seconds

3. **Migration Script Development**
   ```python
   def migrate_existing_accounts():
       demo_accounts = BusinessAccount.query.filter_by(account_type='demo').all()
       # Skip demo accounts entirely
       
       customer_accounts = BusinessAccount.query.filter_by(account_type='customer').all()
       for account in customer_accounts:
           account.conversation_tone = 'professional'
           account.max_questions = 8
           account.max_duration_seconds = 120
           account.prioritized_topics = ["NPS", "Product Quality", "Support Experience"]
           account.optional_topics = ["Pricing Value"]
   ```

4. **Validation & Testing**
   - Test migration on production data copy
   - Verify demo functionality unchanged
   - Validate default values are reasonable

#### Acceptance Criteria
- Demo accounts remain completely unchanged
- Customer accounts get sensible defaults
- Migration script runs without errors
- All existing functionality continues working

### Phase 6: Comprehensive Testing (Week 4-5)

#### Objectives
- Ensure zero regression in existing functionality
- Validate new customization features work correctly
- Test edge cases and error scenarios

#### Testing Categories

1. **Demo Mode Validation**
   - Public demo page functions identically
   - Trial surveys reference "Archelo Group/ArcheloFlow"
   - Demo dashboard shows aggregated trial data correctly
   - No customization options visible to demo users

2. **Customer Customization Testing**
   - All industry templates produce coherent conversations
   - Survey controls work as specified (limits, priorities)
   - Custom branding appears correctly in conversations
   - Preview functionality matches actual conversations

3. **Data Integrity Testing**
   - Custom conversations produce valid SurveyResponse records
   - Analytics dashboard processes custom survey data correctly
   - No data corruption or loss during migration
   - Campaign and participant systems work with custom surveys

4. **Edge Case Testing**
   - Incomplete customization profiles
   - Extreme values (very short/long limits)
   - Special characters in company descriptions
   - Account type switching scenarios
   - AI prompt generation failures

5. **Performance Testing**
   - Custom prompt generation doesn't slow conversations
   - Database queries remain efficient with new fields
   - Large-scale conversation handling

#### Acceptance Criteria
- All existing functionality works unchanged
- New features meet requirements
- System handles edge cases gracefully
- Performance remains acceptable

### Phase 7: Controlled Deployment (Week 5)

#### Objectives
- Deploy safely with ability to monitor and rollback
- Validate production performance
- Ensure smooth user transition

#### Deployment Strategy

1. **Staging Deployment**
   - Deploy to staging with full production data copy
   - Run complete test suite
   - Performance testing with realistic load

2. **Demo Verification**
   - Confirm public trial experience unchanged
   - Test demo dashboard with live trial data
   - Validate all demo conversation flows

3. **Beta Customer Testing**
   - Select willing customer accounts for beta testing
   - Gather feedback on customization interface
   - Monitor custom conversation quality

4. **Production Deployment**
   - Deploy during low-traffic window
   - Enable feature flag for instant disable capability
   - Monitor system performance and error rates

5. **Post-Deployment Monitoring**
   - Track conversation completion rates
   - Monitor analytics data accuracy
   - Watch for any demo mode issues
   - Collect user feedback on new features

#### Rollback Strategy
- Feature flag to instantly disable customization
- Database rollback capability to pre-migration state
- Demo mode acts as permanent fallback
- Monitoring alerts for any issues

## Success Criteria

### Demo Mode Requirements (MUST MAINTAIN)
✅ Public demo page functions identically to current version  
✅ All trial surveys reference "Archelo Group/ArcheloFlow"  
✅ Demo dashboard shows aggregated trial analytics correctly  
✅ Zero changes to trial user experience  
✅ Demo accounts have no access to customization features  

### Customer Mode Requirements (NEW CAPABILITIES)
✅ Full survey customization for company profile and industry  
✅ Flexible conversation controls (time, questions, topic priorities)  
✅ Industry-specific conversation flows and terminology  
✅ Custom branding and messaging throughout conversations  
✅ Preview functionality to test settings before deployment  

### System Integrity Requirements (CRITICAL)
✅ Analytics dashboard processes all survey data correctly  
✅ Same SurveyResponse structure maintained for backwards compatibility  
✅ Zero data loss or corruption during migration  
✅ Performance remains optimal with new features  
✅ All existing campaigns, participants, and analytics continue working  

## Technical Specifications

### Database Requirements
- PostgreSQL with JSON column support for survey_goals, prioritized_topics, optional_topics
- Proper indexing for industry and conversation_tone fields
- Migration scripts with rollback capability
- Data validation constraints for limits and options

### AI/OpenAI Integration
- GPT-4o model for conversation generation and data extraction
- JSON response format enforcement
- Error handling and fallback logic
- Token usage optimization for custom prompts

### Frontend Framework
- Flask/Jinja2 templates for customization interface
- JavaScript for dynamic form interactions and preview
- Bootstrap 5 for responsive design
- AJAX for seamless save functionality

### Security Considerations
- Account type validation before customization access
- Input sanitization for all custom text fields
- SQL injection prevention in dynamic queries
- XSS protection for user-generated content

## Risk Assessment & Mitigation

### High Risk Items
1. **Demo Mode Disruption**: Mitigated by account type checking and separate test suites
2. **Analytics Data Corruption**: Mitigated by maintaining exact same output structure
3. **AI Prompt Quality**: Mitigated by industry templates and fallback logic

### Medium Risk Items
1. **Performance Impact**: Mitigated by database indexing and prompt caching
2. **User Adoption**: Mitigated by preserving existing functionality as default
3. **Customization Complexity**: Mitigated by sensible defaults and preview functionality

### Low Risk Items
1. **Database Migration**: Additive changes only, comprehensive testing
2. **UI Development**: Isolated to customer accounts, no demo impact
3. **Feature Rollback**: Feature flag capability for instant disable

## Post-Implementation Roadmap

### Immediate Next Phase (Month 2)
- User feedback collection and interface refinements
- Additional industry templates based on customer requests
- Advanced customization options for power users
- Integration with existing campaign and participant systems

### Future Enhancements (Months 3-6)
- A/B testing framework for conversation optimization
- Multi-language support for international clients
- Advanced analytics for custom survey performance
- API endpoints for programmatic customization

### Long-term Vision (6+ Months)
- Machine learning for automatic industry detection
- Custom AI training for specific client vocabularies
- Advanced conversation branching and logic
- White-label platform capabilities

---

This implementation plan transforms VOÏA from a single-purpose tool into a versatile platform capable of serving any industry while maintaining the robust trial experience that demonstrates the platform's capabilities to prospective customers.