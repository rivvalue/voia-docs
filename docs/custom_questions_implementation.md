# Classic Survey Feature - Implementation Plan

**Created:** January 21, 2026  
**Last Updated:** February 8, 2026  
**Status:** Phase 2d Complete - Awaiting Approval  

---

## Part A: Classic Survey System (Dual Survey Type Architecture)

### Overview

Add Classic Survey as an alternative survey type alongside the existing Conversational (VOÏA) surveys. Classic surveys use a structured multi-step form instead of the AI-powered chat interface.

### Key Design Decisions

1. **Zero impact on conversational surveys** - Completely separate code paths
2. **Survey type locked after activation** - `frozen_at` timestamp on ClassicSurveyConfig prevents changes
3. **Classic responses tagged differently** - `source_type='traditional'` for analytics separation
4. **Bilingual support** - All UI text uses `_()` for EN/FR translation
5. **Incremental phased implementation** - Formal approval gates between phases

### Phase 1: Foundation (COMPLETED - Approved)

**What was built:**
- [x] `survey_type` field on Campaign model (default: 'conversational')
- [x] `SurveyTemplate` model for reusable survey configurations
- [x] `ClassicSurveyConfig` model with driver labels, features, sections (bilingual JSON)
- [x] Campaign creation UI with survey type selector (Conversational vs Classic radio buttons)
- [x] Survey type locked after campaign activation via `frozen_at` timestamp
- [x] Database migrations executed successfully
- [x] New SurveyResponse fields: `csat_score`, `ces_score`, `loyalty_drivers`, `recommendation_status`

**Files modified:** `models.py`, `templates/campaigns/create.html`, `campaign_routes.py`

### Phase 2: Participant Flow (COMPLETED - Awaiting Approval)

**What was built:**
- [x] Modified `/survey` route to branch classic campaigns to `/classic_survey` (zero impact on conversational)
- [x] New `/classic_survey` GET route - loads config, prepares driver labels/features/sections, renders template
- [x] New `/submit_classic_survey` POST route - full form handling with data mapping to SurveyResponse
- [x] `templates/classic_survey.html` - Multi-step form with 3 sections:
  - **Section 1**: NPS scale (0-10), dynamic driver checkboxes by NPS category, open-text explanation + improvement, CSAT (1-5), CES (1-8)
  - **Section 2**: Feature evaluation cards (usage/frequency/importance/satisfaction per feature)
  - **Section 3**: Additional insights (4 open text fields + recommendation status with conditional blocker question)
- [x] Survey Settings guard on campaign view - hides conversational settings for classic campaigns, shows "Classic Survey" badge
- [x] `source_type='traditional'` set on classic survey responses
- [x] Server-side NPS validation (required field + range check 0-10)
- [x] Client-side validation (NPS required before advancing sections)
- [x] Progress bar tracking across sections

**Files modified:** `routes.py`, `templates/classic_survey.html`, `templates/campaigns/view.html`

**Data mapping:**
| Form field | SurveyResponse column |
|---|---|
| NPS score (0-10) | `nps_score`, `nps_category` |
| Driver checkboxes | `loyalty_drivers` (JSON array) |
| Driver explanation | `recommendation_reason` |
| Improvement feedback | `improvement_feedback` |
| CSAT (1-5) | `csat_score`, `satisfaction_rating` |
| CES (1-8) | `ces_score` |
| Feature evaluations | `general_feedback` (JSON) |
| Section 3 insights | `additional_comments` (concatenated text) |
| Recommendation status | `recommendation_status` |

**Validation guide:**
1. Create a classic campaign → confirm survey type selector appears
2. View classic campaign → confirm "Classic Survey" badge (not conversational settings)
3. Open classic survey link → confirm multi-step form (not chat)
4. Walk through form → NPS required before advancing, drivers appear dynamically
5. Submit → saves to database with `source_type='traditional'`
6. Check conversational campaign → confirm zero impact (chat interface unchanged)

### Phase 2b: Survey Preview (COMPLETED)

**What was built:**
- [x] `/campaigns/<id>/preview_survey` route — business-authenticated preview of the classic survey questionnaire
- [x] Preview mode banner with "Back to Campaign" link at top of survey
- [x] Form submission disabled in preview mode (`onsubmit="return false;"`, submit button disabled)
- [x] "Preview Survey" button replaces the static "Classic Survey" badge on campaign view page (both with-participants and no-participants states)
- [x] Opens in new tab (`target="_blank"`) so campaign manager stays on the campaign page
- [x] Tenant isolation enforced — only the campaign owner's business account can preview

**Files modified:** `campaign_routes.py`, `templates/classic_survey.html`, `templates/campaigns/view.html`

**Validation guide:**
1. View any classic campaign (draft or active) → confirm "Preview Survey" button appears
2. Click "Preview Survey" → opens the full survey form in a new tab with preview banner
3. Walk through all 3 sections → NPS selection, driver checkboxes, feature evaluation, insights all interactive
4. Submit button shows "Preview Only — Submit Disabled" and cannot be clicked
5. "Back to Campaign" link returns to the campaign view

### Phase 2c: Response Viewing (COMPLETED)

**What was built:**
- [x] Updated `individual_response` route to detect classic surveys and parse classic-specific data:
  - `general_feedback` JSON parsed into feature evaluation objects
  - `loyalty_drivers` JSON resolved against `ClassicSurveyConfig` driver labels for human-readable display
  - `is_classic` flag passed to template for conditional rendering
- [x] Updated `individual_response.html` with classic-specific display:
  - Ratings section shows CSAT (1-5) and CES (1-8) for classic; standard ratings for conversational
  - Loyalty Drivers section with tag-style display
  - Recommendation Status section with color-coded indicators (recommended/would consider/would not recommend)
  - Right panel shows Feature Evaluations in card layout (usage, frequency, importance, satisfaction per feature) instead of conversation transcript
  - `general_feedback` excluded from Written Feedback section for classic (it stores JSON, not text)
- [x] Updated `responses_list.html` with classic-specific columns:
  - CSAT and CES columns added to table for classic campaigns
  - "Classic Survey" badge in page header
- [x] Updated `campaign_responses` route to pass `is_classic` flag to template

**Files modified:** `campaign_routes.py`, `templates/campaigns/individual_response.html`, `templates/campaigns/responses_list.html`

**Validation guide:**
1. Open a classic campaign → click "Responses" → confirm CSAT and CES columns appear in table, "Classic Survey" badge visible
2. Click "View Details" on a classic response → confirm CSAT/CES scores shown in Ratings section
3. Loyalty drivers display as tags (if selected by participant)
4. Recommendation status shows color-coded indicator
5. Right panel shows Feature Evaluations (not conversation transcript)
6. Open a conversational campaign response → confirm layout unchanged (conversation transcript still shows)

### Phase 2d: Welcome Page & V2 Design Compliance (COMPLETED)

**What was built:**
- [x] Welcome/landing page for classic survey participants — matching the conversational survey experience:
  - Hero section with business branding (logo, company name, tagline)
  - Personalized greeting ("Hi [name], thank you for participating")
  - Campaign metadata (name, objective, respond-by deadline)
  - Participant info card (company, name, email — read-only fields)
  - "Start Survey" call-to-action button that reveals the survey form
- [x] Switched template from `base.html` to `base_minimal.html` to remove the "Welcome to VOÏA Demo" navbar banner (not appropriate for real participants)
- [x] Reused V2 `conv-hero` CSS classes (same as conversational survey) for consistent design:
  - Primary-red gradient hero, Montserrat/Karla typography, V2 spacing/radius/shadow tokens
  - `btn-voia-primary` for the Start Survey button
- [x] Added fixed-position language selector (since `base_minimal.html` has no navbar)
- [x] Preview mode bypasses welcome page — shows survey form directly for campaign managers
- [x] Route updated to pass `campaign_description`, `campaign_start_date`, `campaign_end_date` to template
- [x] CSRF token timeout extended to 2 hours to prevent "Security token validation failed" errors on longer sessions
- [x] Campaign activation route improved: graceful handling when campaign is already active (info message instead of error)

**Files modified:** `templates/classic_survey.html`, `routes.py`, `app.py`, `campaign_routes.py`

**Validation guide:**
1. Open a participant survey link for a classic campaign → welcome page appears with branding, greeting, campaign details
2. No "Welcome to VOÏA Demo" banner in the navbar
3. Participant info (name, email, company) displayed as read-only fields
4. Click "Start Survey" → survey form appears, welcome page hides
5. Language selector visible in top-right corner
6. Preview mode (from campaign view) → survey form shows immediately, no welcome page
7. Colors and layout match the conversational survey welcome page (V2 design tokens)

### Phase 3+ (Planned)

- Classic survey config UI (admin editing of drivers/features/sections)
- Analytics charts for classic survey data
- Campaign comparison (classic vs conversational)

---

## Part B: Custom Questions for Traditional Surveys

### Overview

Enable business account users to define custom questions for traditional surveys. Custom questions are **additive** - they supplement the mandatory core metrics (NPS, satisfaction ratings) to ensure analytics compatibility.

**Status:** Ready for Implementation  
**Estimated Effort:** 7-10 days

### Key Design Decisions

1. **Core metrics remain mandatory** - NPS, satisfaction, service, pricing, product ratings always captured
2. **Custom questions are additive** - Rendered after core questions
3. **Backward compatible** - Campaigns without custom questions work exactly as before
4. **No changes to SurveyResponse** - Custom responses stored in separate table
5. **Bilingual support** - EN/FR question text

---

## Database Schema

### CampaignQuestion Model

```python
class CampaignQuestion(db.Model):
    """Custom question defined for a campaign's traditional survey."""
    __tablename__ = 'campaign_question'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    
    # Question content (bilingual)
    question_text_en = db.Column(db.Text, nullable=False)
    question_text_fr = db.Column(db.Text, nullable=True)
    
    # Question type: 'text', 'textarea', 'rating_1_5', 'rating_0_10', 'yes_no', 'single_choice', 'multiple_choice'
    question_type = db.Column(db.String(50), nullable=False, default='text')
    
    # Options for choice questions (JSON array: ["Option A", "Option B", "Option C"])
    options_json = db.Column(db.Text, nullable=True)
    
    # Configuration
    is_required = db.Column(db.Boolean, default=False)
    display_order = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaign = db.relationship('Campaign', backref=db.backref('custom_questions', lazy='dynamic'))
```

### QuestionResponse Model

```python
class QuestionResponse(db.Model):
    """Response to a custom campaign question."""
    __tablename__ = 'question_response'
    
    id = db.Column(db.Integer, primary_key=True)
    survey_response_id = db.Column(db.Integer, db.ForeignKey('survey_response.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('campaign_question.id'), nullable=False)
    
    # Response data
    response_value = db.Column(db.String(255), nullable=True)  # For ratings, yes/no, single choice
    response_text = db.Column(db.Text, nullable=True)  # For text, textarea, multiple choice (JSON)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    survey_response = db.relationship('SurveyResponse', backref=db.backref('custom_responses', lazy='dynamic'))
    question = db.relationship('CampaignQuestion', backref=db.backref('responses', lazy='dynamic'))
```

---

## Phased Implementation Plan

### Phase 1: Database Foundation (Day 1)

**Tasks:**
- [ ] Add `CampaignQuestion` model to `models.py`
- [ ] Add `QuestionResponse` model to `models.py`
- [ ] Run database migrations via SQLAlchemy

**Validation Checkpoint 1:**
- [ ] Verify tables created: `SELECT * FROM campaign_question LIMIT 1;`
- [ ] Verify existing surveys still work (complete a traditional survey)
- [ ] Confirm no errors in application logs

**Rollback:**
```sql
DROP TABLE IF EXISTS question_response;
DROP TABLE IF EXISTS campaign_question;
```

---

### Phase 2: Backend API (Day 2)

**Tasks:**
- [ ] Add route `GET /business/campaign/<id>/questions` - List questions
- [ ] Add route `POST /business/campaign/<id>/questions` - Create question
- [ ] Add route `PUT /business/campaign/<id>/questions/<qid>` - Update question
- [ ] Add route `DELETE /business/campaign/<id>/questions/<qid>` - Delete question
- [ ] Add route `POST /business/campaign/<id>/questions/reorder` - Reorder questions
- [ ] Add authorization: only campaign owner can manage questions

**Validation Checkpoint 2:**
- [ ] Test CRUD operations via API (curl or Postman)
- [ ] Verify authorization prevents unauthorized access
- [ ] Confirm existing campaign routes unchanged

**Rollback:**
```bash
git checkout <checkpoint> -- business_auth_routes.py
```

---

### Phase 3: Question Editor UI (Days 3-4)

**Tasks:**
- [ ] Add "Custom Questions" tab to campaign edit page (`templates/business/campaign_edit.html`)
- [ ] Build question list with add/edit/delete buttons
- [ ] Create question form modal (type selector, text fields, options editor)
- [ ] Implement drag-and-drop reordering
- [ ] Add question type icons and previews

**Question Types Supported:**
| Type | Input Control | Response Storage |
|------|--------------|------------------|
| `text` | Single-line input | `response_text` |
| `textarea` | Multi-line textarea | `response_text` |
| `rating_1_5` | Radio buttons 1-5 | `response_value` |
| `rating_0_10` | Radio buttons 0-10 | `response_value` |
| `yes_no` | Yes/No buttons | `response_value` |
| `single_choice` | Radio buttons | `response_value` |
| `multiple_choice` | Checkboxes | `response_text` (JSON array) |

**Validation Checkpoint 3:**
- [ ] Create campaign with 3+ custom questions of different types
- [ ] Verify questions save and reload correctly
- [ ] Test reordering and deletion
- [ ] Verify bilingual fields (EN/FR)

**Rollback:**
```bash
git checkout <checkpoint> -- templates/business/campaign_edit.html
git checkout <checkpoint> -- static/js/campaign_questions.js
```

---

### Phase 4: Survey Form Integration (Days 5-6)

**Tasks:**
- [ ] Update `survey_form` route to pass custom questions to template
- [ ] Modify `templates/survey.html` to render custom questions after core questions
- [ ] Keep NPS, satisfaction, service, pricing, product ratings mandatory
- [ ] Add dynamic rendering logic per question type
- [ ] Implement bilingual rendering based on participant language
- [ ] Add form validation for required custom questions

**Survey Structure:**
```
Step 1: Basic Information (fixed)
Step 2: NPS Score (fixed, mandatory)
Step 3: Core Ratings (fixed - satisfaction, product, service, pricing)
Step 4: Custom Questions (dynamic, from database)
Step 5: Additional Feedback (fixed)
Step 6: Submit
```

**Validation Checkpoint 4:**
- [ ] Complete survey on campaign WITH custom questions - all questions appear
- [ ] Complete survey on campaign WITHOUT custom questions - works as before
- [ ] Switch language and verify bilingual rendering
- [ ] Test required vs optional custom questions

**Rollback:**
```bash
git checkout <checkpoint> -- templates/survey.html
git checkout <checkpoint> -- routes.py
```

---

### Phase 5: Response Storage & Analytics (Days 7-8)

**Tasks:**
- [ ] Update `submit_survey_form` to extract custom question responses from form
- [ ] Save responses to `QuestionResponse` table
- [ ] Verify AI analysis still runs on core metrics (no changes needed)
- [ ] Update CSV export to include custom question columns
- [ ] Add custom responses to survey response detail view

**Export Format:**
```
existing_columns..., custom_q1_text, custom_q1_response, custom_q2_text, custom_q2_response, ...
```

**Validation Checkpoint 5:**
- [ ] Submit survey with custom questions and verify responses stored
- [ ] Check AI analysis generates sentiment/churn scores (core metrics)
- [ ] Export CSV and verify custom question columns present
- [ ] View survey response detail and see custom answers

**Rollback:**
```bash
git checkout <checkpoint> -- routes.py
git checkout <checkpoint> -- business_auth_routes.py  # export routes
```

---

### Phase 6: Final Validation & Documentation (Day 9-10)

**Tasks:**
- [ ] Full regression testing on existing campaigns (no custom questions)
- [ ] Test AI conversational surveys are unaffected
- [ ] Update `replit.md` with feature documentation
- [ ] Add rollback procedure to this document

**Validation Checkpoint 6:**
- [ ] All existing functionality works
- [ ] New feature works end-to-end
- [ ] Documentation complete
- [ ] Ready for production

---

## Complete Rollback Procedure

If any phase causes issues, follow these steps:

### Immediate Rollback (Any Phase)

```bash
# 1. Restore code to pre-implementation state
git checkout 9b3322155bcc430e84cd97d60958785dce566070 -- models.py
git checkout 9b3322155bcc430e84cd97d60958785dce566070 -- routes.py
git checkout 9b3322155bcc430e84cd97d60958785dce566070 -- business_auth_routes.py
git checkout 9b3322155bcc430e84cd97d60958785dce566070 -- templates/survey.html
git checkout 9b3322155bcc430e84cd97d60958785dce566070 -- templates/business/campaign_edit.html

# 2. Drop new database tables (if created)
psql $DATABASE_URL -c "DROP TABLE IF EXISTS question_response CASCADE;"
psql $DATABASE_URL -c "DROP TABLE IF EXISTS campaign_question CASCADE;"

# 3. Restart application
pkill gunicorn && gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

### Verification After Rollback

- [ ] Traditional surveys work (submit test survey)
- [ ] AI conversational surveys work
- [ ] Campaign management works
- [ ] CSV exports work
- [ ] No errors in logs

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Existing surveys break | All changes additive; core form unchanged if no custom questions |
| Export schema changes | Custom columns appended at end; existing columns unchanged |
| Performance degradation | Questions loaded with campaign; lazy loading for responses |
| Data loss on rollback | Custom questions/responses in separate tables; dropping doesn't affect SurveyResponse |

---

## Success Criteria

1. Business users can add custom questions during campaign setup
2. Traditional surveys render core questions + custom questions
3. Campaigns without custom questions work exactly as before
4. Custom responses are stored and included in exports
5. AI analysis continues to work on core metrics
6. Full backward compatibility maintained
