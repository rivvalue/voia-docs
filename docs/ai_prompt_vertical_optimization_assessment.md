# AI Conversational Survey Prompt Engineering - Vertical Optimization Assessment

**Document Version**: 1.0  
**Date**: October 25, 2025  
**Status**: Gap Analysis Complete - Awaiting Prioritization Decisions  
**Prepared By**: Business Analyst + Solution Architect  
**Scope**: Multi-Vertical Efficiency Enhancement for VOÏA AI Conversational Surveys  

---

## Executive Summary

This assessment evaluates the VOÏA AI conversational survey prompt engineering system to identify gaps and enhancement opportunities for improved efficiency across business verticals (Healthcare, SaaS, Professional Services, Restaurant, Finance, Manufacturing, Education, Retail, etc.).

**Key Findings**:
- ✅ **Current System Strengths**: Hybrid architecture with 2-tier customization (campaign + business account), role/tier-based personalization, flexible configuration
- ⚠️ **Critical Gaps Identified**: 3 gaps block regulated vertical adoption (Healthcare, Finance, EU markets)
- 🎯 **High-Priority Enhancements**: 3 gaps provide competitive differentiation for vertical-specific adoption
- 📊 **Total Gaps Assessed**: 10 gaps spanning compliance, KPIs, terminology, follow-up logic, sentiment analysis, and infrastructure

**Recommended Investment**: 
- **Phase 1** (Critical + Foundation): 12-15 engineering days over 2 sprints
- **Phase 2** (Competitive Differentiation): 15-20 engineering days
- **Phase 3** (Strategic Long-Term): 2-3 weeks (defer until Phase 2 complete)

---

## 1. Feature Description: Current AI Prompt Engineering System

### 1.1 System Overview

VOÏA (Voice Of Client) uses AI-powered conversational surveys with **GPT-4o** to conduct natural language customer feedback collection. The system employs a **hybrid prompt architecture** that dynamically generates conversation prompts based on business account and campaign-specific customization.

### 1.2 Current Architecture Components

#### **Component 1: PromptTemplateService** (prompt_template_service.py)
Central service responsible for generating dynamic AI system prompts.

**Initialization**:
```python
PromptTemplateService(
    business_account_id=5,  # Tenant-level defaults
    campaign_id=42          # Campaign-specific overrides
)
```

**Customization Priority Chain**:
```
Campaign-Specific Data
    ↓ (if missing)
Business Account Defaults
    ↓ (if missing)
System Demo Defaults
```

#### **Component 2: Customization Fields**

**Business Account Level** (persistent tenant identity):
```python
# models.py - BusinessAccount table
industry = db.Column(db.String(100))  # Healthcare, SaaS, Retail, etc.
company_description = db.Column(db.Text)  # 500 chars
product_description = db.Column(db.Text)  # 500 chars
target_clients_description = db.Column(db.Text)  # 300 chars
conversation_tone = db.Column(db.String(50))  # Professional, Warm, Casual, Formal
survey_goals = db.Column(db.JSON)  # Array of goal strings
custom_system_prompt = db.Column(db.Text)  # Advanced override
```

**Campaign Level** (project-specific overrides):
```python
# models.py - Campaign table
product_description = db.Column(db.Text)
target_clients_description = db.Column(db.Text)
survey_goals = db.Column(db.JSON)
max_questions = db.Column(db.Integer, default=8)
max_duration_seconds = db.Column(db.Integer, default=120)
max_follow_ups_per_topic = db.Column(db.Integer, default=2)
prioritized_topics = db.Column(db.JSON)
optional_topics = db.Column(db.JSON)
custom_end_message = db.Column(db.Text)
custom_system_prompt = db.Column(db.Text)
```

#### **Component 3: Hybrid Prompt Structure** (Currently Feature-Flagged)

**Enabled when**: `VOIA_USE_HYBRID_PROMPT=true` environment variable

**Prompt Components**:
1. **Survey Configuration** (JSON): Company name, industry, goals, max questions, tone
2. **Participant Profile**: Name, role, region, customer tier, language, company
3. **Conversation History**: Full message exchange context
4. **Survey Data Collected**: Structured JSON of extracted fields
5. **Conversation Guidelines**: Role-based, tier-based, regional personalization
6. **Response Format**: JSON schema for AI output

**Example Hybrid Prompt**:
```
SURVEY CONFIGURATION:
{
  "company_name": "HealthFirst Clinic",
  "industry": "Healthcare",
  "product_description": "Primary care medical services",
  "conversation_tone": "professional",
  "goals": [
    {"priority": 1, "topic": "Patient Satisfaction", "description": "Overall care experience"},
    {"priority": 2, "topic": "Appointment Scheduling", "description": "Booking process efficiency"}
  ],
  "max_questions": 8
}

PARTICIPANT PROFILE:
- Name: Sarah Johnson
- Role: Patient
- Region: North America
- Language: en
- Company: Self

CONVERSATION HISTORY:
[AI] "Hi Sarah! Thank you for taking the time to share your feedback..."
[User] "The wait time was too long..."

SURVEY DATA COLLECTED SO FAR:
{
  "nps_score": null,
  "satisfaction_rating": 3,
  "wait_time_feedback": "too long"
}

CONVERSATION STEP: 2 / 8

You are VOÏA, an AI-powered customer feedback specialist conducting a survey for HealthFirst Clinic.

Personalization guidelines (adapt based on participant profile):
- C-Level/VP roles: Focus on ROI, strategic value, executive concerns
- Manager/Team Lead roles: Focus on team productivity, operational efficiency
- End User roles: Focus on day-to-day usability, feature requests
- Enterprise tier: Ask about integration, compliance, scalability
- SMB/Startup tier: Focus on ease of use, value for money, support

RESPONSE FORMAT: Return JSON with fields: message, message_type, step, topic, progress, is_complete
```

#### **Component 4: Legacy Prompt Structure** (Currently Active in Production)

**Simpler format** without structured JSON configuration:
```
You are conducting a customer feedback survey about {company_name}.

BUSINESS CONTEXT:
- Industry: {industry}
- Target Clients: {target_clients_description}

CONVERSATION HISTORY:
{conversation_history}

SURVEY DATA COLLECTED SO FAR:
{extracted_data}

CONVERSATION STEP: {step_count}

YOUR ROLE: You are a helpful customer feedback specialist having a natural, {tone} conversation.
Your goal is to collect feedback about {company_name}:
{prioritized_topics}

GUIDELINES:
- Keep the conversation natural and engaging
- Ask ONE question at a time
- Don't ask for information you already have
- Reference their previous responses
```

### 1.3 Current Personalization Capabilities

#### **Role-Based Adaptation** (Hardcoded in hybrid prompt):
| Role | Focus Areas |
|------|-------------|
| **C-Level/VP** | ROI, strategic value, executive concerns, business impact |
| **Manager/Team Lead** | Team productivity, operational efficiency, workflow improvements |
| **End User** | Day-to-day usability, feature requests, user experience |

#### **Customer Tier-Based Adaptation** (Hardcoded in hybrid prompt):
| Tier | Focus Areas |
|------|-------------|
| **Enterprise** | Integration, compliance, scalability, enterprise features |
| **SMB/Startup** | Ease of use, value for money, support responsiveness |

#### **Regional Considerations** (Generic guidance):
- Use region-appropriate examples
- Timezone-aware language
- *No specific regional compliance language implemented*

### 1.4 Industry-Specific Guidance (Documentation Only)

**From Implementation Plan** (not fully implemented in code):

| Industry | Suggested Terminology | Suggested Focus Areas |
|----------|----------------------|----------------------|
| **Healthcare** | "Patient experience" (not "user"), "care quality" | Appointment scheduling, staff professionalism, patient safety |
| **SaaS** | "Onboarding experience", "feature usability" | Product functionality, integration challenges, technical support |
| **Restaurant** | "Dining experience", "food quality", "ambiance" | Meal satisfaction, service speed, staff friendliness |

⚠️ **Current Implementation**: These are **documentation templates only** - not dynamically injected into prompts based on industry selection.

---

## 2. Feature Analysis: Capabilities & Limitations

### 2.1 Current Strengths

✅ **1. Flexible Hybrid Architecture**
- Campaign-level overrides allow project-specific customization
- Graceful fallback chain prevents data gaps
- Feature flag enables controlled rollout of new prompt structure

✅ **2. Multi-Dimensional Personalization**
- Role-based (executive vs manager vs end user)
- Tier-based (enterprise vs SMB)
- Regional awareness (basic)

✅ **3. Structured Configuration**
- JSON-based survey configuration enables programmatic manipulation
- Participant profile integration with segmentation attributes
- Conversation history and extracted data context for AI continuity

✅ **4. Extensibility via Custom Prompts**
- `custom_system_prompt` field allows business accounts to override default templates
- Supports advanced users with specialized needs

✅ **5. Multi-Tenant Architecture**
- Business account isolation ensures data and configuration separation
- Campaign-level granularity supports multiple survey types per tenant

### 2.2 Current Limitations

❌ **1. Generic Question Flow Across All Verticals**
- Same conversation logic applied to Healthcare, SaaS, Restaurant, Finance
- No vertical-specific question libraries or topic prioritization
- AI must infer industry context from generic `industry` field

❌ **2. Universal Metrics Schema**
- Extracted data limited to: NPS, satisfaction rating, pricing rating, service rating, product value rating
- No support for vertical-specific KPIs (e.g., "Patient Readmission Likelihood", "Uptime SLA Compliance")

❌ **3. Compliance-Agnostic Prompts**
- No HIPAA-aware language for Healthcare
- No GDPR references for EU clients
- No PCI-DSS context for Finance/Payment verticals
- **Risk**: Regulatory non-compliance blocks enterprise adoption in regulated industries

❌ **4. Manual Terminology Management**
- Business accounts must manually write custom prompts to use vertical terminology
- No automated translation: "user" → "patient" (Healthcare) or "diner" (Restaurant)
- **Result**: Inconsistent language across campaigns unless manually managed

❌ **5. Follow-Up Question Logic Lacks Vertical Intelligence**
- Generic follow-ups: "Can you tell me more about that?"
- **Example Gap**: If Healthcare patient mentions "wait time", AI should probe "emergency vs scheduled appointment" context, not generic "what caused the delay?"

❌ **6. One-Size-Fits-All Sentiment Analysis**
- Universal sentiment calibration treats "adequate" as neutral
- **Vertical Context Missing**: "Adequate care" in Healthcare should trigger concern, but "adequate support response time" in SaaS may be acceptable

❌ **7. No Sub-Vertical Classification**
- Business accounts can select one industry only
- **Example Gap**: Healthcare provider with both "Primary Care" and "Specialty Surgery" divisions cannot differentiate survey focus areas

❌ **8. Monolithic Prompt Structure**
- 280+ line system prompt with embedded JSON, guidelines, and examples
- Difficult to maintain, test, or version
- **Technical Debt Risk**: Every enhancement requires full prompt rewrite and regression testing

❌ **9. No Prompt Performance Tracking**
- Cannot A/B test prompt variations
- No metrics on prompt effectiveness (completion rate, data quality, conversation length)
- **Opportunity Cost**: Cannot optimize prompts based on empirical data

❌ **10. Feature Flag Not Enabled in Production**
- `VOIA_USE_HYBRID_PROMPT=false` - legacy prompt still active
- Hybrid architecture built but not deployed
- **Result**: Recent investments in structured configuration unused

---

## 3. Risk Assessment: Gap Prioritization

### 3.1 Critical Gaps (BLOCKING Vertical Adoption)

#### **Gap #3: Compliance & Regulatory Language Context** 🔴 **CRITICAL**

**Business Impact**: **Blocks adoption in Healthcare, Finance, EU markets**

**Problem Statement**:
VOÏA prompts do not include industry-specific compliance framing, preventing use in regulated industries where survey language must acknowledge data protection, privacy, and regulatory requirements.

**Concrete Example - Healthcare (HIPAA Compliance)**:
```
❌ CURRENT PROMPT (Non-Compliant):
"Can you describe any issues you experienced during your recent visit?"

✅ REQUIRED PROMPT (HIPAA-Aware):
"Your feedback will be kept confidential in accordance with HIPAA privacy regulations. 
Can you describe any issues you experienced during your recent visit? 
(Note: Please do not share specific medical diagnoses or treatment details.)"
```

**Concrete Example - Finance (PCI-DSS Compliance)**:
```
❌ CURRENT PROMPT (Security Risk):
"How was your experience with our payment processing?"

✅ REQUIRED PROMPT (PCI-DSS-Aware):
"How was your experience with our secure payment processing? 
(Important: Never share your full credit card number, CVV, or PIN in this conversation.)"
```

**Concrete Example - EU Clients (GDPR Compliance)**:
```
❌ CURRENT PROMPT (Non-Compliant):
"Thank you for your feedback! We'll use this to improve our services."

✅ REQUIRED PROMPT (GDPR-Aware):
"Thank you for your feedback! Your data will be processed in accordance with GDPR. 
You have the right to request deletion of this feedback at any time by contacting [email]."
```

**Required Solution**:
1. **Compliance Fragment Library**:
   - Create modular compliance text snippets per industry + region
   - Store in database: `compliance_packs` table with fields:
     ```sql
     industry VARCHAR(100)
     region VARCHAR(50)  -- US, EU, CA, etc.
     pack_type VARCHAR(50)  -- intro, data_collection_notice, closing
     content TEXT
     legal_review_date DATE
     ```

2. **Prompt Template Modularization**:
   - Break monolithic prompt into components:
     ```
     [System Identity]
     + [Compliance Context] ← Injected based on industry + participant region
     + [Survey Configuration]
     + [Participant Profile]
     + [Conversation Guidelines]
     + [Response Format]
     ```

3. **Feature Flag Rollout**:
   - Enable per business account: `enable_compliance_language BOOLEAN`
   - Gradual rollout with legal review per vertical

**Implementation Estimate**: **3-4 engineering days**
- Day 1: Prompt template refactoring (modular components)
- Day 2: Compliance pack database schema + content seeding
- Day 3: Prompt service integration + feature flag
- Day 4: Legal copy review + testing with Healthcare/Finance test accounts

**Backward Compatibility Risk**: **Medium**
- Existing prompts continue working (compliance injection off by default)
- Business accounts must opt-in to compliance language
- Migration path: Provide templates for common verticals, allow custom overrides

**Maintenance Overhead**: **Moderate**
- Requires legal/compliance review when regulations change (HIPAA, GDPR updates)
- Content library per region (US, EU, CA, AU, etc.)
- Estimated: 1 day/quarter for policy library updates

**Business Value if Implemented**:
- ✅ Unblocks Healthcare vertical (estimated 15-20% of target market)
- ✅ Enables EU expansion (GDPR compliance mandatory)
- ✅ Reduces legal risk exposure for existing accounts
- ✅ Competitive differentiation: "Compliance-ready AI surveys"

**Risk if Not Implemented**:
- ❌ Cannot sell to regulated industries (Healthcare, Finance, Legal, Government)
- ❌ Legal liability exposure for non-compliant data collection
- ❌ Missed revenue opportunity in high-value verticals

---

### 3.2 High-Priority Gaps (Competitive Differentiation)

#### **Gap #2: Vertical-Specific KPIs & Metrics** 🟠 **HIGH**

**Business Impact**: **Limits analytical depth for vertical-specific insights**

**Problem Statement**:
Current extracted data schema captures only generic metrics (NPS, satisfaction, pricing, service, product value). Vertical-specific KPIs cannot be tracked, preventing industry-tailored analytics.

**Concrete Examples of Missing KPIs**:

| Vertical | Current Limitation | Required KPI |
|----------|-------------------|--------------|
| **Healthcare** | Only generic satisfaction rating | • Patient Readmission Likelihood<br>• Care Coordination Quality<br>• Provider Communication Effectiveness |
| **SaaS** | No uptime/reliability metrics | • System Uptime Satisfaction<br>• Integration Stability Rating<br>• Feature Adoption Rate |
| **Restaurant** | No atmosphere/ambiance tracking | • Food Quality vs Price Value<br>• Ambiance Rating<br>• Speed of Service Rating |
| **Professional Services** | No deliverable quality metrics | • Deliverable Quality vs Expectations<br>• Responsiveness to Requests<br>• Industry Expertise Rating |
| **Manufacturing** | No supply chain metrics | • Delivery Timeliness<br>• Product Defect Rate Perception<br>• Supply Chain Communication |

**Current Workaround**:
Business accounts must use generic `custom_question` text fields, losing structured analytics.

**Required Solution**:

1. **Schema Extension**:
   ```sql
   -- Add to survey_responses table
   ALTER TABLE survey_responses 
   ADD COLUMN vertical_kpis JSONB DEFAULT '{}';
   
   -- Example vertical_kpis data:
   {
     "healthcare_patient_readmission_likelihood": 2,  -- 1-5 scale
     "healthcare_care_coordination_quality": 4,
     "saas_uptime_satisfaction": 5,
     "restaurant_ambiance_rating": 4
   }
   ```

2. **KPI Metadata Registry**:
   ```sql
   CREATE TABLE vertical_kpi_definitions (
       id SERIAL PRIMARY KEY,
       industry VARCHAR(100) NOT NULL,
       kpi_key VARCHAR(100) NOT NULL,  -- healthcare_patient_readmission_likelihood
       kpi_label VARCHAR(200) NOT NULL,  -- "Patient Readmission Likelihood"
       data_type VARCHAR(50) NOT NULL,  -- rating_1_5, yes_no, percentage, text
       prompt_template TEXT,  -- "On a scale of 1-5, how likely..."
       created_at TIMESTAMP DEFAULT NOW(),
       UNIQUE(industry, kpi_key)
   );
   ```

3. **Prompt Service Integration**:
   - Load vertical KPIs based on `business_account.industry`
   - Inject KPI questions into conversation flow
   - Extract vertical KPI responses into `vertical_kpis` JSONB column

4. **Analytics Dashboard Updates**:
   - Display vertical KPIs in campaign insights (alongside NPS/satisfaction)
   - Trend analysis for industry-specific metrics
   - Segmentation by vertical KPIs (e.g., "High patient readmission risk" segment)

**Implementation Estimate**: **5-6 engineering days**
- Day 1: Schema design + migration (vertical_kpis JSONB column)
- Day 2: KPI metadata table + seed data for top 4 verticals
- Day 3: Prompt service integration (dynamic KPI injection)
- Day 4: AI extraction logic updates (parse vertical KPI responses)
- Day 5: Backend API updates (include vertical_kpis in response JSON)
- Day 6: Frontend dashboard components (display vertical KPIs)

**Backward Compatibility Risk**: **Low**
- `vertical_kpis` column is nullable with default empty dict
- Existing surveys continue working without vertical KPIs
- New surveys automatically include vertical KPIs if industry is set

**Maintenance Overhead**: **Medium**
- KPI taxonomy stewardship (add new KPIs as verticals request them)
- Prompt template updates when KPI definitions change
- Estimated: 2 days/quarter for KPI library expansion

**Business Value if Implemented**:
- ✅ Competitive differentiation: "Industry-tailored analytics"
- ✅ Higher perceived value for vertical-specific accounts
- ✅ Enables industry benchmarking (e.g., "Your patient readmission risk is 15% below industry average")
- ✅ Supports vertical-specific marketing campaigns

---

#### **Gap #5: Industry-Intelligent Follow-Up Questions** 🟠 **HIGH**

**Business Impact**: **Improves conversation relevance and data quality**

**Problem Statement**:
AI uses generic follow-up prompts ("Can you tell me more?") regardless of industry context, resulting in irrelevant probes and missed opportunities to gather actionable insights.

**Concrete Examples of Poor Follow-Ups**:

**Example 1: Healthcare - Wait Time Feedback**
```
[User] "The wait time was too long."

❌ CURRENT FOLLOW-UP (Generic):
"Can you tell me more about what caused the delay?"

✅ INDUSTRY-INTELLIGENT FOLLOW-UP:
"I'm sorry to hear that. Was this for a scheduled appointment or an emergency visit? 
Understanding the context will help us improve wait times."
```

**Example 2: SaaS - Feature Request**
```
[User] "I wish the reporting feature was more customizable."

❌ CURRENT FOLLOW-UP (Generic):
"What specific customizations would you like to see?"

✅ INDUSTRY-INTELLIGENT FOLLOW-UP:
"That's helpful feedback! Are you looking for more flexible data filters, 
custom chart types, or the ability to schedule automated reports? 
This will help us prioritize our roadmap."
```

**Example 3: Restaurant - Food Quality Issue**
```
[User] "The steak was overcooked."

❌ CURRENT FOLLOW-UP (Irrelevant):
"What would you suggest we improve in our product roadmap?" ← Wrong vertical context!

✅ INDUSTRY-INTELLIGENT FOLLOW-UP:
"I apologize for that experience. Did our server offer to replace it, 
and how was the rest of your meal?"
```

**Required Solution**:

1. **Follow-Up Logic Map** (Industry + Topic → Follow-Up Template):
   ```json
   {
     "healthcare": {
       "wait_time": {
         "follow_ups": [
           "Was this for a scheduled appointment or an emergency visit?",
           "How long did you wait compared to your scheduled time?",
           "Did staff communicate the reason for the delay?"
         ]
       },
       "staff_professionalism": {
         "follow_ups": [
           "Can you describe the specific interaction?",
           "Did you escalate this concern to a supervisor?",
           "Which department was this related to?"
         ]
       }
     },
     "saas": {
       "feature_request": {
         "follow_ups": [
           "Is this feature critical for your workflow or a nice-to-have?",
           "Have you found a workaround, or is this blocking your team?",
           "Would you be interested in beta testing if we build this?"
         ]
       },
       "onboarding_difficulty": {
         "follow_ups": [
           "Which part of onboarding was most confusing?",
           "Did you use our documentation, video tutorials, or contact support?",
           "What would have made onboarding smoother?"
         ]
       }
     }
   }
   ```

2. **Prompt Service Enhancement**:
   - Load follow-up map based on `business_account.industry`
   - When user mentions a topic (detected via keyword/sentiment), select follow-up from map
   - Fallback to generic follow-up if no industry match

3. **LLM Guardrails**:
   - Add instruction to system prompt:
     ```
     FOLLOW-UP GUIDELINES:
     When the user mentions {topic}, use these industry-specific follow-up questions:
     {follow_up_templates}
     
     Only use generic follow-ups if the topic is not in the pre-defined list.
     ```

**Implementation Estimate**: **4 engineering days**
- Day 1: Design follow-up map data structure (JSON config vs database table)
- Day 2: Seed follow-up templates for top 4 verticals × top 10 topics each
- Day 3: Prompt service integration (load and inject follow-up templates)
- Day 4: Evaluation harness (test conversation quality with vertical follow-ups)

**Backward Compatibility Risk**: **Low**
- Existing prompts continue using generic follow-ups
- New prompts automatically use industry-intelligent follow-ups if industry is set
- Fallback to generic if follow-up map missing for a topic

**Maintenance Overhead**: **Medium**
- Expand follow-up map as new topics emerge from real conversations
- Review effectiveness quarterly (do industry follow-ups improve data quality?)
- Estimated: 1-2 days/quarter for follow-up library expansion

**Business Value if Implemented**:
- ✅ Higher conversation relevance = better participant experience
- ✅ More actionable insights (specific context-rich feedback)
- ✅ Reduced survey abandonment (participants feel understood)
- ✅ Competitive messaging: "Industry-expert AI conversations"

---

#### **Gap #1: Industry-Specific Question Banks** 🟡 **COMPETITIVE DIFFERENTIATOR**

**Business Impact**: **Raises adoption in target verticals (Hospitality, Retail, Professional Services)**

**Problem Statement**:
Business accounts must manually write survey goals and topics for their industry. Pre-built question libraries for common verticals would accelerate onboarding and ensure best-practice coverage.

**Concrete Example - Restaurant Industry**:

**Current State** (Manual Configuration Required):
```
Business Account Admin must write:
- Survey Goals: ["Food quality feedback", "Service speed", "Ambiance assessment"]
- Prioritized Topics: ["Meal satisfaction", "Server friendliness", "Cleanliness"]
- Custom Questions: Manually type each question
```

**Desired State** (Pre-Built Question Bank):
```
Admin selects: "Restaurant - Fine Dining" question bank
↓
Auto-populates:
- Survey Goals: 
  1. "Dining experience quality"
  2. "Service excellence and attentiveness"
  3. "Food quality and presentation"
  4. "Ambiance and atmosphere"
  5. "Value for price"

- Question Templates:
  1. "How would you rate the overall quality of your meal?"
  2. "Was your server attentive and knowledgeable about the menu?"
  3. "How would you describe the restaurant's atmosphere?"
  4. "Did the food quality justify the price point?"
  5. "Would you recommend us to friends and family?"
```

**Question Bank Examples**:

| Vertical | Sub-Vertical | Question Count | Example Questions |
|----------|-------------|----------------|-------------------|
| **Healthcare** | Primary Care | 12 | • Ease of appointment booking<br>• Provider listening and communication<br>• Wait time satisfaction<br>• Explanation of treatment plan clarity |
| **Healthcare** | Specialty Care | 10 | • Coordination with primary care provider<br>• Specialist expertise confidence<br>• Treatment outcome satisfaction |
| **SaaS** | B2B Enterprise | 15 | • Onboarding experience<br>• Integration with existing tools<br>• Technical support responsiveness<br>• Feature request prioritization |
| **SaaS** | B2C Consumer | 12 | • Ease of getting started<br>• Interface intuitiveness<br>• Value for subscription price<br>• Mobile app experience |
| **Restaurant** | Fine Dining | 10 | • Reservation process<br>• Greeting and seating experience<br>• Food presentation<br>• Wine/beverage pairing recommendations |
| **Restaurant** | Quick Service | 8 | • Order accuracy<br>• Speed of service<br>• Food freshness<br>• Cleanliness of dining area |
| **Professional Services** | Consulting | 12 | • Clarity of deliverables<br>• Responsiveness to requests<br>• Industry expertise demonstrated<br>• ROI vs engagement cost |
| **Retail** | E-Commerce | 14 | • Website browsing experience<br>• Product search accuracy<br>• Checkout process ease<br>• Shipping speed and packaging<br>• Return process (if applicable) |

**Required Solution**:

1. **Question Bank Schema**:
   ```sql
   CREATE TABLE question_banks (
       id SERIAL PRIMARY KEY,
       industry VARCHAR(100) NOT NULL,
       sub_industry VARCHAR(100),
       bank_name VARCHAR(200) NOT NULL,
       description TEXT,
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   CREATE TABLE question_templates (
       id SERIAL PRIMARY KEY,
       question_bank_id INTEGER REFERENCES question_banks(id) ON DELETE CASCADE,
       priority INTEGER NOT NULL,  -- 1 = highest priority
       question_text TEXT NOT NULL,
       expected_data_type VARCHAR(50),  -- rating_1_5, yes_no, text, nps_0_10
       topic_category VARCHAR(100),  -- satisfaction, pricing, support, product
       created_at TIMESTAMP DEFAULT NOW()
   );
   ```

2. **Admin UI - Question Bank Selector**:
   - Business Account Settings: "Select Industry Question Bank"
   - Dropdown: Industry → Sub-Industry → Question Bank
   - Preview: Show all questions before applying
   - Action: "Apply to Campaign" button

3. **Campaign Configuration Integration**:
   - Auto-populate `campaign.survey_goals` from question bank
   - Auto-populate `campaign.prioritized_topics` from question bank
   - Allow manual editing after application (customization on top of template)

4. **Content Management System** (Optional - Phase 2):
   - Admin interface to add/edit question banks
   - Version control for question templates
   - A/B testing: Track which question banks drive highest completion rates

**Implementation Estimate**: **3 engineering days**
- Day 1: Database schema + seed data for 4 verticals (Healthcare, SaaS, Restaurant, Retail)
- Day 2: Admin UI for question bank selection + preview
- Day 3: Campaign configuration integration (apply template to campaign)

**Backward Compatibility Risk**: **None**
- Purely additive feature (optional question bank selection)
- Existing manual configuration workflows unchanged

**Maintenance Overhead**: **Moderate**
- Content governance: Review and expand question banks quarterly
- Community feedback: Allow business accounts to suggest questions
- Quality control: Ensure questions align with VOÏA conversation flow
- Estimated: 2-3 days/quarter for content updates

**Business Value if Implemented**:
- ✅ Faster onboarding (reduce setup time from 30 min to 5 min)
- ✅ Best-practice guidance (ensure comprehensive coverage)
- ✅ Marketing differentiation: "100+ pre-built industry question templates"
- ✅ Higher perceived value for vertical-specific positioning

---

### 3.3 Medium-Priority Gaps (Operational Efficiency)

#### **Gap #6: Sentiment Analysis Vertical Calibration** 🟡 **COMPETITIVE DIFFERENTIATOR**

**Business Impact**: **Improves sentiment accuracy for vertical-specific language**

**Problem Statement**:
Universal sentiment model misinterprets industry-specific language nuances, leading to incorrect positive/neutral/negative classifications.

**Concrete Examples**:

| Phrase | Universal Sentiment | Healthcare Context | SaaS Context | Correct Sentiment |
|--------|-------------------|-------------------|--------------|-------------------|
| "Adequate care" | Neutral (0.0) | ⚠️ Concern (should be negative) | N/A | Healthcare: **Negative** (-0.3) |
| "Acceptable support response time" | Neutral (0.0) | N/A | ✅ Satisfactory (neutral OK) | SaaS: **Neutral** (0.0) |
| "Standard service" | Neutral (0.0) | ⚠️ Underwhelming | ✅ Expected baseline | Context-dependent |
| "Met expectations" | Positive (+0.5) | ⚠️ Bare minimum | ✅ Success | Context-dependent |

**Current Risk**:
- Churn risk scores underestimate dissatisfaction in Healthcare ("adequate" flagged as neutral, not negative)
- Growth opportunities missed (SaaS users saying "met expectations" flagged positive, masking "exceeded expectations" gap)

**Required Solution**:

**Option A: Vertical Calibration Matrix** (Lightweight - 1-2 days):
```python
SENTIMENT_CALIBRATION = {
    "healthcare": {
        "adequate": -0.3,  # Override neutral → slightly negative
        "acceptable": -0.2,
        "satisfactory": 0.0,  # Neutral
        "excellent": +0.8,
        "outstanding": +1.0
    },
    "saas": {
        "adequate": 0.0,  # Neutral OK for SaaS
        "acceptable": 0.0,
        "meets expectations": +0.2,  # Slightly positive
        "exceeds expectations": +0.8,
        "game-changing": +1.0
    },
    "restaurant": {
        "adequate": -0.4,  # Very negative in hospitality
        "fine": -0.1,
        "good": +0.3,
        "delicious": +0.8,
        "unforgettable": +1.0
    }
}
```

**Option B: Fine-Tuned ML Model** (Advanced - 1-2 weeks):
- Train industry-specific sentiment models using vertical feedback datasets
- Deploy separate models per industry (healthcare_sentiment, saas_sentiment, etc.)
- Requires labeled training data (500+ examples per vertical)

**Recommended Approach**: Start with Option A (calibration matrix), migrate to Option B if ROI justifies ML investment.

**Implementation Estimate**: **1.5 days (Option A) / 1-2 weeks (Option B)**

**Maintenance Overhead**: **High (Option B) / Medium (Option A)**
- Option A: Update calibration matrix quarterly based on feedback analysis
- Option B: Continuous model retraining, drift monitoring, A/B testing

**Business Value**:
- ✅ More accurate churn risk scores
- ✅ Better growth opportunity identification
- ✅ Competitive messaging: "Industry-calibrated sentiment analysis"

---

#### **Gap #4: Industry Terminology Dictionaries** 🟢 **QUICK WIN**

**Business Impact**: **Improves conversation tone consistency**

**Problem Statement**:
AI uses generic terminology ("user", "customer", "product") instead of industry-appropriate terms, reducing conversation naturalness.

**Terminology Translation Table**:

| Generic Term | Healthcare | SaaS | Restaurant | Professional Services |
|--------------|-----------|------|-----------|----------------------|
| **User** | Patient | User / Customer | Diner / Guest | Client |
| **Product** | Care Services / Treatment | Software / Platform | Menu / Dining Experience | Engagement / Deliverable |
| **Support** | Patient Services | Technical Support / Customer Success | Host / Server | Account Manager |
| **Experience** | Patient Experience | User Experience | Dining Experience | Client Engagement |
| **Onboarding** | Patient Intake | User Onboarding | Reservation / Seating | Engagement Kickoff |

**Required Solution**:

1. **Dictionary Registry**:
   ```json
   {
     "healthcare": {
       "user": "patient",
       "product": "care services",
       "support": "patient services",
       "experience": "patient experience",
       "onboarding": "patient intake"
     },
     "restaurant": {
       "user": "diner",
       "product": "menu",
       "support": "server",
       "experience": "dining experience",
       "onboarding": "seating process"
     }
   }
   ```

2. **Prompt Template Injection**:
   ```python
   # In PromptTemplateService
   def get_terminology_guide(self) -> str:
       industry = self.business_account.industry
       if industry in TERMINOLOGY_DICTIONARIES:
           terms = TERMINOLOGY_DICTIONARIES[industry]
           return f"""
           INDUSTRY TERMINOLOGY:
           Use these terms consistently:
           - Refer to participants as: {terms['user']}
           - Refer to the offering as: {terms['product']}
           - Refer to assistance as: {terms['support']}
           """
       return ""
   ```

**Implementation Estimate**: **1.5 engineering days**
- Day 1: Build terminology dictionary registry (JSON config file)
- Day 1.5: Integrate into prompt template service + test with 4 verticals

**Maintenance Overhead**: **Low**
- Add new verticals to dictionary as needed (30 min per vertical)
- Review terminology quarterly for industry changes

**Business Value**:
- ✅ More professional conversation tone
- ✅ Higher participant engagement (feels industry-native)
- ✅ Reduced customization burden on business accounts

---

#### **Gap #7: Response Validation (Topic-Industry Relevance)** 🟢 **MEDIUM PRIORITY**

**Business Impact**: **Prevents off-topic responses from skewing analytics**

**Problem Statement**:
AI doesn't validate whether participant responses are relevant to the business industry, allowing off-topic feedback to pollute analytics.

**Example Irrelevant Responses**:
- SaaS survey receiving "food quality" feedback (participant confused context)
- Healthcare survey receiving "software feature requests" (wrong industry association)
- Restaurant survey receiving "API integration issues" (participant error)

**Required Solution**:

1. **Validation Rules**:
   ```python
   INDUSTRY_TOPIC_BLOCKLIST = {
       "saas": ["food quality", "meal", "dining", "ambiance"],
       "restaurant": ["API", "integration", "software bug", "uptime"],
       "healthcare": ["product roadmap", "software features"]
   }
   ```

2. **AI Validation Prompt**:
   ```
   Before accepting the response, validate:
   - Is this feedback relevant to {industry}?
   - If the user mentions topics unrelated to {industry}, politely redirect:
     "I appreciate your feedback, but I'd like to focus on your experience with 
     {company_name}'s {product_description}. Can you share thoughts on that?"
   ```

**Implementation Estimate**: **2 engineering days**

**Business Value**:
- ✅ Cleaner analytics (no off-topic noise)
- ✅ Better participant experience (AI redirects gracefully)

---

#### **Gap #8: Sub-Vertical / Multi-Division Support** 🟡 **MEDIUM PRIORITY**

**Business Impact**: **Enables differentiated surveys for business accounts with multiple divisions**

**Problem Statement**:
Business accounts can select only one industry. Organizations with multiple divisions (e.g., hospital with "Primary Care" + "Emergency Services" + "Specialty Surgery") cannot differentiate survey focus.

**Required Solution**:

1. **Schema Update**:
   ```sql
   ALTER TABLE campaigns 
   ADD COLUMN sub_industry VARCHAR(100);
   
   -- Example values:
   -- industry="Healthcare", sub_industry="Primary Care"
   -- industry="Healthcare", sub_industry="Emergency Services"
   -- industry="SaaS", sub_industry="B2B Enterprise"
   -- industry="SaaS", sub_industry="B2C Consumer"
   ```

2. **Prompt Service Enhancement**:
   - Load sub-industry-specific question banks, terminology, follow-ups
   - Fallback to industry-level defaults if sub-industry not set

**Implementation Estimate**: **2 engineering days**

**Business Value**:
- ✅ Supports multi-division enterprise accounts
- ✅ More granular analytics (Primary Care NPS vs Specialty Surgery NPS)

---

### 3.4 Foundational Gap (Technical Debt)

#### **Gap #9: Prompt Modularity & Maintainability** 🔴 **FOUNDATIONAL**

**Business Impact**: **Prerequisite for implementing Gaps #3, #5, #1**

**Problem Statement**:
Current 280-line monolithic prompt structure blocks extensibility. Every enhancement requires full prompt rewrite and regression testing.

**Required Solution**:

**Modular Prompt Architecture**:
```python
class ModularPromptBuilder:
    def build_prompt(self):
        return self._join_modules([
            self.system_identity(),       # "You are VOÏA..."
            self.compliance_context(),    # HIPAA, GDPR notices ← Gap #3
            self.survey_configuration(),  # JSON config
            self.participant_profile(),   # Segmentation data
            self.terminology_guide(),     # Industry dictionary ← Gap #4
            self.conversation_history(),  # Previous messages
            self.extracted_data(),        # Collected fields
            self.conversation_guidelines(),  # Personalization rules
            self.follow_up_map(),         # Industry-specific follow-ups ← Gap #5
            self.response_format()        # JSON schema
        ])
    
    def compliance_context(self):
        """Inject compliance language based on industry + region"""
        if self.business_account.industry == "Healthcare":
            return self._load_compliance_pack("HIPAA")
        elif self.participant.region == "EU":
            return self._load_compliance_pack("GDPR")
        return ""
```

**Benefits**:
- ✅ Each module independently testable
- ✅ Easy to add/remove prompt sections
- ✅ Version control per module (not entire 280-line prompt)
- ✅ A/B testing at module level

**Implementation Estimate**: **3-4 engineering days**
- Day 1-2: Refactor `PromptTemplateService` into modular builder
- Day 3: Update unit tests to cover each module
- Day 4: Regression testing with existing campaigns

**Maintenance Benefit**: **High**
- Future enhancements require editing single modules, not entire prompt
- Reduces regression risk

**Prerequisite For**: Gaps #3, #4, #5, #1 (all require injecting new prompt sections)

---

### 3.5 Strategic Long-Term Gap

#### **Gap #10: Prompt A/B Testing Infrastructure** 🔵 **STRATEGIC (DEFER)**

**Business Impact**: **Enables data-driven prompt optimization**

**Problem Statement**:
No empirical measurement of prompt effectiveness. Cannot test whether prompt variant A drives higher completion rates than variant B.

**Required Solution**:

1. **Prompt Variant Tracking**:
   ```sql
   CREATE TABLE prompt_variants (
       id SERIAL PRIMARY KEY,
       variant_name VARCHAR(100) NOT NULL,
       variant_description TEXT,
       prompt_template TEXT NOT NULL,
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   ALTER TABLE survey_responses 
   ADD COLUMN prompt_variant_id INTEGER REFERENCES prompt_variants(id);
   ```

2. **Outcome Metrics**:
   - Completion rate (% of surveys finished)
   - Average conversation length (messages)
   - Data quality score (% of fields collected)
   - Participant satisfaction (post-survey rating)

3. **Experimentation Framework**:
   - Randomly assign participants to variant A vs variant B
   - Track outcomes per variant
   - Statistical significance testing (confidence intervals, p-values)

**Implementation Estimate**: **1 week**

**Recommendation**: **Defer until Phases 1-2 complete**
- Requires stable modular prompt architecture (Gap #9)
- Needs telemetry pipeline for outcome tracking
- Added complexity - prioritize vertical gaps first

---

## 4. Open Points & Recommendations

### 4.1 Implementation Roadmap

#### **Phase 1: Critical + Foundation** (Next 2 Sprints)
**Goal**: Enable regulated vertical adoption + establish extensible architecture

| Priority | Gap | Effort | Dependencies | Business Value |
|----------|-----|--------|--------------|----------------|
| 🔴 CRITICAL | #9: Prompt Modularity | 3-4 days | None | Prerequisite for all other gaps |
| 🔴 CRITICAL | #3: Compliance Language | 3-4 days | Gap #9 | Unblocks Healthcare, Finance, EU |
| 🟢 QUICK WIN | #4: Terminology Dictionaries | 1.5 days | Gap #9 | Improves conversation quality |

**Total Phase 1 Effort**: **8-10 engineering days** (1.5-2 sprints)

**Deliverables**:
- ✅ Modular prompt architecture deployed
- ✅ Compliance packs for HIPAA (Healthcare) + GDPR (EU) + PCI-DSS (Finance)
- ✅ Terminology dictionaries for 4 verticals (Healthcare, SaaS, Restaurant, Professional Services)
- ✅ Feature flag: `enable_compliance_language` per business account
- ✅ `VOIA_USE_HYBRID_PROMPT=true` enabled in production after QA

**Success Metrics**:
- Zero regression in existing campaign completion rates
- At least 2 Healthcare pilot accounts enabled with compliance language
- Legal/compliance team sign-off on HIPAA/GDPR packs

---

#### **Phase 2: Competitive Differentiation** (Post-Stabilization, 3-4 Sprints)
**Goal**: Vertical-specific analytics and conversation intelligence

| Priority | Gap | Effort | Dependencies | Business Value |
|----------|-----|--------|--------------|----------------|
| 🟠 HIGH | #2: Vertical KPIs | 5-6 days | Phase 1 complete | Industry-tailored analytics |
| 🟠 HIGH | #5: Industry-Intelligent Follow-Ups | 4 days | Gap #9 | Better data quality |
| 🟡 DIFFERENTIATOR | #1: Question Banks | 3 days | None | Faster onboarding |
| 🟡 DIFFERENTIATOR | #6: Sentiment Calibration | 1.5 days | None | Accurate churn scoring |
| 🟢 MEDIUM | #7: Response Validation | 2 days | None | Cleaner analytics |
| 🟡 MEDIUM | #8: Sub-Vertical Support | 2 days | None | Multi-division accounts |

**Total Phase 2 Effort**: **17.5-20 engineering days** (3.5-4 sprints)

**Deliverables**:
- ✅ Vertical KPIs for 4 verticals (Healthcare, SaaS, Restaurant, Professional Services)
- ✅ Industry-intelligent follow-up map (40+ follow-up templates across 4 verticals)
- ✅ Question banks for 8 sub-verticals (2 per vertical)
- ✅ Sentiment calibration matrices for 4 verticals
- ✅ Campaign sub-industry field + UI selector

**Success Metrics**:
- 20% reduction in survey abandonment rate (better follow-ups)
- Vertical KPI adoption: 50%+ of new campaigns use vertical KPIs
- Question bank usage: 30%+ of new campaigns apply templates

---

#### **Phase 3: Strategic Long-Term** (6+ Months Out)
**Goal**: Data-driven optimization and advanced ML

| Priority | Gap | Effort | Dependencies | Business Value |
|----------|-----|--------|--------------|----------------|
| 🔵 STRATEGIC | #10: Prompt A/B Testing | 1 week | Telemetry pipeline | Empirical optimization |
| 🔵 STRATEGIC | #6: ML Sentiment Models | 1-2 weeks | Training data + ML infrastructure | Advanced sentiment accuracy |

**Recommendation**: **Defer until Phase 2 complete** + telemetry infrastructure in place

---

### 4.2 Key Decisions Required

#### **Decision #1: Compliance Language Legal Review Budget**
**Question**: Allocate budget for legal/compliance review of HIPAA, GDPR, PCI-DSS language packs?

**Options**:
- **Option A**: External legal counsel review (~$5K-10K)
- **Option B**: Internal compliance team review (if available)
- **Option C**: Use industry-standard templates with disclaimer (higher risk)

**Recommendation**: Option A or B (legal liability exposure too high for Option C)

---

#### **Decision #2: Vertical KPI Schema Approach**
**Question**: Store vertical KPIs in JSONB column or dedicated normalized tables?

**Options**:
- **Option A: JSONB Column** (chosen in Gap #2 analysis)
  - Pros: Flexible schema, fast iteration, no migrations for new KPIs
  - Cons: Complex queries, no foreign key constraints
- **Option B: Normalized Tables** (vertical_kpi_values with foreign keys)
  - Pros: Relational integrity, easier joins, better query performance
  - Cons: Requires migration for every new KPI

**Recommendation**: Option A (JSONB) for MVP, migrate to Option B if KPI count exceeds 20 per vertical

---

#### **Decision #3: Feature Flag Rollout Strategy**
**Question**: Enable `VOIA_USE_HYBRID_PROMPT` globally or per-tenant?

**Options**:
- **Option A: Global Feature Flag** (all tenants switch to hybrid prompt)
  - Pros: Simpler deployment, consistent experience
  - Cons: Higher regression risk, all-or-nothing rollout
- **Option B: Per-Tenant Feature Flag** (business accounts opt-in)
  - Pros: Gradual rollout, easy rollback, A/B testing opportunity
  - Cons: Two codepaths to maintain, migration complexity

**Recommendation**: Option B (per-tenant flag) for Phase 1, migrate to global once validated

---

#### **Decision #4: Question Bank Content Governance**
**Question**: Who maintains question bank content (internal team vs community-sourced)?

**Options**:
- **Option A: Internal Curation** (VOÏA team writes all question banks)
  - Pros: Quality control, consistent tone, legal review
  - Cons: Slow expansion, limited vertical expertise
- **Option B: Community-Sourced** (business accounts submit templates for approval)
  - Pros: Faster expansion, real-world validation, vertical expertise
  - Cons: Moderation overhead, quality inconsistency risk
- **Option C: Hybrid** (internal for top 4 verticals, community for long tail)
  - Pros: Best of both worlds
  - Cons: Requires moderation workflow

**Recommendation**: Option C (hybrid approach)

---

### 4.3 Risk Mitigation Strategies

#### **Risk #1: Over-Engineering Vertical Specificity**
**Concern**: Too much vertical customization creates maintenance burden

**Mitigation**:
- Start with top 4 verticals only (Healthcare, SaaS, Restaurant, Professional Services)
- Measure adoption and ROI per vertical before expanding
- Retire unused vertical configurations quarterly (prune low-usage KPIs, question banks)

---

#### **Risk #2: Legal Liability for Compliance Language**
**Concern**: Incorrect HIPAA/GDPR language exposes VOÏA to regulatory risk

**Mitigation**:
- Require legal counsel review before deploying compliance packs
- Include disclaimers: "This template is provided as guidance only. Consult your legal team."
- Per-tenant opt-in (business accounts acknowledge compliance responsibility)
- Version tracking: Log which compliance pack version was used per survey

---

#### **Risk #3: Technical Debt from Prompt Fragmentation**
**Concern**: Modular prompts create 10+ fragments that are hard to coordinate

**Mitigation**:
- Strict module naming convention (system_identity, compliance_context, etc.)
- Integration tests that validate full assembled prompt
- Versioning: Each module has semantic version (v1.0, v1.1, etc.)
- Deprecation policy: Retire old module versions after 6 months

---

#### **Risk #4: Performance Degradation (Larger Prompts)**
**Concern**: Compliance + terminology + follow-ups increase prompt size (tokens), slowing AI response

**Mitigation**:
- Benchmark prompt token count before/after enhancements
- Set token budget: Max 2000 tokens per system prompt
- Use prompt compression techniques (abbreviations, remove redundant sections)
- Monitor AI response latency per prompt variant

---

### 4.4 Success Metrics & KPIs

#### **Phase 1 Success Criteria**:
- ✅ Zero regression in campaign completion rate (baseline: 65%)
- ✅ At least 2 Healthcare pilot accounts using compliance language
- ✅ Legal team approval of HIPAA + GDPR packs
- ✅ Terminology dictionaries reduce "custom_system_prompt" usage by 20%

#### **Phase 2 Success Criteria**:
- ✅ Vertical KPI adoption: 50%+ of new campaigns
- ✅ Question bank usage: 30%+ of new campaigns
- ✅ Survey abandonment rate reduced by 20% (better follow-ups)
- ✅ Industry-intelligent follow-ups increase data quality score by 15%

#### **Long-Term North Star Metrics**:
- **Vertical Penetration**: 80% of Healthcare accounts use compliance language
- **Time-to-First-Survey**: Reduce from 30 min to 5 min (question bank impact)
- **Data Quality Score**: Increase from 70% to 85% (vertical KPIs + follow-ups)
- **NPS of VOÏA Platform**: Track business account satisfaction with vertical customization

---

## 5. Appendix

### 5.1 Current vs Enhanced Prompt Comparison

**Current Prompt (Legacy, 150 tokens)**:
```
You are conducting a customer feedback survey about HealthFirst Clinic.

BUSINESS CONTEXT:
- Industry: Healthcare

CONVERSATION HISTORY:
[AI] Hi! How was your recent visit?
[User] The wait time was too long.

SURVEY DATA COLLECTED SO FAR:
{"nps_score": null, "satisfaction_rating": 3}

YOUR ROLE: You are a helpful customer feedback specialist having a natural, professional conversation.

GUIDELINES:
- Ask ONE question at a time
- Don't ask for information you already have
```

**Enhanced Prompt (Phase 1 + 2, 300 tokens)**:
```
COMPLIANCE NOTICE:
Your feedback will be kept confidential in accordance with HIPAA privacy regulations.
Please do not share specific medical diagnoses or treatment details.

SURVEY CONFIGURATION:
{
  "company_name": "HealthFirst Clinic",
  "industry": "Healthcare",
  "sub_industry": "Primary Care",
  "product_description": "Primary care medical services",
  "conversation_tone": "professional"
}

PARTICIPANT PROFILE:
- Name: Sarah Johnson
- Role: Patient
- Company: Self

CONVERSATION HISTORY:
[AI] Hi Sarah! Thank you for taking time to share your feedback about your recent visit.
[User] The wait time was too long.

SURVEY DATA COLLECTED SO FAR:
{
  "nps_score": null,
  "satisfaction_rating": 3,
  "wait_time_feedback": "too long",
  "vertical_kpis": {
    "healthcare_wait_time_rating": 2
  }
}

You are VOÏA, an AI-powered customer feedback specialist conducting a survey for HealthFirst Clinic.

INDUSTRY TERMINOLOGY:
- Refer to participants as: patients
- Refer to the offering as: care services
- Refer to assistance as: patient services

FOLLOW-UP GUIDELINES:
When a patient mentions "wait time", use these follow-up questions:
- "Was this for a scheduled appointment or an emergency visit?"
- "How long did you wait compared to your scheduled time?"
- "Did staff communicate the reason for the delay?"

RESPONSE FORMAT: Return JSON with fields: message, message_type, step, topic, progress, is_complete
```

**Token Increase**: 150 → 300 tokens (+100% increase)
**Estimated Latency Impact**: +200-300ms per AI response
**Mitigation**: Stay within 2000-token budget, monitor P95 latency

---

### 5.2 Related Documentation

- **Current Implementation**: `prompt_template_service.py`
- **AI Conversation Logic**: `ai_conversational_survey.py`
- **Data Models**: `models.py` (BusinessAccount, Campaign, SurveyResponse)
- **System Architecture**: `replit.md`
- **Customization Implementation Plan**: `VOÏA_Customizable_Implementation_Plan.md`

---

### 5.3 Glossary

- **Vertical**: Industry category (Healthcare, SaaS, Restaurant, etc.)
- **Sub-Vertical**: Industry subdivision (Healthcare → Primary Care, Specialty Surgery)
- **Compliance Pack**: Pre-written legal/regulatory language for specific industry+region
- **Terminology Dictionary**: Industry-specific word mappings (user → patient, product → care services)
- **Question Bank**: Pre-built collection of survey questions for a vertical
- **Vertical KPI**: Industry-specific metric (e.g., Patient Readmission Likelihood)
- **Follow-Up Map**: Industry-specific follow-up question templates
- **Sentiment Calibration**: Industry-specific sentiment scoring adjustments
- **Prompt Modularity**: Breaking monolithic prompt into reusable components

---

**Document Status**: 🟢 **READY FOR REVIEW & PRIORITIZATION**

**Next Steps**: 
1. Review gap analysis with stakeholders
2. Approve Phase 1 budget and legal review allocation
3. Prioritize Phase 2 gaps (high vs medium priority)
4. Assign engineering resources for Phase 1 (8-10 days)
