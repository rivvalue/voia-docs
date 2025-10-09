# VOÏA Error Monitoring Setup Guide

## Overview
This guide explains how to configure error monitoring for VOÏA, particularly important for Phase 2b UI migration tracking. The system supports Sentry (backend errors) and LogRocket (frontend sessions/errors).

## Quick Start

### Enable Error Monitoring
```bash
# In .env file or environment
ERROR_MONITORING_ENABLED=true
ERROR_MONITORING_DEBUG=true  # Optional: verbose logging
```

### Configure Sentry (Backend Errors)
```bash
# Get DSN from https://sentry.io
SENTRY_DSN=https://[key]@[org].ingest.sentry.io/[project]
SENTRY_ENVIRONMENT=development  # or staging, production
SENTRY_TRACES_SAMPLE_RATE=0.1   # 10% of requests (0.0-1.0)
```

### Configure LogRocket (Frontend Sessions)
```bash
# Get App ID from https://logrocket.com
LOGROCKET_APP_ID=your-app-id/voïa
```

---

## Integration with Flask App

### Method 1: app.py Integration (Recommended)
```python
from error_monitoring import error_monitor

# After creating Flask app
error_monitor.init_app(app)

# Make error monitor available globally
app.error_monitor = error_monitor
```

### Method 2: Manual Integration
```python
from flask import Flask
from error_monitoring import ErrorMonitor

app = Flask(__name__)
error_monitor = ErrorMonitor(app)
```

---

## Phase 2b Specific Features

### UI Version Tracking
Error monitor automatically tracks UI version with every error:

```python
# Automatically captured with each error:
{
    'contexts': {
        'phase2b': {
            'ui_version': 'v2',  # from session
            'feature_flags': {
                'sidebar_enabled': True
            }
        }
    }
}
```

### Feature Flag Context
All errors include feature flag state for debugging v1/v2 issues.

---

## Usage Examples

### Capture Exceptions
```python
from app import app

try:
    risky_operation()
except Exception as e:
    app.error_monitor.capture_exception(e, context={
        'operation': 'data_migration',
        'phase': 'phase2b'
    })
    raise
```

### Capture Messages/Events
```python
app.error_monitor.capture_message(
    "Phase 2b v2 UI activated for user",
    level='info',
    context={
        'ui_version': 'v2',
        'user_id': user.id
    }
)
```

### Set User Context
```python
# After user login
app.error_monitor.set_user(
    user_id=user.id,
    email=user.email,
    username=user.username
)
```

### Add Breadcrumbs
```python
# Track user actions leading to error
app.error_monitor.add_breadcrumb(
    message="User clicked sidebar nav item",
    category="ui.click",
    level="info",
    data={
        'item': 'campaigns',
        'ui_version': 'v2'
    }
)
```

### Function Decorator
```python
from error_monitoring import monitor_errors

@monitor_errors(context_name='phase2b_migration')
def migrate_user_preferences():
    # Errors automatically captured with context
    pass
```

---

## LogRocket Frontend Integration

### Template Integration
Add to your base template `<head>`:

```html
{% if logrocket_enabled %}
  {{ logrocket_init_script() | safe }}
{% endif %}
```

### Manual JavaScript Integration
```html
<script src="https://cdn.lr-in-prod.com/LogRocket.min.js"></script>
<script>
  LogRocket.init('your-app-id/voïa');
  
  // Identify user
  LogRocket.identify('{{ current_user.id }}', {
    email: '{{ current_user.email }}',
    ui_version: '{{ ui_version }}'
  });
  
  // Track Phase 2b UI version
  LogRocket.track('UI Version', {
    version: '{{ ui_version }}'
  });
</script>
```

### Custom Event Tracking
```javascript
// Track UI version changes
document.addEventListener('uiVersionChanged', function(e) {
    LogRocket.track('UI Version Changed', {
        from: e.detail.oldVersion,
        to: e.detail.newVersion
    });
});

// Track sidebar interactions
document.querySelectorAll('.sidebar-nav-item').forEach(item => {
    item.addEventListener('click', function() {
        LogRocket.track('Sidebar Navigation', {
            item: this.dataset.name,
            ui_version: document.body.dataset.uiVersion
        });
    });
});
```

---

## Environment-Specific Configuration

### Development
```bash
ERROR_MONITORING_ENABLED=true
ERROR_MONITORING_DEBUG=true
SENTRY_ENVIRONMENT=development
SENTRY_TRACES_SAMPLE_RATE=1.0  # 100% sampling in dev
```

### Staging
```bash
ERROR_MONITORING_ENABLED=true
ERROR_MONITORING_DEBUG=false
SENTRY_ENVIRONMENT=staging
SENTRY_TRACES_SAMPLE_RATE=0.5  # 50% sampling
```

### Production
```bash
ERROR_MONITORING_ENABLED=true
ERROR_MONITORING_DEBUG=false
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% sampling (cost control)
```

---

## Phase 2b Monitoring Checklist

### Pre-Migration
- [ ] Configure Sentry DSN
- [ ] Configure LogRocket App ID
- [ ] Test error capture in development
- [ ] Verify UI version context in errors
- [ ] Set up Sentry alerts for critical errors

### During Migration
- [ ] Monitor v1 vs v2 error rates
- [ ] Track sidebar navigation errors
- [ ] Watch for feature flag related issues
- [ ] Review LogRocket sessions for UX problems

### Post-Migration
- [ ] Compare error rates v1 vs v2
- [ ] Identify and fix v2-specific issues
- [ ] Document lessons learned
- [ ] Adjust sampling rates if needed

---

## Testing Error Monitoring

### Test Configuration
```bash
# Run configuration test
python error_monitoring.py
```

Output should show:
```
VOÏA Error Monitoring Configuration Test
==================================================

Environment Configuration:
  ERROR_MONITORING_ENABLED: true
  SENTRY_DSN: https://...
  LOGROCKET_APP_ID: abc123...

Status:
  ✅ Error monitoring is configured and ready
```

### Test Sentry Integration
```python
# In Python shell or test route
from app import app

with app.app_context():
    try:
        1 / 0
    except Exception as e:
        app.error_monitor.capture_exception(e, context={
            'test': 'sentry_integration'
        })

# Check Sentry dashboard for error
```

### Test LogRocket Integration
```javascript
// In browser console
LogRocket.track('Test Event', { source: 'manual_test' });

// Check LogRocket dashboard for event
```

---

## Filtering Sensitive Data

### Automatic Filtering
The error monitor automatically filters:
- Authorization headers
- Cookie values
- X-Api-Key headers
- PII (when send_default_pii=False)

### Custom Filtering
```python
# In error_monitoring.py _sentry_before_send()
def _sentry_before_send(self, event, hint):
    # Add custom filtering
    if 'request' in event and 'data' in event['request']:
        data = event['request']['data']
        if 'password' in data:
            data['password'] = '[Filtered]'
    
    return event
```

---

## Monitoring Dashboards

### Sentry Dashboard
Key metrics to watch:
- **Error Rate**: Errors per minute
- **Affected Users**: Unique users experiencing errors
- **Release**: Group errors by deployment
- **Environment**: Filter by dev/staging/production
- **Tags**: Filter by ui_version, feature_flags

### LogRocket Dashboard
Key metrics to watch:
- **Session Count**: Total sessions recorded
- **Error Sessions**: Sessions with errors
- **Rage Clicks**: Frustrated user interactions
- **UI Performance**: Load times, interactions
- **Session Replay**: Visual playback of user sessions

---

## Cost Management

### Sentry Quotas
```bash
# Control sampling to manage quota
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% of requests

# Use Sentry's quota management
# - Set monthly event limits
# - Configure spike protection
# - Filter noisy errors
```

### LogRocket Quotas
```bash
# Conditional initialization
if (window.location.hostname === 'production.replit.app') {
    LogRocket.init('app-id');
}

# Sample sessions
if (Math.random() < 0.5) {  // 50% sampling
    LogRocket.init('app-id');
}
```

---

## Troubleshooting

### Issue: "Sentry not initialized"
**Cause:** SENTRY_DSN not set or invalid

**Solution:**
```bash
# Verify DSN
echo $SENTRY_DSN

# Test with valid DSN
SENTRY_DSN=https://[key]@[org].ingest.sentry.io/[project] python error_monitoring.py
```

### Issue: "LogRocket script not loading"
**Cause:** Content Security Policy or ad blocker

**Solution:**
```html
<!-- Add CSP header -->
<meta http-equiv="Content-Security-Policy" 
      content="script-src 'self' https://cdn.lr-in-prod.com">

<!-- Or check browser console for CSP errors -->
```

### Issue: "Errors not appearing in Sentry"
**Cause:** Network issues or rate limiting

**Solution:**
```python
# Enable debug mode
ERROR_MONITORING_DEBUG=true

# Check logs for Sentry connection errors
# Verify Sentry project settings allow events
```

### Issue: "Too many events, quota exceeded"
**Cause:** High error rate or low sampling

**Solution:**
```bash
# Reduce sampling rate
SENTRY_TRACES_SAMPLE_RATE=0.05  # 5% instead of 10%

# Add error filtering in Sentry dashboard
# - Ignore specific error types
# - Filter by URL patterns
# - Set up spike protection
```

---

## Phase 2b Error Monitoring Strategy

### Week 1: v2 Alpha (10% rollout)
- Sample 100% of v2 users
- Sample 10% of v1 users (baseline)
- Monitor closely for v2-specific errors
- Daily error rate comparison

### Week 2-3: v2 Beta (25-50% rollout)
- Sample 50% of v2 users
- Sample 10% of v1 users
- Focus on performance metrics
- Weekly error trend analysis

### Week 4: v2 General Availability (100% rollout)
- Sample 10% of all users
- Compare final v1 vs v2 metrics
- Document improvements
- Archive v1 monitoring data

---

## Best Practices

### DO:
- ✅ Set user context after login
- ✅ Add breadcrumbs for user actions
- ✅ Include Phase 2b context (ui_version, feature_flags)
- ✅ Test error monitoring in development
- ✅ Filter sensitive data
- ✅ Set appropriate sampling rates
- ✅ Review errors daily during Phase 2b

### DON'T:
- ❌ Send PII to Sentry/LogRocket
- ❌ Set 100% sampling in production
- ❌ Ignore noisy errors (filter them)
- ❌ Forget to update context on UI version change
- ❌ Rely on error monitoring without logging
- ❌ Capture every exception (be selective)

---

## Appendix: Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ERROR_MONITORING_ENABLED` | `false` | Enable/disable error monitoring |
| `ERROR_MONITORING_DEBUG` | `false` | Verbose logging for debugging |
| `SENTRY_DSN` | - | Sentry project DSN |
| `SENTRY_ENVIRONMENT` | `development` | Environment name |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.1` | Trace sampling rate (0.0-1.0) |
| `LOGROCKET_APP_ID` | - | LogRocket application ID |

---

## Support Resources

### Sentry
- Documentation: https://docs.sentry.io/platforms/python/guides/flask/
- Dashboard: https://sentry.io
- Pricing: https://sentry.io/pricing/

### LogRocket
- Documentation: https://docs.logrocket.com/docs
- Dashboard: https://app.logrocket.com
- Pricing: https://logrocket.com/pricing/

### VOÏA Team
- For configuration help: Check this guide first
- For integration issues: Review error_monitoring.py
- For Phase 2b strategy: See Phase 2b monitoring checklist

---

**Last Updated:** October 9, 2025 (Phase 2b Pre-Implementation)  
**Version:** 1.0  
**Maintainer:** VOÏA Development Team
