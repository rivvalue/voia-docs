# Overview
The Voice of Client (VOÏA) is a Flask-based system for comprehensive customer feedback collection and AI-powered analysis, specializing in Net Promoter Score (NPS) surveys. Its purpose is to convert raw customer feedback into actionable insights, identifying sentiment, key themes, churn risk, and growth opportunities. VOÏA aims to provide businesses, particularly Rivvalue Inc., with a robust tool for understanding customer sentiment, improving services, and fostering organic growth through AI-driven analysis of customer interactions. The project features a production-ready multi-tenant participant management system with extensive email delivery capabilities and AI-powered survey functionalities.

# Recent Changes
**October 10, 2025 - Multi-Tenant Branding & Mobile UX Enhancement**
-   **Multi-Tenant Logo System**: Business account logos display in v2 UI sidebar header (80px height, 220px width max) for authenticated users; Removed duplicate Rivvalue logo/title from top banner for cleaner UI.
-   **Selective Trial Branding**: Archelo demo logo now appears ONLY on trial pages (demo_intro, dashboard) via endpoint-based context filtering, keeping Home page clean and brand-neutral for marketing.
-   **User Display Enhancement**: Fixed navbar dropdown to show user's actual name instead of company name via session['business_user_name'] storage.
-   **Mobile Navigation Fix**: User dropdown now always visible outside collapsible menu on mobile, preventing sidebar overlay conflicts with z-index hierarchy (dropdown: 10003 > sidebar: 10002 > navbar: 10000).
-   **Context Processor Logic**: Intelligent branding_context injection based on authentication state and route endpoint (trial_pages: ['demo_intro', 'dashboard']).
-   **Testing**: Architect-approved with verified multi-tenant isolation, selective logo display, mobile UX improvements, and no functional regressions.

# User Preferences
Preferred communication style: Simple, everyday language.
User interface tone: Thought leadership and research-oriented language, avoiding sales-oriented messaging.
Project customization: Rivvalue Inc. branding and conversational AI surveys for enhanced user experience.

# System Architecture
The system is a Flask web application with a multi-tiered architecture. The frontend uses Jinja2, Bootstrap 5 (dark theme), custom CSS, vanilla JavaScript, and Chart.js. The backend is Flask with SQLAlchemy ORM, designed for scalability from SQLite to PostgreSQL. AI integration, primarily via OpenAI API, handles natural language processing, sentiment analysis, and conversational surveys (VOÏA), supplemented by TextBlob.

Key architectural decisions and features:
-   **UI/UX**: Multi-step survey forms, interactive dashboards, chat-style interfaces for conversational surveys, and Rivvalue Inc. branding with a professional blue color scheme. Modern sidebar navigation with dark gradient theme and VOÏA red accents, mobile responsiveness, and active state highlighting. The Settings Hub features a 4-card layout (Account Settings, User Management, Data Management, System Settings) with reusable components.
-   **Technical Implementations**:
    -   **Survey Collection**: Multi-step forms with dynamic follow-up questions and real-time validation.
    -   **AI Analysis Engine**: Sentiment analysis, key theme extraction, churn risk assessment, growth opportunity identification, and NPS-based growth factor analysis.
    -   **Conversational Surveys**: AI-powered (GPT-4o) natural language interface, dynamic question generation, real-time processing, and structured data extraction.
    -   **Data Management**: Centralized data aggregation, NPS calculation, time-based filtering, and optimized database queries.
    -   **Authentication**: JWT token-based with email validation, admin roles, server-side token generation, and automatic invalidation post-survey.
    -   **Performance**: PostgreSQL migration, database indexing, connection pooling, asynchronous background tasks for AI, IP-based rate limiting, optimized dashboard queries, and admin-configurable response caching.
-   **Security**: Token-based authentication, duplicate response prevention, enhanced rate limiting, and robust input validation.
-   **Branding**: "VOÏA - Voice Of Client" with "AI Powered Client Insights" subtitle and a specific tagline.
-   **Multi-Tenant Architecture**: Business Accounts, Campaigns, and Participants with tenant isolation via `business_account_id` scoping, dual authentication, and a token system for survey access. Includes a lightweight scheduler for campaign lifecycle automation.
-   **Email Delivery System**: Custom SMTP configuration per business account with encrypted password storage, connection testing, professional VOÏA-branded templates, background task processing, and delivery tracking.
-   **Campaign Lifecycle Management**: Automated status transitions, multi-tenant scheduling, automatic KPI snapshot generation, and background task management for email retries.
-   **Hybrid Survey Customization**: Campaign-specific survey personalization with business account defaults for tailored AI conversations while maintaining brand identity.
-   **License Management System**: Enterprise-ready license management with usage tracking and enforcement, including anniversary-based calculation, and limits on campaigns, users, and participants.
-   **Business Account User Management**: Multi-tenant user management with a professional UI, license-aware counters, user creation workflows with validation, email verification, editing, role management, status controls, and admin-triggered password resets.
-   **Mandatory Onboarding System**: Extensible guided setup workflow for business account administrators with JSON-based progress tracking, license-conditional enforcement, and configurable validation system.
-   **Performance Optimization System**: Query optimization consolidating dashboard data retrieval, Flask-Caching integration with configurable settings, strategic database indexing, and an automatic fallback strategy for queries. Multi-tenant cache isolation.
-   **Feature Flag System**: Production-ready infrastructure for UI version toggling with environment variable control, rollout percentage, and user toggling.

# External Dependencies
-   **OpenAI API**: For advanced AI functionalities including sentiment analysis, theme extraction, and conversational surveys.
-   **Bootstrap CDN**: For responsive UI components and styling.
-   **Chart.js CDN**: For interactive data visualizations.
-   **Font Awesome CDN**: For iconography.
-   **Python Packages**: Flask, SQLAlchemy, OpenAI client library, TextBlob, cryptography, Flask-Caching.