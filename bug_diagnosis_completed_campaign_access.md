# 🐛 BUG DIAGNOSIS: Completed Campaign Access

**Reported Issue**: Participant opens survey link after campaign has completed; VOÏA does not inform them that the campaign has ended.

**Severity**: **MEDIUM** - Affects user experience but does not cause data corruption or system failure

**Impact**: Participants see survey forms instead of a clear "campaign ended" message, leading to confusion and poor user experience.

---

## 📊 CURRENT BEHAVIOR (Diagnosis)

### **Token Verification Flow**

When a participant clicks their survey link, the system follows this flow:

1. **Route Handler** (`routes.py` - lines 704-757)
   - Receives token from URL: `/survey?token={jwt_token}`
   - Calls `verify_survey_access(token)` to validate access

2. **Token Verification** (`campaign_participant_token_system.py` - lines 94-160)
   - Decodes JWT token to extract `association_id`
   - Loads `CampaignParticipant` association from database
   - **CRITICAL CHECK** (lines 127-129):
     ```python
     if campaign.status not in ['ready', 'active']:
         return {'valid': False, 'error': f'Campaign is {campaign.status} and cannot accept responses'}
     ```
   - **For completed campaigns**: Returns `{'valid': False, 'error': 'Campaign is completed and cannot accept responses'}`

3. **Route Response** (`routes.py` - lines 732-739)
   ```python
   else:
       # Get default branding for unauthenticated users
       branding = get_branding_context()
       return render_template('survey_choice.html', 
                            authenticated=False, 
                            error=verification['error'],  # ✅ Error is passed
                            user_email=None,
                            branding=branding)
   ```

4. **Template Rendering** (`templates/survey_choice.html`)
   - **BUG LOCATION**: Template receives `error` variable but **NEVER displays it**
   - Shows survey choice cards (AI Conversational vs Traditional Form)
   - Participant sees survey options even though campaign is completed

---

## 🔍 ROOT CAUSE ANALYSIS

### **Primary Issue**: Template Does Not Display Error Messages

The `survey_choice.html` template has **NO error handling logic**:

```jinja2
<!-- Current template structure (simplified) -->
<div class="card">
    <div class="card-header">
        <h4>Welcome, {{ participant_name }}!</h4>
    </div>
    <div class="card-body">
        <!-- Shows survey options -->
        <!-- NO check for {{ error }} variable -->
    </div>
</div>
```

**What happens**:
1. ✅ Backend correctly detects campaign is completed
2. ✅ Backend correctly sets `error` in response
3. ❌ Frontend ignores the `error` variable completely
4. ❌ Participant sees normal survey interface

---

## 🎯 AFFECTED USER JOURNEYS

### **Scenario 1: Late Responder (Most Common)**
- **Timeline**: Campaign runs Jan 1-31, closes Feb 1
- **Participant**: Receives invitation Jan 15, busy with work
- **Access Attempt**: Opens link Feb 5 (4 days after campaign closed)
- **Current Experience**: Sees survey form, attempts to start, gets confused
- **Expected Experience**: Clear message: "This campaign ended on Feb 1. Thank you for your interest."

### **Scenario 2: Email Delay**
- **Timeline**: Campaign closes at 11:59 PM
- **Participant**: Email arrives in their inbox at 11:50 PM due to email server delays
- **Access Attempt**: Opens link 15 minutes later (after midnight)
- **Current Experience**: Sees survey form with no explanation
- **Expected Experience**: "This campaign has just ended. We appreciate your willingness to participate."

### **Scenario 3: Forwarded Link**
- **Timeline**: Campaign completed 2 months ago
- **Participant**: Another team member forwarded them the link
- **Access Attempt**: Opens archived link
- **Current Experience**: Sees survey, tries to submit, gets backend error
- **Expected Experience**: "This campaign is no longer active. Please contact [company] for current feedback opportunities."

### **Scenario 4: Already Responded**
- **Current Handling**: ✅ **WORKS CORRECTLY** (line 132-133)
  ```python
  if association.status == 'completed':
      return {'valid': False, 'error': 'Survey has already been completed for this campaign'}
  ```
- This error is also not displayed in the template

---

## 🏗️ SYSTEM ARCHITECTURE REVIEW

### **Campaign Status Lifecycle**

```
draft → ready → active → completed
  ↓       ↓       ↓         ↓
  ❌     ✅      ✅        ❌  (Survey access allowed)
```

**Status Definitions** (`models.py` - line 191):
- `draft`: Campaign being configured (not accepting responses)
- `ready`: Campaign scheduled but not yet started (may accept early responses)
- `active`: Campaign in progress (accepting responses)
- `completed`: Campaign closed via `close_campaign()` method (should reject responses)

**Campaign Completion Triggers** (`models.py` - lines 447-492):
```python
def close_campaign(self):
    """Mark campaign as completed and generate KPI snapshot"""
    self.status = 'completed'
    self.completed_at = datetime.utcnow()
    # Generates KPI snapshot
    # Triggers executive report generation
```

### **Token Security Check Locations**

| Check Type | File | Lines | Current Behavior |
|------------|------|-------|------------------|
| **Campaign Status** | `campaign_participant_token_system.py` | 127-129 | ✅ Rejects completed campaigns |
| **Association Status** | `campaign_participant_token_system.py` | 132-133 | ✅ Rejects completed responses |
| **Token Expiration** | `campaign_participant_token_system.py` | 153-154 | ✅ Rejects expired tokens (72hr) |
| **Template Display** | `templates/survey_choice.html` | N/A | ❌ NO ERROR DISPLAY |

---

## 🔧 WHAT NEEDS TO CHANGE

### **Files Requiring Updates**

1. **`templates/survey_choice.html`** (Primary Fix)
   - Add error display logic
   - Show user-friendly "campaign ended" message
   - Hide survey form options when error is present

2. **`templates/survey.html`** (Secondary Fix)
   - Same error handling for traditional form route
   - Currently no error display

3. **`templates/conversational_survey_business.html`** (Secondary Fix)
   - Same error handling for conversational route
   - Currently no error display

4. **`campaign_participant_token_system.py`** (Enhancement)
   - Return more specific error codes (not just text)
   - Allow frontend to customize messages per error type

5. **Translation Files** (i18n Support)
   - Add French/English messages for all error scenarios

---

## 📋 BUSINESS ANALYST COLLABORATION

### **Questions for Business Decision-Making**

#### **Q1: Message Tone - What should participants see?**

**Option A: Empathetic & Apologetic**
> "We're sorry, but this feedback campaign ended on [DATE]. We truly value your input and apologize for any inconvenience. For questions, please contact [COMPANY]."

**Option B: Informative & Neutral**
> "This feedback campaign closed on [DATE]. Thank you for your interest in providing feedback."

**Option C: Encouraging & Forward-Looking**
> "This campaign has concluded, but your feedback still matters! Please contact [COMPANY] to share your thoughts or watch for our next campaign."

**Recommendation**: **Option A** - Balances professionalism with empathy, reduces frustration.

---

#### **Q2: Information Display - What details should we show?**

**Minimum Information**:
- ✅ Campaign has ended (status)
- ✅ Campaign name

**Additional Information (Optional)**:
- Campaign end date (when it closed)
- Campaign description/objective
- Contact information for follow-up questions
- Expected next campaign timeline (if known)
- Link to company website or support

**Recommendation**: Show **campaign name + end date + company contact info** (balanced detail level).

---

#### **Q3: Contact Options - How can participants reach out?**

**Option A: Generic Company Contact**
> "For questions, please contact [COMPANY_NAME]"

**Option B: Specific Campaign Manager Email**
> "For questions, contact [CAMPAIGN_MANAGER_EMAIL]"

**Option C: Support Ticket System**
> "Submit a question via our support portal: [LINK]"

**Option D: No Contact Info**
> Just inform them campaign ended, no follow-up option

**Recommendation**: **Option A or B** - Depends on business account preferences (configurable?).

---

#### **Q4: Multiple Error Types - How specific should messages be?**

**Error Types to Handle**:

| Error Type | Backend Message | Suggested User Message |
|------------|----------------|------------------------|
| **Campaign Completed** | `Campaign is completed and cannot accept responses` | "This campaign ended on [DATE]." |
| **Campaign Not Started** | `Campaign is ready and cannot accept responses` | "This campaign hasn't started yet. Please check back on [START_DATE]." |
| **Campaign Drafted** | `Campaign is draft and cannot accept responses` | "This campaign is not yet available. Please contact [COMPANY] for more information." |
| **Already Responded** | `Survey has already been completed for this campaign` | "Thank you! You already submitted your feedback for this campaign on [DATE]." |
| **Token Expired** | `Token has expired` | "This survey link has expired. Please contact [COMPANY] if you still wish to provide feedback." |
| **Invalid Token** | `Invalid token` | "This survey link is invalid. Please contact [COMPANY] for assistance." |

**Recommendation**: **Differentiate between top 4 errors** (Completed, Already Responded, Expired, Invalid).

---

#### **Q5: Branding Consistency - Should error page match survey branding?**

**Option A: Full Branding**
- Show company logo
- Use brand colors
- Include campaign name and description
- Consistent with normal survey experience

**Option B: Minimal Branding**
- Plain error message
- VOÏA branding only
- No campaign-specific context

**Recommendation**: **Option A** - Maintains professional brand experience even in error scenarios.

---

#### **Q6: Mobile Responsiveness - How should this look on mobile?**

**Considerations**:
- 40-60% of survey links are opened on mobile devices
- Error message should be immediately visible (above the fold)
- Avoid long text blocks on small screens
- Large, clear typography

**Recommendation**: **Mobile-first design** with icon + heading + concise message (< 50 words).

---

## 🎨 PROPOSED SOLUTION DESIGN

### **Error Display UI (High-Level)**

```
┌─────────────────────────────────────────┐
│  [COMPANY LOGO]                         │
│                                         │
│  ⚠️  Campaign Has Ended                 │
│                                         │
│  The "[CAMPAIGN NAME]" feedback         │
│  campaign closed on [END DATE].         │
│                                         │
│  Thank you for your interest in         │
│  providing feedback. We appreciate      │
│  your willingness to participate.       │
│                                         │
│  For questions, please contact:         │
│  [COMPANY NAME / EMAIL]                 │
│                                         │
│  ┌──────────────────────────┐          │
│  │  Return to Home Page     │          │
│  └──────────────────────────┘          │
└─────────────────────────────────────────┘
```

---

### **Implementation Complexity**

| Component | Complexity | Estimated Time | Risk Level |
|-----------|-----------|----------------|------------|
| **Template Error Display** | 🟢 Low | 1-2 hours | 🟢 Low |
| **Error Type Detection** | 🟢 Low | 30 min | 🟢 Low |
| **i18n Translation** | 🟡 Medium | 1 hour | 🟢 Low |
| **Branding Integration** | 🟢 Low | 30 min | 🟢 Low |
| **Mobile Responsiveness** | 🟢 Low | 30 min | 🟢 Low |
| **Testing (All Routes)** | 🟡 Medium | 2 hours | 🟡 Medium |
| **Total** | 🟢 **Low** | **~6 hours** | 🟢 **Low** |

---

## 🧪 TESTING REQUIREMENTS

### **Test Scenarios**

1. **Completed Campaign Access**
   - Create campaign → Activate → Close → Access survey link
   - Expected: Error page with "campaign ended" message

2. **Draft Campaign Access**
   - Create campaign (leave as draft) → Access survey link
   - Expected: Error page with "campaign not available" message

3. **Already Responded**
   - Complete survey → Try to access link again
   - Expected: Error page with "already responded" message

4. **Expired Token (72 hours)**
   - Generate token → Wait 72 hours → Access link
   - Expected: Error page with "link expired" message

5. **Invalid Token**
   - Access /survey?token=fake123
   - Expected: Error page with "invalid link" message

6. **Mobile Display**
   - Test all above scenarios on mobile viewport (375px width)
   - Expected: Readable, well-formatted error messages

7. **Bilingual Support**
   - Test all scenarios with French campaign (`language_code='fr'`)
   - Expected: Error messages in French

8. **Branding Consistency**
   - Test with business account that has custom logo/colors
   - Expected: Error page uses business branding

---

## 🚀 ROLLOUT STRATEGY

### **Phase 1: Core Fix (Minimum Viable)**
- Add error display to `survey_choice.html`
- Add error display to `conversational_survey_business.html`
- English-only messages
- Basic styling (Bootstrap alert component)
- **Deploy Immediately** (fixes critical UX issue)

### **Phase 2: Enhanced UX**
- Differentiate error types (completed vs expired vs invalid)
- Add bilingual support (French translations)
- Improve styling (brand colors, icons, better typography)
- Add company contact information
- **Deploy in 1 week**

### **Phase 3: Advanced Features**
- Configurable error messages per business account
- "Notify me for next campaign" signup form
- Redirect to company website option
- Analytics tracking (how many people access expired links)
- **Deploy in 2-4 weeks**

---

## 📝 DECISION LOG

### **Awaiting User Input On:**

1. ✋ **Message Tone**: Empathetic (Option A), Neutral (Option B), or Encouraging (Option C)?
2. ✋ **Information Level**: Minimal (name only) or Detailed (name + date + contact)?
3. ✋ **Contact Options**: Generic company, specific email, support portal, or none?
4. ✋ **Error Granularity**: Single "campaign ended" message or differentiate 4+ error types?
5. ✋ **Branding**: Full brand consistency or minimal/generic design?
6. ✋ **Rollout Phase**: Implement Phase 1 only (quick fix) or all 3 phases?

---

## 🎯 RECOMMENDED NEXT STEPS (Pending User Approval)

### **Immediate Actions (Do Not Implement Yet)**

1. **Business Decisions** (User Input Required)
   - Review Q1-Q6 above and provide guidance on tone, detail level, contact options
   - Approve error message templates
   - Confirm branding requirements

2. **Technical Design** (After Business Approval)
   - Design error page layout (wireframe/mockup)
   - Define error message structure (JSON schema)
   - Plan template refactoring approach

3. **Implementation** (After Design Approval)
   - Update 3 survey templates with error display logic
   - Add error type detection to token verification
   - Create translation keys for French support
   - Add CSS styling for error states

4. **Testing** (Before Production)
   - Execute 8 test scenarios listed above
   - Verify mobile responsiveness
   - Confirm bilingual support works
   - Test brand customization

5. **Deployment** (After Testing)
   - Deploy to production
   - Monitor error logs for campaign-ended access attempts
   - Gather user feedback on new error messages

---

## 📚 APPENDIX: Code References

### **Key Files for Implementation**

| File | Lines | Purpose |
|------|-------|---------|
| `campaign_participant_token_system.py` | 127-129 | Campaign status check |
| `campaign_participant_token_system.py` | 132-133 | Association completed check |
| `routes.py` | 704-757 | `/survey` route handler |
| `routes.py` | 759-819 | `/survey_form` route handler |
| `routes.py` | 2549-2640 | `/conversational_survey` route handler |
| `templates/survey_choice.html` | All | Template requiring error display |
| `templates/survey.html` | All | Traditional form template |
| `templates/conversational_survey_business.html` | All | Conversational template |
| `models.py` | 447-492 | `close_campaign()` method |
| `models.py` | 191 | Campaign status field definition |

---

**Status**: ⏸️ **DIAGNOSIS COMPLETE - AWAITING USER REVIEW & APPROVAL**

**Next Action**: User to review business questions (Q1-Q6) and provide guidance before implementation begins.
