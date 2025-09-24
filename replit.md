# Overview
The Voice of Client (VOÏA) is a Flask-based system designed for comprehensive customer feedback collection and AI-powered analysis, specializing in Net Promoter Score (NPS) surveys. Its core purpose is to convert raw customer feedback into actionable insights, identifying sentiment, key themes, churn risk, and growth opportunities. VOÏA aims to provide businesses, particularly Rivvalue Inc., with a robust tool for understanding customer sentiment, improving services, and fostering organic growth through AI-driven analysis of customer interactions. The project features a production-ready multi-tenant participant management system with extensive email delivery capabilities and AI-powered survey functionalities.

# Recent Changes

## September 24, 2025
**Transcript Add-on Assignment Bug Fix**
- **Root Cause Identified**: Fixed critical logic bug in transcript add-on assignment where empty dictionary `{}` evaluated to `False` in boolean context, causing `has_transcript_analysis` to be incorrectly set to `False` despite checkbox being checked
- **UI Workflow Fix**: Updated `business_auth_routes.py` to explicitly track transcript add-on enabled state with `{'enabled': True}` flag instead of relying on empty dictionary
- **Service Logic Correction**: Modified `license_service.py` to use explicit `transcript_addon_enabled` flag instead of truthy evaluation of potentially empty configuration dictionary
- **Resolution**: Videotron account (ID 14) transcript add-on manually enabled and UI assignment workflow now functions correctly for future assignments

**Scalability Assessment Completed**
- **Target Scale Analysis**: Evaluated system capacity to support 100-500 clients with 200-2,000 survey participants per campaign (20k-1M total participants)
- **Current Capacity**: System reliably handles 20k-50k participants (100-150 clients) on existing Replit infrastructure
- **Infrastructure Bottlenecks Identified**: PostgreSQL 10GB storage limit, in-memory task queue, basic SMTP email delivery, and OpenAI API rate limiting as primary scaling constraints
- **Scaling Recommendations**: Documented three-phase approach requiring database migration to external provider, professional email service integration, and distributed background processing for 300+ client support

## September 23, 2025
**Critical License Management Bug Fixes**
- **Resolved License Template Regression**: Fixed critical same-day regression from commit a72ef98 that broke license template field naming throughout the system
- **Template Field Standardization**: Updated license_info.html and license history templates to use correct LicenseHistory model field names:
  - Changed `days_until_expiry` to `days_remaining()` method calls
  - Changed `expiration_date` references to `expires_at` field
  - Fixed license history banner display issues where expiration information wasn't showing
- **Email Configuration Fix**: Resolved missing EmailConfiguration record for Videotron business account (ID 14) that was preventing invitation emails from sending
- **License Lookup Verification**: Debugged and confirmed that LicenseService.get_current_license() and LicenseHistory.get_current_license() methods are working correctly with proper license detection
- **System Stability**: All license-related functionality now displays correct expiration dates and license status information across the multi-tenant system

**Performance Optimization System (Stage 1 & 2)**
- **Query Optimization Framework**: Implemented feature-flag controlled database query optimizations with eager loading, query hints, and optimized dashboard queries to reduce database round trips
- **AI Analysis Consolidation**: Optimized AI processing to use single OpenAI API call instead of 5 separate calls, significantly reducing API costs and response times
- **Worker Scaling System**: Added auto-scaling Gunicorn workers based on CPU cores with feature flags for async workers and gevent support for improved I/O performance  
- **Database Connection Optimization**: Enhanced connection pooling with environment-specific configurations, timeout optimizations, and connection pre-ping for reliability
- **Performance Monitoring**: Integrated comprehensive performance monitoring system with real-time metrics tracking and optimization status validation
- **Prompt Template Optimization**: Streamlined dynamic prompt generation with hybrid business+campaign data loading and efficient fallback logic
- **Data Processing Efficiency**: Added theme consolidation and normalization functions to reduce data duplication and improve analysis accuracy

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

# Scalability Analysis & Infrastructure Planning

## Current Infrastructure Capacity
**Replit Platform Limits:**
- PostgreSQL Database: 10 GiB storage maximum
- Autoscale Deployment: 1 vCPU, 2 GiB RAM per instance (horizontal scaling available)
- Serverless scaling with pay-per-use model

**Current System Capacity:**
- **Reliable Operation**: 20,000-50,000 survey participants
- **Client Support**: 100-150 clients with 200-300 participants each
- **Breaking Point**: ~200,000-500,000 responses will exceed database storage limit

## Scaling Bottlenecks

### 🗄️ Database Storage (Critical Blocker)
- **Current**: Replit PostgreSQL with 10 GiB limit
- **Data Footprint**: Survey transcripts (5-20KB), AI analysis (2-5KB), email logs
- **Impact**: System failure when database fills up
- **Solution**: Migrate to external database (Neon, Supabase, AWS RDS) with 50-100GB capacity

### 📧 Email Delivery (Scaling Challenge)
- **Current**: Basic SMTP with threading
- **Challenge**: Bulk campaigns (10,000-100,000 invitations)
- **Problems**: Rate limiting, delivery failures, no bulk optimization
- **Solution**: Integrate professional email service (SendGrid, AWS SES, Mailgun)

### 🤖 AI Processing (Rate Limiting)
- **Current**: One OpenAI call per survey response
- **At Scale**: 1,000,000 responses = 1,000,000 API calls
- **Problems**: OpenAI rate limits, high costs, processing delays
- **Solution**: Batch processing, intelligent caching, rate limiting strategies

### ⚙️ Background Tasks (Not Scalable)
- **Current**: In-memory task queue
- **Problems**: Lost tasks during restarts, no horizontal scaling
- **Solution**: Redis-based Celery or AWS SQS for durable task processing

## Scaling Phases

### Phase 1: Current Capacity (100-150 clients)
- **Participants**: 20,000-40,000
- **Infrastructure**: Existing Replit architecture sufficient
- **Status**: ✅ Operational

### Phase 2: Mid-Scale (200-300 clients)
- **Participants**: 40,000-600,000
- **Required**: Database migration to external provider
- **Status**: ⚠️ Database migration essential

### Phase 3: Full Scale (300-500 clients)
- **Participants**: 600,000-1,000,000
- **Required**: Complete architecture overhaul
- **Components**: External database, professional email service, distributed background processing
- **Status**: 🚀 Full scaling architecture required

## Cost Projections

### Current Costs
- **Replit Infrastructure**: $25-50/month
- **OpenAI API**: Variable based on usage

### Scaled Architecture Costs
- **Total Estimated**: $200-500/month
- **External Database**: $50-150/month (Neon, Supabase, AWS RDS)
- **Email Service**: $50-200/month (SendGrid, AWS SES)
- **Background Processing**: $30-100/month (Redis, worker dynos)
- **Enhanced Monitoring**: $20-50/month

## Migration Recommendations

### Priority 1: Database Scale-Out
- Migrate to managed PostgreSQL with 50-100GB capacity
- Implement full-text search indexing for conversation transcripts
- Add tenant-first composite indexes for multi-tenant performance
- Move large transcript data to object storage (S3-compatible)

### Priority 2: Email Infrastructure
- Integrate bulk email service with API-based delivery
- Implement staged sending with provider webhooks
- Add delivery tracking with automatic retry mechanisms
- Optimize database storage for email logs

### Priority 3: Background Processing
- Replace in-memory TaskQueue with Redis-based Celery
- Implement durable task processing across restarts
- Add horizontal scaling for AI and email processing
- Make all tasks idempotent with retry/backoff logic

# External Dependencies
-   **OpenAI API**: Used for advanced AI functionalities, including sentiment analysis, theme extraction, and the conversational survey system (VOÏA).
-   **Bootstrap CDN**: Provides responsive UI components and styling.
-   **Chart.js CDN**: Used for interactive data visualizations.
-   **Font Awesome CDN**: Provides iconography.
-   **Python Packages**: Flask, SQLAlchemy, OpenAI client library, TextBlob, cryptography.