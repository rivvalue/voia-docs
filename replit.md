# Overview
VOÏA (Voice Of Client) is a Flask-based system designed for collecting and analyzing customer feedback, primarily through Net Promoter Score (NPS) surveys. It leverages AI to transform raw feedback into actionable business insights, including sentiment analysis, key theme identification, churn risk assessment, and growth opportunity discovery. The platform aims to empower businesses, particularly French-speaking organizations, to enhance customer understanding, improve services, and foster organic growth through AI-driven analysis of customer interactions. Key features include a multi-tenant participant management system, robust email delivery capabilities, AI-powered conversational surveys with a hybrid prompt architecture, and advanced participant segmentation for personalized experiences and analytics.

# User Preferences
Preferred communication style: Simple, everyday language.
User interface tone: Thought leadership and research-oriented language, avoiding sales-oriented messaging.
Project customization: Rivvalue Inc. branding and conversational AI surveys for enhanced user experience.
Target market: French-speaking businesses and organizations.

# System Architecture
The system is a multi-tiered Flask web application. The frontend utilizes Jinja2, Bootstrap 5, custom CSS, vanilla JavaScript, and Chart.js for a responsive and interactive user experience. The backend is built with Flask and SQLAlchemy ORM, emphasizing scalability and maintainability. AI functionalities are primarily powered by the OpenAI API for NLP, sentiment analysis, and conversational survey capabilities (VOÏA), augmented by TextBlob.

**UI/UX**: The interface features multi-step survey forms, interactive dashboards, and chat-style conversational surveys. It adheres to Rivvalue Inc. branding guidelines, employing a professional blue color scheme, modern sidebar navigation, and comprehensive accessibility features. Admin and Survey Response pages follow V2 design patterns with specific headers and brand color tokens.

**Technical Implementations**:
-   **Survey Collection**: Implements dynamic, multi-step survey forms with real-time validation and conditional follow-up questions.
-   **AI Analysis Engine**: Provides sentiment analysis, key theme extraction, churn risk identification, growth opportunity assessment, and NPS-based growth factor analysis, delivering AI-generated summaries and reasoning.
-   **Conversational Surveys (VOÏA)**: An AI-powered (GPT-4o) natural language interface that uses a hybrid prompt architecture for dynamic question generation and structured data extraction. Features include role-based persona templates, intelligent role mapping, anonymization guards, multilingual support, and structured context blocks. A V2 Deterministic Controller ensures a robust, backend-controlled survey flow with state persistence, topic normalization, AI language enforcement, and revised data extraction prompts. It also includes advanced role-based questioning adaptation with persona-aware follow-up depth, prompt guidance injection, and deflection detection. Completion-time summary extraction populates topic-specific feedback columns using GPT-4o-mini. Template-based topic transitions (USE_TOPIC_TRANSITIONS flag) provide natural bilingual (FR/EN) acknowledgments when moving between survey topics. **4-Tier Role Prompt Override System (Dec 2025)**: Configurable persona-specific questioning guidance with topic-aware resolution. Resolution hierarchy: Campaign → Business Account → Platform (PlatformSurveySettings) → ROLE_METADATA defaults. Supports topic-specific overrides to prevent role guidance from being inappropriately applied to unrelated topics (e.g., Manager guidance applied only to relevant topics, not Pricing).
-   **Data Management**: Centralized data aggregation, NPS calculation, time-based filtering, optimized database queries, and separate tracking for specific service quality metrics. An automated nightly reconciliation system is in place.
-   **Authentication**: JWT token-based system with email validation, admin roles, server-side token generation, and automatic invalidation. Includes a robust, multi-phase fix for authentication consistency.
-   **Performance & Scalability**: Utilizes a PostgreSQL-backed persistent task queue, database indexing, connection pooling, asynchronous background tasks for AI processing, IP-based rate limiting, optimized dashboard queries, and admin-configurable response caching with multi-tenant isolation.
-   **Audit Trail System**: Comprehensive logging of system activities with accurate timestamp preservation.
-   **Security**: Token-based authentication, duplicate response prevention, enhanced rate limiting, robust input validation, CSRF/XSS protection, and Sentry integration.
-   **Branding**: "VOÏA - Voice Of Client" with "AI Powered Client Insights" subtitle, a specific tagline, multi-tenant logo system, and selective trial branding.
-   **Multi-Tenant Architecture**: Supports Business Accounts, Campaigns, and Participants with strict tenant isolation, dual authentication, and a token system for survey access.
-   **Participant Management**: Features individual and bulk editing, deletion protection, tenure tracking, audit logging, and advanced multi-value filtering.
-   **Manual Commercial Value Tracking**: Company-level commercial value system stored on the Participant model, with CSV upload validation and synchronization.
-   **Email Delivery System**: Production-ready dual-mode infrastructure (AWS SES or client-managed SMTP) with encrypted password storage, connection testing, branded templates, background task processing, delivery tracking, and an automated dual-reminder system.
-   **Campaign Lifecycle Management**: Automated status transitions, multi-tenant scheduling, KPI snapshot generation, and background task management with audit logging.
-   **Concurrent Campaigns System**: Platform admin-controlled support for parallel campaigns with a three-layer enforcement architecture (PostgreSQL trigger, LicenseService, SELECT FOR UPDATE).
-   **Hybrid Survey Customization**: Campaign-specific survey personalization layered over business account defaults.
-   **License Management System**: Enterprise-ready license management with usage tracking and "fail closed" enforcement.
-   **Business Account User Management**: Multi-tenant user management with a professional UI and comprehensive workflows.
-   **Onboarding System**: Progressive, non-blocking onboarding for licensed users with persistent warning banners and progress dashboards.
-   **Feature Flag System**: Production-ready infrastructure for UI version toggling and phased feature rollouts.
-   **Segmentation Analytics**: Comprehensive analytics system with interactive Chart.js visualizations, displaying NPS and satisfaction metrics segmented by participant attributes.
-   **Translation/Internationalization (i18n)**: Production-ready bilingual support (English/French) using Flask-Babel, with a 4-layer fallback architecture.
-   **Transcript Upload System**: AI-powered meeting transcript analysis universally available across all license tiers.
-   **AI Cost Optimization Strategy**: Tiered OpenAI model routing using GPT-4o-mini for most tasks, escalating to GPT-4o for high-risk scenarios.
-   **LLM Gateway Abstraction Layer (Jan 2026)**: Production-ready multi-provider AI architecture enabling Claude/Anthropic alongside OpenAI. Features include: provider-agnostic LLMRequest/LLMResponse dataclasses, 3-tier configuration hierarchy (environment → business account → campaign), OpenAI adapter with full chat/streaming support, Anthropic adapter placeholder, feature flags (LLM_GATEWAY_ENABLED, CLAUDE_ENABLED), per-worker gateway caching with retry-on-transient-failure logic, and structured grep-able logging (LLM_CALL, LLM_GATEWAY_ROUTE, LLM_GATEWAY_STREAM). Maintains 100% backward compatibility with direct OpenAI usage. Tested with 22 pytest tests covering feature flags, routing, thread safety, and backward compatibility.
-   **Notification System**: Real-time in-app notification center with a professional UI for executive reporting and bulk operations.
-   **Unified Async Export System**: Campaign export infrastructure migrated to a unified BulkOperationJob framework, providing asynchronous processing, progress tracking, multi-tenant security, and temporary file retention with automated cleanup.

# External Dependencies
-   **OpenAI API**: For advanced AI functionalities (NLP, sentiment analysis, conversational surveys).
-   **Bootstrap CDN**: For responsive UI components and styling.
-   **Chart.js CDN**: For interactive data visualizations.
-   **Font Awesome CDN**: For iconography.
-   **Python Packages**: Flask, SQLAlchemy, OpenAI client library, TextBlob, cryptography, Flask-Caching.
-   **Sentry**: For error tracking and performance monitoring.
-   **AWS SES / SMTP**: For email delivery infrastructure.