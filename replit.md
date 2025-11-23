# Overview
VOÏA (Voice Of Client) is a Flask-based system for collecting and analyzing customer feedback, with a focus on Net Promoter Score (NPS) surveys. It uses AI to convert feedback into actionable insights, identifying sentiment, key themes, churn risks, and growth opportunities. VOÏA aims to help businesses understand customer sentiment, improve services, and achieve organic growth through AI-driven analysis of customer interactions. The project features a multi-tenant participant management system, extensive email delivery, AI-powered conversational surveys using a hybrid prompt architecture, and participant segmentation for personalized experiences and advanced analytics.

# User Preferences
Preferred communication style: Simple, everyday language.
User interface tone: Thought leadership and research-oriented language, avoiding sales-oriented messaging.
Project customization: Rivvalue Inc. branding and conversational AI surveys for enhanced user experience.
Target market: French-speaking businesses and organizations.

# System Architecture
The system is a Flask web application built with a multi-tiered architecture. The frontend uses Jinja2, Bootstrap 5, custom CSS, vanilla JavaScript, and Chart.js. The backend is Flask with SQLAlchemy ORM, designed for scalability. AI integration leverages the OpenAI API for NLP, sentiment analysis, and conversational surveys (VOÏA), supplemented by TextBlob.

**UI/UX**: Features multi-step survey forms, interactive dashboards, chat-style interfaces for conversational surveys, and Rivvalue Inc. branding with a professional blue color scheme. Includes modern sidebar navigation, mobile responsiveness, accessibility, and a comprehensive breadcrumb system. Admin pages and Survey Response pages follow V2 patterns with specific headers and brand color tokens.

**Technical Implementations**:
-   **Survey Collection**: Multi-step forms with dynamic follow-up questions and real-time validation.
-   **AI Analysis Engine**: Conducts sentiment analysis, key theme extraction, churn risk assessment, growth opportunity identification, and NPS-based growth factor analysis, providing AI-generated summaries and reasoning.
-   **Conversational Surveys (VOÏA)**: AI-powered (GPT-4o) natural language interface with advanced personalization and a hybrid prompt architecture for dynamic question generation and structured data extraction. Features role-based persona templates, intelligent role mapping, anonymization guards, multilingual support, and a structured context block for business metadata. Persistent conversation state storage ensures data recovery. The system uses a universal prompt architecture with parameterized components and role-based goal filtering. It ensures language consistency throughout conversations and logs AI prompts for debugging. Includes industry-specific AI prompt verticalization for customized conversational questions based on business context. **V2 Deterministic Controller** (Nov 2025): Feature-flag controlled deterministic survey flow that eliminates early-stop bugs through pure backend control. Backend controls completion/topic selection decisions while LLM handles only data extraction and question generation. Implements must-ask vs optional topic priority with per-topic follow-up limits. State persistence includes controller_version='v2_deterministic' for V1/V2 routing compatibility. Enabled via DETERMINISTIC_SURVEY_FLOW environment variable. **Critical Fixes (Nov 23, 2025)**: Topic normalization prevents meta-topic circular questions (e.g., "NPS Score" → "NPS"), campaign object passing eliminates session detachment issues for product_description loading, AI language enforcement ensures multilingual consistency throughout conversations, field name mapping (nps_reasoning → recommendation_reason) for database compatibility, and required fields (company_name, respondent_name) now stored in extracted_data at conversation start to prevent database constraint violations during finalization.
-   **Data Management**: Centralized data aggregation, NPS calculation, time-based filtering, optimized database queries, and separate tracking for Professional Services and Support Quality. Includes an automated nightly reconciliation system.
-   **Authentication**: JWT token-based with email validation, admin roles, server-side token generation, and automatic invalidation.
-   **Performance & Scalability**: Utilizes a PostgreSQL-backed persistent task queue, database indexing, connection pooling, asynchronous background tasks for AI, IP-based rate limiting, optimized dashboard queries, admin-configurable response caching with multi-tenant isolation, and frontend optimizations. Scaled for 100 concurrent users with Gunicorn and expanded SQLAlchemy connection pool. Cache security audit (Nov 2025) confirmed all tenant-specific caches properly include business_account_id for isolation (dashboard data, email delivery config).
-   **Audit Trail System**: Comprehensive audit logging with accurate timestamp preservation.
-   **Security**: Token-based authentication, duplicate response prevention, enhanced rate limiting, robust input validation, CSRF/XSS protection, and Sentry integration.
-   **Branding**: "VOÏA - Voice Of Client" with "AI Powered Client Insights" subtitle, specific tagline, multi-tenant logo system, and selective trial branding.
-   **Multi-Tenant Architecture**: Supports Business Accounts, Campaigns, and Participants with tenant isolation, dual authentication, and a token system for survey access. Participant entities support optional segmentation attributes.
-   **Participant Management Enhancements**: Individual editing with conditional email locking, deletion protection, tenure tracking, audit logging, and bulk edit functionality. Includes advanced multi-value filtering and optimized list page load times. Implements atomic row-level locking for bulk operations.
-   **Manual Commercial Value Tracking**: Company-level commercial value system for account intelligence, stored on the Participant model, with CSV upload validation and automatic synchronization.
-   **Email Delivery System**: Production-ready dual-mode email infrastructure (VOÏA-managed AWS SES or client-managed SMTP). Features encrypted password storage, connection testing, VOÏA-branded templates, background task processing, delivery tracking, configurable email content, and an automated reminder system. Includes UI for configuration and multi-tenant isolation.
-   **Dual-Reminder System**: Enhanced automated reminder strategy with two-stage engagement (Midpoint and Last Chance Reminders).
-   **Campaign Lifecycle Management**: Automated status transitions, multi-tenant scheduling, automatic KPI snapshot generation, and background task management with audit logging.
-   **Hybrid Survey Customization**: Campaign-specific survey personalization with business account defaults.
-   **License Management System**: Enterprise-ready license management with usage tracking and enforcement. License enforcement is "fail closed" to prevent unauthorized usage.
-   **Business Account User Management**: Multi-tenant user management with a professional UI, license-aware counters, and comprehensive user workflows.
-   **Onboarding System with Conditional Access**: Progressive, non-blocking onboarding for Core/Plus license holders with persistent warning banners and an onboarding progress dashboard.
-   **Feature Flag System**: Production-ready infrastructure for UI version toggling and frontend refactoring rollout, including an environment variable-based instant rollback mechanism (`USE_REFACTORED_FRONTEND`).
-   **Segmentation Analytics**: Comprehensive analytics system displaying NPS and satisfaction metrics segmented by participant attributes, including interactive Chart.js visualizations.
-   **Demo Data Generation**: High-volume test data scripts for realistic test data generation.
-   **JavaScript Translation Optimization**: Externalized translation payloads to cacheable static JSON files.
-   **Maintenance Mode**: Environment variable-controlled feature restricting access to a "coming soon" page.
-   **Translation/Internationalization (i18n)**: Production-ready bilingual support (English/French) using Flask-Babel, with a 4-layer fallback architecture and session-based language switching.
-   **Transcript Upload System**: AI-powered meeting transcript analysis universally available across all license tiers.
-   **Prompt Preview System (Development Only)**: Environment-gated feature for inspecting AI system prompts in survey customization pages.
-   **AI Cost Optimization Strategy**: Tiered OpenAI model routing architecture for cost reduction, using GPT-4o-mini for most tasks with rule-based escalation to GPT-4o for high-risk scenarios.
-   **Notification System**: Real-time in-app notification center with professional UI for executive report generation and bulk operations. Features rich metadata for deep linking to reports and resources.

# External Dependencies
-   **OpenAI API**: For advanced AI functionalities (sentiment analysis, theme extraction, conversational surveys).
-   **Bootstrap CDN**: For responsive UI components and styling.
-   **Chart.js CDN**: For interactive data visualizations.
-   **Font Awesome CDN**: For iconography.
-   **Python Packages**: Flask, SQLAlchemy, OpenAI client library, TextBlob, cryptography, Flask-Caching.
-   **Sentry**: For error tracking and performance monitoring.
-   **AWS SES / SMTP**: For email delivery.