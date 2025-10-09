# Settings Hub - Phase 1: Section Inventory

## 📊 Complete Section Analysis

### Current Admin Panel Structure
File: `templates/business_auth/admin_panel.html` (1166 lines)
Route: `/business/admin` → `business_auth_routes.py::admin_panel()`

---

## 1. HEADER & NAVIGATION

### 1.1 Admin Header (Lines 389-509)
**Location:** Top of page, gradient background  
**Purpose:** Welcome message, user info, primary navigation  
**Components:**
- Admin avatar with shield icon
- User greeting: `{{ current_user.get_full_name() }}`
- Business account name and role display
- Quick action buttons

**Data Dependencies:**
- `current_user` (BusinessAccountUser object)
- `business_account` (BusinessAccount object)
- Session data: `business_user_id`, `business_account_id`

**Role-Based Visibility:**
- Platform Admin buttons (Analytics Hub, Onboard Business, License Dashboard)
- Standard user buttons (Manage Campaigns, Manage Participants)
- Conditional quick actions dropdown

**Proposed Migration:** → **System Settings** section (keep header actions)

---

### 1.2 Quick Actions Dropdown (Lines 427-504)
**Location:** Header right side  
**Purpose:** Secondary navigation for settings and configuration  
**Components:**
- View Analytics link
- Email Config link
- Brand Settings link
- Survey Customization link (conditional: Core/Plus/Demo accounts only)
- Manage Users link (conditional: `has_permission('manage_users')`)
- License Info link
- Audit Trail link
- Logout link

**Data Dependencies:**
- `business_account.account_type`
- `current_user.has_permission()`
- `current_user.role`

**Proposed Migration:**
- Email Config → **Account Settings** card
- Brand Settings → **Account Settings** card
- Survey Customization → **Account Settings** card
- Manage Users → **User Management** card
- License Info → **System Settings** card
- Audit Trail → **Data Management** card

---

## 2. CONTENT SECTIONS

### 2.1 Account Type Badge (Lines 512-516)
**Location:** Below header  
**Purpose:** Visual indicator of account type  
**Components:**
- Badge with icon (flask for demo, building for customer)
- Text: "Demo Environment" or "Customer Account"

**Data Dependencies:**
- `business_account.account_type`

**Proposed Migration:** → Remain in header or move to **System Settings**

---

### 2.2 Team Management Section (Lines 518-532)
**Location:** First content section  
**Purpose:** Quick access to user management  
**Visibility:** Admin only (`has_permission('manage_users')`)  
**Components:**
- Section title with users icon
- "Manage Users" button
- Usage counter: `X/Y users`

**Data Dependencies:**
- `admin_data.license_info.users_used`
- `admin_data.license_info.users_limit`
- Permission check: `current_user.has_permission('manage_users')`

**Proposed Migration:** → **User Management** card

---

### 2.3 Campaign Management Section (Lines 534-546)
**Location:** After Team Management  
**Purpose:** Quick access to campaign creation  
**Components:**
- Section title with bullhorn icon
- "Manage Campaigns" button
- Descriptive text

**Data Dependencies:** None (static text)

**Proposed Migration:** → Keep as quick action, not in Settings Hub

---

### 2.4 Statistics Overview (Lines 548-586)
**Location:** Grid row with 4 cards  
**Purpose:** High-level metrics dashboard  
**Components:**
- Total Responses (stat-icon primary)
- Total Campaigns (stat-icon success)
- Active Campaigns (stat-icon info)
- Total Participants (stat-icon warning)

**Data Dependencies:**
- `admin_data.stats.total_responses`
- `admin_data.stats.total_campaigns`
- `admin_data.stats.active_campaigns`
- `admin_data.stats.total_participants`

**Database Queries (from route):**
```python
total_responses = SurveyResponse.query.join(Campaign).filter(...).count()
total_campaigns = Campaign.query.filter_by(...).count()
total_participants = Participant.query.filter_by(...).count()
```

**Proposed Migration:** → **System Settings** card (Performance Metrics subsection)

---

### 2.5 Email Invitations Statistics (Lines 588-628)
**Location:** Grid row with 4 cards  
**Purpose:** Email delivery metrics  
**Visibility:** Conditional (`admin_data.stats.get('email_stats')`)  
**Components:**
- Sent Invitations (success icon)
- Pending Invitations (info icon)
- Failed Invitations (warning icon)
- Total Invitations (primary icon)

**Data Dependencies:**
- `admin_data.stats.email_stats.sent_invitations`
- `admin_data.stats.email_stats.pending_invitations`
- `admin_data.stats.email_stats.failed_invitations`
- `admin_data.stats.email_stats.total_invitations`

**Database Queries (from route):**
```python
EmailDelivery.query.filter_by(..., status='sent').count()
EmailDelivery.query.filter_by(..., status='pending').count()
EmailDelivery.query.filter_by(..., status='failed').count()
```

**Proposed Migration:** → **Data Management** card (Email delivery subsection)

---

### 2.6 License Information Section (Lines 630-754)
**Location:** Full-width section with nested grid  
**Purpose:** License status and usage tracking  
**Visibility:** Conditional (`admin_data.license_info`)  
**Components:**
- Section header with "View Details" button
- 4 stat cards:
  - License Type & Status (with expiry countdown)
  - Campaign Usage (X/Y campaigns)
  - User Usage (X/Y team members)
  - Participant Limit (max per campaign)
- License upgrade notice (conditional)

**Data Dependencies:**
- `admin_data.license_info.license_type`
- `admin_data.license_info.license_status`
- `admin_data.license_info.expires_soon`
- `admin_data.license_info.days_remaining`
- `admin_data.license_info.campaigns_used/limit/remaining`
- `admin_data.license_info.users_used/limit/remaining`
- `admin_data.license_info.participants_limit`

**Service Integration:**
```python
from license_service import LicenseService
license_info = LicenseService.get_license_info(business_account.id)
```

**Proposed Migration:** → **System Settings** card (License subsection)

---

### 2.7 Recent Campaigns Section (Lines 756-889)
**Location:** Left column (8 of 12 grid)  
**Purpose:** Campaign overview and quick actions  
**Components:**
- Expandable campaign cards (max 5)
- Campaign status badges (active/ready/draft/completed)
- Key metrics per status
- Action buttons based on status
- Expandable details section

**Data Dependencies:**
- `admin_data.campaigns[]` (list of campaign dicts)
- Each campaign object includes:
  - `campaign.id`, `campaign.name`, `campaign.status`
  - `campaign.description`, `campaign.start_date`, `campaign.end_date`
  - `campaign.response_count`
  - `campaign.days_until_start`, `campaign.days_remaining`, `campaign.days_since_ended`

**Database Queries (from route):**
```python
campaigns = Campaign.query.filter_by(
    business_account_id=business_account.id
).order_by(Campaign.created_at.desc()).limit(5).all()
```

**JavaScript Functions:**
- `toggleCampaignDetails(campaignId)` - Expand/collapse details
- Card hover animations

**Proposed Migration:** → Keep in main dashboard, not in Settings Hub

---

### 2.8 Recent Responses Section (Lines 892-931)
**Location:** Right column (4 of 12 grid)  
**Purpose:** Recent survey response preview  
**Components:**
- Response cards (max 5)
- Respondent name, company, NPS score
- Response date

**Data Dependencies:**
- `admin_data.recent_responses[]`
- Each response includes:
  - `response.respondent_name`
  - `response.company_name`
  - `response.nps_score`
  - `response.created_at`

**Database Queries (from route):**
```python
recent_responses = SurveyResponse.query.join(Campaign).filter(
    Campaign.business_account_id == business_account.id
).order_by(SurveyResponse.created_at.desc()).limit(10).all()
```

**Proposed Migration:** → Keep in main dashboard, not in Settings Hub

---

### 2.9 Onboarding Shortcuts Section (Lines 933-998)
**Location:** Below Recent Responses  
**Purpose:** Quick access to initial setup tasks  
**Visibility:** Conditional (onboarding incomplete)  
**Components:**
- Quick action grid (3 cards):
  - Configure Email (SMTP setup)
  - Add Team Members
  - Create First Campaign

**Data Dependencies:**
- Onboarding status checks
- Business account onboarding progress

**Integration:**
```python
from onboarding_config import OnboardingFlowManager
```

**Proposed Migration:** → **Account Settings** card (Onboarding subsection)

---

### 2.10 Session Information Section (Lines 999-1023)
**Location:** Bottom of page  
**Purpose:** Debug/admin information display  
**Components:**
- Account name
- User full name and email
- User role
- Account type, status, environment badge

**Data Dependencies:**
- `business_account.name`, `business_account.account_type`, `business_account.status`
- `current_user.full_name`, `current_user.email`, `current_user.role`

**Proposed Migration:** → **System Settings** card (Session Info subsection) or remove in production

---

## 3. JAVASCRIPT FUNCTIONS

### 3.1 Session Management (Lines 1030-1046)
**Function:** `checkSessionStatus()`  
**Purpose:** Auto-refresh session every 30 minutes  
**Endpoint:** `{{ url_for("business_auth.session_status") }}`  
**Dependencies:** None (standalone)

**Proposed Migration:** → Keep in base template or Settings Hub

---

### 3.2 Button Loading States (Lines 1048-1059)
**Function:** Quick action button spinner  
**Purpose:** UX feedback during navigation  
**Dependencies:** `.quick-action-btn` elements

**Proposed Migration:** → Reusable component in Settings Hub

---

### 3.3 Campaign Details Toggle (Lines 1061-1081)
**Function:** `toggleCampaignDetails(campaignId)`  
**Purpose:** Expand/collapse campaign cards  
**Dependencies:** Campaign card DOM elements

**Proposed Migration:** → Not needed in Settings Hub

---

### 3.4 Enhanced Interactions (Lines 1084-1102)
**Function:** Card hover animations  
**Purpose:** UX polish for campaign cards  
**Dependencies:** `.campaign-item` elements

**Proposed Migration:** → Adapt for Settings Hub cards

---

### 3.5 Export All Data (Lines 1104-1163)
**Function:** `exportAllData()`  
**Purpose:** System-wide data export  
**Endpoint:** `/api/export_data`  
**Dependencies:** Export button (`#exportAllBtn`)

**Proposed Migration:** → **Data Management** card (Export subsection)

---

## 4. EXTERNAL ROUTES & ENDPOINTS

### Email Configuration
- **Route:** `/business/admin/email-config` (GET)
- **Save Route:** `/business/admin/email-config/save` (POST)
- **Test Route:** `/business/admin/email-config/test` (POST)
- **Data:** `business_account.get_email_configuration()`

### Brand Configuration
- **Route:** `/business/admin/brand-config` (GET)
- **Save Route:** `/business/admin/brand-config/save` (POST)
- **Data:** Business account brand settings

### Survey Configuration
- **Route:** `/business/admin/survey-config` (GET)
- **Save Route:** `/business/admin/survey-config/save` (POST)
- **Visibility:** Core/Plus/Demo accounts only

### User Management
- **Route:** `/business/users` (GET)
- **Create Route:** `/business/users/create` (POST)
- **Edit Route:** `/business/users/<id>/edit` (POST)
- **Permission:** `has_permission('manage_users')`

### License Information
- **Route:** `/business/admin/license-info` (GET)
- **Service:** `LicenseService.get_license_info()`

### Audit Logs
- **Route:** `/business/admin/audit-logs` (GET)
- **Data:** Account activity trail

### Performance Metrics
- **Route:** `/business/admin/performance-metrics` (GET)
- **Data:** Database health, cache status, response times

### Scheduler Status
- **Route:** `/business/admin/scheduler/status` (GET)
- **Control Route:** `/business/admin/scheduler/run` (POST)
- **Data:** Campaign automation status

---

## 5. PROPOSED SETTINGS HUB MAPPING

### 🔧 Account Settings Card
**Components:**
1. **Email Configuration** (from Quick Actions → Email Config)
   - SMTP setup form
   - Connection test button
   - Delivery status indicator
   
2. **Brand Configuration** (from Quick Actions → Brand Settings)
   - Logo upload
   - Color customization
   - Messaging templates
   
3. **Survey Customization** (from Quick Actions → Survey Config)
   - AI conversation settings
   - Question templates
   - Response collection options
   
4. **Onboarding Progress** (from Onboarding Shortcuts)
   - Setup completion checklist
   - Quick setup links

---

### 👥 User Management Card
**Components:**
1. **Team Members** (from Team Management Section)
   - User list table
   - Add/Edit user forms
   - Role assignment
   
2. **License Usage** (from Team Management)
   - Current users counter (X/Y)
   - Visual progress bar
   - Add user button (if slots available)
   
3. **User Permissions Matrix**
   - Role-based access display
   - Permission editing (admin only)

---

### 📁 Data Management Card
**Components:**
1. **Export Full Data** (from JavaScript function)
   - System-wide export button
   - Export history log
   - Download links
   
2. **Audit Logs** (from Quick Actions)
   - Activity trail viewer
   - Filter by date/user/action
   - Export audit logs
   
3. **Email Delivery Metrics** (from Email Invitations Stats)
   - Sent/Pending/Failed counts
   - Delivery success rate
   - Retry failed invitations
   
4. **Database Health** (from Performance Metrics route)
   - Connection status
   - Query performance
   - Index health

---

### ⚙️ System Settings Card
**Components:**
1. **License Information** (from License Info Section)
   - License type and status
   - Expiry countdown
   - Campaign/User/Participant limits
   - Upgrade notices
   
2. **Performance Metrics** (from Statistics Overview + Performance route)
   - Total responses/campaigns/participants
   - Response time metrics
   - Cache status & controls
   
3. **Scheduler Status** (from Scheduler routes)
   - Campaign automation status
   - Background task queue
   - Manual trigger controls
   
4. **Session Information** (from Session Info Section)
   - Current account/user details
   - Environment badge
   - Role display

---

## 6. REUSABLE COMPONENTS IDENTIFIED

### CSS Classes (Reusable)
- `.stat-card` - Metric card layout
- `.stat-icon` - Icon circular background
- `.stat-number` - Large number display
- `.stat-label` - Label text styling
- `.admin-section` - Section container
- `.section-header` - Section title bar
- `.section-title` - Heading with icon
- `.campaign-status` - Status badges
- `.account-badge` - Account type indicator
- `.empty-state` - No data placeholder

### JavaScript Patterns (Reusable)
- Session status checker
- Button loading states
- Expand/collapse animations
- Card hover effects
- AJAX form submissions
- Export data handler

### Template Macros (Candidates)
- Stat card component
- Section header component
- Status badge component
- Loading spinner component
- Empty state component

---

## 7. DATA DEPENDENCY SUMMARY

### From `admin_data` Dictionary:
```python
admin_data = {
    'account_type': business_account.account_type,
    'campaigns': [campaign.to_dict()],  # List of 5 recent campaigns
    'active_campaigns': [...],           # Active campaigns with stats
    'recent_responses': [...],           # Last 10 responses
    'stats': {
        'total_responses': int,
        'total_campaigns': int,
        'active_campaigns': int,
        'total_participants': int,
        'email_stats': {
            'sent_invitations': int,
            'pending_invitations': int,
            'failed_invitations': int,
            'total_invitations': int
        }
    },
    'license_info': {
        'license_type': str,
        'license_status': str,
        'expires_soon': bool,
        'days_remaining': int,
        'campaigns_used': int,
        'campaigns_limit': int,
        'campaigns_remaining': int,
        'users_used': int,
        'users_limit': int,
        'users_remaining': int,
        'participants_limit': int
    }
}
```

### From Direct Objects:
- `business_account` (BusinessAccount model)
- `current_user` (BusinessAccountUser model)
- Session data: `business_user_id`, `business_account_id`

### From External Services:
- `LicenseService.get_license_info()`
- `OnboardingFlowManager` (onboarding progress)
- Email delivery status queries

---

## 8. ROLE-BASED VISIBILITY MATRIX

| Section | Platform Admin | Business Admin | Manager | Viewer |
|---------|---------------|----------------|---------|--------|
| Analytics Hub Button | ✅ | ❌ | ❌ | ❌ |
| Onboard Business Button | ✅ | ❌ | ❌ | ❌ |
| License Dashboard Button | ✅ | ❌ | ❌ | ❌ |
| Team Management Section | ✅ | ✅ (if has_permission) | ❌ | ❌ |
| Manage Users Link | ✅ | ✅ (if has_permission) | ❌ | ❌ |
| Email Config | ✅ | ✅ | ✅ | ❌ |
| Brand Config | ✅ | ✅ | ✅ | ❌ |
| Survey Config | ✅ | ✅ | ✅ | ❌ |
| License Info | ✅ | ✅ | ✅ | ✅ |
| Audit Logs | ✅ | ✅ | ✅ | ❌ |
| Export Data | ✅ | ✅ | ✅ | ❌ |
| Statistics Overview | ✅ | ✅ | ✅ | ✅ |

---

## 9. MIGRATION COMPLEXITY ASSESSMENT

### Low Complexity (1-2 hours each)
- ✅ Account Type Badge (static display)
- ✅ Session Information (read-only data)
- ✅ Statistics Overview (stat cards)
- ✅ Onboarding Shortcuts (link grid)

### Medium Complexity (3-4 hours each)
- ⚠️ Team Management Section (permission checks, user list)
- ⚠️ License Information (complex conditional logic)
- ⚠️ Email Invitations Stats (database queries)
- ⚠️ Export All Data (JavaScript integration)

### High Complexity (5-6 hours each)
- 🔴 Email Configuration (form handling, SMTP testing)
- 🔴 Brand Configuration (file uploads, preview)
- 🔴 Survey Customization (AI settings, templates)
- 🔴 User Management (CRUD operations, validation)
- 🔴 Audit Logs (filtering, pagination, export)
- 🔴 Performance Metrics (real-time data, charts)

---

## 10. NEXT STEPS FOR PHASE 1

✅ **Task 1.1 Complete:** Section inventory created  
⏳ **Task 1.2 Next:** Document data dependencies (in progress)  
⏳ **Task 1.3 Next:** Identify reusable components  
⏳ **Task 1.4 Next:** Create wireframe designs

**Estimated Time Remaining:** 4-6 hours for Phase 1 completion
