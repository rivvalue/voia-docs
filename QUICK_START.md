# 🚀 Quick Start - French Translation in 10 Files

## What You Have

**10 small JSON files** ready for ChatGPT (instead of 1 huge file):
- Parts 01-08: UI templates (~237 strings each)
- Part 09: Flash messages (259 strings)
- Part 10: Email templates (7 strings)

---

## Translate in 3 Steps

### 1️⃣ For Each File (Repeat 10x)

Open ChatGPT and use this prompt:

```
Translate this JSON to professional French (France).
RULES: Translate ONLY "text" values. Keep {variables} unchanged. Use "vous". Keep VOÏA, NPS, API unchanged.

[PASTE translate_part_XX.json HERE]
```

**File workflow:**
1. `translate_part_01_templates.json` → ChatGPT → Save as `translated_part_01.json`
2. `translate_part_02_templates.json` → ChatGPT → Save as `translated_part_02.json`
3. ... repeat through part 10

**⚠️ Important:** Remove "_templates" from filename when saving!

### 2️⃣ Integrate

```bash
python integrate_translations.py
```

### 3️⃣ Test

Restart app and check French text displays correctly.

---

## Files Checklist

After ChatGPT translation, you should have:

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

---

## Common Issues

**"ChatGPT says too big"**
→ Use GPT-4, not GPT-3.5

**"Integration says missing files"**
→ Check names: `translated_part_01.json` not `translate_part_01.json`

**"Variables broken"**
→ Make sure `{campaign_name}` stays `{campaign_name}` (not `{nom_de_campagne}`)

---

## Full Guide

See `FRENCH_TRANSLATION_GUIDE.md` for complete instructions.

---

⏱️ **Time:** ~15 minutes for ChatGPT + 2 minutes integration = **Ready in 20 minutes!**
