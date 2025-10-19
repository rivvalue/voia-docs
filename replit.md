# Overview
The Voice of Client (VOÏA) is a Flask-based system for comprehensive customer feedback collection and AI-powered analysis, specializing in Net Promoter Score (NPS) surveys. Its purpose is to convert raw customer feedback into actionable insights, identifying sentiment, key themes, churn risk, and growth opportunities. VOÏA provides businesses with a robust tool for understanding customer sentiment, improving services, and fostering organic growth through AI-driven analysis of customer interactions. The project features a production-ready multi-tenant participant management system with extensive email delivery capabilities, AI-powered conversational surveys with hybrid prompt architecture, and participant segmentation for personalized experiences and advanced analytics.

# User Preferences
Preferred communication style: Simple, everyday language.
User interface tone: Thought leadership and research-oriented language, avoiding sales-oriented messaging.
Project customization: Rivvalue Inc. branding and conversational AI surveys for enhanced user experience.

# System Architecture
The system is a Flask web application with a multi-tiered architecture. The frontend uses Jinja2, Bootstrap 5, custom CSS, vanilla JavaScript, and Chart.js. The backend is Flask with SQLAlchemy ORM, designed for scalability from SQLite to PostgreSQL. AI integration, primarily via OpenAI API, handles natural language processing, sentiment analysis, and conversational surveys (VOÏA), supplemented by TextBlob.

**UI/UX**: Multi-step survey forms, interactive dashboards, chat-style interfaces for conversational surveys, and Rivvalue Inc. branding with a professional blue color scheme. Modern sidebar navigation, mobile responsiveness, and active state highlighting. The Settings Hub features a 4-card layout with reusable components. Modernized dashboard and campaign pages feature consistent typography, clean white backgrounds with red accents, lighter shadows, and standardized badge styling. The home page features a minimalist design with red accent borders for features and optimized mobile layouts. Business Intelligence Navigation includes a three-tier structure: Overview, Executive Summary, and Campaign Insights, separating strategic oversight from operational analysis. Session-based Breadcrumb Navigation ensures intelligent back-button behavior. Admin pages and the Survey Response page are fully redesigned with Settings Hub v2 patterns, featuring bold red gradient headers, VOÏA brand color tokens, comprehensive ARIA accessibility attributes, and mobile-responsive breakpoints. All inline styles are migrated to custom.css using design system variables, and emoji icons are replaced with FontAwesome. A comprehensive breadcrumb system is implemented across 26 business pages using a reusable component with consistent design patterns and responsive optimization.

**Technical Implementations**:
-   **Survey Collection**: Multi-step forms with dynamic follow-up questions and real-time validation.
-   **AI Analysis Engine**: Sentiment analysis, key theme extraction, churn risk assessment, growth opportunity identification, and NPS-based growth factor analysis.
-   **Conversational Surveys (VOÏA)**: AI-powered (GPT-4o) natural language interface with advanced personalization capabilities. Features include:
    -   **Hybrid Prompt Architecture**: Combines structured JSON configuration (machine-readable constraints, topic priorities, field mappings) with natural language conversation guidance for optimal AI performance
    -   **Participant Segmentation**: Integrates role, region, customer_tier, and language attributes for contextual question adaptation (C-Level gets strategic questions, End Users get tactical ones)
    -   **Topic-to-Field Mapping**: Structured mapping between survey topics and database fields enabling validation, analytics, and observability
    -   **Dynamic Question Generation**: Real-time AI-generated follow-ups based on participant responses and profile
    -   **Structured Data Extraction**: Automatic parsing and validation of conversational responses into database-ready format
    -   **Feature Flag Rollout**: VOIA_USE_HYBRID_PROMPT environment variable for gradual deployment with A/B testing capability
    -   **Backward Compatibility**: Legacy prompt system preserved for safe production rollout
-   **Data Management**: Centralized data aggregation, NPS calculation, time-based filtering, and optimized database queries.
-   **Authentication**: JWT token-based with email validation, admin roles, server-side token generation, and automatic invalidation post-survey.
-   **Performance**: PostgreSQL migration, database indexing (including GIN index), connection pooling (optimized for Neon serverless), asynchronous background tasks for AI, IP-based rate limiting, optimized dashboard queries, admin-configurable response caching, index page response caching, Executive Summary comparison optimization, and frontend optimizations.
-   **Security**: Token-based authentication, duplicate response prevention, enhanced rate limiting, robust input validation, CSRF/XSS protection, and Sentry integration.
-   **Branding**: "VOÏA - Voice Of Client" with "AI Powered Client Insights" subtitle, specific tagline, multi-tenant logo system, and selective trial branding.
-   **Multi-Tenant Architecture**: Business Accounts, Campaigns, and Participants with tenant isolation via `business_account_id` scoping, dual authentication, and a token system for survey access, including a lightweight scheduler. Participant entities support optional segmentation attributes (role, region, customer_tier, language) for personalized survey experiences and advanced analytics segmentation.
-   **Email Delivery System**: Multi-provider email infrastructure (AWS SES, SMTP) with business accounts choosing providers, encrypted password storage, connection testing, professional VOÏA-branded templates, background task processing, delivery tracking, and configurable email content at both business account and campaign levels, with a 3-tier fallback architecture for customization.
-   **Campaign Lifecycle Management**: Automated status transitions, multi-tenant scheduling, automatic KPI snapshot generation, and background task management.
-   **Hybrid Survey Customization**: Campaign-specific survey personalization with business account defaults.
-   **License Management System**: Enterprise-ready license management with usage tracking and enforcement.
-   **Business Account User Management**: Multi-tenant user management with professional UI, license-aware counters, and comprehensive user workflows.
-   **Mandatory Onboarding System**: Extensible guided setup workflow for business account administrators.
-   **Feature Flag System**: Production-ready infrastructure for UI version toggling.

# External Dependencies
-   **OpenAI API**: For advanced AI functionalities including sentiment analysis, theme extraction, and conversational surveys.
-   **Bootstrap CDN**: For responsive UI components and styling.
-   **Chart.js CDN**: For interactive data visualizations.
-   **Font Awesome CDN**: For iconography.
-   **Python Packages**: Flask, SQLAlchemy, OpenAI client library, TextBlob, cryptography, Flask-Caching.
-   **Sentry**: For error tracking and performance monitoring.

# Hybrid Prompt Architecture - Operational Guide

## Overview
The hybrid prompt architecture enables personalized AI-powered conversational surveys by combining structured JSON configuration with natural language guidance. This section provides operational guidance for testing, deployment, and monitoring.

## Feature Flag Configuration
-   **Environment Variable**: `VOIA_USE_HYBRID_PROMPT`
-   **Default Value**: `false` (legacy prompt system active)
-   **Values**: `true` (hybrid prompt), `false` (legacy prompt)
-   **How to Enable**: Set environment variable to `true` in Replit Secrets

## Rollout Strategy
1. **Feature Flag Testing** (Current Phase):
   - Set `VOIA_USE_HYBRID_PROMPT=true` in development
   - Test with participants across different roles, regions, and tiers
   - Validate topic-field mappings and data persistence
   - Monitor AI token usage and response quality

2. **Demo Mode**:
   - Enable for internal business account testing
   - Collect feedback from stakeholders
   - Validate role-based personalization effectiveness

3. **Limited Rollout (10% of Business Accounts)**:
   - Enable for selected business accounts via feature flag
   - Monitor completion rates, topic coverage, and data quality
   - Compare hybrid vs. legacy prompt performance metrics

4. **Full Rollout with A/B Testing**:
   - Randomly assign 50% business accounts to hybrid prompt
   - Track success metrics: completion rate, topic field population, priority order adherence
   - Gradually increase to 100% based on performance data

## Testing Checklist
### Participant Segmentation Testing:
- [ ] Create participants with different roles (C-Level, Manager, End User)
- [ ] Create participants with different customer tiers (Enterprise, SMB, Startup)
- [ ] Create participants with different regions (North America, EMEA, APAC)
- [ ] Upload CSV with segmentation columns
- [ ] Upload CSV without segmentation columns (backward compatibility)
- [ ] Verify participant profiles appear in conversational survey context

### Hybrid Prompt Testing:
- [ ] Start conversational survey with C-Level participant (expect strategic questions)
- [ ] Start conversational survey with End User participant (expect tactical questions)
- [ ] Start conversational survey with Enterprise tier participant (expect integration/compliance focus)
- [ ] Start conversational survey with SMB tier participant (expect value/support focus)
- [ ] Verify topic-field mappings: NPS → nps_score/nps_reasoning
- [ ] Verify topic-field mappings: Additional Feedback → additional_comments
- [ ] Check conversation tone adapts to participant context
- [ ] Validate survey completion and data persistence

### Analytics Validation:
- [ ] Segment NPS scores by role (C-Level vs End User vs Manager)
- [ ] Segment satisfaction ratings by customer tier (Enterprise vs SMB)
- [ ] Segment feedback themes by region (North America vs EMEA vs APAC)
- [ ] Verify all topic fields are populated correctly
- [ ] Verify additional_comments captures Additional Feedback responses

## Success Metrics
-   **Survey Completion Rate**: Target ≥85% (comparable to legacy prompt)
-   **Topic Field Population**: Target ≥95% of critical topics covered
-   **Priority Order Adherence**: Target ≥90% surveys follow topic priority
-   **Token Usage**: Expected +10-15% vs. legacy (structured JSON + personalization)
-   **User Satisfaction**: Qualitative feedback from business accounts and participants

## Topic-to-Field Reference
| Survey Topic | Database Fields | Validation |
|-------------|-----------------|------------|
| NPS | nps_score, nps_reasoning | Score 0-10, reasoning required |
| Business Relationship Tenure | tenure_with_fc | Text field |
| Overall Satisfaction | satisfaction_rating | Rating 1-5 |
| Professional Services Quality | service_rating | Rating 1-5 |
| Support Quality | service_rating | Rating 1-5 |
| Product Value | product_value_rating | Rating 1-5 |
| Pricing Value | pricing_rating | Rating 1-5 |
| Improvement Suggestions | improvement_feedback | Text field |
| Additional Feedback | additional_comments | Text field |

## Troubleshooting
### Issue: Hybrid prompt not activating
-   **Solution**: Verify `VOIA_USE_HYBRID_PROMPT=true` in environment variables
-   **Solution**: Restart application after setting environment variable

### Issue: Topic fields not populating
-   **Solution**: Review TOPIC_FIELD_MAP in prompt_template_service.py
-   **Solution**: Check AI response parsing in ai_conversational_survey.py
-   **Solution**: Verify database fields exist in SurveyResponse model

### Issue: Role-based personalization not working
-   **Solution**: Verify participant has role/tier/region attributes set
-   **Solution**: Check participant_data passed to AIConversationalSurvey
-   **Solution**: Review system prompt includes participant profile section

### Issue: CSV upload fails with segmentation columns
-   **Solution**: Verify column names match exactly: role, region, customer_tier, language
-   **Solution**: Check values match dropdown options (case-sensitive)
-   **Solution**: Use provided CSV template for reference

## Rollback Procedure
If issues arise during rollout:
1. Set `VOIA_USE_HYBRID_PROMPT=false` to revert to legacy prompt
2. Restart application to apply changes
3. All in-progress surveys will use legacy prompt
4. No data loss - participant segmentation fields remain intact
5. Hybrid prompt can be re-enabled after addressing issues

## Future Enhancements
-   Multilingual survey support using language attribute
-   Industry-specific topic templates
-   Custom topic-field mappings per business account
-   Advanced analytics dashboards with segmentation filters
-   AI response validation layer for topic field accuracy