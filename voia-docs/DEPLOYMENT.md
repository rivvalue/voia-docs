# VOÏA Documentation - Deployment Guide

## Overview

This guide explains how to deploy the VOÏA documentation site to GitHub Pages for free hosting.

---

## Prerequisites

1. **GitHub Account** - You need a GitHub account
2. **Git Installed** - Git must be installed on your computer
3. **MkDocs Installed** - Already installed in this project

---

## Option 1: Automatic Deployment (Recommended)

MkDocs includes a built-in command for GitHub Pages deployment.

### Step 1: Initialize Git Repository (if not already done)

```bash
cd voia-docs
git init
git add .
git commit -m "Initial commit: VOÏA documentation site"
```

### Step 2: Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository named `voia-docs` (or your preferred name)
3. **Do not** initialize with README, .gitignore, or license
4. Click "Create repository"

### Step 3: Connect Local Repository to GitHub

Replace `YOUR-USERNAME` with your actual GitHub username:

```bash
git remote add origin https://github.com/YOUR-USERNAME/voia-docs.git
git branch -M main
git push -u origin main
```

### Step 4: Deploy to GitHub Pages

```bash
mkdocs gh-deploy
```

**What this does:**
- Builds the documentation site
- Creates/updates a `gh-pages` branch
- Pushes the built site to GitHub
- GitHub Pages automatically serves the site

### Step 5: Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** → **Pages**
3. Under "Source", select branch: `gh-pages` and folder: `/root`
4. Click **Save**

**Your site will be live at:**
```
https://YOUR-USERNAME.github.io/voia-docs/
```

**Initial build takes 2-5 minutes.**

---

## Option 2: Manual Deployment

If you prefer manual control:

### Step 1: Build the Site

```bash
cd voia-docs
mkdocs build
```

This creates a `site/` directory with static HTML files.

### Step 2: Commit to gh-pages Branch

```bash
# Create gh-pages branch
git checkout --orphan gh-pages

# Remove everything
git rm -rf .

# Copy site files
cp -r site/* .

# Commit
git add .
git commit -m "Deploy documentation"

# Push
git push origin gh-pages

# Return to main branch
git checkout main
```

---

## Updating the Documentation

### After Making Changes

1. **Edit Markdown Files** in `docs/en/` or `docs/fr/`
2. **Test Locally** (optional):
   ```bash
   mkdocs serve
   ```
   Visit http://localhost:8000 to preview

3. **Deploy Updates**:
   ```bash
   git add .
   git commit -m "Update documentation"
   git push origin main
   mkdocs gh-deploy
   ```

**Updates are live in 1-2 minutes.**

---

## Custom Domain (Optional)

### Using Your Own Domain

1. **Buy a domain** (e.g., docs.voia.com)
2. **Add CNAME file** to `docs/` folder:
   ```bash
   echo "docs.voia.com" > docs/CNAME
   ```
3. **Configure DNS** at your domain registrar:
   - Add CNAME record: `docs` → `YOUR-USERNAME.github.io`
4. **Rebuild and deploy**:
   ```bash
   mkdocs gh-deploy
   ```
5. **Enable HTTPS** in GitHub Settings → Pages

**Your site will be at:** `https://docs.voia.com`

---

## Troubleshooting

### Site Not Loading

**Problem:** 404 error when visiting GitHub Pages URL

**Solutions:**
1. Check GitHub Settings → Pages shows `gh-pages` branch
2. Wait 5 minutes (initial build takes time)
3. Hard refresh browser (Ctrl+Shift+R)

---

### CSS Not Loading

**Problem:** Site loads but has no styling

**Solutions:**
1. Check `mkdocs.yml` has correct `site_url`
2. Rebuild: `mkdocs gh-deploy --force`
3. Clear browser cache

---

### Links Broken

**Problem:** Internal links return 404

**Solutions:**
1. Use relative paths in Markdown (e.g., `features.md` not `/features.md`)
2. Rebuild site: `mkdocs build`
3. Test locally first: `mkdocs serve`

---

## Directory Structure

```
voia-docs/
├── docs/
│   ├── en/                  # English documentation
│   │   ├── index.md
│   │   ├── features.md
│   │   └── licenses.md
│   ├── fr/                  # French documentation (placeholders)
│   │   ├── index.md
│   │   ├── features.md
│   │   └── licenses.md
│   └── assets/
│       └── logo.svg         # VOÏA logo
├── overrides/
│   └── custom.css           # VOÏA V2 branding
├── mkdocs.yml               # Configuration
├── site/                    # Built site (generated)
└── DEPLOYMENT.md            # This file
```

---

## Configuration Details

### mkdocs.yml Key Settings

```yaml
site_name: VOÏA Documentation
site_url: https://YOUR-USERNAME.github.io/voia-docs/  # Update this!

theme:
  name: material
  custom_dir: overrides
  palette:
    primary: custom      # VOÏA red (#E13A44)
    accent: custom
  font:
    text: Karla         # VOÏA V2 body font
    code: Roboto Mono
  logo: assets/logo.svg  # VOÏA logo

plugins:
  - search
  - i18n:              # Bilingual support
      languages:
        - locale: en
          default: true
        - locale: fr
```

---

## Adding French Translations

When French content is ready:

1. **Replace placeholder pages** in `docs/fr/` with translated content
2. **Keep the same structure** as English pages
3. **Rebuild and deploy**:
   ```bash
   mkdocs gh-deploy
   ```

**Language selector** automatically appears when both languages have content.

---

## Performance Tips

### Optimize Images

- Use SVG for logo (already done)
- Compress PNG/JPG images before adding
- Keep images under 500KB each

### Fast Deployment

```bash
# Quick update without commit
mkdocs gh-deploy --force
```

---

## Local Development

### Preview Changes Before Deploying

```bash
cd voia-docs
mkdocs serve
```

**Opens at:** http://localhost:8000

**Hot reload:** Changes to `.md` files update automatically

**Press Ctrl+C to stop**

---

## Security & Access

### Public vs Private Repository

**Public Repository (Free):**
- Anyone can read documentation
- Perfect for customer-facing docs

**Private Repository (GitHub Pro required):**
- GitHub Pages works on private repos with Pro plan
- Restrict who can view documentation

---

## Backup & Version Control

All documentation is version-controlled with Git:

```bash
# View history
git log

# Revert to previous version
git checkout COMMIT_HASH docs/en/features.md

# Create backup branch
git branch backup-2025-11-06
git push origin backup-2025-11-06
```

---

## Support & Resources

### MkDocs Material Documentation
https://squidfunk.github.io/mkdocs-material/

### GitHub Pages Documentation  
https://docs.github.com/en/pages

### VOÏA Support
support@voia.com

---

## Quick Reference Commands

```bash
# Test locally
mkdocs serve

# Build site
mkdocs build

# Deploy to GitHub Pages
mkdocs gh-deploy

# Force rebuild and deploy
mkdocs gh-deploy --force

# Check for broken links
mkdocs build --strict
```

---

<div class="text-center text-muted" style="margin-top: 3rem;">
  <p>Your VOÏA documentation site is ready to deploy!</p>
</div>
