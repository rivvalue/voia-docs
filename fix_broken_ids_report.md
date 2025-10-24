# Broken ID Attributes - Verification Report

## Executive Summary
- **Total Broken IDs Found**: 12
- **JavaScript References Found**: 9 matches
- **Critical Impact**: Dashboard KPIs and modals broken in French

---

## Broken IDs in Template (dashboard.html)

### 🔴 CRITICAL - Used by JavaScript (Must Fix)

| Line | Template ID | Expected JS ID | Impact |
|------|-------------|----------------|--------|
| 398 | `total{{ _('Responses') }}` | `totalResponses` | ✅ **KPI value not updating** |
| 405 | `recent{{ _('Responses') }}` | `recentResponses` | ✅ **KPI value not updating** |
| 879 | `company{{ _('Responses') }}Modal` | `companyResponsesModal` | ✅ **Modal won't open** |
| 923 | `company{{ _('Responses') }}Loading` | `companyResponsesLoading` | ✅ **Loading state broken** |
| 931 | `company{{ _('Responses') }}Content` | `companyResponsesContent` | ✅ **Content won't display** |
| 943 | `company{{ _('Responses') }}TableBody` | `companyResponsesTableBody` | ✅ **Table won't populate** |
| 952 | `company{{ _('Responses') }}PaginationInfo` | `companyResponsesPaginationInfo` | ✅ **Pagination broken** |
| 955 | `company{{ _('Responses') }}Pagination` | `companyResponsesPagination` | ✅ **Pagination broken** |
| 963 | `company{{ _('Responses') }}NoData` | `companyResponsesNoData` | ✅ **No data message broken** |

**JavaScript References (dashboard.js)**:
```javascript
Line 1224: document.getElementById('totalResponses').textContent = ...
Line 1226: document.getElementById('recentResponses').textContent = ...
Line 4118: new bootstrap.Modal(document.getElementById('companyResponsesModal'))
Line 4129: document.getElementById('companyResponsesLoading').style.display = ...
Line 4130: document.getElementById('companyResponsesContent').style.display = ...
Line 4181: document.getElementById('companyResponsesTableBody')
Line 4273: document.getElementById('companyResponsesPaginationInfo').textContent = ...
Line 4277: document.getElementById('companyResponsesPagination')
Line 4131: document.getElementById('companyResponsesNoData').style.display = ...
```

---

### ⚠️ LOW PRIORITY - Not Used by JavaScript (Cosmetic)

| Line | Template ID | Status |
|------|-------------|--------|
| 400 | `total{{ _('Responses') }}Trend` | No JS reference found |
| 407 | `recent{{ _('Responses') }}Trend` | No JS reference found |
| 884 | `company{{ _('Responses') }}ModalLabel` | Used by Bootstrap aria-labelledby (auto-lookup) |

**Note**: These should still be fixed for consistency and future-proofing.

---

## aria-label Attributes (Safe - Should Keep Translation)

| Line | Attribute | Status |
|------|-----------|--------|
| 72-114 | `title="{{ _('Click to view full trends') }}"` | ✅ Keep - Accessibility text |
| 262 | `aria-label="{{ _('Comparison table pagination') }}"` | ✅ Keep - Screen reader text |
| 541 | `aria-label="{{ _('Account Intelligence pagination') }}"` | ✅ Keep - Screen reader text |
| 716 | `aria-label="{{ _('Company NPS pagination') }}"` | ✅ Keep - Screen reader text |
| 772 | `aria-label="{{ _('Tenure NPS pagination') }}"` | ✅ Keep - Screen reader text |
| 858 | `aria-label="{{ _('Survey responses pagination') }}"` | ✅ Keep - Screen reader text |
| 896 | `aria-label="{{ _('Close') }}"` | ✅ Keep - Screen reader text |

---

## What Happens in French?

**Current Broken Behavior**:
```html
<!-- English -->
<div id="totalResponses">0</div>  ✅ JavaScript finds it

<!-- French -->
<div id="totalRéponses">0</div>   ❌ JavaScript looks for "totalResponses", finds nothing
```

**After Fix**:
```html
<!-- English -->
<div id="totalResponses">{{ _('Total Responses') }}</div>  ✅ Works

<!-- French -->
<div id="totalResponses">{{ _('Total Responses') }}</div>  ✅ Works (ID stays English, content translates)
```

---

## Summary

✅ **9 Critical IDs** must be fixed (break JavaScript functionality)  
⚠️ **3 Low-priority IDs** should be fixed (consistency)  
✅ **7 aria-label attributes** are correct (should translate)

**Total fixes required**: 12 ID attributes
