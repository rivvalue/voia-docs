# Overview
The Voice of Client (VOÏA) is a Flask-based system for comprehensive customer feedback collection and AI-powered analysis, specializing in Net Promoter Score (NPS) surveys. It converts raw customer feedback into actionable insights, identifying sentiment, key themes, churn risk, and growth opportunities. VOÏA aims to provide businesses, particularly Rivvalue Inc., with a robust tool for understanding customer sentiment, improving services, and fostering organic growth through AI-driven analysis of customer interactions. The project features a production-ready multi-tenant participant management system with extensive email delivery capabilities and AI-powered survey functionalities.

# Recent Changes
**October 10, 2025 - Business Intelligence Dashboard UI Enhancements**
-   **Banner Standardization**: Resized Dashboard hero banner to match Campaigns/Participants pattern - removed col-lg-10 wrapper, implemented responsive columns (col-12 col-md-8/col-12 col-md-4) for proper mobile stacking.
-   **Navigation Rebranding**: Renamed "Dashboard" to "Business Intelligence" in sidebar navigation menu, aligning with data-centric purpose of the page.
-   **Tab Alignment Fix**: Optimized Dashboard tabs to display on single line at desktop widths - reduced padding (1rem 2rem → 0.75rem 1.25rem), reduced margins, added desktop-only nowrap via media query (≥992px) to prevent mobile overflow.
-   **Responsive Logo**: Restored Adelco logo with d-none d-md-block for desktop-only display, maintaining brand presence without mobile clutter.
-   **Testing**: All changes validated with architect review, zero layout regressions, proper responsive behavior across breakpoints confirmed.

**October 9, 2025 - Audit Trail Fix: Export Actions Now Tracked**
-   **Audit Trail Logging**: Added comprehensive audit logging to export_data endpoint. Export actions now properly recorded in Audit Logs page with user information, timestamp, and export details.
-   **Implementation**: Integrated queue_audit_log function with action_type='data_exported', capturing user context (email, name), business account, and export metadata (total_responses, format, timestamp).
-   **Error Handling**: Wrapped audit logging in try/except to ensure export functionality remains unaffected if audit logging fails.
-   **Testing**: Validated with architect review, confirmed audit entries will appear in Audit Logs once task queue processes them.

**October 9, 2025 - Critical Bug Fixes: Breadcrumb Visibility & Export Functionality**
-   **Breadcrumb Visibility Fix**: Enhanced breadcrumb container styling with improved contrast - changed background from subtle #E9E8E4 to clearer #f8f9fa, strengthened border (2px solid #dee2e6), and added subtle box-shadow for depth. Breadcrumbs now clearly visible across all settings sub-pages.
-   **Export Feature Fix**: Corrected export endpoint in Settings Hub v2 Data Management card from '/api/export_user_data' to '/api/export_data'. Eliminated "EMAIL_REQUIRED" error - admin export now correctly downloads all survey responses without requiring email parameter.
-   **Testing**: Both fixes validated with architect review, zero regressions confirmed, application restarted successfully.

**October 9, 2025 - Settings Sub-Pages: Navigation & Breadcrumb Enhancement**
-   **Breadcrumb Navigation**: Added missing breadcrumbs to Audit Logs and License Info pages for consistent navigation across all settings sub-pages.
-   **Unified Naming**: Updated all breadcrumb text from "Admin Panel" to "Settings Hub" across 6 pages (Email Config, Brand Config, Survey Config, User Management, Audit Logs, License Info).
-   **Sub-Page Audit**: Comprehensive audit completed - verified 6 template-based pages and 1 API endpoint, all compliant with VOÏA design guidelines.
-   **Navigation Flow**: Seamless navigation between Settings Hub and all sub-pages, with consistent back-navigation via breadcrumbs.
-   **Documentation**: Created detailed audit report (docs/settings_subpages_audit.md) with findings, fixes, and future enhancement recommendations.

**October 9, 2025 - Settings Hub v2: Layout Optimization Based on User Feedback**
-   **Full-Width Card Layout**: Changed from 2-column grid to full-width stacked cards for better horizontal space utilization and improved readability.
-   **Simplified Responsive Design**: Removed breakpoints - cards now consistently span 100% width across all devices (mobile, tablet, desktop).
-   **Professional Appearance**: More spacious, modern layout aligned with contemporary admin panel design patterns.
-   **CSS Optimization**: Simplified grid system from multi-breakpoint responsive to single `grid-template-columns: 1fr` configuration.

**October 9, 2025 - Settings Hub v2: Phase 3 Content Migration COMPLETE**
-   **All 4 Cards Migrated**: Successfully migrated all admin panel content to Settings Hub v2 4-card layout (Account Settings, User Management, Data Management, System Settings).
-   **Data Bindings Preserved**: All template variables verified intact - admin_data.license_info.*, business_account.account_type, current_user.has_permission() working correctly.
-   **Role-Based Access Control**: Permission checks maintained (manage_users gate for User Management card), fallback UI for restricted users.
-   **Interactive Features**: JavaScript functions integrated for export (download), database health check (API), scheduler status (API) with visual feedback.
-   **Component Architecture**: Established reusable patterns - Settings Item (icon/title/desc/action), Stats Grid (metrics display), Interactive Buttons (loading states).
-   **Zero Regressions**: v1 admin panel untouched, feature flag isolation working (SETTINGS_HUB_V2 defaults to disabled).
-   **Application Tested**: Successfully reloaded with no LSP errors, all routes registered, data flow verified.
-   **Documentation Updated**: Implementation plan updated with Phase 3 completion notes, deliverables, and component architecture.
-   **Ready for Phase 4**: Foundation complete for enhancements (tooltips, progressive disclosure, accessibility audit) or gradual rollout (10%→25%→50%→100%).

**October 9, 2025 - Settings Hub Redesign: Phase 1 Discovery COMPLETE**
-   **Comprehensive Section Inventory**: Documented all 10 admin panel sections with complete role-based visibility matrix, data dependencies, and migration complexity assessment. Mapped to proposed 4-card Settings Hub architecture (Account Settings, User Management, Data Management, System Settings).
-   **Data Dependency Mapping**: Catalogued 50+ data points including admin_data dictionary structure, database models (BusinessAccount, BusinessAccountUser, Campaign, SurveyResponse, EmailDelivery), external services (LicenseService, OnboardingFlowManager, EmailService), form submission flows, and security considerations.
-   **Reusable Component Library**: Identified 20+ reusable components (7 CSS, 6 JavaScript classes, 6 template macros, accessibility helpers) aligned with accordion/grid layout to reduce Phase 2 implementation risk.
-   **Wireframe Designs**: Created 12 wireframes covering mobile/tablet/desktop layouts with complete design system (VOÏA branding #E13A44, responsive breakpoints, WCAG 2.1 AA accessibility specs, animation specifications, icon system).

**October 9, 2025 - Settings Hub Redesign: Phase 2 Foundation COMPLETE**
-   **Feature Flag Infrastructure**: Implemented SETTINGS_HUB_V2 flag with environment variable control (FEATURE_SETTINGS_HUB_V2), 0% rollout default, safe parallel development.
-   **Template Created**: Built admin_panel_v2.html with complete 4-card responsive grid, accordion functionality, keyboard navigation (Enter/Space/Arrow keys), expand/collapse controls.
-   **VOÏA Design System**: Strict adherence to existing CSS variables, Montserrat/Karla fonts, #E13A44 red accent, professional gradient headers.
-   **Zero Regressions**: v1 admin_panel.html remains untouched, feature-flagged routing working correctly.

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
    -   **Performance**: PostgreSQL migration, database indexing, connection pooling, asynchronous background tasks for AI, IP-based rate limiting, optimized dashboard queries (20+ queries consolidated to 2-3), and admin-configurable response caching with 5-minute default timeout.
-   **Security**: Token-based authentication, duplicate response prevention, enhanced rate limiting, and robust input validation.
-   **Branding**: "VOÏA - Voice Of Client" with "AI Powered Client Insights" subtitle and a specific tagline.
-   **Multi-Tenant Architecture**: Business Accounts, Campaigns, and Participants with tenant isolation via `business_account_id` scoping, dual authentication, and a token system for survey access. Includes a lightweight scheduler for campaign lifecycle automation.
-   **Email Delivery System**: Custom SMTP configuration per business account with encrypted password storage, connection testing, professional VOÏA-branded templates, background task processing, and delivery tracking.
-   **Campaign Lifecycle Management**: Automated status transitions (Draft → Ready → Active → Completed), multi-tenant scheduling, automatic KPI snapshot generation, and background task management for email retries.
-   **Hybrid Survey Customization**: Campaign-specific survey personalization with business account defaults for tailored AI conversations while maintaining brand identity.
-   **License Management System**: Enterprise-ready license management with usage tracking and enforcement, including anniversary-based calculation, and limits on campaigns, users, and participants.
-   **Business Account User Management**: Multi-tenant user management with a professional UI, license-aware counters, user creation workflows with validation, email verification, editing, role management, status controls, and admin-triggered password resets.
-   **Mandatory Onboarding System**: Extensible guided setup workflow for business account administrators with Core/Plus licenses, featuring JSON-based progress tracking, license-conditional enforcement, and configurable validation system.
-   **Scalability Assessment**: System reliably handles 20k-50k participants (100-150 clients) on existing Replit infrastructure.
-   **Performance Optimization System**: Query optimization consolidating dashboard data retrieval, Flask-Caching integration with configurable settings (`ENABLE_CACHE`, `CACHE_TIMEOUT`, `CACHE_TYPE`, `USE_OPTIMIZED_DASHBOARD`), strategic database indexing, and an automatic fallback strategy for queries. Multi-tenant cache isolation by `campaign_id` and `business_account_id`.
-   **Feature Flag System**: Production-ready infrastructure for UI version toggling (v1/v2) with environment variable control, rollout percentage, and user toggling.

# External Dependencies
-   **OpenAI API**: For advanced AI functionalities including sentiment analysis, theme extraction, and conversational surveys.
-   **Bootstrap CDN**: For responsive UI components and styling.
-   **Chart.js CDN**: For interactive data visualizations.
-   **Font Awesome CDN**: For iconography.
-   **Python Packages**: Flask, SQLAlchemy, OpenAI client library, TextBlob, cryptography, Flask-Caching.