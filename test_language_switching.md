# Language Switching Test Plan

## ✅ What I Fixed

1. **CSS z-index**: Language selector now appears above sidebar (z-index: 10003)
2. **Cache-busting**: Updated CSS version to force browser reload
3. **Translations**: Verified 94.3% coverage (706/749 strings)
   - "Campaigns" → "Campagnes" ✅
   - "Participants" → "Participants" ✅
   - Dashboard, forms, buttons, etc. all have French translations

## 🧪 How to Test Language Switching

### Step 1: Navigate to a Page
- Go to `/business/participants/` or `/business/campaigns/`
- You should see the language selector (🌐 icon) in the top-right navbar

### Step 2: Switch to French
1. **Click** the language dropdown (🌐 English)
2. **Select** "Français"
3. **Wait** for page reload
4. Page should now display in French

### Step 3: Verify Translation
**On Participants page, you should see:**
- ❌ "Participants" (same in French)
- ✅ "Add Participant" → "Ajouter un participant"
- ✅ "Company Name" → "Nom de l'entreprise"
- ✅ "Email" → "Courriel"
- ✅ "Actions" → "Actions"

**On Campaigns page, you should see:**
- ✅ "Campaigns" → "Campagnes"
- ✅ "Create Campaign" → "Créer une campagne"
- ✅ "Status" → "Statut"
- ✅ "Active" → "Active"

### Step 4: Hard Refresh (If Needed)
If you still see English after switching:
- **Windows/Linux**: `Ctrl + Shift + R`
- **Mac**: `Cmd + Shift + R`

## 🔍 Troubleshooting

**If language doesn't switch:**
1. Check browser console for errors (F12 → Console tab)
2. Verify you're logged in (language is session-based)
3. Try incognito/private window
4. Clear all browser cache

**If some text is still in English:**
- This is expected! Only 94.3% is translated
- 43 strings are still missing French translations
- Report which specific text needs translation

---

**Current Status**: 
- ✅ Language selector visible (top-right)
- ✅ Z-index fixed (above sidebar)
- ✅ Cache updated (forced reload)
- ✅ Translations compiled (94.3% coverage)
- ✅ Ready to test!
