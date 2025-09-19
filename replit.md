# Overview
The Voice of Client (VOÏA) is a Flask-based system designed for comprehensive customer feedback collection and AI-powered analysis, specializing in Net Promoter Score (NPS) surveys. Its core purpose is to convert raw customer feedback into actionable insights, identifying sentiment, key themes, churn risk, and growth opportunities. VOÏA aims to provide businesses, particularly Rivvalue Inc., with a robust tool for understanding customer sentiment, improving services, and fostering organic growth through AI-driven analysis of customer interactions. The project features a production-ready multi-tenant participant management system with extensive email delivery capabilities and AI-powered survey functionalities.

# User Preferences
Preferred communication style: Simple, everyday language.
User interface tone: Thought leadership and research-oriented language, avoiding sales-oriented messaging.
Project customization: Rivvalue Inc. branding and conversational AI surveys for enhanced user experience.

# System Architecture
The system is a Flask web application built on a multi-tiered architecture. The frontend leverages Jinja2 templates, Bootstrap 5 (dark theme), custom CSS, vanilla JavaScript, and Chart.js for data visualization. The backend uses Flask with SQLAlchemy ORM, designed for scalability from SQLite to PostgreSQL. AI integration is central, primarily utilizing the OpenAI API for natural language processing, sentiment analysis, and conversational survey capabilities (VOÏA), supplemented by TextBlob for additional text analysis.

Key architectural decisions and features include:
-   **UI/UX**: Multi-step survey forms, interactive dashboards, chat-style interfaces for conversational surveys. Branding incorporates the Rivvalue Inc. logo, a professional blue color scheme, and specific taglines.
-   **Technical Implementations**:
    -   **Survey Collection**: Multi-step forms, dynamic follow-up questions, real-time validation.
    -   **AI Analysis Engine**: Sentiment analysis, key theme extraction, churn risk assessment, and growth opportunity identification, including NPS-based growth factor analysis.
    -   **Conversational Surveys**: AI-powered (GPT-4o) natural language interface, dynamic question generation, real-time processing, structured data extraction.
    -   **Data Management**: Centralized data aggregation, NPS calculation, time-based filtering, database query optimization.
    -   **Authentication**: JWT token-based authentication with email validation and admin roles, server-side token generation, and automatic token invalidation after survey completion.
    -   **Performance**: PostgreSQL migration, database indexing, connection pooling, asynchronous background tasks for AI analysis, and IP-based rate limiting.
-   **Security**: Token-based authentication, duplicate response prevention, enhanced rate limiting, and robust input validation.
-   **Branding**: "VOÏA - Voice Of Client" branding with "AI Powered Client Insights" subtitle and a specific tagline.
-   **Multi-Tenant Architecture**: Implementation of Business Accounts, Campaigns, and Participants with tenant isolation via `business_account_id` scoping, dual authentication, and a token system for participant survey access. Includes a lightweight scheduler for campaign lifecycle automation.
-   **Email Delivery System**: Custom SMTP configuration per business account with encrypted password storage, connection testing, professional VOÏA-branded templates, background task processing, and comprehensive delivery tracking.
-   **Campaign Lifecycle Management**: Automated status transitions (Draft → Ready → Active → Completed), a multi-tenant scheduling engine, automatic KPI snapshot generation, and background task management for email retry processing.
-   **Hybrid Survey Customization**: Enables campaign-specific survey personalization with business account defaults, supporting tailored AI conversations per campaign while maintaining brand identity.
-   **License Management System**: Enterprise-ready license management with usage tracking and enforcement, including anniversary-based license calculation, campaign activation limits, user count limits, and participant limits.
-   **Business Account User Management**: Multi-tenant user management with a professional UI, license-aware counters, user creation workflows with license validation and email verification, user editing, role management, status controls, and admin-triggered password resets.

# External Dependencies
-   **OpenAI API**: Used for advanced AI functionalities, including sentiment analysis, theme extraction, and the conversational survey system (VOÏA).
-   **Bootstrap CDN**: Provides responsive UI components and styling.
-   **Chart.js CDN**: Used for interactive data visualizations.
-   **Font Awesome CDN**: Provides iconography.
-   **Python Packages**: Flask, SQLAlchemy, OpenAI client library, TextBlob, cryptography.