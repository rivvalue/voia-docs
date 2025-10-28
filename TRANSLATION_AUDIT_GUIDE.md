# VOÏA Translation Audit Guide

## Quick Start

### Run Basic Analysis
```bash
python check_missing_translations.py
```
Shows overall statistics and coverage percentage.

### Run Detailed Analysis
```bash
python check_missing_translations.py --detailed
```
Shows full lists of missing, fuzzy, and duplicate translations.

### Export to CSV for Manual Work
```bash
python check_missing_translations.py --detailed --csv
```
Creates `missing_translations.csv` in the translations directory.

### Check Different .po File
```bash
python check_missing_translations.py --file translations/en/LC_MESSAGES/messages.po
```

---

## Current Status (as of now)

**Translation Coverage: 92.8%** ✅

- **Total strings**: 1,097
- **Translated**: 1,018 (92.8%)
- **Missing**: 79 (7.2%)
- **Fuzzy**: 97 (needs review)
- **Duplicates**: 3 (causing compilation errors)

---

## What the Script Does

### ✅ READ-ONLY - NO MODIFICATIONS
This script **ONLY reads** and analyzes. It does **NOT** modify:
- HTML templates
- JavaScript files
- Python files
- .po files

It's a pure audit/reporting tool.

### Reports Generated

1. **Console Output**: Visual statistics with progress bar
2. **CSV Export**: `missing_translations.csv` with line numbers and missing strings
3. **Exit Code**: Returns 0 if complete, 1 if missing translations found

---

## Understanding the Output

### Untranslated Strings
```
❌ UNTRANSLATED STRINGS (79):
   1. Line 216 | VOÏA - Voice Of Client
```
These strings have empty `msgstr ""` or identical to English.

### Fuzzy Translations
```
⚠️  FUZZY TRANSLATIONS (97):
   1. Line 20 | Business account context not found.
```
Marked with `#, fuzzy` - may be outdated or uncertain. Review and update.

### Duplicate Entries
```
🔁 DUPLICATE ENTRIES (3):
   1. Line 5422 | Setup Complete!
```
Same `msgid` appears multiple times. **Causes compilation errors!**

---

## Fixing Issues

### Priority 1: Fix Duplicates (CRITICAL)
These break compilation. Remove duplicate entries manually from .po file.

**Current duplicates:**
- "Setup Complete!" (Lines 4444 & 5384)
- "Completed" (Lines 4967 & 5399)
- "Optional" (Lines 4107 & 5423)

### Priority 2: Translate Missing Strings
Use the CSV export to track manual translation work.

### Priority 3: Review Fuzzy Translations
Fuzzy strings work but may be outdated. Review and remove `#, fuzzy` marker when confident.

---

## Integration into Workflow

### Weekly Check (Recommended)
```bash
# Add to weekly checklist
python check_missing_translations.py --detailed
```

### Pre-Release Check
```bash
# Before deploying to production
python check_missing_translations.py
if [ $? -ne 0 ]; then
  echo "⚠️ Warning: Incomplete translations"
fi
```

### CI/CD Integration
```yaml
# .github/workflows/translation-check.yml
- name: Check Translation Coverage
  run: python check_missing_translations.py
  continue-on-error: true  # Warning only
```

---

## CSV Export Format

The exported `missing_translations.csv` contains:

| Line | Type | Original English | Current Translation | Status |
|------|------|-----------------|--------------------| -------|
| 216 | Untranslated | VOÏA - Voice Of Client | VOÏA - Voice Of Client | Untranslated |
| 282 | Untranslated | Campaign-specific performance... | | Untranslated |
| 5422 | Duplicate | Setup Complete! | | Duplicate |

Open in Excel/Google Sheets for easy tracking and manual translation work.

---

## Advanced Usage

### Check Multiple Languages
```bash
python check_missing_translations.py --file translations/fr/LC_MESSAGES/messages.po
python check_missing_translations.py --file translations/en/LC_MESSAGES/messages.po
```

### Automate Reports
```bash
# Daily automated check
0 9 * * * cd /path/to/voila && python check_missing_translations.py --csv > /tmp/translation_report.txt
```

---

## Next Steps

1. **Fix 3 duplicate entries** (breaks compilation)
2. **Translate 79 missing strings** (use CSV export)
3. **Review 97 fuzzy translations** (optional quality improvement)
4. **Set up weekly checks** (prevent regression)

---

## Support

For questions or issues with the script:
- Check script output for detailed error messages
- Verify .po file syntax is valid
- Ensure file encoding is UTF-8
