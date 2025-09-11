# Vocsa Platform Clone Deployment Guide

## Overview
This guide will help you clone the Vocsa Intelligence platform to create a full-featured Voice of Client Agent system while keeping the original as a demonstration/sneak peek.

## Prerequisites

### Required Software
- Python 3.8 or higher
- PostgreSQL 12 or higher
- Git
- Modern web browser

### Required API Keys
- OpenAI API key (for AI analysis and conversational features)
- Email service credentials (optional, for notifications)

## Step 1: Clone the Repository

```bash
# Clone the repository
git clone <your-repository-url> voxa-full-platform
cd voxa-full-platform

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Database Setup

### Option A: Local PostgreSQL
```bash
# Create database
createdb voxa_production

# Set environment variables
export DATABASE_URL="postgresql://username:password@localhost:5432/voxa_production"
```

### Option B: Neon (Cloud PostgreSQL)
1. Create account at neon.tech
2. Create new project
3. Copy connection string
4. Set DATABASE_URL environment variable

## Step 3: Environment Configuration

Create `.env` file in project root:
```env
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/voxa_production

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# Flask Security
SESSION_SECRET=your_secure_session_secret_here

# Email (optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Admin Configuration
ADMIN_EMAILS=admin@rivvalue.com,admin@yourdomain.com
```

## Step 4: Initialize Database

```bash
# Run the application to create tables
python main.py

# The application will automatically create all necessary tables
```

## Step 5: Production Configuration

### For Production Deployment:

1. **Update branding** in `templates/base.html` and `static/css/style.css`
2. **Configure domain** in deployment settings
3. **Set up SSL/TLS** certificates
4. **Configure rate limiting** for production load
5. **Set up monitoring** and logging

### Key Files to Customize:
- `templates/index.html` - Landing page messaging
- `templates/base.html` - Site-wide branding
- `static/css/style.css` - Color scheme and styling
- `replit.md` - Update project documentation

## Step 6: Feature Enhancements for Full VoC Agent

### Immediate Enhancements:
1. **Multi-tenant architecture** - Support multiple organizations
2. **Advanced analytics** - Trend analysis, comparative reports
3. **Custom survey templates** - Beyond NPS surveys
4. **Integration APIs** - Connect with CRM systems
5. **Role-based access control** - Multiple user levels
6. **Automated reporting** - Scheduled email reports

### Database Schema Extensions:
```sql
-- Organizations/Tenants
CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User roles and permissions
CREATE TABLE user_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    organization_id INTEGER REFERENCES organizations(id),
    role VARCHAR(50) NOT NULL,
    permissions JSONB
);

-- Custom survey templates
CREATE TABLE survey_templates (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    template_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Step 7: Deployment Options

### Option A: Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway init
railway up
```

### Option B: Heroku
```bash
# Install Heroku CLI
# Create Heroku app
heroku create your-voxa-app
heroku addons:create heroku-postgresql:hobby-dev
git push heroku main
```

### Option C: DigitalOcean App Platform
1. Connect GitHub repository
2. Configure environment variables
3. Deploy automatically

## Step 8: Post-Deployment Configuration

1. **Test all features**:
   - Survey submission (both types)
   - AI analysis pipeline
   - Dashboard analytics
   - Email notifications

2. **Performance optimization**:
   - Database indexing
   - Connection pooling
   - Caching strategy

3. **Security hardening**:
   - Rate limiting configuration
   - Input validation
   - SQL injection prevention

## Step 9: Monitoring and Maintenance

### Recommended Tools:
- **Monitoring**: New Relic, DataDog
- **Error tracking**: Sentry
- **Database monitoring**: PostgreSQL built-in tools
- **Uptime monitoring**: Pingdom, StatusPage

### Key Metrics to Track:
- Survey completion rates
- API response times
- Database query performance
- User engagement metrics

## Troubleshooting

### Common Issues:
1. **Database connection errors**: Check DATABASE_URL format
2. **OpenAI API failures**: Verify API key and rate limits
3. **Email delivery issues**: Check SMTP configuration
4. **Static files not loading**: Verify static file serving

### Log Files:
- Application logs: Check Flask debug output
- Database logs: PostgreSQL log files
- Web server logs: Gunicorn/uWSGI logs

## Support and Documentation

- **Technical documentation**: See `replit.md`
- **API documentation**: Available at `/api/docs` (when enabled)
- **Database schema**: See `models.py`

## Next Steps for Full VoC Agent

1. **Plan multi-tenant architecture**
2. **Design advanced analytics features**
3. **Implement integration APIs**
4. **Create custom survey builder**
5. **Add automated reporting system**

---

*This deployment guide ensures a production-ready Voice of Client Agent platform while maintaining the original as a demonstration system.*