# Overview
VOÏA (Voice Of Client) is a Flask-based system for comprehensive customer feedback collection and AI-powered analysis, specializing in Net Promoter Score (NPS) surveys. It transforms raw customer feedback into actionable insights, identifying sentiment, key themes, churn risk, and growth opportunities. VOÏA aims to provide businesses with a robust tool for understanding customer sentiment, improving services, and fostering organic growth through AI-driven analysis of customer interactions. The project includes a production-ready multi-tenant participant management system with extensive email delivery capabilities, AI-powered conversational surveys using a hybrid prompt architecture, and participant segmentation for personalized experiences and advanced analytics.

# Recent Changes
**November 6, 2025 - Code Analysis & Refactoring Documentation**
- Completed comprehensive code analysis for frontend and backend optimization opportunities
- Created `FRONTEND_REFACTORING_PLAN.md` documenting:
  - 4,600-line dashboard.js monolithic file (50-60% reduction potential)
  - 12,348-line custom.css file (40-50% reduction potential)
  - Inline JavaScript in 20+ templates (browser caching opportunity)
  - Mobile performance optimization strategies
- Created `BACKEND_REFACTORING_PLAN.md` documenting:
  - Redis cache migration opportunity (10x dashboard performance improvement: 500ms → 50ms)
  - Route file consolidation (9,420 lines → modular structure)
  - Code duplication elimination (40% reduction potential)
  - Service layer extraction for improved testability
  - Database indexing opportunities (30-50% query speed improvement)
- All refactoring recommendations are optional and prioritized for future implementation
- System remains stable and fully functional with zero implementation issues

**Previous: October-November 2025 - Dual-Reminder System Strategic Reversal (Phase 4)**
- Reversed reminder logic: "Last Chance" reminder now sends X days BEFORE campaign end (not after invitation)
- Automatic Midpoint Reminder: Sent halfway through campaign duration
- PostgreSQL interval arithmetic for efficient date calculations
- Default changed from 7 to 10 days before campaign end (configurable: 7, 10, or 14 days)
- Frontend validation updated with intelligent spacing checks and edge-case warnings
- Zero migration risk (no active campaigns, only drafts exist)
- Architect review: PASSED with zero implementation issues

# User Preferences
Preferred communication style: Simple, everyday language.
User interface tone: Thought leadership and research-oriented language, avoiding sales-oriented messaging.
Project customization: Rivvalue Inc. branding and conversational AI surveys for enhanced user experience.
Target market: French-speaking businesses and organizations.

# System Architecture
The system is a Flask web application with a multi-tiered architecture, using Jinja2, Bootstrap 5, custom CSS, vanilla JavaScript, and Chart.js for the frontend. The backend is Flask with SQLAlchemy ORM, designed for scalability. AI integration primarily uses the OpenAI API for NLP, sentiment analysis, and conversational surveys (VOÏA), supplemented by TextBlob.

**UI/UX**: Features multi-step survey forms, interactive dashboards, chat-style interfaces for conversational surveys, and Rivvalue Inc. branding with a professional blue color scheme. Includes modern sidebar navigation, mobile responsiveness, accessibility features (ARIA, WCAG 2.1 AA), and a comprehensive breadcrumb system. Redesigned admin pages and the Survey Response page follow V2 patterns with bold red gradient headers and VOÏA brand color tokens. Demo platform pages are V2 compliant with zero inline styles and standardized patterns.

**Technical Implementations**:
-   **Survey Collection**: Multi-step forms with dynamic follow-up questions and real-time validation.
-   **AI Analysis Engine**: Sentiment analysis, key theme extraction, churn risk assessment, growth opportunity identification, and NPS-based growth factor analysis.
-   **Conversational Surveys (VOÏA)**: AI-powered (GPT-4o) natural language interface with advanced personalization and a hybrid prompt architecture for dynamic question generation and structured data extraction. Features role-based persona templates (5-tier system) that adapt AI tone and focus based on participant seniority, intelligent role mapping, anonymization guards, and multilingual support. Enhanced AI prompt personalization with a structured context block for full business metadata. Persistent conversation state storage ensures data recovery.
-   **Data Management**: Centralized data aggregation, NPS calculation, time-based filtering, optimized database queries, and separate tracking for Professional Services and Support Quality. Automated nightly reconciliation system for data consistency.
-   **Authentication**: JWT token-based with email validation, admin roles, server-side token generation, and automatic invalidation.
-   **Performance & Scalability**: PostgreSQL-backed persistent task queue, database indexing, connection pooling, asynchronous background tasks for AI, IP-based rate limiting, optimized dashboard queries, admin-configurable response caching, and frontend optimizations. Scaled for 100 concurrent users with Gunicorn and expanded SQLAlchemy connection pool. Environment-aware static file caching.
-   **Audit Trail System**: Comprehensive audit logging with accurate timestamp preservation, integrated with a PostgreSQL task queue.
-   **Security**: Token-based authentication, duplicate response prevention, enhanced rate limiting, robust input validation, CSRF/XSS protection, and Sentry integration.
-   **Branding**: "VOÏA - Voice Of Client" with "AI Powered Client Insights" subtitle, specific tagline, multi-tenant logo system, and selective trial branding.
-   **Multi-Tenant Architecture**: Supports Business Accounts, Campaigns, and Participants with tenant isolation, dual authentication, and a token system for survey access. Participant entities support optional segmentation attributes.
-   **Participant Management Enhancements**: Individual editing with conditional email locking, deletion protection, tenure tracking, audit logging, and bulk edit functionality. Advanced multi-value filtering. Optimized participant list page load times. Implemented atomic row-level locking for bulk operations to prevent race conditions.
-   **Manual Commercial Value Tracking**: Company-level commercial value system for account intelligence, stored on the Participant model, with CSV upload validation and automatic synchronization.
-   **Email Delivery System**: Production-ready dual-mode email infrastructure (VOÏA-managed AWS SES or client-managed SMTP). Features encrypted password storage, connection testing, VOÏA-branded templates, background task processing, delivery tracking, configurable email content with 3-tier fallback, and automated reminder system. Includes comprehensive UI for configuration and multi-tenant isolation.
-   **Dual-Reminder System (Strategic Reversal)**: Enhanced automated reminder strategy with two-stage engagement: (1) Midpoint Reminder sent automatically halfway through campaign duration (e.g., Day 45 in a 90-day campaign), and (2) Last Chance Reminder sent X days BEFORE campaign closes (configurable: 7, 10, or 14 days; default 10). This reversal from the previous "days after invitation" model creates better spacing and urgency: midpoint catches participants who haven't started yet, while last-chance creates deadline pressure. Backend uses PostgreSQL interval arithmetic for efficient SQL-based date calculations. Frontend JavaScript displays both reminder dates with intelligent spacing validation and edge-case warnings.
-   **Campaign Lifecycle Management**: Automated status transitions, multi-tenant scheduling, automatic KPI snapshot generation, and background task management with audit logging.
-   **Hybrid Survey Customization**: Campaign-specific survey personalization with business account defaults.
-   **License Management System**: Enterprise-ready license management with usage tracking and enforcement.
-   **Business Account User Management**: Multi-tenant user management with professional UI, license-aware counters, and comprehensive user workflows.
-   **Onboarding System with Conditional Access**: Progressive, non-blocking onboarding for Core/Plus license holders with persistent warning banners and an onboarding progress dashboard.
-   **Feature Flag System**: Production-ready infrastructure for UI version toggling.
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