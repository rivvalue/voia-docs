# VOÏA French Translation Guide

## Overview
This guide explains how to translate the VOÏA platform to French using AI (ChatGPT/OpenAI) as your translator.

**Total strings to translate:** 2,161
- Templates (UI): 1,895 strings
- Flash messages: 259 strings  
- Email templates: 7 strings

**Estimated translation time:** 10-15 minutes with ChatGPT

---

## Files Created

| File | Purpose |
|------|---------|
| `extract_translations.py` | Python script that extracts all English strings from codebase |
| `voila_strings_to_translate.json` | JSON file with all English strings (ready for translation) |
| `CHATGPT_TRANSLATION_PROMPT.txt` | Copy-paste prompt template for ChatGPT |
| `integrate_translations.py` | Python script that integrates French translations back into code |
| `FRENCH_TRANSLATION_GUIDE.md` | This guide |

---

## Step-by-Step Translation Process

### Step 1: Get the Strings (ALREADY DONE ✓)
The extraction has already been completed. You have:
- ✅ `voila_strings_to_translate.json` - 2,161 strings ready for translation

### Step 2: Translate with ChatGPT

1. **Open `voila_strings_to_translate.json`** in a text editor
2. **Copy the ENTIRE contents** of the file (all ~13,000 lines)
3. **Open ChatGPT** (GPT-4 recommended, GPT-4 Turbo even better)
4. **Use this exact prompt:**

```
I need you to translate a JSON file containing English strings from a SaaS platform to professional French (France market).

**CRITICAL RULES:**

1. Translate ONLY the "text" field values - all other fields stay unchanged
2. Preserve all variables: {variable_name}, {{variable}}, {%...%}
   Example: "Welcome {name}" → "Bienvenue {name}" (NOT "Bienvenue {nom}")
3. Use professional business French (France, not Quebec)
4. Use formal "vous", not "tu"
5. Keep unchanged: VOÏA, NPS, API, technical terms in UPPERCASE
6. Return the COMPLETE JSON with only "text" values translated

**TERMINOLOGY:**
- Campaign → Campagne
- Participant → Participant  
- Survey → Enquête
- Dashboard → Tableau de bord
- Feedback → Retour d'information
- Business Account → Compte entreprise
- Insights → Analyses

[PASTE THE ENTIRE voila_strings_to_translate.json CONTENTS HERE]
```

5. **Send to ChatGPT**
6. **Wait 30-60 seconds** for ChatGPT to process
7. **Copy the entire response** (it will be JSON with French translations)
8. **Save as `voila_strings_translated.json`** in the same directory

### Step 3: Integrate Translations

Run the integration script:

```bash
python integrate_translations.py
```

This will automatically:
- ✅ Replace English text in all 58 HTML templates
- ✅ Update 259 flash messages in Python files
- ✅ Translate 7 email templates in `email_service.py`

### Step 4: Test the Platform

1. **Restart the application**
2. **Test key pages:**
   - Login page
   - Dashboard
   - Campaign creation
   - Participant management  
   - Email previews
3. **Check for:**
   - Proper French text display
   - No broken layouts
   - Variables still work (e.g., {campaign_name} shows actual name)
   - Buttons and forms function correctly

---

## Sample Translations

| English | French |
|---------|--------|
| Dashboard | Tableau de bord |
| Create New Campaign | Créer une nouvelle campagne |
| Participants | Participants |
| Business Intelligence | Intelligence d'affaires |
| Settings | Paramètres |
| Your feedback is requested | Votre retour d'information est demandé |
| Complete Your Survey | Complétez votre enquête |
| Campaign created successfully! | Campagne créée avec succès ! |
| Invalid email address | Adresse e-mail invalide |

---

## Troubleshooting

### ChatGPT says "JSON too large"
**Solution:** Split the JSON into 2-3 smaller parts:
1. Extract just `templates` section → translate → save as `part1.json`
2. Extract just `flash_messages` section → translate → save as `part2.json`
3. Extract just `email_templates` section → translate → save as `part3.json`
4. Manually combine all parts back into one `voila_strings_translated.json`

### Some translations look awkward
**Solution:** You can manually edit `voila_strings_translated.json` before running integration:
1. Open `voila_strings_translated.json`
2. Search for the awkward French text
3. Edit the "text" field to better French
4. Save and run `python integrate_translations.py` again

### Variables are broken (showing {campaign_name} instead of actual name)
**Problem:** ChatGPT accidentally modified the variable syntax

**Solution:**
1. Check `voila_strings_translated.json`
2. Find strings with `{campaign_name}`, `{business_account_name}`, etc.
3. Ensure they still have curly braces exactly as in English
4. Example: `"{campaign_name}"` should NOT become `"{nom_de_campagne}"`

### Layout is broken after translation
**Cause:** French text is longer than English (typically 15-20% longer)

**Solutions:**
- Adjust CSS padding/margins
- Use shorter French alternatives for buttons/labels
- Add `white-space: nowrap` for cramped buttons

---

## Advanced: Re-extracting Strings

If you add new features and need to extract new strings:

```bash
python extract_translations.py
```

This will regenerate `voila_strings_to_translate.json` with all current strings.

---

## Key Translation Principles

1. **Consistency:** Use the same French term throughout
   - Good: Always "campagne" for "campaign"
   - Bad: Mix "campagne", "initiative", "projet"

2. **Formality:** Always use "vous" (formal you)
   - Good: "Créez votre compte"
   - Bad: "Crée ton compte"

3. **Preserve Technical Terms:**
   - Keep: NPS, API, OAuth, JSON, CSV
   - Translate: user → utilisateur, password → mot de passe

4. **Variable Safety:**
   - Good: "Bienvenue {name}"
   - Bad: "Bienvenue {nom}" (breaks the code!)

---

## Summary Checklist

- [ ] Extract strings (DONE ✓)
- [ ] Open ChatGPT (GPT-4)
- [ ] Paste prompt + JSON content
- [ ] Get French translation
- [ ] Save as `voila_strings_translated.json`
- [ ] Run `python integrate_translations.py`
- [ ] Test the platform
- [ ] Fix any layout issues
- [ ] Review translations in context
- [ ] Done! 🎉

---

## Timeline

| Task | Time |
|------|------|
| Prepare ChatGPT prompt | 2 min |
| ChatGPT translation | 1 min |
| Integration script | 30 sec |
| Testing & fixes | 1-2 hours |
| **TOTAL** | **~2 hours** |

---

## Questions?

If you encounter issues:
1. Check this guide first
2. Review the Troubleshooting section
3. Manually edit `voila_strings_translated.json` if needed
4. Re-run integration script as many times as needed (it's safe to re-run)
