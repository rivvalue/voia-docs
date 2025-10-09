# Settings Hub - Phase 1: Data Dependencies

## 📊 Data Flow Architecture

### 1. DATA SOURCES

#### 1.1 Session Data (Flask Session)
```python
session.get('business_user_id')      # Current user ID
session.get('business_account_id')   # Current business account ID
```

**Usage:**
- Authentication checks
- Tenant isolation
- Audit logging
- User context display

---

#### 1.2 Database Models (SQLAlchemy)

**BusinessAccount Model:**
```python
business_account = BusinessAccount.query.get(business_account_id)

# Available attributes:
business_account.id
business_account.name
business_account.account_type        # 'demo', 'customer'
business_account.status              # 'active', 'inactive'
business_account.contact_email
business_account.created_at
business_account.get_email_configuration()  # Returns email config dict
```

**BusinessAccountUser Model:**
```python
current_user = BusinessAccountUser.query.get(user_id)

# Available attributes:
current_user.id
current_user.email
current_user.first_name
current_user.last_name
current_user.get_full_name()         # Returns "First Last"
current_user.role                    # 'platform_admin', 'business_account_admin', etc.
current_user.is_active_user
current_user.email_verified
current_user.has_permission(permission_name)  # Permission check
current_user.is_platform_admin()     # Boolean check
```

**Campaign Model:**
```python
campaigns = Campaign.query.filter_by(
    business_account_id=business_account.id
).order_by(Campaign.created_at.desc()).limit(5).all()

# Each campaign dict includes:
campaign.to_dict() = {
    'id': int,
    'name': str,
    'description': str,
    'status': str,              # 'draft', 'ready', 'active', 'completed'
    'start_date': str,
    'end_date': str,
    'response_count': int,
    'days_until_start': int,
    'days_remaining': int,
    'days_since_ended': int
}
```

**SurveyResponse Model:**
```python
recent_responses = SurveyResponse.query.join(Campaign).filter(
    Campaign.business_account_id == business_account.id
).order_by(SurveyResponse.created_at.desc()).limit(10).all()

# Available attributes:
response.respondent_name
response.company_name
response.nps_score
response.created_at
```

**EmailDelivery Model:**
```python
EmailDelivery.query.filter_by(
    business_account_id=business_account.id,
    email_type='participant_invitation',
    status='sent'  # or 'pending', 'failed'
).count()

# Status values: 'sent', 'pending', 'failed'
# Email types: 'participant_invitation', 'reminder', etc.
```

**Participant Model:**
```python
Participant.query.filter_by(
    business_account_id=business_account.id
).count()

# Used for total participant count
```

---

#### 1.3 External Services

**LicenseService:**
```python
from license_service import LicenseService
license_info = LicenseService.get_license_info(business_account.id)

# Returns dictionary:
{
    'license_type': str,           # 'core', 'plus', 'pro', 'trial'
    'license_status': str,         # 'active', 'trial', 'expired'
    'license_start': datetime,
    'license_end': datetime,
    'expires_soon': bool,          # True if < 30 days
    'days_remaining': int,         # Days until expiry
    'days_since_expired': int,     # Days since expiry (if expired)
    
    # Usage limits:
    'campaigns_limit': int,
    'campaigns_used': int,
    'campaigns_remaining': int,
    
    'users_limit': int,
    'users_used': int,
    'users_remaining': int,
    
    'participants_limit': int      # Per campaign limit
}
```

**OnboardingFlowManager:**
```python
from onboarding_config import OnboardingFlowManager

# Get onboarding status
flow = OnboardingFlowManager.get_flow_for_license(license_type)
progress = OnboardingFlowManager.get_progress(business_account.id)

# Returns:
{
    'steps': ['welcome', 'smtp', 'users', 'complete'],
    'mandatory': bool,
    'current_step': str,
    'completed_steps': [],
    'is_complete': bool
}
```

**EmailService:**
```python
from email_service import EmailService
email_config = business_account.get_email_configuration()

# Returns:
{
    'smtp_host': str,
    'smtp_port': int,
    'smtp_username': str,
    'smtp_password': str,  # Encrypted
    'from_email': str,
    'from_name': str,
    'use_tls': bool,
    'use_ssl': bool
}
```

---

### 2. DATA FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────┐
│                   USER REQUEST                       │
│          GET /business/admin (Settings Hub)         │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│            AUTHENTICATION MIDDLEWARE                 │
│  - Check session (business_user_id, business_account_id) │
│  - Validate user/account existence                   │
│  - Check permissions based on role                   │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              DATA AGGREGATION LAYER                  │
│                 (admin_panel route)                  │
├─────────────────────────────────────────────────────┤
│ 1. Load Business Account                            │
│    └─ BusinessAccount.query.get(account_id)         │
│                                                      │
│ 2. Load Current User                                │
│    └─ BusinessAccountUser.query.get(user_id)        │
│                                                      │
│ 3. Get License Info                                 │
│    └─ LicenseService.get_license_info(account_id)   │
│                                                      │
│ 4. Load Campaigns (5 recent)                        │
│    └─ Campaign.query.filter_by(...).limit(5)        │
│                                                      │
│ 5. Load Recent Responses (10 recent)                │
│    └─ SurveyResponse.query.join(...).limit(10)      │
│                                                      │
│ 6. Calculate Statistics                             │
│    ├─ Total responses count                         │
│    ├─ Total campaigns count                         │
│    ├─ Active campaigns count                        │
│    ├─ Total participants count                      │
│    └─ Email delivery stats (sent/pending/failed)    │
│                                                      │
│ 7. Build admin_data Dictionary                      │
│    └─ Combine all data into template context        │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              TEMPLATE RENDERING                      │
│         (admin_panel.html → admin_panel_v2.html)    │
├─────────────────────────────────────────────────────┤
│ Context Variables:                                   │
│  - business_account (BusinessAccount object)        │
│  - current_user (BusinessAccountUser object)        │
│  - admin_data (Dictionary with all aggregated data) │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│           SETTINGS HUB V2 SECTIONS                   │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────────────────────────────────────┐   │
│  │      🔧 ACCOUNT SETTINGS CARD               │   │
│  ├─────────────────────────────────────────────┤   │
│  │ Data: business_account.get_email_configuration() │
│  │       business_account.account_type         │   │
│  │       onboarding progress (if applicable)   │   │
│  └─────────────────────────────────────────────┘   │
│                                                      │
│  ┌─────────────────────────────────────────────┐   │
│  │      👥 USER MANAGEMENT CARD                │   │
│  ├─────────────────────────────────────────────┤   │
│  │ Data: admin_data.license_info.users_*       │   │
│  │       current_user.has_permission()         │   │
│  │       BusinessAccountUser.get_by_business_account() │
│  └─────────────────────────────────────────────┘   │
│                                                      │
│  ┌─────────────────────────────────────────────┐   │
│  │      📁 DATA MANAGEMENT CARD                │   │
│  ├─────────────────────────────────────────────┤   │
│  │ Data: admin_data.stats.email_stats          │   │
│  │       Export endpoint: /api/export_data     │   │
│  │       Audit logs endpoint: /admin/audit-logs│   │
│  └─────────────────────────────────────────────┘   │
│                                                      │
│  ┌─────────────────────────────────────────────┐   │
│  │      ⚙️ SYSTEM SETTINGS CARD                │   │
│  ├─────────────────────────────────────────────┤   │
│  │ Data: admin_data.license_info               │   │
│  │       admin_data.stats (all metrics)        │   │
│  │       Performance metrics endpoint          │   │
│  │       Scheduler status endpoint             │   │
│  └─────────────────────────────────────────────┘   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

### 3. CRITICAL DATA DEPENDENCIES BY SECTION

#### Account Settings Card

**Email Configuration:**
```python
# Data source:
email_config = business_account.get_email_configuration()

# Dependencies:
- business_account.id
- Encrypted password storage
- SMTP connection test endpoint: /admin/email-config/test

# Form endpoints:
POST /admin/email-config/save  # Save SMTP settings
POST /admin/email-config/test  # Test connection
```

**Brand Configuration:**
```python
# Data source:
brand_config = {
    'logo_url': business_account.logo_url,
    'primary_color': business_account.primary_color,
    'secondary_color': business_account.secondary_color,
    'brand_message': business_account.brand_message
}

# Dependencies:
- File upload handling (logo)
- Color picker validation
- business_account.id for updates

# Form endpoint:
POST /admin/brand-config/save
```

**Survey Customization:**
```python
# Data source:
survey_config = {
    'ai_conversation_tone': business_account.ai_conversation_tone,
    'custom_questions': business_account.custom_questions,
    'response_collection_mode': business_account.response_collection_mode
}

# Visibility condition:
business_account.account_type in ['customer', 'demo']

# Form endpoint:
POST /admin/survey-config/save
```

**Onboarding Progress:**
```python
# Data source:
from onboarding_config import OnboardingFlowManager
progress = OnboardingFlowManager.get_progress(business_account.id)

# Dependencies:
- business_account.license_type
- Onboarding step completion tracking
- Skip condition: license_type == 'pro'

# Endpoints:
GET /business/onboarding          # Current step
GET /business/onboarding/<step>   # Specific step
POST /business/onboarding/<step>  # Complete step
```

---

#### User Management Card

**Team Members List:**
```python
# Data source:
users = BusinessAccountUser.get_by_business_account(business_account.id)
users_count = business_account.current_users_count  # Active users only

# Dependencies:
- current_user.has_permission('manage_users')
- admin_data.license_info.users_used
- admin_data.license_info.users_limit

# Endpoints:
GET  /business/users              # User list
POST /business/users/create       # Create user
POST /business/users/<id>/edit    # Edit user
POST /business/users/<id>/toggle  # Toggle status
```

**License Usage Display:**
```python
# Data source:
license_info = admin_data.license_info

# Calculated values:
usage_percentage = (users_used / users_limit) * 100
users_remaining = users_limit - users_used
can_add_user = users_remaining > 0

# Visual elements:
- Progress bar (0-100%)
- Counter display (X/Y users)
- Add user button (disabled if limit reached)
```

---

#### Data Management Card

**Export Full Data:**
```python
# Endpoint:
GET /api/export_data

# Returns:
{
    'data': {
        'campaigns': [...],
        'responses': [...],
        'participants': [...]
    },
    'export_info': {
        'total_responses': int,
        'export_date': str,
        'business_account_id': int
    }
}

# Dependencies:
- Authentication required
- Tenant isolation (business_account_id filter)
- JavaScript handler: exportAllData()
```

**Audit Logs:**
```python
# Endpoint:
GET /business/admin/audit-logs?page=1&action_type=all&user_id=all

# Query parameters:
- page: int (pagination)
- action_type: str (filter by action)
- user_id: int (filter by user)
- date_from: str (filter by date range)
- date_to: str (filter by date range)

# Returns:
{
    'logs': [...],
    'total_count': int,
    'page': int,
    'per_page': int
}
```

**Email Delivery Metrics:**
```python
# Data source:
admin_data.stats.email_stats = {
    'sent_invitations': EmailDelivery.query.filter_by(..., status='sent').count(),
    'pending_invitations': EmailDelivery.query.filter_by(..., status='pending').count(),
    'failed_invitations': EmailDelivery.query.filter_by(..., status='failed').count(),
    'total_invitations': EmailDelivery.query.filter_by(...).count()
}

# Calculated metrics:
success_rate = (sent / total) * 100 if total > 0 else 0

# Action endpoints:
POST /business/admin/email-delivery/<id>/retry  # Retry failed
```

**Database Health:**
```python
# Endpoint:
GET /business/admin/performance-metrics

# Returns:
{
    'overall_status': 'healthy|warning|critical',
    'connection': {
        'status': 'active',
        'pool_size': int,
        'active_connections': int
    },
    'indexes': {
        'idx_campaign_business_status': {'status': 'present', 'definition': str},
        'idx_campaign_dates': {'status': 'present', 'definition': str}
    },
    'constraints': {
        'single_active_campaign_constraint': {'status': 'present|missing'}
    },
    'performance': {
        'avg_query_time': float,
        'slow_queries_count': int
    }
}
```

---

#### System Settings Card

**License Information:**
```python
# Data source:
license_info = admin_data.license_info  # From LicenseService

# Display elements:
1. License Type Card
   - license_type (Core/Plus/Pro/Trial)
   - license_status (Active/Trial/Expired)
   - Expiry countdown or days since expired

2. Campaign Usage Card
   - campaigns_used / campaigns_limit
   - campaigns_remaining
   - Visual progress bar

3. User Usage Card
   - users_used / users_limit
   - users_remaining
   - Visual progress bar

4. Participant Limit Card
   - participants_limit (per campaign)
   
# Conditional alerts:
- expires_soon == True → Warning banner
- campaigns_remaining <= 1 → Upgrade notice
- users_remaining <= 1 → Upgrade notice
```

**Performance Metrics:**
```python
# Data source:
admin_data.stats = {
    'total_responses': int,
    'total_campaigns': int,
    'active_campaigns': int,
    'total_participants': int
}

# Additional endpoint:
GET /business/admin/performance-metrics

# Returns:
{
    'response_times': {
        'avg_dashboard_load': float,
        'avg_query_time': float
    },
    'cache_status': {
        'enabled': bool,
        'hit_rate': float,
        'size': int
    },
    'optimization_status': {
        'use_optimized_dashboard': bool,
        'cache_timeout': int
    }
}
```

**Scheduler Status:**
```python
# Endpoint:
GET /business/admin/scheduler/status

# Returns:
{
    'scheduler_active': bool,
    'last_run': datetime,
    'next_scheduled_run': datetime,
    'task_queue_stats': {
        'pending_tasks': int,
        'completed_tasks': int,
        'failed_tasks': int
    },
    'campaign_automation': {
        'auto_activate_enabled': bool,
        'auto_complete_enabled': bool
    }
}

# Control endpoint:
POST /business/admin/scheduler/run  # Manual trigger
```

**Session Information:**
```python
# Data source (direct from objects):
session_info = {
    'account': {
        'name': business_account.name,
        'type': business_account.account_type,
        'status': business_account.status,
        'environment': 'Demo' if business_account.account_type == 'demo' else 'Production'
    },
    'user': {
        'full_name': current_user.full_name,
        'email': current_user.email,
        'role': current_user.role,
        'role_display': role_name_mapping[current_user.role]
    }
}

# No external dependencies - rendered directly
```

---

### 4. FORM SUBMISSION FLOWS

#### Email Configuration Save
```
User Form Input
    ↓
POST /admin/email-config/save
    ↓
Validate SMTP credentials
    ↓
Encrypt password
    ↓
Save to business_account
    ↓
Flash success message
    ↓
Redirect to Settings Hub
```

#### Test Email Connection
```
User clicks "Test Connection"
    ↓
POST /admin/email-config/test
    ↓
Attempt SMTP connection
    ↓
Send test email
    ↓
Return JSON response
    ↓
Display success/error message
```

#### User Creation
```
User Form Input
    ↓
POST /business/users/create
    ↓
Validate email uniqueness
    ↓
Check license limit
    ↓
Create BusinessAccountUser
    ↓
Generate invitation token
    ↓
Send invitation email
    ↓
Flash success message
    ↓
Redirect to User Management
```

#### Export Data
```
User clicks "Export All Data"
    ↓
JavaScript: exportAllData()
    ↓
GET /api/export_data
    ↓
Aggregate all data (campaigns, responses, participants)
    ↓
Return JSON
    ↓
JavaScript: Create blob and download
    ↓
Display success message
```

---

### 5. PERMISSION-BASED DATA FILTERING

```python
# Permission matrix affects data visibility:

if current_user.role == 'platform_admin':
    # Full access to all business accounts
    # Can create business accounts
    # Can assign licenses
    
elif current_user.has_permission('manage_users'):
    # Can view/edit users in their business account
    # Can access team management section
    
elif current_user.has_permission('manage_campaigns'):
    # Can create/edit campaigns
    # Can manage participants
    
else:  # Viewer role
    # Read-only access
    # Limited settings visibility
```

**Data Scoping Rules:**
```python
# Always filter by business_account_id for tenant isolation:
Campaign.query.filter_by(business_account_id=current_account_id)
SurveyResponse.query.join(Campaign).filter(Campaign.business_account_id==current_account_id)
Participant.query.filter_by(business_account_id=current_account_id)
EmailDelivery.query.filter_by(business_account_id=current_account_id)

# Exception: Platform admins can access all accounts
if current_user.is_platform_admin():
    # Can query across business accounts
    # Has access to license dashboard
    # Can create/edit business accounts
```

---

### 6. CACHING CONSIDERATIONS

**Current Caching:**
```python
# From replit.md - Performance Optimization System:
- ENABLE_CACHE (true/false)
- CACHE_TIMEOUT (default: 300 seconds)
- CACHE_TYPE (simple/redis)
- USE_OPTIMIZED_DASHBOARD (true/false)

# Cache keys scoped by:
- campaign_id
- business_account_id

# Prevents data leakage between tenants
```

**Settings Hub Caching Strategy:**
```python
# Cache License Info (changes infrequently):
@cache.cached(timeout=300, key_prefix=lambda: f'license_info_{business_account_id}')
def get_license_info():
    return LicenseService.get_license_info(business_account_id)

# Cache Performance Metrics (30 second refresh):
@cache.cached(timeout=30, key_prefix=lambda: f'perf_metrics_{business_account_id}')
def get_performance_metrics():
    return calculate_metrics()

# Do NOT cache:
- User list (changes frequently with user creation/editing)
- Email delivery status (real-time updates)
- Scheduler status (needs real-time visibility)
```

---

### 7. ERROR HANDLING & FALLBACKS

```python
# Standard error handling pattern:
try:
    # Load data
    license_info = LicenseService.get_license_info(business_account.id)
    
except Exception as e:
    logger.error(f"Error loading license info: {e}")
    
    # Fallback to default values:
    license_info = {
        'license_type': 'unknown',
        'license_status': 'error',
        'campaigns_limit': 0,
        'users_limit': 0,
        'participants_limit': 0
    }
    
    # Flash user-friendly message:
    flash('Unable to load license information. Using default values.', 'warning')
```

**Graceful Degradation:**
- If license service fails → Show limited info, disable creation buttons
- If email stats fail → Hide email metrics section
- If audit logs fail → Show error message, maintain other functionality
- If performance metrics fail → Use cached values or show "N/A"

---

### 8. SECURITY CONSIDERATIONS

**Authentication:**
```python
@require_business_auth  # Decorator on all routes
@require_permission('manage_users')  # For user management
@require_platform_admin  # For platform-only features
```

**Data Sanitization:**
```python
# Always sanitize user input:
business_name = request.form.get('business_name', '').strip()
email = request.form.get('email', '').strip().lower()

# Validate formats:
email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
```

**Tenant Isolation:**
```python
# Always verify business_account_id matches session:
if campaign.business_account_id != session.get('business_account_id'):
    logger.warning(f"Cross-tenant access attempt")
    return abort(403)
```

**Sensitive Data:**
```python
# Never expose in templates:
- SMTP passwords (encrypted storage only)
- API keys (masked display: sk-***ABCD)
- Invitation tokens (one-time use)

# Secure transmission:
- Use HTTPS for all endpoints
- Encrypt passwords before storage
- Hash invitation tokens
```

---

## SUMMARY

### Total Data Points: 50+
- **Session Data:** 2 (user_id, account_id)
- **Business Account:** 8 attributes
- **Current User:** 10 attributes + methods
- **License Info:** 12 metrics
- **Statistics:** 8 metrics
- **Email Stats:** 4 metrics
- **Campaigns:** 10 attributes per campaign
- **Responses:** 4 attributes per response
- **External Services:** 3 (License, Onboarding, Email)
- **Endpoints:** 20+ API routes

### Data Refresh Rates:
- **Real-time:** Session info, user permissions
- **30 seconds:** Performance metrics, scheduler status
- **5 minutes:** License info, statistics (with caching)
- **On-demand:** Email delivery, audit logs, export data

### Critical Dependencies:
1. LicenseService (for usage limits)
2. Onboarding system (for setup progress)
3. Email configuration (for SMTP functionality)
4. Permission system (for access control)
