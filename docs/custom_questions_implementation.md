# Classic Survey Feature - Implementation Plan

**Created:** January 21, 2026  
**Last Updated:** February 9, 2026  
**Status:** Part A Complete | Part B (Objective-Based Survey Configuration) Architecture Defined  

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

### Phase 2e: Classic Analytics & Cross-Type Comparison (COMPLETED)

**What was built:**
- [x] Dedicated `/api/classic_survey_analytics` endpoint serving 5 chart types:
  - CSAT distribution (1-5 scale)
  - CES distribution (1-8 scale)
  - Driver attribution with bilingual labels (resolved from ClassicSurveyConfig)
  - Feature adoption/satisfaction analysis
  - Recommendation status breakdown
- [x] Chart.js rendering integrated into campaign insights page via `checkAndLoadClassicAnalytics()`
- [x] Conditionally displayed for classic campaigns only
- [x] Cross-type comparison: survey_type badge on campaigns (purple=Classic, blue=Conversational AI)
- [x] Shared metrics (NPS, satisfaction, response rate) work for both survey types via type-agnostic dashboard data pipeline
- [x] Comparison API includes survey_type field
- [x] 30 automated tests covering model CRUD, freeze logic, route access control, data storage, analytics API, tenant isolation, cross-type comparison, and regression safety

**Files modified:** `routes.py`, `data_storage.py`, `templates/campaign_insights.html`, `tests/test_classic_survey.py`

### Phase 2f: KPI Snapshots & Analytics Tab UX Redesign (COMPLETED)

**What was built:**
- [x] CampaignKPISnapshot model extended with 8 classic-specific fields:
  - `survey_type` — campaign survey type at snapshot time
  - `avg_csat` — average CSAT score (Float)
  - `avg_ces` — average CES score (Float)
  - `csat_distribution` — CSAT score distribution (JSON in TEXT)
  - `ces_distribution` — CES score distribution (JSON in TEXT)
  - `driver_attribution` — NPS driver attribution data (JSON in TEXT)
  - `feature_analytics` — feature evaluation analytics (JSON in TEXT)
  - `recommendation_distribution` — recommendation status breakdown (JSON in TEXT)
- [x] `generate_campaign_kpi_snapshot()` captures classic metrics when `survey_type=='classic'`, reusing analytics logic from `classic_survey_analytics` endpoint. Conversational campaigns leave classic fields as None.
- [x] `convert_snapshot_to_dashboard_format()` includes `classic_analytics_snapshot` only when `snapshot.survey_type == 'classic'`
- [x] Classic analytics endpoint serves from snapshot for completed campaigns (avoids recalculating from raw responses)
- [x] Analytics tab redesigned with mutually exclusive containers:
  - `#conversationalAnalyticsSection` — NPS distribution, sentiment, tenure, growth factor, ratings (shown for conversational campaigns)
  - `#classicAnalyticsSection` — CSAT, CES, drivers, features, recommendation (shown for classic campaigns)
  - `checkAndLoadClassicAnalytics()` toggles visibility based on campaign survey_type
  - Prevents Chart.js conflicts between survey types
- [x] 7 new snapshot-specific tests (37 total) covering:
  - Snapshot model has classic fields
  - Snapshot `to_dict()` includes classic fields
  - Conversational snapshot unaffected
  - Snapshot generation captures classic data
  - Snapshot generation for conversational has no classic data
  - Snapshot conversion includes classic analytics for classic
  - Snapshot conversion excludes classic analytics for conversational

**Files modified:** `models.py`, `data_storage.py`, `routes.py`, `templates/campaign_insights.html`, `tests/test_classic_survey.py`

**Validation guide:**
1. View a completed classic campaign → Analytics tab shows classic charts (CSAT, CES, drivers, features, recommendation)
2. View a completed conversational campaign → Analytics tab shows conversational charts only (NPS, sentiment, tenure, growth factor)
3. No Chart.js conflicts — each survey type renders in its own container
4. Generate a KPI snapshot for a classic campaign → snapshot includes avg_csat, avg_ces, distributions
5. Generate a KPI snapshot for a conversational campaign → classic fields remain null
6. Classic analytics endpoint for completed campaign → serves from snapshot (not recalculated)

### Phase 2g: Driver Impact Analysis & NPS-CSAT-CES Correlation (COMPLETED)

**What was built:**
- [x] **Driver Impact Analysis (Diverging Bar Chart)**: Replaced simple driver count chart with NPS-aware impact analysis
  - Each driver now tracked by NPS category: promoters, passives, detractors counts
  - Net impact score calculated per driver (promoters minus detractors)
  - Diverging horizontal bar chart: green bars (promoters) extend right, red bars (detractors) extend left
  - Sorted by net impact — strengths at top, weaknesses at bottom
  - Tooltip shows per-category breakdown and net impact score
  - Custom legend with color-coded NPS categories
  - Backward-compatible fallback: old snapshot data without NPS breakdown renders as simple bar chart
- [x] **NPS-CSAT-CES Correlation Chart**: Bubble scatter chart revealing metric relationships
  - Each dot = one survey response, positioned by CSAT (x-axis, 1-5) and CES (y-axis, 1-8)
  - Color-coded by NPS category (green=Promoter, yellow=Passive, red=Detractor)
  - Bubble size proportional to NPS score
  - Chart.js bubble chart with interactive tooltips
- [x] **Correlation Summary Card**: Key insight stats below the scatter chart
  - NPS-CSAT alignment percentage (% of Promoters who also gave high CSAT)
  - Average CES by NPS category (Detractors vs Promoters)
  - Auto-generated insight text (e.g., "Detractors report 1.8x higher effort than Promoters")
- [x] `correlation_data` column added to CampaignKPISnapshot model (TEXT, JSON)
  - Stores scatter points and summary stats for completed campaign snapshots
  - No database migration needed beyond ALTER TABLE ADD COLUMN
- [x] Snapshot generation captures correlation data alongside enriched driver breakdown
- [x] Snapshot loading serves correlation data with backward-compatible fallback for old snapshots
- [x] 38 total tests (1 new: test_analytics_correlation_data, updated: driver attribution and snapshot tests)

**Files modified:** `models.py`, `data_storage.py`, `routes.py`, `templates/campaign_insights.html`, `tests/test_classic_survey.py`

**Validation guide:**
1. Open a classic campaign with responses → "Driver Impact Analysis" chart shows diverging bars (green right, red left)
2. Drivers sorted by net impact — strongest positive drivers at top
3. Hover tooltip shows promoters/passives/detractors counts and net impact
4. "NPS-CSAT-CES Correlation" scatter chart shows colored dots by NPS category
5. Correlation summary card shows alignment %, avg CES by category, and insight text
6. Old snapshots without NPS breakdown → fallback to simple bar chart (no crash)
7. New snapshot generation → includes enriched driver data and correlation points

### Phase 2h: Classic Survey Executive Reports (COMPLETED)

**What was built:**
- [x] **Classic survey awareness in executive reports**: Report generation now detects campaign survey_type and includes classic-specific analytics when applicable
- [x] **Classic data collection**: _collect_classic_analytics method gathers CSAT/CES averages & distributions, driver attribution with NPS breakdown (promoters/passives/detractors/net_impact), correlation points & summary (alignment %, avg CES by NPS category, insight text), feature analytics, and recommendation counts
- [x] **4 new matplotlib chart methods** for PDF rendering:
  - _create_csat_distribution_chart: Color-coded bar chart (1-5 scale)
  - _create_ces_distribution_chart: Color-coded bar chart (1-8 scale)
  - _create_driver_impact_chart: Diverging horizontal bar chart (green promoters right, red detractors left, sorted by net impact)
  - _create_correlation_scatter_chart: Scatter plot with NPS category color coding, sized by NPS score
- [x] **Classic sections in HTML template**: CSAT/CES KPI cards in overview, CSAT/CES distribution charts, Driver Impact Analysis chart + breakdown table, NPS-CSAT-CES Correlation scatter chart + summary card (alignment %, avg CES by category, insight text), Feature analytics table, Recommendation breakdown
- [x] **Conversational report unchanged**: Sentiment chart and Average Ratings section conditionally hidden for classic surveys; all other shared sections (NPS, high risk accounts, themes, timeline) remain for both types
- [x] **Edge case handling**: All chart methods have empty-data fallbacks; correlation insight_text uses explicit None checks to handle 0.0 values correctly

**Files modified:** `executive_report_service.py`

**Validation guide:**
1. Generate executive report for a conversational campaign → Report looks exactly like before (no changes)
2. Generate executive report for a classic campaign → Report includes CSAT/CES KPI cards, distribution charts, driver impact chart, correlation scatter + summary, feature analytics, recommendation breakdown
3. Classic report does NOT show sentiment breakdown chart or conversational average ratings section
4. Empty classic data → Charts show "No data available" fallback text
5. Report Details section now shows Survey Type

### Part A Summary

**Part A is FULLY COMPLETE as of February 9, 2026.** All phases delivered:
- Phase 1: Foundation (models, survey type selector)
- Phase 2: Participant survey form (multi-step classic questionnaire)
- Phase 2b: Survey preview for campaign managers
- Phase 2c: Response viewing (classic-specific display)
- Phase 2d: Welcome page & V2 design compliance
- Phase 2e: Classic analytics & cross-type comparison
- Phase 2f: KPI snapshots & analytics tab redesign
- Phase 2g: Driver Impact Analysis & NPS-CSAT-CES correlation
- Phase 2h: Classic survey executive reports
- Classic survey config editor UI (drivers/features/sections editing)

### Pending: Performance Optimizations (from Architect Review, Feb 2026)

4 items identified during performance validation — not blockers for Part B:
1. **Matplotlib figure cleanup (High)** — Verify all chart methods explicitly close figures after saving to buffer to prevent memory leaks
2. **Classic analytics query optimization (Medium)** — Select only needed columns instead of full response rows for large campaigns
3. **Classic analytics endpoint caching (Medium)** — Confirm classic_survey_analytics route leverages response caching strategy
4. **Concurrent report generation safeguards (Medium)** — Rate limiting or queue-based generation to prevent memory spikes

---

## Part B: Objective-Based Survey Configuration

### Vision

VOÏA uses an **Objective-Based Survey Configuration** paradigm — NOT question-based design.

Instead of:
> "Create your survey"

VOÏA offers:
> **"What do you want to understand?"**

Users configure **intent**, not methodology.

**Status:** Architecture Defined — Implementation Pending  
**Last Updated:** February 9, 2026

### Core Principle

Each business objective unlocks a **pre-designed, expert-curated question set** with proven ordering, scales, and logic. Users never see or manipulate individual questions — they select what they want to learn, and VOÏA handles the survey design.

### Example Objectives

| Objective | What It Answers | Target Use Case |
|---|---|---|
| **360 CX View** | Comprehensive customer experience assessment across all touchpoints | General CX health check |
| **Understand Loyalty Drivers** | What drives customers to stay or recommend | Retention strategy |
| **Understand Churn Risk** | Why customers leave and early warning signals | Churn prevention |
| **Prioritize Product Roadmap** | Which features matter most to customers | Product planning |
| **Diagnose Onboarding Friction** | Where new customers struggle in their journey | Onboarding improvement |
| **Prepare Renewal Discussions** | Customer sentiment and priorities before contract renewal | Account management |

### What Each Objective Includes

Every objective is a **self-describing template** that packages both halves together:

**Survey Side:**
- Curated question set with proven ordering
- Appropriate scales and response types for each question
- Section organization optimized for respondent experience
- Bilingual support (EN/FR)

**Analytics Side:**
- Pre-built dashboard charts specific to the objective's data
- KPI definitions and calculation logic
- Executive report sections with appropriate chart types (matplotlib)
- AI insight prompts tailored to the objective's focus area

One cannot exist without the other. Adding a new objective to VOÏA means delivering both the question set AND its analytics module as a single unit.

---

### Architecture

#### Self-Describing Template Model

Each objective/template defines:

```
Template = {
    Metadata:       name, description, icon, category
    Questions:      ordered list of questions with types, scales, options
    Sections:       how questions are grouped in the survey form
    Metrics:        how to calculate KPIs from the answers
    Charts:         what chart type to use for each metric (bar, distribution, diverging, scatter, heatmap)
    Report:         which KPIs and charts appear in the executive report
    AI Prompts:     objective-specific insight generation prompts
}
```

#### Layered Survey Assembly

Every classic survey is assembled from two layers:

1. **Core Metrics (mandatory, always present):**
   - NPS (0-10) with category-based driver attribution
   - CSAT (1-5)
   - CES (1-8)
   - These provide standardized cross-campaign benchmarking regardless of objective

2. **Objective-Specific Questions (from selected template):**
   - Curated questions that serve the chosen objective
   - Rendered after core metrics in the survey form
   - Analytics pre-built for the known data structure

#### Relationship to Current Classic Survey

The current Part A classic survey (NPS + CSAT + CES + drivers + features + recommendation) becomes the **first template**: **"360 CX View"**. This is a reframing, not a rebuild:

- The existing `ClassicSurveyConfig` with its drivers, features, and sections = the "360 CX View" template definition
- The existing classic analytics (CSAT/CES distributions, driver impact, correlation, feature analytics, recommendation) = the "360 CX View" analytics module
- The existing executive report classic sections = the "360 CX View" report module

No existing functionality is lost or rewritten. It is repositioned as the first entry in the objective catalog.

#### Campaign Configuration Flow

1. User creates a new classic campaign
2. System presents: **"What do you want to understand?"** with available objectives
3. User selects an objective (one per campaign in v1)
4. System auto-assembles the survey from core metrics + objective's question set
5. User can preview the assembled survey
6. Objective choice is locked after campaign activation (existing freeze pattern)

---

### Key Design Decisions

1. **One objective per campaign (v1)** — Keeps surveys focused, avoids question overlap/deduplication, and makes analytics clean. Multi-objective support can be added later.
2. **Core metrics always mandatory** — NPS, CSAT, CES captured in every survey regardless of objective, enabling cross-campaign and cross-objective benchmarking.
3. **Templates are paired units** — Every template ships its question set AND its analytics module together. You cannot add one without the other.
4. **Configuration-driven, not hardcoded** — Objectives and question sets are stored as data (database/config), not as code. Adding a new objective does not require code changes to the rendering or analytics engines.
5. **Platform admin controls the catalog** — Only platform admins can create/modify objectives. Business users select from the catalog. This ensures survey quality and analytics consistency.
6. **Backward compatible** — Existing classic campaigns continue to work exactly as they do today. The "360 CX View" template maps directly to the current classic survey structure.
7. **Versioning** — Templates carry a version number. Updates to a template do not affect campaigns already using an earlier version.
8. **Bilingual** — All template content (question text, section titles, option labels) supports EN/FR.

---

### Phased Implementation Roadmap

#### Phase B1: Reframe Current Classic Survey as "360 CX View" Template

**Scope:** UI and data model changes only. No new survey content or analytics.

- [ ] Create `SurveyObjective` model (name, description, icon, category, version, is_active, is_system)
- [ ] Create mapping between `SurveyObjective` and `ClassicSurveyConfig` (objective_id on campaign or config)
- [ ] Seed "360 CX View" as the first (and only) objective with metadata
- [ ] Update campaign creation flow: replace direct classic config setup with objective selection step ("What do you want to understand?")
- [ ] When "360 CX View" is selected, auto-create `ClassicSurveyConfig` with current default values (same behavior as today, different UX framing)
- [ ] Campaign view shows selected objective name and description
- [ ] Lock objective choice after activation (existing freeze pattern)
- [ ] Existing classic campaigns without an objective assignment default to "360 CX View" (backward compatibility)

**Outcome:** Users experience the new "What do you want to understand?" flow. Only one option available ("360 CX View"), but the architecture is in place for more.

#### Phase B2: Generic Survey Rendering Engine

**Scope:** Decouple survey form rendering from hardcoded field references.

- [ ] Define a question specification format within the template (question key, type, scale range, options, section, order, required flag, bilingual text)
- [ ] Build a generic survey form renderer that reads the template's question specifications and generates the appropriate form inputs (rating scales, checkboxes, text areas, etc.)
- [ ] Build a generic response storage mechanism: `ObjectiveAnswer` table (response_id, question_key, answer_type, numeric_value, text_value, options_json)
- [ ] Migrate the "360 CX View" survey rendering to use the generic engine (same output, different internal path)
- [ ] Verify all existing classic survey functionality produces identical results through the new engine

**Outcome:** Survey forms are rendered from template configuration, not hardcoded HTML. Adding new questions or sections to a template does not require template code changes.

#### Phase B3: Generic Analytics Engine

**Scope:** Decouple analytics from hardcoded chart methods and field references.

- [ ] Define an analytics specification format within the template: metric definitions (which questions feed which KPIs), chart definitions (chart type, data source, labels, colors), and report section definitions
- [ ] Build a chart type registry: question_type → appropriate chart renderer (distribution bar, diverging bar, scatter, frequency, heatmap)
- [ ] Build a generic KPI calculator that computes metrics from template-defined formulas
- [ ] Build a dashboard composer that renders chart sections based on the template's analytics spec
- [ ] Build an executive report composer that generates report sections from the template's report spec
- [ ] Migrate "360 CX View" analytics to use the generic engine (same charts and KPIs, different internal path)
- [ ] Verify all existing analytics, dashboard charts, and executive report sections produce identical results

**Outcome:** Analytics are driven by template configuration. Each template defines what to measure and how to visualize it. The rendering engine is shared.

#### Phase B4: Second Objective — Proof of Architecture

**Scope:** Add a second objective to validate the architecture works end-to-end.

- [ ] Design a second objective (e.g., "Understand Churn Risk") with its curated question set
- [ ] Define its analytics spec: KPIs, chart types, report sections
- [ ] Add it to the objective catalog (database seed)
- [ ] Verify: campaign creation offers two choices, survey renders the correct questions, analytics show the correct charts, executive report includes the correct sections
- [ ] Verify: "360 CX View" campaigns are completely unaffected

**Outcome:** The architecture is proven. Adding the third, fourth, fifth objective follows the same pattern — define the template, seed it, done.

#### Phase B5+: Expand the Objective Catalog

Future objectives to design and add (each following the same template pattern):
- [ ] Understand Loyalty Drivers
- [ ] Prioritize Product Roadmap
- [ ] Diagnose Onboarding Friction
- [ ] Prepare Renewal Discussions
- [ ] Platform admin UI for managing the objective catalog

---

### Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| Generic engine produces different results than current hardcoded analytics | High | Phase B2/B3 include explicit verification that output is identical before switching |
| Over-engineering the generic engine before proving value | Medium | Phase B1 is pure reframing (minimal changes). B2/B3 only needed before adding second objective |
| Template specification format too rigid for future objectives | Medium | Design spec format based on requirements of 3-4 known objectives before finalizing |
| Performance regression from generic rendering vs hardcoded | Low | Generic engine uses same underlying queries/matplotlib; overhead is configuration lookup only |
| Backward compatibility for existing campaigns | Medium | Default assignment to "360 CX View" for campaigns without explicit objective |

### Pragmatic Approach

Phases B1 through B3 can be done incrementally. The most pragmatic path:

- **Phase B1 can be done now** — it's a small UI/data model change that reframes the existing experience without touching analytics or survey rendering internals.
- **Phases B2-B3 should be done together**, but only when you're ready to add the second objective. Building the generic engine without a second template to validate it risks over-engineering.
- **Phase B4 is the proof point** — if the second objective works cleanly through the generic engine, the architecture is validated and every subsequent objective is just configuration.

---

### Success Criteria

1. Users see "What do you want to understand?" when creating a classic campaign — not "Create your survey"
2. Each objective delivers a complete, expert-designed survey with no user configuration of individual questions
3. Each objective ships with its own analytics dashboard, KPIs, and executive report sections
4. Adding a new objective requires only template configuration, not code changes to the rendering or analytics engines
5. Existing "360 CX View" campaigns and analytics work identically to today
6. Full backward compatibility maintained throughout all phases
