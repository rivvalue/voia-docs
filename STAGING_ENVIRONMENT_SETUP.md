# VOÏA Staging Environment Setup Guide

## Overview
This guide provides comprehensive instructions for setting up a staging environment for VOÏA Phase 2b UI migration. A staging environment is critical for testing v2 sidebar navigation, feature flags, and rollback procedures before production deployment.

## Why Staging Environment?

### Phase 2b Specific Needs
- **UI Testing**: Validate v2 sidebar navigation with real data
- **Feature Flag Testing**: Verify rollout percentage and user toggle
- **Error Monitoring**: Test Sentry/LogRocket integration
- **Rollback Testing**: Practice restoration procedures
- **Multi-Tenant Isolation**: Ensure business account data separation
- **Performance Testing**: Benchmark v2 vs v1 performance

### Testing Scenarios
1. Gradual rollout simulation (10% → 25% → 50% → 100%)
2. User toggle between v1/v2 interfaces
3. Feature flag state persistence
4. Error monitoring context accuracy
5. Database rollback validation
6. Email delivery with SMTP

---

## Environment Options

### Option 1: Replit Staging (Recommended for Phase 2b)

**Pros:**
- ✅ Identical to production infrastructure
- ✅ Built-in database and rollback
- ✅ Easy environment variable management
- ✅ No additional hosting costs
- ✅ Quick deployment

**Cons:**
- ❌ Shares Replit account quota
- ❌ Limited to Replit infrastructure

**Setup Steps:**
1. Fork/clone production Repl
2. Rename to "VOÏA-Staging"
3. Configure staging database
4. Set staging environment variables
5. Deploy and test

### Option 2: External Staging Server

**Pros:**
- ✅ Independent infrastructure
- ✅ Production-like environment
- ✅ Dedicated resources
- ✅ Custom domain support

**Cons:**
- ❌ Additional hosting costs
- ❌ More complex setup
- ❌ Separate database management

**Platforms:**
- Heroku (easiest)
- AWS/GCP (most control)
- DigitalOcean (good balance)

---

## Replit Staging Setup (Detailed)

### Step 1: Create Staging Repl

#### Method A: Fork Existing Repl
```bash
# In Replit UI:
1. Open production Repl
2. Click "Fork" button
3. Rename: "VOÏA-Staging"
4. Description: "VOÏA Phase 2b Staging Environment"
```

#### Method B: Clone from Git
```bash
# Create new Repl from GitHub
1. Click "Create Repl"
2. Select "Import from GitHub"
3. Enter repository URL
4. Choose "Python" template
5. Name: "VOÏA-Staging"
```

### Step 2: Configure Staging Database

#### Create Separate Database
```bash
# In staging Repl:
1. Open Database tab
2. Create new PostgreSQL database
3. Note connection string
```

#### Initialize Schema
```bash
# In staging Repl shell:
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

#### Seed Test Data (Optional)
```bash
# Import demo data for testing
python demo_data_generator.py --campaign-name "Staging Test Q1 2025"
```

### Step 3: Configure Environment Variables

#### Required Variables
```bash
# In Replit Secrets tab:

# Database
DATABASE_URL=<staging_database_url>

# Security
SESSION_SECRET=<generate_new_secret>  # DO NOT reuse production

# Feature Flags (Phase 2b)
FEATURE_FLAGS_ENABLED=true
SIDEBAR_ROLLOUT_PERCENTAGE=100  # Full access in staging
ALLOW_UI_VERSION_TOGGLE=true

# Error Monitoring
ERROR_MONITORING_ENABLED=true
ERROR_MONITORING_DEBUG=true
SENTRY_DSN=<staging_sentry_dsn>  # Separate from production
SENTRY_ENVIRONMENT=staging
SENTRY_TRACES_SAMPLE_RATE=1.0  # 100% sampling in staging
LOGROCKET_APP_ID=<staging_logrocket_id>  # Separate from production

# Performance
ENABLE_CACHE=true
CACHE_TIMEOUT=300
USE_OPTIMIZED_DASHBOARD=true

# Email (use test SMTP)
DEFAULT_SMTP_HOST=smtp.mailtrap.io  # Or similar test service
DEFAULT_SMTP_PORT=2525
DEFAULT_SMTP_USER=<test_smtp_user>
DEFAULT_SMTP_PASSWORD=<test_smtp_password>
DEFAULT_SMTP_FROM_EMAIL=staging@voïa.test

# Staging Identifier
ENVIRONMENT=staging
IS_STAGING=true
```

#### Generate Secrets
```python
# Generate SESSION_SECRET
python -c "import secrets; print(secrets.token_hex(32))"
```

### Step 4: Deploy Staging Environment

#### Start Application
```bash
# Staging uses same command as production
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

#### Verify Deployment
```bash
# Check application health
curl https://<staging-repl-url>.replit.app/health

# Expected response:
{"status": "healthy", "environment": "staging"}
```

### Step 5: Verify Configuration

#### Test Checklist
- [ ] Database connection works
- [ ] Session management functional
- [ ] Feature flags accessible
- [ ] Error monitoring configured
- [ ] Email delivery works (test SMTP)
- [ ] UI v2 loads correctly
- [ ] Sidebar navigation functional

---

## External Staging Setup (Heroku Example)

### Prerequisites
```bash
# Install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login to Heroku
heroku login
```

### Create Heroku App
```bash
# Create staging app
heroku create voïa-staging

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Set buildpack
heroku buildpacks:set heroku/python
```

### Configure Environment
```bash
# Set all required environment variables
heroku config:set SESSION_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
heroku config:set FEATURE_FLAGS_ENABLED=true
heroku config:set SIDEBAR_ROLLOUT_PERCENTAGE=100
heroku config:set ERROR_MONITORING_ENABLED=true
heroku config:set SENTRY_ENVIRONMENT=staging
heroku config:set ENVIRONMENT=staging
heroku config:set IS_STAGING=true

# Verify configuration
heroku config
```

### Deploy Application
```bash
# Deploy from git
git push heroku main

# Run database migrations
heroku run python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Check logs
heroku logs --tail
```

---

## Database Management

### Staging Database Strategy

#### Option 1: Production Snapshot (Recommended)
```bash
# Export production data (anonymized)
python database_backup.py backup prod-snapshot "Production data for staging"

# Import to staging
# 1. Copy backup file to staging environment
# 2. Use Replit rollback to restore data
# 3. Anonymize sensitive data
```

#### Option 2: Generated Test Data
```bash
# Generate realistic test data
python demo_data_generator.py \
  --campaign-name "Staging Q1 2025" \
  --num-companies 50 \
  --num-responses 500
```

#### Option 3: Empty Database
```bash
# Start fresh for schema testing
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### Data Anonymization
```python
# Anonymize production data for staging
from app import app, db
from models import User, SurveyResponse

with app.app_context():
    # Anonymize user emails
    users = User.query.all()
    for user in users:
        user.email = f"user{user.id}@staging.test"
    
    # Anonymize company names
    responses = SurveyResponse.query.all()
    for response in responses:
        response.company_name = f"Company {response.id}"
    
    db.session.commit()
```

---

## Testing Procedures

### Phase 2b UI Testing

#### Test Case 1: Sidebar Navigation
```
1. Login to staging environment
2. Verify sidebar visible (v2 UI)
3. Click each navigation item
4. Verify correct page loads
5. Check URL routing
6. Test responsive behavior (mobile/tablet/desktop)
```

#### Test Case 2: Feature Flag Toggle
```
1. Login as user
2. Access UI version toggle
3. Switch v1 → v2
4. Verify sidebar appears
5. Switch v2 → v1
6. Verify tabs reappear
7. Check session persistence
```

#### Test Case 3: Rollout Percentage
```bash
# Set rollout to 50%
SIDEBAR_ROLLOUT_PERCENTAGE=50

# Test with multiple users:
1. Login as 10 different users
2. Track UI version assignment
3. Verify ~50% get v2
4. Verify assignment is sticky (same user always gets same version)
```

#### Test Case 4: Error Monitoring
```javascript
// Trigger test error in v2 UI
document.querySelector('.sidebar-nav-item').dispatchEvent(new Event('error'));

// Verify in Sentry:
1. Check error appears
2. Verify Phase 2b context (ui_version='v2')
3. Verify feature flags captured
4. Check breadcrumbs recorded

// Verify in LogRocket:
1. Find session recording
2. Check UI version tracked
3. Verify user actions captured
```

### Performance Testing

#### Benchmark v1 vs v2
```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test v1 dashboard
ab -n 100 -c 10 https://staging.replit.app/dashboard?ui_version=v1

# Test v2 dashboard
ab -n 100 -c 10 https://staging.replit.app/dashboard?ui_version=v2

# Compare response times
```

#### Database Query Analysis
```python
# Enable query logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Load dashboard and review queries
# Target: <5 queries for dashboard load
```

### Rollback Testing

#### Test Checkpoint Restoration
```bash
# 1. Create checkpoint
python checkpoint_utils.py create "pre-phase2b-test" "Before sidebar test"

# 2. Make changes (modify feature flags, UI)
# 3. Verify rollback works
#    Use Replit UI > Tools > Rollback
#    Select "pre-phase2b-test" checkpoint
#    Restore

# 4. Verify state restored
#    - Feature flags reset
#    - Database unchanged
#    - Files reverted
```

---

## Continuous Integration

### Automated Staging Deployment

#### GitHub Actions Example
```yaml
# .github/workflows/deploy-staging.yml
name: Deploy to Staging

on:
  push:
    branches: [develop]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Deploy to Replit Staging
        run: |
          curl -X POST ${{ secrets.REPLIT_STAGING_WEBHOOK }}
      
      - name: Run Smoke Tests
        run: |
          python -m pytest tests/smoke/ --staging
      
      - name: Notify Team
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
            -d '{"text": "Staging deployed and tested ✅"}'
```

### Smoke Tests
```python
# tests/smoke/test_staging.py
import os
import requests
import pytest

STAGING_URL = os.environ.get('STAGING_URL', 'https://staging.replit.app')

def test_application_health():
    response = requests.get(f"{STAGING_URL}/health")
    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'

def test_feature_flags_enabled():
    response = requests.get(f"{STAGING_URL}/")
    assert 'ui_version' in response.cookies

def test_database_connection():
    response = requests.get(f"{STAGING_URL}/dashboard")
    assert response.status_code == 200

def test_error_monitoring():
    # Verify Sentry DSN configured
    assert os.environ.get('SENTRY_DSN'), "Sentry not configured"
```

---

## Environment Promotion

### Staging → Production Workflow

#### Step 1: Staging Validation
```
✅ All Phase 2b tests pass
✅ Error monitoring verified
✅ Performance benchmarks met
✅ Rollback tested successfully
✅ Team review completed
```

#### Step 2: Production Preparation
```bash
# 1. Create production checkpoint
python checkpoint_utils.py create "pre-phase2b-production" "Before Phase 2b deployment"

# 2. Update production environment variables
# Copy staging config to production (adjust as needed)

# 3. Configure production error monitoring
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1  # Lower sampling in production
```

#### Step 3: Gradual Rollout
```bash
# Week 1: Alpha (10%)
SIDEBAR_ROLLOUT_PERCENTAGE=10

# Week 2: Beta (25%)
SIDEBAR_ROLLOUT_PERCENTAGE=25

# Week 3: Expanded (50%)
SIDEBAR_ROLLOUT_PERCENTAGE=50

# Week 4: General Availability (100%)
SIDEBAR_ROLLOUT_PERCENTAGE=100
```

#### Step 4: Monitor & Verify
```
1. Check error rates (Sentry)
2. Monitor user sessions (LogRocket)
3. Review performance metrics
4. Collect user feedback
5. Document lessons learned
```

---

## Troubleshooting

### Issue: Staging database not accessible
**Symptoms:** Connection errors, timeout

**Solution:**
```bash
# Verify DATABASE_URL
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1;"

# Recreate if needed
# Replit: Delete and recreate database
# Heroku: heroku pg:reset DATABASE_URL
```

### Issue: Feature flags not working
**Symptoms:** Sidebar not appearing, toggle missing

**Solution:**
```bash
# Verify environment variables
echo $FEATURE_FLAGS_ENABLED
echo $SIDEBAR_ROLLOUT_PERCENTAGE

# Check feature_flags.py loaded
python -c "from feature_flags import FLAGS; print(FLAGS)"

# Clear session cache
# Browser: Delete cookies for staging domain
```

### Issue: Error monitoring not capturing
**Symptoms:** No errors in Sentry/LogRocket

**Solution:**
```bash
# Verify configuration
python error_monitoring.py

# Check DSN validity
curl -X POST <SENTRY_DSN> -d '{"test": true}'

# Enable debug logging
ERROR_MONITORING_DEBUG=true
```

### Issue: UI version not persisting
**Symptoms:** Version resets on page reload

**Solution:**
```python
# Verify session configuration
from app import app
print(app.secret_key)  # Should not be None

# Check cookie settings
# Ensure HTTPS in production
app.config['SESSION_COOKIE_SECURE'] = True  # For production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
```

---

## Best Practices

### DO:
- ✅ Use separate database for staging
- ✅ Generate new SESSION_SECRET (don't reuse production)
- ✅ Use test SMTP service (Mailtrap, etc.)
- ✅ Anonymize production data before staging import
- ✅ Test rollback procedures regularly
- ✅ Enable 100% error monitoring sampling
- ✅ Document all configuration differences
- ✅ Run smoke tests after each deployment
- ✅ Keep staging data realistic but not sensitive

### DON'T:
- ❌ Use production database in staging
- ❌ Share SESSION_SECRET between environments
- ❌ Send real emails from staging
- ❌ Expose staging to public (use auth)
- ❌ Skip rollback testing
- ❌ Deploy to production without staging validation
- ❌ Use production API keys in staging
- ❌ Ignore staging errors (they indicate production risk)

---

## Staging Environment Checklist

### Initial Setup
- [ ] Staging Repl/server created
- [ ] Separate database configured
- [ ] Environment variables set
- [ ] Session secret generated (new)
- [ ] Error monitoring configured (separate)
- [ ] Test SMTP configured
- [ ] Application deployed
- [ ] Health check passes

### Phase 2b Specific
- [ ] Feature flags enabled
- [ ] Sidebar rollout at 100%
- [ ] UI toggle accessible
- [ ] v1/v2 both functional
- [ ] Error monitoring captures UI version
- [ ] LogRocket tracks navigation
- [ ] Rollback tested successfully

### Testing
- [ ] Smoke tests pass
- [ ] UI navigation works (v1 & v2)
- [ ] Feature flags toggle correctly
- [ ] Error monitoring verified
- [ ] Performance acceptable
- [ ] Database operations work
- [ ] Email delivery confirmed (test)

### Production Readiness
- [ ] All Phase 2b tests pass
- [ ] Team review completed
- [ ] Rollback procedure documented
- [ ] Production checkpoint created
- [ ] Gradual rollout plan ready
- [ ] Monitoring dashboards configured

---

## Cost Considerations

### Replit Staging
- **Compute:** Shares account quota
- **Database:** Free tier sufficient for staging
- **Bandwidth:** Minimal cost
- **Total:** ~$0/month (within Replit plan)

### External Staging (Heroku)
- **App:** Hobby tier ($7/month)
- **Database:** Mini tier ($5/month)
- **Add-ons:** Sentry/LogRocket free tiers
- **Total:** ~$12/month

### Optimization Tips
- Use smaller database tier
- Limit error monitoring sampling if needed
- Archive old staging data regularly
- Use free tier services where possible

---

## Support & Resources

### Documentation
- Feature Flags: `FEATURE_FLAG_SYSTEM.md`
- Error Monitoring: `ERROR_MONITORING_SETUP.md`
- Database Backup: `BACKUP_RESTORE_GUIDE.md`
- Phase 2b Plan: `PHASE_2B_PRE_IMPLEMENTATION.md`

### Tools
- Replit Dashboard: https://replit.com
- Sentry: https://sentry.io
- LogRocket: https://logrocket.com
- Mailtrap (test SMTP): https://mailtrap.io

### VOÏA Team
- Staging issues: Check this guide first
- Configuration help: Review environment variables
- Testing questions: See testing procedures section
- Production deployment: Follow promotion workflow

---

**Last Updated:** October 9, 2025 (Phase 2b Pre-Implementation)  
**Version:** 1.0  
**Maintainer:** VOÏA Development Team  
**Next Review:** After Phase 2b completion
