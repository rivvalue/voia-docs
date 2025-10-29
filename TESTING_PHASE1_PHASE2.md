# Testing Guide: Phase 1 & 2 - Platform Email Settings

## ✅ Phase 1: Database Schema - VERIFIED

### Database Schema Verification
All database changes have been verified:
- ✅ `platform_email_settings` table created with all required columns
- ✅ `email_configurations` table extended with 11 new columns
- ✅ Existing email configurations preserved (3 records found)
- ✅ Default values set correctly (`use_platform_email=false`, `domain_verified=false`)

---

## 🧪 Phase 2: Platform Email Settings UI Testing

### Pre-requisites
1. **Platform Admin Access Required**
   - You need a business account user with `is_platform_admin=True`
   - To check/create platform admin:
   ```sql
   -- Check existing platform admins
   SELECT id, email, first_name, last_name, is_platform_admin 
   FROM business_account_users 
   WHERE is_platform_admin = true;
   
   -- OR create a platform admin (replace ID with your user)
   UPDATE business_account_users 
   SET is_platform_admin = true 
   WHERE id = 1;  -- Change to your user ID
   ```

2. **Login to Business Account**
   - Go to `/business/login`
   - Use platform admin credentials

---

### Test 1: Access Control (Security) 🔒

**Objective:** Verify only platform admins can access the page

**Steps:**
1. Login as a **regular business user** (not platform admin)
2. Try to access: `/business/admin/platform-email-settings`
3. **Expected Result:** Should be redirected or see access denied

4. Login as a **platform admin**
5. Access: `/business/admin/platform-email-settings`
6. **Expected Result:** Page loads successfully with the configuration form

**SQL to test with regular user:**
```sql
-- Temporarily remove platform admin status
UPDATE business_account_users 
SET is_platform_admin = false 
WHERE id = 1;  -- Your test user

-- Then restore it
UPDATE business_account_users 
SET is_platform_admin = true 
WHERE id = 1;
```

---

### Test 2: UI/UX Verification ✨

**Objective:** Verify Settings Hub v2 design patterns

**Steps:**
1. Navigate to `/business/admin/platform-email-settings`
2. **Visual Checks:**
   - ✅ Red gradient header with white text
   - ✅ Platform Administrator badge visible
   - ✅ Breadcrumb navigation (Settings → Platform Email Settings)
   - ✅ Info box explaining VOÏA-managed email delivery
   - ✅ Status indicator showing "No platform email configuration found"
   - ✅ Form fields properly styled (Settings Hub v2 patterns)
   - ✅ Test Connection button is disabled (no config yet)
   - ✅ Cancel and Save buttons visible

3. **Responsive Check:**
   - Resize browser to mobile size
   - Verify form remains usable on small screens

---

### Test 3: Save Platform Email Settings 💾

**Objective:** Verify configuration can be saved and encrypted properly

**Steps:**
1. Fill out the form:
   - **AWS Region:** `us-east-1`
   - **SMTP Server:** `email-smtp.us-east-1.amazonaws.com`
   - **SMTP Port:** `587`
   - **SMTP Username:** `test-username` (dummy for testing)
   - **SMTP Password:** `test-password` (dummy for testing)
   - **Use TLS:** Checked
   - **Use SSL:** Unchecked

2. Click "Save Configuration"

3. **Expected Results:**
   - ✅ Success message: "Platform email settings saved successfully"
   - ✅ Status changes to "exists but not verified"
   - ✅ Test Connection button becomes enabled
   - ✅ Password field shows "(leave blank to keep current)"

4. **Verify in Database:**
```sql
SELECT 
    aws_region,
    smtp_server,
    smtp_port,
    smtp_username,
    length(smtp_password_encrypted) as password_encrypted_length,
    use_tls,
    use_ssl,
    is_verified,
    configured_at,
    updated_at
FROM platform_email_settings;
```

**Expected Database State:**
- Password should be encrypted (length > 50 characters)
- `is_verified = false`
- `configured_at` and `updated_at` timestamps present

---

### Test 4: Password Encryption Verification 🔐

**Objective:** Verify password encryption/decryption works

**Python Test (run in Python console or create test script):**
```python
from models import PlatformEmailSettings
from app import app, db

with app.app_context():
    # Get platform settings
    settings = PlatformEmailSettings.query.first()
    
    # Test decryption
    decrypted = settings.get_smtp_password()
    print(f"Decrypted password: {decrypted}")
    
    # Verify it matches what you entered
    assert decrypted == "test-password", "Password decryption failed!"
    print("✅ Password encryption/decryption working correctly")
```

---

### Test 5: Update Without Password Change 🔄

**Objective:** Verify you can update other fields without re-entering password

**Steps:**
1. Go back to `/business/admin/platform-email-settings`
2. Change AWS Region to `us-west-2`
3. Leave password field **blank**
4. Click "Save Configuration"

5. **Expected Results:**
   - ✅ Settings saved successfully
   - ✅ AWS region updated to `us-west-2`
   - ✅ Password remains unchanged (still decrypts to `test-password`)

6. **Verify in Database:**
```sql
SELECT aws_region FROM platform_email_settings;
-- Should show: us-west-2
```

---

### Test 6: Test Connection (Will Fail - Expected) ⚠️

**Objective:** Verify connection testing works (expected to fail with dummy credentials)

**Steps:**
1. Click "Test Connection" button
2. **Expected Results:**
   - ✅ Button shows "Testing..." with spinner
   - ✅ Modal appears with error message
   - ✅ Error message indicates authentication failure or connection error
   - ✅ Troubleshooting tips displayed in modal
   - ✅ `is_verified` remains `false` in database

**Note:** This will fail because we're using dummy credentials. In production, you'd use real AWS SES credentials.

---

### Test 7: Audit Logging Verification 📝

**Objective:** Verify all actions are audit logged

**Check Audit Logs:**
```sql
SELECT 
    action_type,
    resource_type,
    resource_id,
    user_name,
    details,
    created_at
FROM audit_logs
WHERE resource_type = 'platform_email_settings'
ORDER BY created_at DESC
LIMIT 10;
```

**Expected Entries:**
- `platform_email_settings_update` (when saving config)
- `platform_email_settings_test` (when testing connection)

---

## 🔄 Non-Regression Testing

### Test 8: Existing Email Configuration Still Works

**Objective:** Verify business account email config page is not broken

**Steps:**
1. Go to `/business/admin/email-config`
2. **Expected Results:**
   - ✅ Page loads without errors
   - ✅ Existing email configurations display correctly
   - ✅ Can still save/update business-specific SMTP settings
   - ✅ Test connection still works for business accounts
   - ✅ No new fields visible yet (VOÏA-managed mode UI comes in Phase 4)

**SQL Check:**
```sql
-- Verify existing business email configs still exist
SELECT 
    business_account_id,
    email_provider,
    smtp_server,
    is_verified,
    use_platform_email  -- Should be false for all existing configs
FROM email_configurations;
```

---

### Test 9: Model Methods Work Correctly

**Python Test:**
```python
from models import PlatformEmailSettings, EmailConfiguration
from app import app, db

with app.app_context():
    # Test PlatformEmailSettings encryption
    platform = PlatformEmailSettings.query.first()
    if platform:
        pwd = platform.get_smtp_password()
        print(f"✅ PlatformEmailSettings password decryption works: {pwd is not None}")
    
    # Test EmailConfiguration still works
    email_config = EmailConfiguration.query.first()
    if email_config:
        # Test existing encryption methods
        if email_config.smtp_password_encrypted:
            pwd = email_config.get_smtp_password()
            print(f"✅ EmailConfiguration password decryption works: {pwd is not None}")
        
        # Test new fields have defaults
        print(f"✅ use_platform_email default: {email_config.use_platform_email}")
        print(f"✅ domain_verified default: {email_config.domain_verified}")
```

---

### Test 10: Application Startup

**Objective:** Verify application starts without errors

**Check Logs:**
```bash
# Check for errors in startup
grep -i "error\|exception\|traceback" /tmp/logs/Start_application_*.log

# Should see clean startup with:
# - Database validation passed
# - Task queue initialized
# - No import errors
```

---

## 📋 Test Results Checklist

Copy this checklist to track your testing:

### Phase 1: Database
- [x] platform_email_settings table exists
- [x] email_configurations new columns exist  
- [x] Existing data preserved
- [x] Default values correct

### Phase 2: Functionality
- [ ] Access control works (platform admin only)
- [ ] UI follows Settings Hub v2 design
- [ ] Can save platform email settings
- [ ] Password encryption works
- [ ] Can update without changing password
- [ ] Test connection button works (fails as expected with dummy data)
- [ ] Audit logging captures all actions

### Non-Regression
- [ ] Business email config page still works
- [ ] Existing email configurations functional
- [ ] Model methods work correctly
- [ ] Application starts without errors

---

## 🐛 Common Issues & Solutions

### Issue: "Platform Administrator Only" Access Denied

**Solution:**
```sql
-- Grant platform admin status
UPDATE business_account_users 
SET is_platform_admin = true 
WHERE email = 'your-email@example.com';
```

### Issue: Password Decryption Fails

**Cause:** EMAIL_ENCRYPTION_KEY environment variable not set
**Solution:** The system falls back to SESSION_SECRET, which should work for development

### Issue: Template Not Found

**Cause:** Workflow not restarted after adding new template
**Solution:** Refresh the page or restart the workflow

---

## ✅ Success Criteria

Phase 1 & 2 are considered successful when:

1. ✅ All database schema changes are in place
2. ✅ Platform email settings page is accessible to platform admins only
3. ✅ Configuration can be saved and retrieved
4. ✅ Password encryption/decryption works correctly
5. ✅ Connection testing executes (even if it fails with dummy credentials)
6. ✅ Audit logging captures all actions
7. ✅ Existing business email configurations are not affected
8. ✅ Application runs without errors

---

## 🚀 Next Steps (Phase 3)

Once testing is complete, Phase 3 will add:
- Domain management UI for platform admins
- DKIM record entry forms
- Domain verification status tracking
- Multi-domain support per business account
