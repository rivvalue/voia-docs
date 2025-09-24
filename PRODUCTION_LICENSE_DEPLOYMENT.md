# Production License Deployment Guide

## Overview

This guide provides step-by-step instructions for setting up the VOÏA license system in production environment using **Option 1: Manual License Recreation**. This approach ensures clean license initialization without development data contamination.

## Prerequisites

### Environment Requirements
- Production VOÏA application deployed and running
- PostgreSQL database accessible
- Python 3.x environment with project dependencies
- Flask application context available

### Required Components
The license system includes these components (automatically available in production deployment):
- `license_templates.py` - License template definitions (Core, Plus, Pro, Trial)
- `license_service.py` - License management service layer
- `models.py` - Database models including LicenseHistory and BusinessAccount
- Database tables: `business_accounts`, `license_history`, `license_usage_snapshots`

## Deployment Process

### Step 1: Validate Environment

First, run the setup script in **dry-run mode** to validate the production environment:

```bash
python3 production_license_setup_fixed.py --dry-run --verbose
```

**Expected Output:**
```
✅ Database connection validated
✅ Table business_accounts exists
✅ Table license_history exists
✅ Available license templates: [Core, Plus, Pro, Trial]
```

If validation fails, resolve issues before proceeding.

### Step 2: Execute Production Setup

Run the script in production mode to create business accounts and assign licenses:

```bash
python3 production_license_setup_fixed.py --verbose
```

**What This Creates:**

#### Business Accounts:
1. **Rivvalue Inc** (premium account)
   - Contact: admin@rivvalue.com
   - Industry: Technology Consulting
   - Status: Active

2. **Demo Account** (demo account)
   - Contact: demo@voia.com
   - Industry: Various
   - Status: Active

#### License Assignments:
1. **Rivvalue Inc → Pro License**
   - 50 campaigns/year
   - 100 users maximum
   - 50,000 participants/campaign
   - 24-month duration
   - Enhanced enterprise limits

2. **Demo Account → Trial License**
   - 1 campaign/year
   - 2 users maximum
   - 50 participants/campaign
   - 1-month duration
   - Basic trial features

### Step 3: Validation

The script automatically validates the setup by:
- Testing license lookup functionality
- Verifying license period calculations  
- Confirming usage limit enforcement
- Validating comprehensive license information retrieval

## License Templates Available

### Core License
- **Campaigns**: 4/year
- **Users**: 5 maximum
- **Participants**: 200/campaign
- **Duration**: 12 months
- **Features**: Basic Analytics, Email Support, Standard Templates

### Plus License
- **Campaigns**: 4/year
- **Users**: 10 maximum
- **Participants**: 2,000/campaign
- **Duration**: 12 months
- **Features**: Advanced Analytics, Priority Support, Custom Templates, API Access

### Pro License (Customizable)
- **Campaigns**: Customizable (default 12/year)
- **Users**: Customizable (default 25)
- **Participants**: Customizable (default 10,000/campaign)
- **Duration**: Customizable (default 12 months)
- **Features**: Custom Analytics, Dedicated Support, White Label, Custom Integrations, SLA Guarantee

### Trial License
- **Campaigns**: 1/year
- **Users**: 2 maximum
- **Participants**: 50/campaign
- **Duration**: 1 month
- **Features**: Basic Features, Limited Support

## Post-Deployment Operations

### Adding New Business Accounts

```python
from app import app, db
from models import BusinessAccount
from license_service import LicenseService

with app.app_context():
    # Create business account
    account = BusinessAccount()
    account.name = "Customer Name"
    account.account_type = "customer"
    account.contact_email = "admin@customer.com"
    account.status = "active"
    db.session.add(account)
    db.session.commit()
    
    # Assign license
    success, license_record, message = LicenseService.assign_license_to_business(
        business_id=account.id,
        license_type="plus",  # or "core", "pro", "trial"
        created_by="admin"
    )
```

### Modifying License Limits

For Pro licenses with custom limits:

```python
from license_service import LicenseService

with app.app_context():
    custom_config = {
        'max_campaigns_per_year': 20,
        'max_users': 50,
        'max_participants_per_campaign': 25000,
        'duration_months': 12
    }
    
    success, license_record, message = LicenseService.assign_license_to_business(
        business_id=account_id,
        license_type="pro",
        custom_config=custom_config,
        created_by="admin"
    )
```

### Monitoring License Usage

```python
from license_service import LicenseService

with app.app_context():
    # Get comprehensive license info
    license_info = LicenseService.get_license_info(account_id)
    
    print(f"License Type: {license_info['license_type']}")
    print(f"Campaigns Used: {license_info['campaigns_used']}/{license_info['campaigns_limit']}")
    print(f"Users: {license_info['users_used']}/{license_info['users_limit']}")
    print(f"Days Remaining: {license_info['days_remaining']}")
```

## Troubleshooting

### Common Issues

**1. Database Connection Failed**
- Verify DATABASE_URL environment variable
- Check database server accessibility
- Confirm database exists and tables are created

**2. License Template Not Found**
- Ensure license_templates.py is properly deployed
- Verify LicenseTemplateManager is accessible
- Check for import errors in license system

**3. License Assignment Failed** 
- Check business account exists and is active
- Verify license template is valid
- Review custom_config parameters for Pro licenses

### Validation Commands

Check license system health:
```python
from app import app
from license_service import LicenseService

with app.app_context():
    # Test license lookup
    license = LicenseService.get_current_license(account_id)
    print(f"Current license: {license.license_type if license else 'None'}")
    
    # Test usage limits
    can_activate = LicenseService.can_activate_campaign(account_id)
    can_add_user = LicenseService.can_add_user(account_id)
    print(f"Can activate campaign: {can_activate}")
    print(f"Can add user: {can_add_user}")
```

## Security Considerations

- License assignments are logged with creator information
- All license operations require Flask application context
- Database transactions ensure consistency
- License transitions are handled atomically

## Backup and Recovery

Before making license changes in production:
1. Backup the `license_history` table
2. Backup the `business_accounts` table
3. Test changes in staging environment first

## Support

For license system issues:
1. Check application logs for detailed error messages
2. Verify database table integrity
3. Ensure all license system components are deployed
4. Contact development team with specific error details

---

**Deployment Status**: Ready for production use  
**Last Updated**: September 24, 2025  
**Version**: 1.0