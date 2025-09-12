# Voice of Client Agent - AWS Deployment Guide

## Overview
A production-ready customer feedback platform featuring **VOÏA**, an advanced conversational AI assistant. Supports both traditional NPS surveys and natural language conversations, with comprehensive AI-powered analysis and secure authentication for 500+ concurrent users.

## Features
- **VOÏA Conversational AI**: Natural language surveys with intelligent conversation flow
- **Traditional NPS Surveys**: Multi-step forms with progressive disclosure
- **Complete Rating System**: Professional services, product value, pricing, and support ratings
- **Business Relationship Analysis**: Tenure tracking and growth factor analysis
- **AI-Powered Analysis**: Sentiment analysis, theme extraction, churn risk assessment
- **Secure Authentication**: JWT token-based system with email verification
- **Duplicate Prevention**: One response per email with optional overwrite
- **Rate Limiting**: Protection against abuse and spam (500+ concurrent users)
- **Real-time Dashboard**: Analytics and insights visualization with growth potential
- **Background Processing**: Asynchronous AI analysis with task queue

## Quick Start

### 1. Download the Code
Download all files from your Replit project to your local machine.

### 2. Environment Variables
Create a `.env` file with the following variables:

```bash
# Database
DATABASE_URL=postgresql://username:password@host:port/database

# Security
SESSION_SECRET=your-session-secret-key-here

# OpenAI API
OPENAI_API_KEY=your-openai-api-key-here

# Optional: For production logging
FLASK_ENV=production
```

### 3. Dependencies
Install Python dependencies:

```bash
pip install -r requirements.txt
```

Required packages:
- Flask 3.0.3
- SQLAlchemy 2.0.31
- OpenAI 1.35.13
- psycopg2-binary 2.9.9
- gunicorn 23.0.0
- Other dependencies as listed in pyproject.toml

### 4. Database Setup
The application automatically creates tables on startup. Ensure your PostgreSQL database is accessible.

### 5. Run the Application
```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 main:app
```

## AWS Deployment Options

### Option 1: AWS Elastic Beanstalk (Recommended)
1. **Create Application**: Use Elastic Beanstalk console
2. **Upload Code**: Zip your project files
3. **Configure Environment**: Set environment variables in EB console
4. **Database**: Use RDS PostgreSQL instance
5. **Auto-scaling**: Configure for 500+ users

### Option 2: AWS EC2 with Load Balancer
1. **Launch EC2 Instance**: Ubuntu 22.04 LTS recommended
2. **Install Dependencies**: Python 3.11, pip, nginx
3. **Configure Database**: RDS PostgreSQL
4. **Set up Load Balancer**: Application Load Balancer for high availability
5. **Configure Auto Scaling**: Auto Scaling Group for traffic spikes

### Option 3: AWS ECS with Fargate
1. **Create Docker Image**: Use provided Dockerfile
2. **Push to ECR**: Amazon Elastic Container Registry
3. **Create ECS Service**: Fargate for serverless containers
4. **Configure Load Balancer**: Application Load Balancer
5. **Auto Scaling**: Service auto-scaling based on CPU/memory

## Production Configuration

### Database Configuration
```python
# For AWS RDS PostgreSQL
DATABASE_URL = "postgresql://username:password@rds-endpoint:5432/database"

# Connection pooling for high load
pool_size = 20
max_overflow = 50
pool_pre_ping = True
pool_recycle = 300
```

### Security Configuration
- Use AWS Secrets Manager for sensitive data
- Enable HTTPS with SSL/TLS certificates
- Configure CORS for your domain
- Set up WAF for additional security

### Performance Optimization
- Use CloudFront CDN for static assets
- Configure Redis for caching (optional)
- Enable compression in nginx/ALB
- Monitor with CloudWatch

## File Structure
```
voice-of-client-agent/
├── main.py              # Application entry point
├── app.py               # Flask app configuration
├── routes.py            # API routes and endpoints
├── models.py            # Database models
├── models_auth.py       # Authentication models
├── auth_system.py       # JWT authentication system
├── ai_analysis.py       # OpenAI integration
├── task_queue.py        # Background processing
├── rate_limiter.py      # Rate limiting system
├── data_storage.py      # Data aggregation
├── templates/           # HTML templates
├── static/             # CSS, JavaScript, assets
└── requirements.txt    # Python dependencies
```

## API Endpoints

### Authentication
- `POST /auth/request-token` - Generate JWT token
- `POST /auth/verify-token` - Verify token validity

### Survey
- `GET /survey` - Survey form
- `POST /submit_survey` - Submit survey (prevents duplicates)
- `POST /submit_survey_overwrite` - Update existing response

### Analytics
- `GET /dashboard` - Analytics dashboard
- `GET /api/dashboard_data` - Dashboard metrics
- `GET /api/survey_responses` - Survey data (paginated)
- `GET /api/export_data` - Export survey data

### Monitoring
- `GET /health` - Health check
- `GET /api/queue_status` - Background task status

## Security Features

### Authentication
- JWT tokens with 24-hour expiration
- Email-based authentication
- Token audit trail with IP tracking

### Rate Limiting
- Token requests: 5 per minute per IP
- Survey submissions: 10 per minute per IP
- API calls: 100 per minute per IP

### Data Protection
- Duplicate response prevention
- Input validation and sanitization
- SQL injection protection
- XSS protection

## Monitoring and Logging
- Health check endpoint for load balancers
- Comprehensive error logging
- Task queue monitoring
- Authentication audit trail

## Support
For deployment assistance or custom modifications, contact your development team.

## License
Proprietary - All rights reserved