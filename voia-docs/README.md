# VOÏA Documentation Site

Professional end-user documentation for the VOÏA platform, built with MkDocs Material and deployed on GitHub Pages.

## Features

✅ **Bilingual Support** - English (complete) + French (structure ready for translation)  
✅ **VOÏA V2 Branding** - Custom colors (#E13A44), Montserrat/Karla fonts, and logo  
✅ **Searchable** - Instant search with language-specific indexes  
✅ **Mobile-Responsive** - Works perfectly on all devices  
✅ **Free Hosting** - GitHub Pages (no cost)  
✅ **Version Controlled** - All content in Git  

---

## Content Overview

### English Documentation (~900 lines)

**Getting Started (index.md)** - 200+ lines
- Platform overview
- Quick start guide (4 steps)
- Popular features
- User roles and licenses

**Features Guide (features.md)** - 500+ lines  
- AI-powered survey intelligence
- Campaign management
- Participant management
- Analytics & business intelligence
- Communication & email system
- User management & permissions
- Branding & customization
- Security & privacy
- Data export & integration

**License Guide (licenses.md)** - 200+ lines
- License tiers (Core, Plus, Pro, Trial)
- Usage tracking
- Upgrading/downgrading
- FAQ and troubleshooting

### French Documentation

Placeholder pages with "Translation coming soon" message.  
Structure is ready for translated content.

---

## Quick Start

### View Locally

```bash
cd voia-docs
mkdocs serve
```

Visit http://localhost:8000

### Deploy to GitHub Pages

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete instructions.

Quick deploy:
```bash
mkdocs gh-deploy
```

---

## Project Structure

```
voia-docs/
├── docs/
│   ├── en/              # English documentation
│   ├── fr/              # French documentation (placeholders)
│   └── assets/          # Images and logo
├── overrides/
│   └── custom.css       # VOÏA V2 branding
├── mkdocs.yml           # Configuration
├── DEPLOYMENT.md        # Deployment instructions
└── README.md            # This file
```

---

## VOÏA V2 Branding

### Colors

- Primary Red: `#E13A44`
- Red Hover: `#C52D36`
- Light Gray: `#E9E8E4`
- Medium Gray: `#BDBDBD`
- Primary Black: `#1a1a1a`

### Typography

- **Headings:** Montserrat (Google Fonts)
- **Body Text:** Karla (Google Fonts)
- **Code:** Roboto Mono

---

## Adding French Translations

1. Replace placeholder content in `docs/fr/`
2. Keep same filename structure as English
3. Rebuild: `mkdocs build`
4. Deploy: `mkdocs gh-deploy`

---

## Updating Content

1. Edit Markdown files in `docs/en/` or `docs/fr/`
2. Test locally: `mkdocs serve`
3. Commit changes:
   ```bash
   git add .
   git commit -m "Update documentation"
   git push
   ```
4. Deploy: `mkdocs gh-deploy`

---

## Built With

- **MkDocs** - Static site generator
- **Material for MkDocs** - Professional theme
- **mkdocs-static-i18n** - Multilingual support
- **GitHub Pages** - Free hosting

---

## License

© 2025 VOÏA Platform - All Rights Reserved

---

## Support

For questions about this documentation:
- **Technical Issues:** Check [DEPLOYMENT.md](DEPLOYMENT.md)
- **Content Updates:** Edit Markdown files directly
- **VOÏA Platform:** support@voia.com
