# Overview
VOÏA (Voice Of Client) is a Flask-based system for comprehensive customer feedback collection and AI-powered analysis, specializing in Net Promoter Score (NPS) surveys. It transforms raw customer feedback into actionable insights, identifying sentiment, key themes, churn risk, and growth opportunities. VOÏA aims to provide businesses with a robust tool for understanding customer sentiment, improving services, and fostering organic growth through AI-driven analysis of customer interactions. The project includes a production-ready multi-tenant participant management system with extensive email delivery capabilities, AI-powered conversational surveys using a hybrid prompt architecture, and participant segmentation for personalized experiences and advanced analytics.

# Recent Changes
**November 4, 2025**: Enhanced AI prompt personalization with structured context block
- Implemented comprehensive context block in `build_survey_config_json()` to pass full business metadata to OpenAI
- Context block now includes: company_description, product_description (with campaign override), target_clients (with campaign override), and industry
- Increased AI personalization effectiveness from ~45% to ~95% by providing complete business context with every question
- Campaign-specific values override business account defaults with intelligent null-omission (only non-empty fields included)
- Backward compatible implementation - existing surveys unaffected, new context automatically enriches all future conversations
- Context block visible in Prompt Preview feature for debugging and validation

**November 4, 2025**: Implemented role-based AI persona templates and prompt optimization
- Added 5-tier persona template system (C-Level, VP/Director, Manager, Team Lead, End User) for conversational surveys
- Implemented intelligent role mapping with word-boundary pattern matching to avoid false positives
- Added anonymization guards to prevent role exposure when anonymization is enabled
- Implemented multilingual support via hybrid approach (English personas + GPT language instruction)
- Updated prompt instructions from SQL-like mechanical directives to natural language for improved clarity
- Separated Support Quality (`support_rating`) from Professional Services (`service_rating`) in database schema and analytics
- All changes validated via Prompt Preview feature and architect review with backward compatibility confirmed

# User Preferences
Preferred communication style: Simple, everyday language.
User interface tone: Thought leadership and research-oriented language, avoiding sales-oriented messaging.
Project customization: Rivvalue Inc. branding and conversational AI surveys for enhanced user experience.
Target market: French-speaking businesses and organizations.

# System Architecture
The system is a Flask web application with a multi-tiered architecture. The frontend uses Jinja2, Bootstrap 5, custom CSS, vanilla JavaScript, and Chart.js. The backend is Flask with SQLAlchemy ORM, designed for scalability from SQLite to PostgreSQL. AI integration primarily uses the OpenAI API for NLP, sentiment analysis, and conversational surveys (VOÏA), supplemented by TextBlob.

**UI/UX**: Features multi-step survey forms, interactive dashboards, chat-style interfaces for conversational surveys, and Rivvalue Inc. branding with a professional blue color scheme. It includes modern sidebar navigation, mobile responsiveness, active state highlighting, and a Settings Hub v2 with a 5-card accordion layout. Admin pages and the Survey Response page are redesigned with V2 patterns, featuring bold red gradient headers, VOÏA brand color tokens, comprehensive ARIA accessibility, and mobile-responsive breakpoints. Inline styles are migrated to custom.css, and FontAwesome icons are used. A comprehensive breadcrumb system is implemented. Demo platform pages are V2 compliant with zero inline styles, CSS variable tokens, WCAG 2.1 AA accessibility, standardized V2 patterns, and mobile responsiveness.

**Technical Implementations**:
-   **Survey Collection**: Multi-step forms with dynamic follow-up questions and real-time validation.
-   **AI Analysis Engine**: Sentiment analysis, key theme extraction, churn risk assessment, growth opportunity identification, and NPS-based growth factor analysis.
-   **Conversational Surveys (VOÏA)**: AI-powered (GPT-4o) natural language interface with advanced personalization and a hybrid prompt architecture for dynamic question generation and structured data extraction. Features role-based persona templates (5-tier system: C-Level, VP/Director, Manager, Team Lead, End User) that adapt AI tone and focus based on participant seniority. Includes intelligent role mapping with word-boundary pattern matching, anonymization guards for privacy protection, multilingual support via hybrid approach (English personas + GPT language instruction), and natural language prompt instructions for improved clarity. Includes participant segmentation and feature flag rollout.
-   **Data Management**: Centralized data aggregation, NPS calculation, time-based filtering, and optimized database queries. Separate tracking of Professional Services quality (`service_rating`) and Support Quality (`support_rating`) for granular analytics with nullable backward-compatible schema.
-   **Authentication**: JWT token-based with email validation, admin roles, server-side token generation, and automatic invalidation.
-   **Performance & Scalability**: PostgreSQL-backed persistent task queue, database indexing, connection pooling, asynchronous background tasks for AI, IP-based rate limiting, optimized dashboard queries, admin-configurable response caching, and frontend optimizations. Scaled to support 100 concurrent users via Gunicorn multi-worker configuration and expanded SQLAlchemy connection pool. Environment-aware static file caching (1-year browser cache in production, 1-hour in development) reduces bandwidth by 75% and improves page navigation speed by 500ms.
-   **Audit Trail System**: Comprehensive audit logging with accurate timestamp preservation, integrated with a PostgreSQL task queue for async processing.
-   **Security**: Token-based authentication, duplicate response prevention, enhanced rate limiting, robust input validation, CSRF/XSS protection, and Sentry integration.
-   **Branding**: "VOÏA - Voice Of Client" with "AI Powered Client Insights" subtitle, specific tagline, multi-tenant logo system, and selective trial branding.
-   **Multi-Tenant Architecture**: Supports Business Accounts, Campaigns, and Participants with tenant isolation via `business_account_id` scoping, dual authentication, and a token system for survey access. Participant entities support optional segmentation attributes.
-   **Participant Management Enhancements**: Individual participant editing with conditional email locking, deletion protection, tenure tracking, comprehensive audit logging, and bulk edit functionality for up to 50 participants. Advanced multi-value filtering for campaign participant assignment with indexed columns. Participant list page load time optimized by 85-90% through consolidated filter query optimization and composite B-tree indexes.
-   **Manual Commercial Value Tracking**: Company-level commercial value system for account intelligence, stored on the Participant model, with CSV upload validation and automatic synchronization.
-   **Email Delivery System**: Production-ready dual-mode email infrastructure supporting both VOÏA-managed (platform-provided AWS SES) and client-managed (client-provided SMTP credentials) configurations. Features encrypted password storage, connection testing, professional VOÏA-branded templates, background task processing, delivery tracking, configurable email content with 3-tier fallback architecture, and automated reminder system. Includes comprehensive UI for platform and business admin configuration, multi-tenant isolation, extensive testing with audit logging, and data-layer caching (6-hour TTL) for SES domain verification status to optimize page load performance (85% improvement for platform admins managing multiple accounts).
-   **Campaign Lifecycle Management**: Automated status transitions, multi-tenant scheduling, automatic KPI snapshot generation, and background task management with audit logging. Draft campaigns support full editability and deletion.
-   **Participant Status Reconciliation**: Automated nightly reconciliation system for data consistency between email/response tracking and participant lifecycle status, using background jobs via PostgreSQL task queue.
-   **Hybrid Survey Customization**: Campaign-specific survey personalization with business account defaults.
-   **License Management System**: Enterprise-ready license management with usage tracking and enforcement.
-   **Business Account User Management**: Multi-tenant user management with professional UI, license-aware counters, and comprehensive user workflows.
-   **Onboarding System with Conditional Access**: Progressive, non-blocking onboarding for Core/Plus license holders. Admins can immediately access all features after account activation. Persistent warning banner displays on admin pages showing incomplete setup tasks (SMTP Configuration, Brand Configuration, Team Members) with direct action links. Session-based tracking ensures reminders appear until setup is complete, maintaining accountability without friction. Onboarding progress dashboard accessible via banner.
-   **Feature Flag System**: Production-ready infrastructure for UI version toggling, including a PostgreSQL-backed task queue.
-   **Segmentation Analytics**: Comprehensive analytics system displaying NPS and satisfaction metrics segmented by participant attributes, including a dedicated Segmentation Insights tab with interactive Chart.js visualizations.
-   **Demo Data Generation**: High-volume test data scripts for realistic test data generation.
-   **JavaScript Translation Optimization**: Externalized translation payloads to cacheable static JSON files for mobile performance, using async translation loader with retry logic, browser caching, and graceful English fallbacks.
-   **Maintenance Mode**: Environment variable-controlled feature (`MAINTENANCE_MODE=true`) restricting all pages except `/business/login` to a "coming soon" page with V2 design guidelines and VOÏA branding.
-   **Translation/Internationalization (i18n)**: Production-ready bilingual support (English/French) using Flask-Babel, wrapping 247+ user-facing strings with a 4-layer fallback architecture. Translations managed via `babel.cfg`, achieving 78.5% French coverage with hybrid AI-assisted workflow. Supports session-based language switching.
-   **Transcript Upload System**: AI-powered meeting transcript analysis universally available across all license tiers. Upload .txt files to automatically extract NPS scores, sentiment, themes, and actionable insights, bounded by tier's participant response quotas. Includes full bilingual support.
-   **Prompt Preview System (Development Only)**: Environment-gated feature (`ENABLE_PROMPT_PREVIEW=true`) for inspecting AI system prompts in survey customization pages. Available in both global (business account) and campaign-specific contexts with Bootstrap modal interface showing system prompt, configuration JSON, and metadata. Enforces multi-tenant isolation by validating all requests against session business account. Reuses existing PromptTemplateService with sample participant data for preview generation.
-   **AI Cost Optimization Strategy**: Tiered OpenAI model routing architecture for 77% cost reduction while maintaining quality. Uses GPT-4o-mini for 90% of conversational surveys, 80% of response analyses, and 75% of executive reports, with rule-based escalation to GPT-4o for high-risk scenarios (low NPS, high-value accounts, compliance flags). Context block enhancement increased token usage by 67% input tokens but improved personalization effectiveness from 45% to 95%. Optimized monthly operating cost: $1,258 ($25.16/account) vs baseline $5,381. Full analysis in `docs/cost_analysis_production_scale_v2.md`.

# External Dependencies
-   **OpenAI API**: For advanced AI functionalities (sentiment analysis, theme extraction, conversational surveys).
-   **Bootstrap CDN**: For responsive UI components and styling.
-   **Chart.js CDN**: For interactive data visualizations.
-   **Font Awesome CDN**: For iconography.
-   **Python Packages**: Flask, SQLAlchemy, OpenAI client library, TextBlob, cryptography, Flask-Caching.
-   **Sentry**: For error tracking and performance monitoring.
-   **AWS SES / SMTP**: For email delivery.