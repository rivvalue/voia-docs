# Overview
VOÏA (Voice Of Client) is a Flask-based system for comprehensive customer feedback collection and AI-powered analysis, specializing in Net Promoter Score (NPS) surveys. Its purpose is to convert raw customer feedback into actionable insights, identifying sentiment, key themes, churn risk, and growth opportunities. VOÏA provides businesses with a robust tool for understanding customer sentiment, improving services, and fostering organic growth through AI-driven analysis of customer interactions. The project features a production-ready multi-tenant participant management system with extensive email delivery capabilities, AI-powered conversational surveys with hybrid prompt architecture, and participant segmentation for personalized experiences and advanced analytics.

# User Preferences
Preferred communication style: Simple, everyday language.
User interface tone: Thought leadership and research-oriented language, avoiding sales-oriented messaging.
Project customization: Rivvalue Inc. branding and conversational AI surveys for enhanced user experience.
Target market: French-speaking businesses and organizations.

# System Architecture
The system is a Flask web application with a multi-tiered architecture. The frontend uses Jinja2, Bootstrap 5, custom CSS, vanilla JavaScript, and Chart.js. The backend is Flask with SQLAlchemy ORM, designed for scalability from SQLite to PostgreSQL. AI integration, primarily via OpenAI API, handles natural language processing, sentiment analysis, and conversational surveys (VOÏA), supplemented by TextBlob.

**UI/UX**: Multi-step survey forms, interactive dashboards, chat-style interfaces for conversational surveys, and Rivvalue Inc. branding with a professional blue color scheme. It features modern sidebar navigation, mobile responsiveness, and active state highlighting. The Settings Hub v2 uses a 5-card accordion layout for account, user, data, system, and platform administration settings. Admin pages and the Survey Response page are redesigned with Settings Hub v2 patterns, featuring bold red gradient headers, VOÏA brand color tokens, comprehensive ARIA accessibility attributes, and mobile-responsive breakpoints. All inline styles are migrated to custom.css, and emoji icons are replaced with FontAwesome. A comprehensive breadcrumb system is implemented across business pages. Demo platform pages are fully V2 compliant with zero inline styles, CSS variable tokens, WCAG 2.1 AA accessibility, standardized V2 card/button/typography patterns, JavaScript refactored to use CSS classes, and mobile-responsive breakpoints.

**Technical Implementations**:
-   **Survey Collection**: Multi-step forms with dynamic follow-up questions and real-time validation.
-   **AI Analysis Engine**: Sentiment analysis, key theme extraction, churn risk assessment, growth opportunity identification, and NPS-based growth factor analysis.
-   **Conversational Surveys (VOÏA)**: AI-powered (GPT-4o) natural language interface with advanced personalization, using a hybrid prompt architecture for dynamic question generation and structured data extraction. Includes participant segmentation and feature flag rollout.
-   **Data Management**: Centralized data aggregation, NPS calculation, time-based filtering, and optimized database queries.
-   **Authentication**: JWT token-based with email validation, admin roles, server-side token generation, and automatic invalidation.
-   **Performance & Scalability**: PostgreSQL-backed persistent task queue, database indexing, connection pooling, asynchronous background tasks for AI, IP-based rate limiting, optimized dashboard queries, admin-configurable response caching, and frontend optimizations. Scaled to support 100 concurrent users via Gunicorn multi-worker configuration and expanded SQLAlchemy connection pool.
-   **Audit Trail System**: Comprehensive audit logging with accurate timestamp preservation, integrated with a PostgreSQL task queue for async processing of all system audit points.
-   **Security**: Token-based authentication, duplicate response prevention, enhanced rate limiting, robust input validation, CSRF/XSS protection, and Sentry integration.
-   **Branding**: "VOÏA - Voice Of Client" with "AI Powered Client Insights" subtitle, specific tagline, multi-tenant logo system, and selective trial branding.
-   **Multi-Tenant Architecture**: Business Accounts, Campaigns, and Participants with tenant isolation via `business_account_id` scoping, dual authentication, and a token system for survey access, including a lightweight scheduler. Participant entities support optional segmentation attributes for personalized survey experiences and advanced analytics.
-   **Participant Management Enhancements**: Individual participant editing with conditional email locking, deletion protection for participants with survey responses, tenure tracking, and comprehensive audit logging. Bulk edit functionality allows updating up to 50 participants simultaneously for various attributes. Advanced multi-value filtering for campaign participant assignment with indexed columns.
-   **Manual Commercial Value Tracking**: Company-level commercial value system for accurate account intelligence, stored on the Participant model, with CSV upload validation and automatic synchronization.
-   **Email Delivery System**: Multi-provider email infrastructure (AWS SES, SMTP) with business accounts choosing providers, encrypted password storage, connection testing, professional VOÏA-branded templates, background task processing, delivery tracking, and configurable email content with a 3-tier fallback architecture. Includes an automated reminder system with campaign-level configuration.
-   **Campaign Lifecycle Management**: Automated status transitions, multi-tenant scheduling, automatic KPI snapshot generation, and background task management with comprehensive audit logging. Draft campaigns support full editability and deletion with cascade removal, protected by status validation and multi-tenant security.
-   **Participant Status Reconciliation**: Automated nightly reconciliation system to ensure data consistency between email/response tracking and participant lifecycle status, with background jobs running via PostgreSQL task queue scheduler.
-   **Hybrid Survey Customization**: Campaign-specific survey personalization with business account defaults.
-   **License Management System**: Enterprise-ready license management with usage tracking and enforcement.
-   **Business Account User Management**: Multi-tenant user management with professional UI, license-aware counters, and comprehensive user workflows.
-   **Mandatory Onboarding System**: Extensible guided setup workflow for business account administrators.
-   **Feature Flag System**: Production-ready infrastructure for UI version toggling, including a PostgreSQL-backed task queue.
-   **Segmentation Analytics**: Comprehensive analytics system displaying NPS and satisfaction metrics segmented by participant attributes, including a dedicated Segmentation Insights tab in Campaign Insights with interactive Chart.js visualizations.
-   **Demo Data Generation**: High-volume test data scripts capable of generating realistic test data for development and staging.
-   **JavaScript Translation Optimization**: Externalized translation payloads from inline JavaScript objects to cacheable static JSON files to eliminate mobile performance degradation. Uses async translation loader with retry logic, browser caching, and graceful English fallbacks.

# External Dependencies
-   **OpenAI API**: For advanced AI functionalities including sentiment analysis, theme extraction, and conversational surveys.
-   **Bootstrap CDN**: For responsive UI components and styling.
-   **Chart.js CDN**: For interactive data visualizations.
-   **Font Awesome CDN**: For iconography.
-   **Python Packages**: Flask, SQLAlchemy, OpenAI client library, TextBlob, cryptography, Flask-Caching.
-   **Sentry**: For error tracking and performance monitoring.
-   **AWS SES / SMTP**: For email delivery.