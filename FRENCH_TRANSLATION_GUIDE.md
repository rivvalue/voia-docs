# VOÏA French Translation Guide (10 Files)

## Overview
This guide explains how to translate the VOÏA platform to French using ChatGPT in 10 manageable parts.

**Total strings:** 2,161 (split into 10 files for ChatGPT compatibility)
**Estimated time:** 15-20 minutes with ChatGPT

---

## Why 10 Files?

The original JSON file (13,000 lines) is too large for ChatGPT's context window. We've split it into 10 smaller files that ChatGPT can easily handle.

---

## Files You Have

### Source Files (English - to translate):
1. `translate_part_01_templates.json` - 237 UI strings
2. `translate_part_02_templates.json` - 237 UI strings
3. `translate_part_03_templates.json` - 237 UI strings
4. `translate_part_04_templates.json` - 237 UI strings
5. `translate_part_05_templates.json` - 237 UI strings
6. `translate_part_06_templates.json` - 237 UI strings
7. `translate_part_07_templates.json` - 237 UI strings
8. `translate_part_08_templates.json` - 236 UI strings
9. `translate_part_09_flash_messages.json` - 259 flash messages
10. `translate_part_10_email_templates.json` - 7 email templates

### Helper Scripts:
- `split_translation_files.py` - Already run (created the 10 files above)
- `integrate_translations.py` - Combines all translations back into code
- `CHATGPT_TRANSLATION_PROMPT.txt` - Prompt template to use

---

## Step-by-Step Translation Process

### Step 1: Prepare ChatGPT Prompt

Open `CHATGPT_TRANSLATION_PROMPT.txt` and copy the main prompt (you'll use it 10 times).

### Step 2: Translate Each File (Repeat 10 Times)

For each file from 01 to 10:

1. **Open** `translate_part_01_templates.json`
2. **Copy** ALL contents (Ctrl+A, Ctrl+C)
3. **Go to ChatGPT** (GPT-4 recommended)
4. **Paste** the prompt from `CHATGPT_TRANSLATION_PROMPT.txt`
5. **Add** the JSON content after the prompt
6. **Send** to ChatGPT
7. **Wait** 10-20 seconds for translation
8. **Copy** ChatGPT's response (the translated JSON)
9. **Save** as `translated_part_01.json` (note: remove "_templates" from filename)

**Repeat for all 10 files:**
- `translate_part_01_templates.json` → `translated_part_01.json`
- `translate_part_02_templates.json` → `translated_part_02.json`
- `translate_part_03_templates.json` → `translated_part_03.json`
- ... and so on through part 10

### Step 3: Verify You Have All 10 Translated Files

Check your directory has:
```
✓ translated_part_01.json
✓ translated_part_02.json
✓ translated_part_03.json
✓ translated_part_04.json
✓ translated_part_05.json
✓ translated_part_06.json
✓ translated_part_07.json
✓ translated_part_08.json
✓ translated_part_09.json
✓ translated_part_10.json
```

### Step 4: Integrate All Translations

Run the integration script:

```bash
python integrate_translations.py
```

This will:
- ✅ Load all 10 translated files
- ✅ Merge them together
- ✅ Replace English text in all HTML templates
- ✅ Update flash messages in Python files
- ✅ Translate email templates

### Step 5: Test the Platform

1. Restart the application
2. Navigate through key pages
3. Check translations display correctly
4. Verify variables work (e.g., {campaign_name} shows actual names)

---

## Quick Reference: ChatGPT Prompt

```
I need you to translate a JSON file from English to professional French (France market).

RULES:
1. Translate ONLY the "text" field values
2. Keep {variables}, {{variables}}, {%...%} EXACTLY as-is
3. Use formal "vous", professional tone
4. Keep unchanged: VOÏA, NPS, API

SUGGESTED TRANSLATIONS:
- Campaign → Campagne
- Participant → Participant
- Survey → Enquête
- Dashboard → Tableau de bord
- Feedback → Retour d'information

[PASTE translate_part_XX.json HERE]
```

---

## Timeline

| Task | Time per File | Total Time |
|------|---------------|------------|
| Copy JSON | 10 sec | 2 min |
| ChatGPT translate | 20 sec | 3 min |
| Save result | 10 sec | 2 min |
| **Subtotal (10 files)** | | **~7 min** |
| Integration | | 30 sec |
| Testing & fixes | | 1-2 hours |
| **GRAND TOTAL** | | **~2 hours** |

---

## Troubleshooting

### "I don't have all 10 files!"

Run the split script again:
```bash
python split_translation_files.py
```

### "ChatGPT still says the file is too big!"

- Make sure you're using GPT-4 or GPT-4 Turbo (not GPT-3.5)
- Each file should be ~1,000-1,500 lines max
- Try breaking that specific part in half manually

### "Integration script says files are missing"

Check your translated files are named correctly:
- ✅ `translated_part_01.json` (correct)
- ❌ `translate_part_01.json` (wrong - this is the English version)
- ❌ `translated_part_01_templates.json` (wrong - remove "_templates")

### "Some translations look weird in context"

1. Find the awkward text in one of the `translated_part_XX.json` files
2. Edit the "text" field to better French
3. Re-run `python integrate_translations.py`
4. Test again

### "Variables are broken!"

Check the translated JSON - variables must keep exact syntax:
- ✅ `{campaign_name}` (correct)
- ❌ `{nom_de_campagne}` (wrong - ChatGPT translated the variable name)

Find and fix in the translated JSON, then re-integrate.

---

## File Breakdown

| File | Content | Strings |
|------|---------|---------|
| Part 01 | Templates: test_token, survey_choice, survey forms | 237 |
| Part 02 | Templates: dashboard, analytics | 237 |
| Part 03 | Templates: campaign insights, business auth | 237 |
| Part 04 | Templates: admin panels, settings | 237 |
| Part 05 | Templates: email config, brand config | 237 |
| Part 06 | Templates: licenses, onboarding | 237 |
| Part 07 | Templates: participants, campaigns | 237 |
| Part 08 | Templates: responses, components | 236 |
| Part 09 | Flash messages from all Python files | 259 |
| Part 10 | Email templates (invitations, reminders) | 7 |

---

## Summary Checklist

- [x] Split large JSON into 10 files (DONE)
- [ ] Translate part 01 with ChatGPT → save as `translated_part_01.json`
- [ ] Translate part 02 with ChatGPT → save as `translated_part_02.json`
- [ ] Translate part 03 with ChatGPT → save as `translated_part_03.json`
- [ ] Translate part 04 with ChatGPT → save as `translated_part_04.json`
- [ ] Translate part 05 with ChatGPT → save as `translated_part_05.json`
- [ ] Translate part 06 with ChatGPT → save as `translated_part_06.json`
- [ ] Translate part 07 with ChatGPT → save as `translated_part_07.json`
- [ ] Translate part 08 with ChatGPT → save as `translated_part_08.json`
- [ ] Translate part 09 with ChatGPT → save as `translated_part_09.json`
- [ ] Translate part 10 with ChatGPT → save as `translated_part_10.json`
- [ ] Run `python integrate_translations.py`
- [ ] Test the platform
- [ ] Fix any issues
- [ ] Done! 🎉

---

## Need Help?

1. Check `CHATGPT_TRANSLATION_PROMPT.txt` for the exact prompt
2. Verify all 10 `translated_part_XX.json` files exist
3. Re-run integration script (safe to run multiple times)
4. Manually edit any problematic translations

---

**Ready?** Start with `translate_part_01_templates.json` and work through all 10 files!
