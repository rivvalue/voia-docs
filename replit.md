# Voice of Client Agent

## Overview

The Voice of Client Agent is a customer feedback collection and analysis system built with Flask. It specializes in gathering Net Promoter Score (NPS) surveys and leveraging AI-powered analysis to extract actionable insights from customer feedback. The system automatically analyzes sentiment, identifies key themes, assesses churn risk, and highlights growth opportunities.

## System Architecture

### Backend Architecture
- **Framework**: Flask web application with SQLAlchemy ORM
- **Database**: SQLite for development (configured to easily switch to PostgreSQL)
- **AI Integration**: OpenAI API for natural language processing and sentiment analysis
- **Data Processing**: TextBlob for additional text analysis capabilities

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 dark theme
- **JavaScript**: Vanilla JavaScript for interactive survey forms and dashboard charts
- **Styling**: Custom CSS with Bootstrap components and Chart.js for data visualization

### Database Schema
The system uses a single main entity `SurveyResponse` that stores:
- Basic respondent information (company, name, email, tenure with FC inc)
- NPS score and category classification
- Multiple rating dimensions (satisfaction, product value, service, pricing)
- Text feedback (improvement suggestions, recommendation reasons, additional comments)
- AI analysis results (sentiment, themes, churn risk, growth opportunities)
- Metadata (creation timestamp, analysis timestamp)

## Key Components

### Survey Collection (`routes.py`, `templates/survey.html`)
- Multi-step survey form with progressive disclosure
- NPS score collection with visual 0-10 rating scale
- Dynamic follow-up questions based on NPS category
- Real-time form validation and progress tracking

### AI Analysis Engine (`ai_analysis.py`)
- Sentiment analysis using OpenAI API and TextBlob
- Key theme extraction from open-text responses
- Churn risk assessment based on scores and feedback content
- Growth opportunity identification from customer suggestions

### Analytics Dashboard (`templates/dashboard.html`, `static/js/dashboard.js`)
- Real-time metrics display (total responses, NPS score, recent activity)
- Interactive charts for NPS distribution, sentiment analysis, and ratings
- High-risk account identification and monitoring
- Data export functionality

### Data Management (`data_storage.py`)
- Centralized data aggregation for dashboard metrics
- NPS calculation and categorization logic
- Time-based filtering for trend analysis
- Database query optimization for reporting

## Data Flow

1. **Survey Collection**: Customers complete multi-step NPS survey through web interface
2. **Data Storage**: Response data is stored in SQLite database with automatic categorization
3. **AI Processing**: Background analysis extracts sentiment, themes, and risk factors
4. **Dashboard Display**: Aggregated insights are presented through interactive charts and metrics
5. **Export/Action**: Results can be exported or used to trigger customer success actions

## External Dependencies

### Required APIs
- **OpenAI API**: For advanced sentiment analysis and theme extraction
- **Bootstrap CDN**: For responsive UI components and dark theme
- **Chart.js CDN**: For interactive data visualizations
- **Font Awesome CDN**: For consistent iconography

### Python Packages
- Flask ecosystem (SQLAlchemy, templating)
- OpenAI client library
- TextBlob for natural language processing
- Standard libraries for JSON handling and datetime operations

## Deployment Strategy

### Development Environment
- SQLite database for local development
- Environment variables for API keys and configuration
- Flask development server with debug mode
- Automatic database table creation on startup

### Production Considerations
- Database migration path from SQLite to PostgreSQL
- Environment-based configuration management
- Proxy fix middleware for proper header handling
- Logging configuration for monitoring and debugging

### Environment Variables
- `OPENAI_API_KEY`: Required for AI analysis functionality
- `DATABASE_URL`: Database connection string (defaults to SQLite)
- `SESSION_SECRET`: Flask session security key

## Performance Optimizations for High Load (500+ Users)

### Database Optimizations
- **PostgreSQL Migration**: Switched from SQLite to PostgreSQL for better concurrency
- **Connection Pooling**: Configured pool_size=20, max_overflow=50 for handling concurrent connections
- **Database Indexing**: Added indexes on frequently queried fields (company_name, respondent_email, nps_score, nps_category, created_at, analyzed_at)
- **Query Optimization**: Implemented pagination for API endpoints to prevent large data transfers

### Asynchronous Processing
- **Background Task Queue**: Implemented in-memory task queue with 3 worker threads for AI analysis
- **Non-blocking Survey Submission**: Survey submissions now return immediately while AI analysis runs in background
- **Graceful Degradation**: System continues functioning even if AI analysis fails

### Rate Limiting & Security
- **Per-IP Rate Limiting**: 10 survey submissions per minute per IP address
- **API Rate Limiting**: 100 requests per minute per IP for API endpoints
- **Request Validation**: Enhanced input validation and error handling

### API Performance
- **Pagination**: Survey responses API supports pagination (max 100 per page)
- **Efficient Data Transfer**: Optimized JSON responses with only necessary data
- **Caching Strategy**: Prepared for Redis integration if needed

### Monitoring & Health Checks
- **Health Check Endpoint**: `/health` provides system status monitoring
- **Queue Status Monitoring**: `/api/queue_status` shows background processing metrics
- **Error Logging**: Comprehensive logging for debugging and monitoring

### Infrastructure Readiness
- **Horizontal Scaling Ready**: Stateless design allows for load balancer deployment
- **Database Connection Management**: Optimized for concurrent access patterns
- **Memory Management**: Efficient task queue with bounded memory usage

## Security Implementation for 500+ Users

### Email-Based Token Authentication
- **JWT Token System**: Secure 24-hour tokens tied to email addresses
- **Token Generation**: `/auth/request-token` endpoint with rate limiting (5 requests/min)
- **Token Verification**: `/auth/verify-token` endpoint for validation
- **Audit Trail**: AuthToken model tracks token usage, IP addresses, and user agents

### Duplicate Response Prevention
- **Primary Endpoint**: `/submit_survey` - Prevents duplicate responses per email
- **Overwrite Endpoint**: `/submit_survey_overwrite` - Allows users to update responses
- **Email Validation**: Server-side email format validation and normalization
- **Authentication Middleware**: `@require_auth` decorator validates tokens and checks duplicates

### Enhanced Rate Limiting
- **Survey Submissions**: 10 per minute per IP for authenticated users
- **Token Requests**: 5 per minute per IP to prevent token spam  
- **Overwrite Operations**: 5 per minute per IP for stricter control
- **API Endpoints**: 100 requests per minute per IP for dashboard access

### Frontend Security Features
- **Token Storage**: Secure localStorage management with automatic validation
- **Authentication Flow**: Guided user experience from token generation to survey
- **Error Handling**: Comprehensive error messages for auth failures and duplicates
- **Session Management**: Automatic token verification and renewal prompts

### Security Endpoints
- **Health Check**: `/health` - System status including auth system health
- **Queue Monitoring**: `/api/queue_status` - Background processing metrics
- **Token Management**: Audit trail for all authentication activities

## AI-Powered Conversational Surveys

### Conversational Survey System
- **Natural Language Interface**: AI-powered conversations replace traditional forms
- **OpenAI Integration**: GPT-4o model for intelligent question generation and response analysis
- **Real-time Processing**: Dynamic follow-up questions based on user responses
- **Structured Data Extraction**: Automatic conversion of natural language to survey metrics

### Key Features
- **Personalized Experience**: AI adapts questions based on previous responses
- **Multi-topic Coverage**: NPS scoring, satisfaction ratings, improvement suggestions
- **Conversation History**: Complete chat logs stored for analysis
- **Progress Tracking**: Visual progress indicator for survey completion
- **Graceful Fallbacks**: System continues functioning even if AI analysis fails

### Technical Implementation
- **Frontend**: Chat-style interface with typing indicators and message bubbles
- **Backend**: RESTful API endpoints for conversation management
- **Data Flow**: Natural language → AI analysis → structured database storage
- **Integration**: Seamless connection with existing analytics and dashboard

## Rivvalue Inc. Branding

### Visual Identity
- **Logo Integration**: Rivvalue Inc. logo prominently displayed across all pages
- **Brand Colors**: Professional blue color scheme with Rivvalue branding
- **Consistent Styling**: Bootstrap dark theme customized for Rivvalue aesthetics

### Deployment Package
- **AWS EC2 Ready**: Complete deployment guide for Debian 12 x86_64
- **Production Configuration**: Optimized for 500+ concurrent users
- **Docker Support**: Containerization ready for scalable deployment
- **Environment Variables**: Secure configuration management

## Changelog
- July 03, 2025: Initial setup with basic NPS survey functionality
- July 03, 2025: Performance optimization for 500+ concurrent users - PostgreSQL migration, async processing, rate limiting, monitoring
- July 03, 2025: Security implementation - JWT authentication, duplicate prevention, audit trails
- July 04, 2025: AI conversational surveys - OpenAI integration, natural language processing, Rivvalue branding
- July 06, 2025: Fixed conversational survey loops and data transfer issues - now fully functional end-to-end
- July 06, 2025: Updated survey questions to reference "FC inc" as supplier instead of participant's company
- July 06, 2025: Redesigned visual interface with new color palette (#FFFFFF, #E9E8E4, #BDBDBD, #E13A44, #000000)
- July 06, 2025: Added tenure dimension - captures business relationship duration with FC inc for enhanced analysis
- July 06, 2025: Enhanced survey specificity - updated service questions to "FC inc Service Delivery & Support" for more relevant feedback
- July 06, 2025: Improved churn risk display - replaced confusing percentages with clear categorical levels (Minimal, Low, Medium, High)
- July 06, 2025: Fixed survey form validation - added required validation for step 3 ratings to ensure service and satisfaction data is collected
- July 06, 2025: Updated dashboard high-risk account filtering to use categorical risk levels instead of percentage thresholds for accurate classification
- July 06, 2025: Enhanced growth opportunities display by grouping them by company name for better organization and readability
- July 06, 2025: Enhanced churn risk detection to include high-risk language like "burden", "caused us", "credits", "compensation" for more accurate risk assessment
- July 06, 2025: Fixed Chart.js CDN source map error and cleaned up dashboard JavaScript debugging code
- July 06, 2025: Fixed critical historical churn risk misclassification - updated 4 detractor responses to proper High/Medium risk levels
- July 06, 2025: Fixed sentiment analysis accuracy issue - replaced unreliable TextBlob with business-aware analysis, corrected 14 historical responses
- July 06, 2025: Added tenure distribution visualization to dashboard - shows business relationship duration with FC inc for customer segmentation
- July 07, 2025: Implemented NPS-based growth factor analysis using SaaS B2B lookup table - calculates organic growth potential from customer satisfaction
- July 07, 2025: Enhanced conversational AI survey with separate questions for professional services quality, product value, pricing appreciation, and support services following NPS and satisfaction questions
- July 07, 2025: Fixed Coka's missing tenure data and enhanced conversational survey to capture tenure - now includes tenure question as first step for complete business relationship analysis
- July 07, 2025: Renamed conversational AI agent to "Voxa" throughout platform and created comprehensive deployment guide with all 2025 enhancements
- July 08, 2025: Updated branding to "Voxa - Voice Of Client Agent" across all pages, changed subtitle to "AI Powered Client Insights" and added tagline "Voxa: Hear what matters. Act on what counts."
- July 08, 2025: Enhanced tagline styling with red color (#E13A44) and larger font size, removed robot icons from all pages for cleaner UI

## User Preferences

Preferred communication style: Simple, everyday language.
Project customization: Rivvalue Inc. branding and conversational AI surveys for enhanced user experience.