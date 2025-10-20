# Overview
The Voice of Client (VOÏA) is a Flask-based system for comprehensive customer feedback collection and AI-powered analysis, specializing in Net Promoter Score (NPS) surveys. Its purpose is to convert raw customer feedback into actionable insights, identifying sentiment, key themes, churn risk, and growth opportunities. VOÏA provides businesses with a robust tool for understanding customer sentiment, improving services, and fostering organic growth through AI-driven analysis of customer interactions. The project features a production-ready multi-tenant participant management system with extensive email delivery capabilities, AI-powered conversational surveys with hybrid prompt architecture, and participant segmentation for personalized experiences and advanced analytics.

# Recent Changes
**October 20, 2025 - Security & Platform Admin Features**
- **Password Change Audit Trail**: Implemented comprehensive audit logging for password reset operations with IP address tracking, user context, and method attribution (self-service reset via forgot password flow)
- **Platform Admin User Directory**: Added read-only user directory to Business Analytics Hub showing users across all business accounts with:
  - SQLAlchemy selectinload optimization (fetches 20 accounts with users in 2 queries instead of N+1 pattern)
  - Collapsible accordion UI showing user details per business account
  - User status, role, email, and last login information
  - Supports active/inactive user filtering and role-based badges
- **Impact**: Enhanced security audit trail for compliance and platform admin cross-tenant user visibility for better platform oversight

**October 20, 2025 - Performance Optimization & UX Update**
- **LicenseService Query Optimization**: Enhanced `LicenseService.get_license_info()` to accept optional `business_account` and `is_platform_admin` parameters, eliminating duplicate database queries across all admin pages
- **Settings Page Performance**: Reduced load time from 3.7s to <2s by passing pre-fetched BusinessAccount objects to avoid redundant 195ms queries
- **Platform Admin Page Performance**: Reduced load time from 1.2s to <800ms with optimized object reuse patterns
- **License Dashboard Performance**: Reduced load time from 4.7s (61 queries) to <2s (~15-20 queries) by:
  - Passing pre-fetched business_account objects to LicenseService
  - Adding is_platform_admin flag to skip unnecessary user lookups
  - Pre-calculating campaign counts with error handling
  - Fixing platform admin license type validation warnings
- **Route Optimizations**: Updated `admin_panel`, `manage_users`, and `license_dashboard` routes to leverage already-fetched objects and prevent N+1 query patterns
- **Impact**: Eliminated 137-195ms duplicate BusinessAccount queries on every page load, resulting in 40-60% performance improvement across all Settings Hub v2 admin interfaces
- **Login Page UX Improvement**: Removed misleading "Remember me for 7 days" checkbox and replaced with informative text explaining all sessions are 7-day by default, improving user clarity about session management

# User Preferences
Preferred communication style: Simple, everyday language.
User interface tone: Thought leadership and research-oriented language, avoiding sales-oriented messaging.
Project customization: Rivvalue Inc. branding and conversational AI surveys for enhanced user experience.

# System Architecture
The system is a Flask web application with a multi-tiered architecture. The frontend uses Jinja2, Bootstrap 5, custom CSS, vanilla JavaScript, and Chart.js. The backend is Flask with SQLAlchemy ORM, designed for scalability from SQLite to PostgreSQL. AI integration, primarily via OpenAI API, handles natural language processing, sentiment analysis, and conversational surveys (VOÏA), supplemented by TextBlob.

**UI/UX**: Multi-step survey forms, interactive dashboards, chat-style interfaces for conversational surveys, and Rivvalue Inc. branding with a professional blue color scheme. Modern sidebar navigation, mobile responsiveness, and active state highlighting. The Settings Hub v2 features a 5-card accordion layout: Account Settings, User Management, Data Management, System Settings, and Platform Administration (role-restricted for platform admins only). Platform Administration card provides access to cross-tenant tools: Business Analytics Hub, Business Account Onboarding, License Dashboard, and Platform Admin Users. Modernized dashboard and campaign pages feature consistent typography, clean white backgrounds with red accents, lighter shadows, and standardized badge styling. The home page features a minimalist design with red accent borders for features and optimized mobile layouts. Business Intelligence Navigation includes a three-tier structure: Overview, Executive Summary, and Campaign Insights, separating strategic oversight from operational analysis. Session-based Breadcrumb Navigation ensures intelligent back-button behavior. Admin pages and the Survey Response page are fully redesigned with Settings Hub v2 patterns, featuring bold red gradient headers, VOÏA brand color tokens, comprehensive ARIA accessibility attributes, and mobile-responsive breakpoints. All inline styles are migrated to custom.css using design system variables, and emoji icons are replaced with FontAwesome. A comprehensive breadcrumb system is implemented across 26 business pages using a reusable component with consistent design patterns and responsive optimization.

**Technical Implementations**:
-   **Survey Collection**: Multi-step forms with dynamic follow-up questions and real-time validation.
-   **AI Analysis Engine**: Sentiment analysis, key theme extraction, churn risk assessment, growth opportunity identification, and NPS-based growth factor analysis.
-   **Conversational Surveys (VOÏA)**: AI-powered (GPT-4o) natural language interface with advanced personalization capabilities, featuring a hybrid prompt architecture combining structured JSON with natural language guidance for dynamic question generation and structured data extraction. Includes participant segmentation and feature flag rollout capabilities.
-   **Data Management**: Centralized data aggregation, NPS calculation, time-based filtering, and optimized database queries.
-   **Authentication**: JWT token-based with email validation, admin roles, server-side token generation, and automatic invalidation.
-   **Performance**: PostgreSQL migration, database indexing, connection pooling, asynchronous background tasks for AI, IP-based rate limiting, optimized dashboard queries, admin-configurable response caching, index page response caching, Executive Summary comparison optimization, frontend optimizations, and LicenseService query optimization (eliminates duplicate BusinessAccount queries by accepting optional pre-fetched objects, reducing Settings page load from 3.7s to <2s, Platform Admin page from 1.2s to <800ms, and License Dashboard from 4.7s to <2s with query count reduction from 61 to ~15-20).
-   **Security**: Token-based authentication, duplicate response prevention, enhanced rate limiting, robust input validation, CSRF/XSS protection, and Sentry integration.
-   **Branding**: "VOÏA - Voice Of Client" with "AI Powered Client Insights" subtitle, specific tagline, multi-tenant logo system, and selective trial branding.
-   **Multi-Tenant Architecture**: Business Accounts, Campaigns, and Participants with tenant isolation via `business_account_id` scoping, dual authentication, and a token system for survey access, including a lightweight scheduler. Participant entities support optional segmentation attributes (role, region, customer_tier, language) for personalized survey experiences and advanced analytics segmentation.
-   **Manual Commercial Value Tracking**: Company-level commercial value system for accurate account intelligence, stored on the Participant model, with CSV upload validation and automatic synchronization across participants from the same company.
-   **Email Delivery System**: Multi-provider email infrastructure (AWS SES, SMTP) with business accounts choosing providers, encrypted password storage, connection testing, professional VOÏA-branded templates, background task processing, delivery tracking, and configurable email content at both business account and campaign levels, with a 3-tier fallback architecture for customization.
-   **Campaign Lifecycle Management**: Automated status transitions, multi-tenant scheduling, automatic KPI snapshot generation, and background task management with comprehensive audit logging for both manual and automated actions. Draft campaigns support full editability (name, dates, description) and deletion with cascade removal of participant associations, all protected by status validation and multi-tenant security. Manual lifecycle control preserves user agency with explicit transitions: draft → ready → active → completed. All campaign status changes (manual or scheduler-driven) are logged to the audit trail with attribution metadata.
-   **Hybrid Survey Customization**: Campaign-specific survey personalization with business account defaults.
-   **License Management System**: Enterprise-ready license management with usage tracking and enforcement.
-   **Business Account User Management**: Multi-tenant user management with professional UI, license-aware counters, and comprehensive user workflows.
-   **Mandatory Onboarding System**: Extensible guided setup workflow for business account administrators.
-   **Feature Flag System**: Production-ready infrastructure for UI version toggling.
-   **Segmentation Analytics**: Comprehensive analytics system displaying NPS and satisfaction metrics segmented by participant attributes (role, region, customer tier). Includes a dedicated Segmentation Insights tab in Campaign Insights with interactive Chart.js visualizations showing NPS distribution across segments, detailed satisfaction ratings table, and historical preservation through campaign snapshots. Supports NULL handling by grouping unmapped participants as "Unspecified" for complete data coverage.
-   **Demo Data Generation**: High-volume test data scripts (`generate_demo_data.py` and `generate_demo_data_simple.py`) capable of generating 1000 responses per campaign across 70 companies. Scripts automatically populate all participant segmentation fields (role, region, customer_tier, language) and enforce company-level commercial value consistency across all participants from the same company. Support campaign reuse patterns and realistic NPS distributions for staging and development testing.

# External Dependencies
-   **OpenAI API**: For advanced AI functionalities including sentiment analysis, theme extraction, and conversational surveys.
-   **Bootstrap CDN**: For responsive UI components and styling.
-   **Chart.js CDN**: For interactive data visualizations.
-   **Font Awesome CDN**: For iconography.
-   **Python Packages**: Flask, SQLAlchemy, OpenAI client library, TextBlob, cryptography, Flask-Caching.
-   **Sentry**: For error tracking and performance monitoring.