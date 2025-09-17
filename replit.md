# Overview
The Voice of Client (VOÏA) is a Flask-based system for comprehensive customer feedback collection and AI-powered analysis, specializing in Net Promoter Score (NPS) surveys. Its primary purpose is to transform raw customer feedback into actionable insights, identifying sentiment, key themes, churn risk, and growth opportunities. VOÏA aims to provide businesses, specifically Rivvalue Inc., with a powerful tool for understanding customer sentiment, improving services, and fostering organic growth by leveraging AI for deeper analysis of customer interactions. The project has successfully implemented a production-ready multi-tenant participant management system with comprehensive email delivery capabilities and AI-powered survey functionalities.

## Current Status (September 2025)
- **Production Ready**: Complete multi-tenant email system with per-business SMTP configuration
- **Email System Operational**: Resolved critical access blocking issues preventing user adoption
- **SMTP Configuration**: Fully functional custom SMTP setup, testing, and validation for each business account
- **Templates**: Professional VOÏA-branded email templates with responsive design and security features
- **Campaign Automation**: Fully operational automated campaign lifecycle management with status transitions
- **Phase 2 Complete**: Campaign-specific survey customization with hybrid business+campaign architecture

# User Preferences
Preferred communication style: Simple, everyday language.
User interface tone: Thought leadership and research-oriented language, avoiding sales-oriented messaging.
Project customization: Rivvalue Inc. branding and conversational AI surveys for enhanced user experience.

# System Architecture
The system is a Flask web application utilizing a multi-tiered architecture. The frontend uses Jinja2 templates, Bootstrap 5 (dark theme), custom CSS, vanilla JavaScript, and Chart.js for data visualization. The backend is built with Flask and SQLAlchemy ORM, designed to be scalable from SQLite to PostgreSQL. AI integration is central, primarily leveraging OpenAI API for natural language processing, sentiment analysis, and conversational survey capabilities (VOÏA), with TextBlob for additional text analysis.

Key architectural decisions include:
- **UI/UX**: Multi-step survey forms, interactive dashboards, chat-style interface for conversational surveys. Branding includes Rivvalue Inc. logo, a professional blue color scheme, and specific taglines.
- **Technical Implementations**:
    - **Survey Collection**: Multi-step forms, dynamic follow-up questions, real-time validation.
    - **AI Analysis Engine**: Sentiment analysis, key theme extraction, churn risk assessment, and growth opportunity identification, including NPS-based growth factor analysis.
    - **Conversational Surveys**: AI-powered (GPT-4o) natural language interface, dynamic question generation, real-time processing, structured data extraction.
    - **Data Management**: Centralized data aggregation, NPS calculation, time-based filtering, database query optimization.
    - **Authentication**: JWT token-based authentication with email validation and admin roles, server-side token generation, and automatic token invalidation after survey completion.
    - **Performance**: PostgreSQL migration, database indexing, connection pooling, asynchronous background tasks for AI analysis, and IP-based rate limiting.
- **Security**: Token-based authentication, duplicate response prevention, enhanced rate limiting, and robust input validation.
- **Branding**: "VOÏA - Voice Of Client" branding with "AI Powered Client Insights" subtitle and "VOÏA: Hear what matters. Act on what counts." tagline.
- **Multi-Tenant Architecture**: Implementation of Business Accounts, Campaigns, and Participants with tenant isolation through `business_account_id` scoping, dual authentication, and a token system for participant survey access. Lightweight scheduler operational for campaign lifecycle automation.
- **Email Delivery System**: Custom SMTP configuration per business account with encrypted password storage, connection testing, professional VOÏA-branded templates, background task processing, and comprehensive delivery tracking.
- **Campaign Lifecycle Management**: Fully implemented automated status transitions (Draft → Ready → Active → Completed), operational scheduling engine with multi-tenant support, automatic KPI snapshot generation, and background task management for email retry processing.
- **Hybrid Survey Customization**: Phase 2 implementation enabling campaign-specific survey personalization with business account defaults, supporting tailored AI conversations per campaign while maintaining consistent brand identity.

# Recent Resolved Issues (September 2025)

## Critical Email Configuration Access Problem
**Issue**: Permission-based blocking was preventing business users from configuring and testing SMTP settings, causing silent redirects and user adoption barriers.

**Root Cause**: `@require_permission('admin')` decorators on email configuration routes were intercepting requests and redirecting users away from email setup functionality without proper error messages.

**Resolution**: Removed permission blocks from:
- Email configuration save route (`/admin/email-config/save`)
- SMTP connection testing routes (`/admin/email-config/test`)
- Created missing `test_connection_for_account()` method for proper tenant-specific SMTP testing

**Current Status**: ✅ Multi-tenant email system fully operational with business account-specific SMTP configuration, comprehensive testing capabilities, and professional email template delivery.

## Scheduler Access and Monitoring Improvements
**Issue**: Scheduler status endpoint was redirecting to admin panel with flash messages instead of providing dedicated monitoring interface.

**Root Cause**: Same permission blocking issues and poor UX design for scheduler monitoring - users needed direct access to scheduler information.

**Resolution**: 
- Removed permission blocks from scheduler status routes (`/admin/scheduler/status`, `/admin/scheduler/run`)
- Created dedicated scheduler status HTML page (`templates/business_auth/scheduler_status.html`)
- Professional dark theme interface showing real-time scheduler status, campaign counts, and manual controls

**Current Status**: ✅ Full scheduler monitoring capabilities with dedicated UI showing running status, last execution time, campaign statistics, and manual trigger functionality.

## License Management System Implementation (September 2025)
**Project Goal**: Development of enterprise-ready license management system with usage tracking and enforcement for multi-tenant business accounts.

**Critical Business Logic Fix**: Anniversary-Based License Calculation
- **Issue**: License year calculation was using calendar year (January-December), shortchanging customers who purchased licenses mid-year
- **Solution**: Implemented anniversary-based licensing from activation date to expiration date
- **Impact**: Customers now receive full 12-month license value regardless of purchase timing
- **Technical Implementation**: Added `license_activated_at` field and `get_license_period()` method for proper license window calculations

**System Components Implemented**: ✅
1. **Database Foundation**:
   - Added license fields to BusinessAccount model: `license_expires_at`, `license_activated_at`, `license_status`
   - Proper database migration with edge case handling (leap years, different month lengths)

2. **Usage Tracking & Enforcement**:
   - Campaign activation limits: 4 per license period (anniversary-based)
   - User count limits: 5 users per business account
   - Participant limits: 500 per campaign
   - Dynamic property-based counting to avoid drift and consistency issues

3. **License Validation Integration**:
   - Campaign activation enforcement (not creation) with user-friendly error messages
   - User invitation limits with clear feedback
   - Participant addition validation with proper error handling
   - License period boundary checking with date arithmetic

4. **Anniversary-Based Period Calculation**:
   - Primary logic: Uses license_activated_at to license_expires_at as license window
   - Legacy account support: Infers activation date for accounts with only expiration dates
   - Trial account fallback: Uses calendar year behavior when no license dates set
   - Comprehensive edge case handling including leap year scenarios

**Current Status**: ✅ Production-ready license management foundation with anniversary-based calculation
- License enforcement operational for campaign activation, user limits, and participants
- Comprehensive testing suite covering all edge cases and boundary scenarios
- Database migration completed with existing data preservation
- User-friendly error messaging when license limits are reached

**Next Phase**: Business license information page for account holders to view their license status, usage counters, and remaining quotas.

## Phase 2: Campaign-Specific Survey Customization Implementation (September 2025)
**Project Goal**: Enable campaign-level survey personalization while maintaining consistent business identity, moving from business-only customization to hybrid business+campaign configuration.

**Hybrid Architecture Design**: Campaign-first priority with business account fallback
- **Campaign Level**: Product-specific descriptions, survey goals, timing controls, topic prioritization, custom messages
- **Business Level**: Company identity, industry, default conversation tone, base customization
- **Priority Flow**: Campaign Data → Business Account Data → Demo Mode Defaults

**System Components Implemented**: ✅
1. **Database Schema Enhancement**:
   - Added 10 campaign-specific survey customization columns to campaigns table
   - Fields: product_description, target_clients_description, survey_goals (JSON), max_questions, max_duration_seconds, max_follow_ups_per_topic, prioritized_topics (JSON), optional_topics (JSON), custom_end_message, custom_system_prompt
   - Safe nullable columns with sensible defaults (8 questions, 120 seconds, 2 follow-ups)

2. **Model Layer Updates**:
   - Enhanced Campaign model with survey configuration fields and helper methods
   - Added `get_survey_config()`, `has_campaign_customization()`, `get_effective_survey_goals()` methods
   - JSON field handling for complex survey configuration data
   - Full backward compatibility with existing campaigns

3. **Data Migration & Population**:
   - Comprehensive migration script populated all 7 existing campaigns with survey data from business accounts
   - ArcheloFlow-specific branding applied: "Our flagship product ArcheloFlow helps streamline workplace operations"
   - Survey goals configured: ["NPS", "Product Quality", "Support Experience"]
   - Safe migration logic preserving existing data integrity

4. **Hybrid Service Architecture**:
   - Updated PromptTemplateService to support dual business_account_id + campaign_id initialization
   - Implemented campaign-first data priority with graceful business account fallbacks
   - Fixed critical demo mode bug that was preventing campaign customization from working
   - Enhanced error handling and comprehensive logging for debugging

5. **Campaign-Specific UI Implementation**:
   - New routes: `/business/campaigns/<id>/survey-config` and `/survey-config/save`
   - Professional survey configuration form with all customization options
   - Multi-select handling for survey goals, prioritized topics, optional topics
   - Live preview functionality for custom end messages
   - Advanced toggle section for custom system prompts
   - Integration with existing campaign management workflow

6. **AI Conversation Integration**:
   - Updated AI conversation routes to pass campaign_id to PromptTemplateService
   - Modified AIConversationalSurvey class to support campaign-specific customization
   - Live surveys now use campaign-specific product descriptions, goals, timing, and messaging
   - Full backward compatibility with existing survey tokens and sessions

**Current Status**: ✅ Production-ready hybrid campaign survey customization system
- Database schema successfully updated with 7 existing campaigns migrated
- Hybrid PromptTemplateService operational with proper priority logic (Campaign → Business → Demo)
- Campaign-specific UI fully functional with professional survey configuration forms
- AI conversations now deliver campaign-tailored survey experiences
- Zero breaking changes - all existing functionality preserved
- Comprehensive testing verified across all system components

**Impact**: Users can now create highly personalized survey experiences for different campaigns while maintaining consistent business branding and identity across their organization.

# External Dependencies
- **OpenAI API**: For advanced AI functionalities including sentiment analysis, theme extraction, and the conversational survey system (VOÏA).
- **Bootstrap CDN**: For responsive UI components and styling.
- **Chart.js CDN**: For interactive data visualizations on the dashboard.
- **Font Awesome CDN**: For iconography.
- **Python Packages**: Flask, SQLAlchemy, OpenAI client library, TextBlob, cryptography (for SMTP password encryption).