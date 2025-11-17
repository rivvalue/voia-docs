# Overview
VOÏA (Voice Of Client) is a Flask-based system for comprehensive customer feedback collection and AI-powered analysis, specializing in Net Promoter Score (NPS) surveys. It transforms raw customer feedback into actionable insights, identifying sentiment, key themes, churn risk, and growth opportunities. VOÏA aims to provide businesses with a robust tool for understanding customer sentiment, improving services, and fostering organic growth through AI-driven analysis of customer interactions. The project includes a production-ready multi-tenant participant management system with extensive email delivery capabilities, AI-powered conversational surveys using a hybrid prompt architecture, and participant segmentation for personalized experiences and advanced analytics.

# Recent Changes (November 17, 2025)

**Phase 1: French Language Support Foundation (COMPLETE)**
- **Database Schema**: Added `language_code` column to campaigns table (VARCHAR(5), CHECK constraint for 'en'/'fr', indexed) with backward-compatible default 'en'
- **Campaign Model**: Updated Campaign model with language_code field, included in to_dict() serialization
- **Bilingual Theme Mappings**: Created JSON configuration system (config/theme_mappings.json) with 15 canonical themes covering ~50-80 French/English variations
- **Theme Consolidation**: Enhanced consolidate_theme_name() to load bilingual mappings from JSON with 5-minute cache, graceful fallback to legacy English-only mappings
- **Feature Flags**: Implemented USE_BILINGUAL_THEMES environment variable (default: true) for instant rollback capability
- **Data Isolation**: Added mandatory campaign_id validation to /api/account_intelligence endpoint preventing cross-language data contamination
- **Response Tracking**: Added optional response_language field to survey_response table for analytics and segmentation
- **Architect Status**: Foundation reviewed and approved - no blocking defects, security validated, performance acceptable

**Pending Integration (Phases 2-5)**:
- Campaign UI language selector in creation/edit forms
- Email template rendering based on campaign language
- Survey page language injection into Flask-Babel session
- AI conversational prompt context for French/English responses
- End-to-end testing in staging environment

# Recent Changes (November 10, 2025)

**Phase 3 Frontend Refactoring - Functional Migration (ALL SPRINTS COMPLETE)**
- **MIGRATION COMPLETE**: All 5 sprints migrated (~3,054 lines total) with comprehensive orchestration layer
  - **Sprint 1 - charts.js** (~700 lines): 6 chart functions (NPS, sentiment, ratings, themes, tenure, growth factor) with mobile responsiveness
  - **Sprint 2 - account-intelligence.js** (~822 lines): 12 functions for high-risk accounts, growth opportunities, pagination, search with 300ms debounce
  - **Sprint 3 - comparison.js** (~630 lines): 8 functions for campaign comparison, executive summary, company comparison tables with pagination
  - **Sprint 4 - kpi-overview.js** (~441 lines): 10 functions for dashboard data loading, progressive rendering, auto-refresh, export functionality
  - **Sprint 5 - survey-insights.js** (~461 lines): 8 functions for survey response tables, company NPS, tenure NPS with API-based pagination
  - **Bootstrap utilities enhanced**: Added formatCampaignStatus() and formatDate() for shared formatting logic
  - **Orchestration layer complete**: dashboard-init.js implements campaign filter dropdown, global indicator, proper async initialization flow
- **ARCHITECTURE VALIDATED**: All modules use IIFE pattern, export to window.dashboardModules, proper state management via window.dashboardState
- **ASYNC FLOW VERIFIED**: initializeCampaigns() properly awaits kpiOverview.loadDashboardData() with error handling
- **SESSIONSTORAGE CONSISTENCY**: Raw ISO dates stored, formatted only at render time for locale/timezone consistency
- **SECURITY VALIDATED**: XSS protection via escapeHtml(), DOM-safe rendering, no credential exposure
- **PRODUCTION STATUS**: USE_REFACTORED_FRONTEND=false (legacy mode) - comprehensive testing required before enabling modular system
- **ROLLBACK SAFETY**: Original dashboard.js untouched, instant zero-downtime toggle capability maintained

**Phase 2 Frontend Refactoring - Structural Optimization (COMPLETE & PRODUCTION-READY)**
- **ARCHITECTURE COMPLETE**: Modular structure established for scalability
  - Created 7 JavaScript module scaffolds + fully implemented charts.js
  - Split custom.css (12,348 lines) into 6 tiered modules: base, utilities, components, pages, responsive, print (284KB total)
  - Implemented proper load order: bootstrap → data-service → features → init
  - Established window.dashboardState for global state, window.dashboardModules for exports
- **TESTED & VALIDATED**: Feature flag rollback mechanism works flawlessly (instant toggle, zero downtime)

**Phase 1 Frontend Refactoring - Performance Optimization (COMPLETE & PRODUCTION-READY)**
- Extracted inline JavaScript to external cached files for faster subsequent page loads
- Created modular JS utilities: campaign-form.js (13KB), participant-form.js (1.8KB), color-override.js (3.8KB)
- Implemented feature flag toggle system (USE_REFACTORED_FRONTEND) for instant zero-downtime rollback
- Enhanced resource hints in base.html (preconnect, dns-prefetch for CDN optimization)
- Maintained full bilingual support (English/French) with window.CampaignFormI18n translation bridge
- Eliminated ~70 lines of duplicate color override logic across dashboard.js
- All changes architect-reviewed and production-tested

# User Preferences
Preferred communication style: Simple, everyday language.
User interface tone: Thought leadership and research-oriented language, avoiding sales-oriented messaging.
Project customization: Rivvalue Inc. branding and conversational AI surveys for enhanced user experience.
Target market: French-speaking businesses and organizations.

# System Architecture
The system is a Flask web application with a multi-tiered architecture, using Jinja2, Bootstrap 5, custom CSS, vanilla JavaScript, and Chart.js for the frontend. The backend is Flask with SQLAlchemy ORM, designed for scalability. AI integration primarily uses the OpenAI API for NLP, sentiment analysis, and conversational surveys (VOÏA), supplemented by TextBlob.

**UI/UX**: Features multi-step survey forms, interactive dashboards, chat-style interfaces for conversational surveys, and Rivvalue Inc. branding with a professional blue color scheme. Includes modern sidebar navigation, mobile responsiveness, accessibility features, and a comprehensive breadcrumb system. Admin pages and the Survey Response page follow V2 patterns with bold red gradient headers and VOÏA brand color tokens.

**Technical Implementations**:
-   **Survey Collection**: Multi-step forms with dynamic follow-up questions and real-time validation.
-   **AI Analysis Engine**: Sentiment analysis, key theme extraction, churn risk assessment, growth opportunity identification, and NPS-based growth factor analysis. Features AI-generated plain-language summaries and reasoning explanations for transparency and trust-building with end-users.
-   **Conversational Surveys (VOÏA)**: AI-powered (GPT-4o) natural language interface with advanced personalization and a hybrid prompt architecture for dynamic question generation and structured data extraction. Features role-based persona templates (5-tier system), intelligent role mapping, anonymization guards, and multilingual support. Enhanced AI prompt personalization with a structured context block for full business metadata. Persistent conversation state storage ensures data recovery.
-   **Data Management**: Centralized data aggregation, NPS calculation, time-based filtering, optimized database queries, and separate tracking for Professional Services and Support Quality. Automated nightly reconciliation system.
-   **Authentication**: JWT token-based with email validation, admin roles, server-side token generation, and automatic invalidation.
-   **Performance & Scalability**: PostgreSQL-backed persistent task queue, database indexing, connection pooling, asynchronous background tasks for AI, IP-based rate limiting, optimized dashboard queries, admin-configurable response caching, and frontend optimizations. Scaled for 100 concurrent users with Gunicorn and expanded SQLAlchemy connection pool. Environment-aware static file caching.
-   **Audit Trail System**: Comprehensive audit logging with accurate timestamp preservation, integrated with a PostgreSQL task queue.
-   **Security**: Token-based authentication, duplicate response prevention, enhanced rate limiting, robust input validation, CSRF/XSS protection, and Sentry integration.
-   **Branding**: "VOÏA - Voice Of Client" with "AI Powered Client Insights" subtitle, specific tagline, multi-tenant logo system, and selective trial branding.
-   **Multi-Tenant Architecture**: Supports Business Accounts, Campaigns, and Participants with tenant isolation, dual authentication, and a token system for survey access. Participant entities support optional segmentation attributes.
-   **Participant Management Enhancements**: Individual editing with conditional email locking, deletion protection, tenure tracking, audit logging, and bulk edit functionality. Advanced multi-value filtering. Optimized participant list page load times. Implemented atomic row-level locking for bulk operations to prevent race conditions.
-   **Manual Commercial Value Tracking**: Company-level commercial value system for account intelligence, stored on the Participant model, with CSV upload validation and automatic synchronization.
-   **Email Delivery System**: Production-ready dual-mode email infrastructure (VOÏA-managed AWS SES or client-managed SMTP). Features encrypted password storage, connection testing, VOÏA-branded templates, background task processing, delivery tracking, configurable email content with 3-tier fallback, and automated reminder system. Includes comprehensive UI for configuration and multi-tenant isolation.
-   **Dual-Reminder System (Strategic Reversal)**: Enhanced automated reminder strategy with two-stage engagement: (1) Midpoint Reminder sent automatically halfway through campaign duration, and (2) Last Chance Reminder sent X days BEFORE campaign closes (configurable: 7, 10, or 14 days; default 10). Backend uses PostgreSQL interval arithmetic for efficient SQL-based date calculations. Frontend JavaScript displays both reminder dates with intelligent spacing validation and edge-case warnings.
-   **Campaign Lifecycle Management**: Automated status transitions, multi-tenant scheduling, automatic KPI snapshot generation, and background task management with audit logging.
-   **Hybrid Survey Customization**: Campaign-specific survey personalization with business account defaults.
-   **License Management System**: Enterprise-ready license management with usage tracking and enforcement.
-   **Business Account User Management**: Multi-tenant user management with professional UI, license-aware counters, and comprehensive user workflows.
-   **Onboarding System with Conditional Access**: Progressive, non-blocking onboarding for Core/Plus license holders with persistent warning banners and an onboarding progress dashboard.
-   **Feature Flag System**: Production-ready infrastructure for UI version toggling and frontend refactoring rollout.
-   **Frontend Refactoring Toggle**: Environment variable-based instant rollback mechanism (`USE_REFACTORED_FRONTEND`) enabling safe incremental deployment of optimized frontend code with zero-downtime rollback capability.
-   **Segmentation Analytics**: Comprehensive analytics system displaying NPS and satisfaction metrics segmented by participant attributes, including interactive Chart.js visualizations.
-   **Demo Data Generation**: High-volume test data scripts for realistic test data generation.
-   **JavaScript Translation Optimization**: Externalized translation payloads to cacheable static JSON files for mobile performance.
-   **Maintenance Mode**: Environment variable-controlled feature restricting access to a "coming soon" page.
-   **Translation/Internationalization (i18n)**: Production-ready bilingual support (English/French) using Flask-Babel, with a 4-layer fallback architecture and session-based language switching.
-   **Transcript Upload System**: AI-powered meeting transcript analysis universally available across all license tiers.
-   **Prompt Preview System (Development Only)**: Environment-gated feature for inspecting AI system prompts in survey customization pages, available in global and campaign-specific contexts.
-   **AI Cost Optimization Strategy**: Tiered OpenAI model routing architecture for 77% cost reduction, using GPT-4o-mini for most tasks with rule-based escalation to GPT-4o for high-risk scenarios.
-   **Notification System**: Real-time in-app notification center with professional UI for executive report generation and bulk operations. Features polished bell icon with unread badges, category-specific icons, mobile-responsive dropdown design with smooth animations, and Flask-Babel integration for French/English support. Notifications include rich metadata for deep linking to reports and resources.

# External Dependencies
-   **OpenAI API**: For advanced AI functionalities (sentiment analysis, theme extraction, conversational surveys).
-   **Bootstrap CDN**: For responsive UI components and styling.
-   **Chart.js CDN**: For interactive data visualizations.
-   **Font Awesome CDN**: For iconography.
-   **Python Packages**: Flask, SQLAlchemy, OpenAI client library, TextBlob, cryptography, Flask-Caching.
-   **Sentry**: For error tracking and performance monitoring.
-   **AWS SES / SMTP**: For email delivery.