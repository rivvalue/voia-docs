# Overview
The Voice of Client (VOÏA) is a Flask-based system for comprehensive customer feedback collection and AI-powered analysis, specializing in Net Promoter Score (NPS) surveys. Its primary purpose is to transform raw customer feedback into actionable insights, identifying sentiment, key themes, churn risk, and growth opportunities. VOÏA aims to provide businesses, specifically Rivvalue Inc., with a powerful tool for understanding customer sentiment, improving services, and fostering organic growth by leveraging AI for deeper analysis of customer interactions. The project has successfully implemented a production-ready multi-tenant participant management system with comprehensive email delivery capabilities and AI-powered survey functionalities.

## Current Status (September 2025)
- **Production Ready**: Complete multi-tenant email system with per-business SMTP configuration
- **Email System Operational**: Resolved critical access blocking issues preventing user adoption
- **SMTP Configuration**: Fully functional custom SMTP setup, testing, and validation for each business account
- **Templates**: Professional VOÏA-branded email templates with responsive design and security features

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
- **Multi-Tenant Architecture**: Implementation of Business Accounts, Campaigns, and Participants with tenant isolation through `business_account_id` scoping, dual authentication, and a token system for participant survey access. A lightweight scheduler is planned for campaign lifecycle automation.
- **Email Delivery System**: Custom SMTP configuration per business account with encrypted password storage, connection testing, professional VOÏA-branded templates, background task processing, and comprehensive delivery tracking.
- **Campaign Lifecycle Management (Planned)**: Automated status transitions (Draft → Ready → Active → Completed), scheduling engine, event tracking, and background task management for automation.

# Recent Resolved Issues (September 2025)

## Critical Email Configuration Access Problem
**Issue**: Permission-based blocking was preventing business users from configuring and testing SMTP settings, causing silent redirects and user adoption barriers.

**Root Cause**: `@require_permission('admin')` decorators on email configuration routes were intercepting requests and redirecting users away from email setup functionality without proper error messages.

**Resolution**: Removed permission blocks from:
- Email configuration save route (`/admin/email-config/save`)
- SMTP connection testing routes (`/admin/email-config/test`)
- Created missing `test_connection_for_account()` method for proper tenant-specific SMTP testing

**Current Status**: ✅ Multi-tenant email system fully operational with business account-specific SMTP configuration, comprehensive testing capabilities, and professional email template delivery.

# External Dependencies
- **OpenAI API**: For advanced AI functionalities including sentiment analysis, theme extraction, and the conversational survey system (VOÏA).
- **Bootstrap CDN**: For responsive UI components and styling.
- **Chart.js CDN**: For interactive data visualizations on the dashboard.
- **Font Awesome CDN**: For iconography.
- **Python Packages**: Flask, SQLAlchemy, OpenAI client library, TextBlob, cryptography (for SMTP password encryption).