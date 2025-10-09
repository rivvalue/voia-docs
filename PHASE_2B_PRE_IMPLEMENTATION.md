# Phase 2b Pre-Implementation Documentation
## Sidebar Navigation - Current State Baseline

**Document Purpose**: Capture current navigation structure BEFORE Phase 2b implementation  
**Created**: October 9, 2025  
**Status**: Pre-Implementation Documentation

---

## 1. Current Navigation Architecture

### Two-Tier Navigation System (Current)

**Primary Tier** (Top-level tabs):
- **INSIGHTS** - Data analysis and reporting
- **ADMIN** - Account and system management

**Secondary Tier** (Context-dependent sub-tabs):

**INSIGHTS Section:**
1. Overview - KPIs and high churn risk accounts
2. Account Intelligence - Risk vs opportunity analysis  
3. Analytics - Detailed charts and metrics
4. Survey Insights - Response patterns and NPS analysis
5. Executive Summary - Campaign comparison reports

**ADMIN Section:**
1. Admin Tools - Platform administration features

---

## 2. Current User Flows

### 2.1 Business User Authentication Flow

```
/business/login (GET)
  ↓
User enters credentials
  ↓
POST /business/login
  ↓
Session created (business_user_id, business_account_id)
  ↓
Redirect to /business/admin (Admin Panel)
```

**Session Data Stored:**
- `business_user_id` - Current user ID
- `business_account_id` - Tenant scope
- `user_role` - Permission level

**Roles**:
- `platform_admin` - System-wide access
- `business_account_admin` - Full business account access
- `manager` - Campaign and participant management
- `viewer` - Read-only analytics

### 2.2 Campaign Management Flow

```
Admin Panel (/business/admin)
  ↓
Click "Manage Campaigns" button
  ↓
Campaign List (/business/campaigns/)
  ↓
Actions:
  - Create Campaign → /business/campaigns/create
  - View Details → /business/campaigns/<id>
  - Manage Participants → /business/campaigns/<id>/participants
  - Send Invitations → POST /business/campaigns/<id>/send-invitations
  - Export Data → GET /business/campaigns/<id>/export
```

**Campaign Lifecycle States**:
1. `draft` - Initial creation, editable
2. `ready` - Configuration complete, ready to launch
3. `active` - Currently running, collecting responses
4. `completed` - Ended, read-only analysis mode

### 2.3 Participant Management Flow

```
Admin Panel OR Campaign View
  ↓
Navigate to Participants
  ↓
Options:
  1. Global View: /business/participants/ (all participants)
  2. Campaign View: /business/campaigns/<id>/participants (filtered)
  ↓
Actions:
  - Add Individual → /business/participants/create
  - Bulk Upload → /business/participants/upload (CSV)
  - Assign to Campaign → POST /business/campaigns/<id>/participants/add
  - Send Invitation → POST /business/participants/<id>/send-invitation
```

### 2.4 Dashboard & Analytics Flow

```
Dashboard (/dashboard OR /)
  ↓
Two-Tier Navigation:
  PRIMARY: [INSIGHTS] [ADMIN]
  SECONDARY (if INSIGHTS): [Overview] [Account Intelligence] [Analytics] [Survey Insights] [Executive Summary]
  ↓
Campaign Filter (Persistent via sessionStorage):
  - Applies to: Dashboard, Analytics pages ONLY
  - Excludes: Participants (global view), Settings
  ↓
Data Display:
  - KPI Cards (NPS, Total Responses, Churn Risk, Growth Potential)
  - Charts (Themes, Sentiment, Company NPS, Tenure NPS)
  - Account Intelligence Table (Risk/Opportunity balance)
```

### 2.5 Token-Based Survey Access Flow (Public)

```
User receives email invitation
  ↓
Clicks survey link with token parameter
  ↓
GET /survey?token=<jwt_token>
  ↓
Token validation (72-hour expiry)
  ↓
Survey Type Selection:
  1. Traditional: Multi-step form submission
  2. Conversational (VOÏA): AI-powered chat interface
  ↓
Response Processing:
  - Data extraction and validation
  - AI sentiment analysis
  - Churn risk assessment
  - Growth opportunity identification
  ↓
Response saved → Token invalidated → Thank you page
```

---

## 3. Current Page Structure & Dependencies

### 3.1 Dashboard (templates/dashboard.html)

**JavaScript Dependencies**:
- `static/js/dashboard.js` - 3000+ lines
  - Tab switching: `switchPrimarySection(section)`
  - Data loading: `loadDashboardData()`, `refreshData()`
  - Campaign filtering: `applyCampaignFilter()`, `clearCampaignFilter()`
  - Chart rendering: Chart.js initialization
  - Export functions: `exportData()`, `exportUserData()`

**Critical State Variables**:
```javascript
let currentPrimarySection = 'insights';
let currentDashboardData = null;
let chartsInitialized = false;
let selectedCampaignId = sessionStorage.getItem('selectedCampaignId');
```

**HTML Structure**:
```html
<div class="two-tier-navigation">
  <ul class="nav nav-pills primary-nav">
    <li><button onclick="switchPrimarySection('insights')">INSIGHTS</button></li>
    <li><button onclick="switchPrimarySection('admin')">ADMIN</button></li>
  </ul>
  
  <div id="insightsSection">
    <ul class="nav nav-tabs secondary-nav">
      <li><button data-bs-toggle="tab" data-bs-target="#overview">Overview</button></li>
      <!-- ... more tabs -->
    </ul>
  </div>
</div>
```

### 3.2 Campaign List (templates/campaigns/list.html)

**Key Features**:
- Grid/Table view toggle
- Status filtering (Draft, Ready, Active, Completed)
- Real-time participant counts
- Engagement metrics per campaign
- Action buttons (View, Analytics, Participants, Export, Executive Report)

**Template Variables**:
```python
{
  'campaigns': campaign_data,  # List of campaign dicts
  'business_account': current_account.to_dict()
}
```

### 3.3 Admin Panel (templates/business_auth/admin_panel.html)

**Sections**:
1. Welcome header with user info
2. Quick action buttons (Manage Campaigns, Participants)
3. Platform admin tools (if authorized)
4. Recent campaigns preview
5. License usage widget

**Permission Checks**:
```python
@require_business_auth
@require_permission('manage_participants')
```

---

## 4. Current URL Routing Structure

### Business Account Routes
```python
/business/login                      # Login page
/business/logout                     # Logout action
/business/admin                      # Admin panel (landing after login)
/business/analytics                  # Business analytics view
/business/users                      # User management
/business/users/create              # Add new user
/business/email-config              # SMTP configuration
/business/brand-config              # Brand settings
/business/survey-config             # Survey customization
```

### Campaign Routes
```python
/business/campaigns/                # List campaigns
/business/campaigns/create          # Create campaign
/business/campaigns/<id>            # View campaign details
/business/campaigns/<id>/edit       # Edit campaign
/business/campaigns/<id>/participants  # Campaign participants
/business/campaigns/<id>/send-invitations  # Send emails
/business/campaigns/<id>/export     # Export campaign data
```

### Participant Routes
```python
/business/participants/             # List all participants (global)
/business/participants/create       # Add participant
/business/participants/upload       # Bulk CSV upload
/business/participants/<id>         # View participant
/business/participants/<id>/delete  # Remove participant
```

### Dashboard & Analytics Routes
```python
/                                   # Public landing (redirects)
/dashboard                          # Main dashboard (requires auth)
/api/dashboard-data                 # Dashboard data API
/api/comparison                     # Campaign comparison API
```

---

## 5. Critical JavaScript Functions (Dashboard)

### Navigation Control
```javascript
function switchPrimarySection(section) {
    // Toggles between INSIGHTS and ADMIN sections
    // Updates active states, shows/hides secondary nav
}
```

### Campaign Filter Persistence
```javascript
function applyCampaignFilter() {
    // Stores in sessionStorage: selectedCampaignId, selectedCampaignName, etc.
    // Reloads dashboard data with campaign filter
}

function clearCampaignFilter() {
    // Removes sessionStorage items
    // Reloads all-campaign data
}
```

### Data Loading Pipeline
```javascript
async function loadDashboardData() {
    // 1. Check campaign filter in sessionStorage
    // 2. Fetch from /api/dashboard-data?campaign_id=X
    // 3. Update KPI cards
    // 4. Render charts
    // 5. Populate tables
}
```

---

## 6. Current UI Components & Patterns

### Header Gradients
```css
Dashboard: linear-gradient(135deg, rgba(red, 0.08) 0%, rgba(red, 0.12) 100%)
Campaigns: linear-gradient(135deg, rgba(red, 0.1) 0%, rgba(red, 0.15) 100%)
Admin: linear-gradient(135deg, rgba(red, 0.1) 0%, rgba(red, 0.15) 100%)
```

### Card Components
- `.kpi-card` - Dashboard metrics (NPS, responses, churn risk)
- `.stat-card` - Admin panel statistics
- `.campaign-card` - Grid view campaign items
- `.chart-card` - Analytics visualizations

### Button Hierarchy
- Primary: `.btn-primary` - Main actions (Create Campaign, Send Invitations)
- Secondary: `.btn-outline-primary` - Less prominent actions
- Tertiary: `.btn-outline-secondary` - Optional actions
- Icon-only: Action buttons in tables (view, edit, delete)

---

## 7. Security & Multi-Tenant Isolation

### Tenant Scoping Implementation
```python
# ALL queries must include business_account_id filter
campaigns = Campaign.query.filter_by(
    business_account_id=current_account.id
).all()
```

### Permission Decorators
```python
@require_business_auth  # Ensures valid session
@require_permission('manage_participants')  # Role-based access
```

### Data Isolation Checkpoints
1. Session validation on every request
2. Business account ID in all database queries
3. Token-to-participant validation for surveys
4. Campaign-to-business-account ownership verification

---

## 8. Known Issues & Pain Points

### Navigation Confusion
1. **Dual Entry Points**: Admin Panel accessible from navbar AND dashboard admin tab
2. **Unclear Scope**: Participants accessible globally and per-campaign
3. **No Breadcrumbs**: Deep navigation lacks context (Campaign → Participants → Upload)
4. **Tab State Loss**: Browser refresh loses active tab selection

### JavaScript Complexity
1. **Dashboard.js**: 3000+ lines, hard to debug
2. **Tab Dependencies**: Complex state management across primary/secondary tabs
3. **Chart Lifecycle**: Charts sometimes fail to render on tab switch

### CSS Specificity Conflicts
1. **Inline Styles**: Dashboard has extensive inline styling
2. **Page-Specific CSS**: Each page has `<style>` blocks overriding global styles
3. **Shadow Overuse**: Most cards use `--shadow-lg` indiscriminately

---

## 9. Dependencies to Preserve

### Critical Functionality That MUST Work in v2
1. ✅ Campaign lifecycle automation (Draft → Ready → Active → Completed)
2. ✅ Email delivery triggers (invitation sends)
3. ✅ Participant token generation (survey access)
4. ✅ Dashboard API aggregation (KPI calculations)
5. ✅ Multi-tenant data isolation (security)
6. ✅ License management UI (Pro/Plus/Core features)
7. ✅ Campaign filter persistence (sessionStorage)
8. ✅ Responsive table patterns (mobile cards)

### JavaScript Libraries in Use
- **Chart.js** - Dashboard visualizations
- **Bootstrap 5** - UI components, modals, tabs
- **Font Awesome** - Icons throughout UI
- **Native Fetch API** - AJAX requests

---

## 10. Rollback Readiness

### Git Baseline Commit
**Before Phase 2b starts**: Create tagged commit  
```bash
git tag -a v2.0-pre-sidebar -m "Baseline before Phase 2b sidebar implementation"
git push origin v2.0-pre-sidebar
```

### Critical Files to Backup
1. `templates/base.html` - Current layout foundation
2. `templates/dashboard.html` - Two-tier navigation structure
3. `static/js/dashboard.js` - Navigation and state logic
4. `static/css/custom.css` - Global styles
5. `routes.py`, `business_auth_routes.py`, `campaign_routes.py` - URL patterns

### Restore Procedure (if needed)
```bash
# Quick rollback to pre-sidebar state
git checkout v2.0-pre-sidebar -- templates/base.html
git checkout v2.0-pre-sidebar -- templates/dashboard.html
git checkout v2.0-pre-sidebar -- static/js/dashboard.js
```

---

## 11. Next Steps (Phase 2b Development)

### Pre-Implementation Checklist
- [x] Document current navigation structure ✅
- [ ] Implement feature flag system (v1/v2 toggle)
- [ ] Create database backup mechanism
- [ ] Set up error monitoring configuration
- [ ] Document staging environment requirements

### Development Phase
- [ ] Create `base_v2.html` with sidebar layout
- [ ] Build sidebar component (desktop 280px)
- [ ] Build bottom nav (mobile 64px)
- [ ] Create `dashboard_v2.html` parallel template
- [ ] Write `navigation_v2.js` separate file

---

**Document Status**: ✅ Complete  
**Review Date**: October 9, 2025  
**Next Action**: Implement feature flag system
