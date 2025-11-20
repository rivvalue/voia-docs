# Overview
VOÏA (Voice Of Client) is a Flask-based system for comprehensive customer feedback collection and AI-powered analysis, specializing in Net Promoter Score (NPS) surveys. It transforms raw customer feedback into actionable insights, identifying sentiment, key themes, churn risk, and growth opportunities. VOÏA aims to provide businesses with a robust tool for understanding customer sentiment, improving services, and fostering organic growth through AI-driven analysis of customer interactions. The project includes a production-ready multi-tenant participant management system with extensive email delivery capabilities, AI-powered conversational surveys using a hybrid prompt architecture, and participant segmentation for personalized experiences and advanced analytics.

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
-   **AI Analysis Engine**: Sentiment analysis, key theme extraction, churn risk assessment, growth opportunity identification, and NPS-based growth factor analysis. Features AI-generated plain-language summaries and reasoning explanations.
-   **Conversational Surveys (VOÏA)**: AI-powered (GPT-4o) natural language interface with advanced personalization and a hybrid prompt architecture for dynamic question generation and structured data extraction. Features role-based persona templates, intelligent role mapping, anonymization guards, and multilingual support. Enhanced AI prompt personalization with a structured context block for full business metadata. Persistent conversation state storage ensures data recovery.
-   **Industry-Specific AI Prompt Verticalization (Nov 2025)**: Topic-mapped hint system that customizes conversational survey questions based on business industry context. Platform admin controls industry list (10 industries: EMS, Healthcare, Software, Financial Services, etc.) and default hint library via config file. Three-tier governance: Platform defaults → Business Account custom overrides (industry_topic_hints JSON field) → Campaign-specific industry selection. Priority cascade for effective industry: Campaign.industry → BusinessAccount.industry → "Generic" fallback. Integrated into PromptTemplateService to inject industry-specific keywords (e.g., EMS emphasizes "defects, throughput, line reliability" for Product Quality; Healthcare emphasizes "workflow reliability, data accuracy, patient safety"). Demo mode respects configured industries for testing.
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
-   **Dual-Reminder System**: Enhanced automated reminder strategy with two-stage engagement (Midpoint and Last Chance Reminders).
-   **Campaign Lifecycle Management**: Automated status transitions, multi-tenant scheduling, automatic KPI snapshot generation, and background task management with audit logging.
-   **Hybrid Survey Customization**: Campaign-specific survey personalization with business account defaults.
-   **License Management System**: Enterprise-ready license management with usage tracking and enforcement. **Security fix (Nov 2025)**: Changed license enforcement from "fail open" to "fail closed" - system now denies campaign activation when license checks fail, protecting revenue and preventing unlimited usage during system errors.
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