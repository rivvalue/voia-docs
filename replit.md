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

## Changelog
- July 03, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.