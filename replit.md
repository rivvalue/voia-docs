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
- Basic respondent information (company, name, email)
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

## Changelog
- July 03, 2025: Initial setup with basic NPS survey functionality
- July 03, 2025: Performance optimization for 500+ concurrent users - PostgreSQL migration, async processing, rate limiting, monitoring

## User Preferences

Preferred communication style: Simple, everyday language.