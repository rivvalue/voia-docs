# Bug #1 and AWS SES Display Analysis

**Date:** October 30, 2025  
**Status:** Investigation Complete

---

## Issue #1: "Manage Domains" Access (Bug #1)

### Current Status: ✅ **WORKING AS DESIGNED** (Not a Bug)

### Investigation Results

**Route Protection:**
```python
@business_auth_bp.route('/admin/platform-email-domains')
@require_business_auth              # Must be logged in
@require_platform_admin             # Must have platform admin role
def platform_email_domains():
```

**Access Control:**
- **Location:** `/business/admin/platform-email-domains`
- **Required Role:** Platform Administrator ONLY
- **Link Location:** Platform Email Settings page (also platform-admin only)

### Who Can Access "Manage Domains"?

✅ **CAN ACCESS:**
- Users with `is_platform_admin = True` in their BusinessAccountUser record
- Must be logged into a business account session

❌ **CANNOT ACCESS:**
- Regular business account administrators
- Business account users without platform admin flag
- Unauthenticated users

### Verification Steps

To verify if you have platform admin access:

1. **Check your user role in database:**
   ```sql
   SELECT id, email, full_name, is_platform_admin, role
   FROM business_account_users
   WHERE email = 'your_email@example.com';
   ```
   
   Expected result: `is_platform_admin = true`

2. **Check session:**
   - Log in to VOÏA
   - Navigate to `/business/admin/platform-email-settings`
   - If you can access this page, you're a platform admin
   - Click "Manage Domains" button (should work)

3. **If access denied:**
   - Your account does not have platform admin privileges
   - Contact system administrator to grant platform admin role

### Why This Access Control Exists

The "Manage Domains" page allows:
- Adding verified domains for ALL business accounts
- Editing DKIM records that affect email deliverability
- Deleting domains used by business accounts
- Viewing all VOÏA-managed email configurations

**Security Rationale:** Only platform administrators should have this power, as it affects the entire VOÏA platform's email infrastructure.

---

## Issue #2: How AWS SES Active Status is Displayed to Business Accounts

### Business Account User View

Business account users (non-platform admins) see their email configuration at:
**Location:** `/business/admin/email-delivery-config`

### Visual Display Components

#### 1. **Status Banner (Top of Page)**

**If AWS SES / VOÏA-Managed is Active:**
```
┌─────────────────────────────────────────────────────────────┐
│ ✓ VOÏA-Managed Email Delivery Active                       │
│ Using verified domain: yourdomain.com                      │
└─────────────────────────────────────────────────────────────┘
```
- Green background (#d4edda)
- Check circle icon
- Shows the verified domain name

**If Client-Managed SMTP is Active:**
```
┌─────────────────────────────────────────────────────────────┐
│ ℹ Client-Managed Email Delivery Active                      │
│ Using your own SMTP server: smtp.gmail.com                 │
└─────────────────────────────────────────────────────────────┘
```
- Blue background (#d1ecf1)
- Info circle icon
- Shows SMTP server name

**If No Configuration:**
```
┌─────────────────────────────────────────────────────────────┐
│ ⚠ No email configuration found                              │
│ Please configure your email delivery method below.         │
└─────────────────────────────────────────────────────────────┘
```
- Yellow background (#fff3cd)
- Warning triangle icon

#### 2. **Mode Selection Radio Buttons**

Business account users see TWO options:

```
○ VOÏA-Managed Email Delivery
  Use platform's AWS SES with your verified domain

○ Client-Managed Email Delivery  
  Use your own SMTP server credentials
```

- Only ONE can be active at a time
- Radio buttons clearly show which mode is selected

#### 3. **VOÏA-Managed Configuration Section**

When AWS SES / VOÏA-Managed is selected:

**Available Domains Dropdown:**
```
Select Verified Domain *
┌──────────────────────────────────────────┐
│ yourdomain.com          [Verified ✓]    │
│ anotherdomain.com       [Verified ✓]    │
└──────────────────────────────────────────┘

Note: Only verified domains are shown. 
Contact platform administrator to add new domains.
```

**What Business Accounts See:**
- Dropdown shows ONLY domains that platform admin has:
  1. Added to the platform
  2. Assigned to their business account
  3. Marked as verified

**What Business Accounts DON'T See:**
- AWS credentials (hidden - platform manages these)
- Unverified domains
- Domains belonging to other business accounts
- The "Manage Domains" button (platform admin only)

#### 4. **DKIM Records Display**

After selecting a domain, business accounts see:

```
┌─────────────────────────────────────────────────────────────┐
│ 🛡️ DNS Configuration Required                               │
│                                                             │
│ Add these DKIM records to your domain's DNS settings:      │
│                                                             │
│ Record 1:                                                   │
│ Name:  abc123._domainkey.yourdomain.com                    │
│ Type:  CNAME                                                │
│ Value: abc123.dkim.amazonses.com                           │
│                                                             │
│ Record 2:                                                   │
│ Name:  def456._domainkey.yourdomain.com                    │
│ Type:  CNAME                                                │
│ Value: def456.dkim.amazonses.com                           │
│                                                             │
│ Record 3:                                                   │
│ Name:  ghi789._domainkey.yourdomain.com                    │
│ Type:  CNAME                                                │
│ Value: ghi789.dkim.amazonses.com                           │
└─────────────────────────────────────────────────────────────┘
```

**Purpose:**
- Shows DNS records that need to be added
- Allows business account to complete email verification
- Copy-paste friendly format

#### 5. **Sender Information Fields**

```
Sender Name *
┌──────────────────────────────────┐
│ Customer Success Team            │
└──────────────────────────────────┘

Sender Email *
┌──────────────────────────────────┐
│ noreply@yourdomain.com           │
└──────────────────────────────────┘
Note: Must use the selected verified domain

Reply-To Email (Optional)
┌──────────────────────────────────┐
│ support@yourdomain.com           │
└──────────────────────────────────┘
```

---

## Admin Panel Dashboard Display

### Platform Admin View

Platform administrators see additional information in:
**Location:** `/business/admin/platform-email-settings`

**Exclusive Platform Admin Features:**

1. **"Manage Domains" Button**
   - Quick link to domain management
   - Prominent red button
   - Located in highlighted card with gradient background

2. **AWS SES Configuration Form**
   - AWS Access Key ID (masked)
   - AWS Secret Access Key (masked)
   - AWS Region selector
   - Test connection button

3. **System-Wide Settings**
   - Default sender name for platform
   - Platform-wide AWS credentials
   - Affects ALL business accounts using VOÏA-managed

### Business Account Admin View (Non-Platform Admin)

Regular business account administrators see:
**Location:** `/business/admin/email-delivery-config`

**What They See:**
- Current email delivery mode status
- Option to switch between VOÏA-managed and Client-managed
- List of available verified domains (if any)
- DKIM records for selected domain
- Sender configuration fields

**What They DON'T See:**
- AWS credentials
- Platform-wide settings
- "Manage Domains" button
- Other business accounts' domains
- Unverified domains

---

## Data Flow: How Business Accounts Get VOÏA-Managed Email

### Step-by-Step Process

```
┌─────────────────────────────────────────────────────────────┐
│ PLATFORM ADMINISTRATOR                                      │
└─────────────────────────────────────────────────────────────┘
           │
           ├─► 1. Configure AWS SES credentials (platform-wide)
           │      Location: /business/admin/platform-email-settings
           │
           ├─► 2. Add verified domain for business account
           │      Location: /business/admin/platform-email-domains
           │      Action: "Add Domain" → Select business account → Enter domain
           │
           ├─► 3. Provide DKIM records to business account
           │      System shows: DKIM Record 1, 2, 3 values
           │
           └─► 4. Mark domain as verified (after DNS confirmed)
                  Action: Edit domain → Check "Domain Verified"

┌─────────────────────────────────────────────────────────────┐
│ BUSINESS ACCOUNT ADMINISTRATOR                              │
└─────────────────────────────────────────────────────────────┘
           │
           ├─► 5. Navigate to Email Delivery Configuration
           │      Location: /business/admin/email-delivery-config
           │
           ├─► 6. See verified domain in dropdown (if admin added it)
           │      Dropdown shows: "yourdomain.com [Verified ✓]"
           │
           ├─► 7. Select VOÏA-Managed mode
           │      Radio button: "VOÏA-Managed Email Delivery"
           │
           ├─► 8. Choose verified domain from dropdown
           │      Select: yourdomain.com
           │
           ├─► 9. Enter sender details
           │      Sender Name: "Customer Success Team"
           │      Sender Email: "noreply@yourdomain.com"
           │
           └─► 10. Save configuration
                   Status banner now shows: "✓ VOÏA-Managed Email Delivery Active"

```

---

## Database Schema

### Relevant Tables

**EmailConfiguration Model:**
```python
class EmailConfiguration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'))
    
    # Mode Selection
    use_platform_email = db.Column(db.Boolean, default=False)  # True = VOÏA-managed
    
    # VOÏA-Managed Fields
    sender_domain = db.Column(db.String(255))                  # e.g., yourdomain.com
    domain_verified = db.Column(db.Boolean, default=False)     # True if DKIM verified
    domain_verified_at = db.Column(db.DateTime)
    dkim_record_1_name = db.Column(db.String(500))
    dkim_record_1_value = db.Column(db.String(500))
    dkim_record_2_name = db.Column(db.String(500))
    dkim_record_2_value = db.Column(db.String(500))
    dkim_record_3_name = db.Column(db.String(500))
    dkim_record_3_value = db.Column(db.String(500))
    
    # Client-Managed Fields
    smtp_server = db.Column(db.String(255))                    # e.g., smtp.gmail.com
    smtp_port = db.Column(db.Integer)                          # e.g., 587
    smtp_username = db.Column(db.String(255))
    smtp_password_encrypted = db.Column(db.Text)               # Encrypted
    smtp_use_tls = db.Column(db.Boolean, default=True)
    
    # Common Fields
    sender_name = db.Column(db.String(255))
    sender_email = db.Column(db.String(255))
    reply_to_email = db.Column(db.String(255))
```

**PlatformEmailSettings Model:**
```python
class PlatformEmailSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # AWS SES Credentials (Platform-Wide)
    aws_access_key_id = db.Column(db.String(255))             # Encrypted
    aws_secret_access_key_encrypted = db.Column(db.Text)      # Encrypted
    aws_region = db.Column(db.String(50))                     # e.g., us-east-1
    
    # Platform defaults
    default_sender_name = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
```

---

## API Routes Summary

### Platform Admin Routes (Require `@require_platform_admin`)

| Route | Purpose | Access |
|-------|---------|--------|
| `/business/admin/platform-email-settings` | Configure AWS SES credentials | Platform Admin |
| `/business/admin/platform-email-domains` | Manage verified domains | Platform Admin |
| `/business/admin/platform-email-domains/add` | Add new domain | Platform Admin |
| `/business/admin/platform-email-domains/edit/<id>` | Edit domain | Platform Admin |
| `/business/admin/platform-email-domains/delete/<id>` | Delete domain | Platform Admin |

### Business Account Routes (Require `@require_business_auth`)

| Route | Purpose | Access |
|-------|---------|--------|
| `/business/admin/email-delivery-config` | View/edit email config | Business Admin |
| `/business/admin/email-delivery-config/save` | Save email config | Business Admin |

---

## Visual Summary: What Each User Type Sees

### Platform Administrator
```
┌──────────────────────────────────────────────────────┐
│ Platform Email Settings                              │
├──────────────────────────────────────────────────────┤
│ ✓ AWS SES Configuration Active                       │
│ Region: us-east-1                                    │
│                                                      │
│ ┌────────────────────────────────────────────────┐  │
│ │ 🌐 Verified Domain Management                  │  │
│ │ Manage verified domains and DKIM records       │  │
│ │                        [Manage Domains] ◄────  │  │ THIS BUTTON
│ └────────────────────────────────────────────────┘  │
│                                                      │
│ AWS Access Key ID: ****5678                         │
│ AWS Secret Key: ********************                │
│ AWS Region: [us-east-1 ▼]                           │
│                                                      │
│ [Test Connection] [Save Settings]                   │
└──────────────────────────────────────────────────────┘
```

### Business Account Administrator
```
┌──────────────────────────────────────────────────────┐
│ Email Delivery Configuration                         │
├──────────────────────────────────────────────────────┤
│ ✓ VOÏA-Managed Email Delivery Active                │
│ Using verified domain: yourdomain.com               │
│                                                      │
│ Email Delivery Mode:                                │
│ ● VOÏA-Managed Email Delivery ◄────────────────────  │ SELECTED MODE
│   Use platform's AWS SES with your verified domain  │
│                                                      │
│ ○ Client-Managed Email Delivery                     │
│   Use your own SMTP server credentials              │
│                                                      │
│ Select Verified Domain:                             │
│ [yourdomain.com ✓ ▼]    ◄──────────────────────────  │ AVAILABLE DOMAINS
│ Note: Only verified domains are shown.              │
│ Contact platform administrator to add new domains.  │
│                                                      │
│ Sender Name: [Customer Success Team]                │
│ Sender Email: [noreply@yourdomain.com]              │
│                                                      │
│ [Save Configuration]                                 │
└──────────────────────────────────────────────────────┘
```

---

## Answers to Your Questions

### Q1: "Not capable of accessing manage domains"

**Answer:** This is **working as designed**, not a bug.

**Explanation:**
- "Manage Domains" is a **platform administrator only** feature
- Access is controlled by the `@require_platform_admin` decorator
- This is intentional for security and operational reasons

**To gain access:**
1. Verify you have platform admin role in database
2. Check: `SELECT is_platform_admin FROM business_account_users WHERE email = 'your_email'`
3. If `is_platform_admin = false`, you need platform admin privileges

**Who should have platform admin access:**
- System administrators
- DevOps team members
- Staff managing VOÏA infrastructure

**Who should NOT have platform admin access:**
- Regular business account administrators
- Business account users
- Client organization staff

### Q2: "How is AWS SES active displayed to business accounts users in their email setting?"

**Answer:** Business account users see AWS SES status in THREE ways:

**1. Status Banner (Most Prominent):**
```
✓ VOÏA-Managed Email Delivery Active
Using verified domain: yourdomain.com
```
- Green background
- Top of Email Delivery Configuration page
- Shows immediately upon page load

**2. Radio Button Selection:**
```
● VOÏA-Managed Email Delivery  ← Filled circle indicates active
○ Client-Managed Email Delivery
```
- Selected radio button shows active mode
- Visual indicator of current configuration

**3. Dropdown Selection:**
```
Selected Domain: yourdomain.com [Verified ✓]
```
- Shows which domain is actively configured
- Green badge indicates verification status

**What Business Accounts DON'T See:**
- AWS credentials (hidden)
- "Manage Domains" button (platform admin only)
- Unverified or other accounts' domains
- Platform-wide AWS configuration

---

## Recommendations

### For Platform Administrators

1. **Document who has platform admin access**
   - Maintain list of platform administrators
   - Review access quarterly
   - Use principle of least privilege

2. **Communicate domain verification process**
   - Provide clear instructions to business accounts
   - Document DKIM record setup steps
   - Offer support during verification

3. **Monitor email configuration status**
   - Track which business accounts use VOÏA-managed
   - Monitor domain verification status
   - Alert on failed email deliveries

### For Business Account Users

1. **Check your email configuration regularly**
   - Navigate to Settings → Email Delivery Configuration
   - Verify status banner shows active configuration
   - Test email sending periodically

2. **Request domains from platform admin**
   - Contact platform administrator to add new domains
   - Provide domain name and access to DNS settings
   - Follow DKIM record setup instructions

3. **Understand your email mode**
   - Know whether you're using VOÏA-managed or Client-managed
   - Understand implications of each mode
   - Document your configuration

---

## Conclusion

**Bug #1 Status:** ✅ **NOT A BUG** - Working as designed
- "Manage Domains" requires platform admin privileges
- Access control is intentional for security
- Verify your user role to gain access

**AWS SES Display:** ✅ **CLEARLY VISIBLE** to business accounts
- Status banner at top of page (green with checkmark)
- Radio button selection shows active mode
- Domain dropdown shows verified domains
- Business accounts see what they need without AWS credentials

**No issues found.** Both features are working correctly as designed.
