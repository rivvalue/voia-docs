# Settings Hub - Phase 1: Wireframe Designs

## 🎨 Visual Layout Specifications

### DESIGN PHILOSOPHY
- **Mobile-first approach:** Start with mobile layout, enhance for larger screens
- **Card-based UI:** Clear visual separation between setting categories
- **Progressive disclosure:** Use accordions to hide complexity
- **VOÏA branding:** Red accent color (#E13A44), dark gradients, modern aesthetics
- **Accessibility-first:** WCAG 2.1 AA compliant, keyboard navigable

---

## 1. MOBILE LAYOUT (320px - 767px)

### 1.1 Stacked Cards View

```
┌─────────────────────────────────────┐
│  ☰  Settings Hub           [UI v2]  │ ← Navbar with hamburger
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Welcome, John Doe                  │
│  Acme Corp · Administrator          │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  🔧 Account Settings          [˅]   │ ← Accordion Header
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────────────────────┐   │
│  │ 📧 Email Configuration      │   │
│  │ SMTP: mail.acme.com         │   │
│  │ Status: ✓ Connected         │   │
│  │         [Test] [Configure]  │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ 🎨 Brand Configuration      │   │
│  │ Logo: acme-logo.png         │   │
│  │ Colors: #E13A44, #1a1a1a    │   │
│  │         [Edit Branding]     │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ 💬 Survey Customization     │   │
│  │ AI Tone: Professional       │   │
│  │ Templates: 3 active         │   │
│  │         [Customize]         │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  👥 User Management           [˅]   │ ← Collapsed
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  📁 Data Management           [˅]   │ ← Collapsed
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  ⚙️  System Settings          [˅]   │ ← Collapsed
└─────────────────────────────────────┘
```

**Interaction Notes:**
- Tap card header to expand/collapse
- Only one section expanded at a time
- Smooth slide animation (300ms)
- Chevron rotates on expand
- Full-width cards for touch-friendly UI

---

### 1.2 Expanded Card Detail (Mobile)

```
┌─────────────────────────────────────┐
│  👥 User Management           [ˆ]   │ ← Expanded
├─────────────────────────────────────┤
│                                     │
│  Team Members: 3/5 users            │
│  ████████████░░░░░ 60%              │ ← Progress bar
│                                     │
│  ┌─────────────────────────────┐   │
│  │ 👤 John Doe                 │   │
│  │    john@acme.com            │   │
│  │    Role: Admin              │   │
│  │    Status: Active           │   │
│  │    [Edit] [Deactivate]      │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ 👤 Jane Smith               │   │
│  │    jane@acme.com            │   │
│  │    Role: Manager            │   │
│  │    Status: Active           │   │
│  │    [Edit] [Deactivate]      │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │ 👤 Bob Johnson              │   │
│  │    bob@acme.com             │   │
│  │    Role: Viewer             │   │
│  │    Status: Active           │   │
│  │    [Edit] [Deactivate]      │   │
│  └─────────────────────────────┘   │
│                                     │
│  [+ Add Team Member]                │
│                                     │
└─────────────────────────────────────┘
```

**Interaction Notes:**
- Scrollable content area
- Sticky header while scrolling
- Action buttons stack on small screens
- Touch-optimized button sizes (44px min)

---

## 2. TABLET LAYOUT (768px - 1199px)

### 2.1 Two-Column Grid

```
┌───────────────────────────────────────────────────────────────┐
│  Settings Hub                                     [UI v2 ˅]   │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│  Welcome, John Doe · Acme Corp · Administrator                │
└───────────────────────────────────────────────────────────────┘

┌─────────────────────────────┐  ┌─────────────────────────────┐
│  🔧 Account Settings   [ˆ]  │  │  👥 User Management    [˅]  │
├─────────────────────────────┤  └─────────────────────────────┘
│                             │
│  📧 Email Configuration     │  ┌─────────────────────────────┐
│  ┌──────────────────────┐   │  │  📁 Data Management    [˅]  │
│  │ SMTP: mail.acme.com  │   │  └─────────────────────────────┘
│  │ Status: ✓ Connected  │   │
│  │ [Test] [Configure]   │   │  ┌─────────────────────────────┐
│  └──────────────────────┘   │  │  ⚙️  System Settings   [˅]  │
│                             │  └─────────────────────────────┘
│  🎨 Brand Configuration     │
│  ┌──────────────────────┐   │
│  │ Logo: acme-logo.png  │   │
│  │ [Edit Branding]      │   │
│  └──────────────────────┘   │
│                             │
│  💬 Survey Customization    │
│  ┌──────────────────────┐   │
│  │ AI Tone: Professional│   │
│  │ [Customize]          │   │
│  └──────────────────────┘   │
│                             │
└─────────────────────────────┘
```

**Layout Notes:**
- 2-column grid (50/50 split)
- Left column: Expanded card
- Right column: Collapsed cards stacked
- Better use of horizontal space
- Multiple cards can be open simultaneously

---

### 2.2 Tablet Expanded State

```
┌───────────────────────────────────────────────────────────────┐
│  Settings Hub                                     [UI v2 ˅]   │
└───────────────────────────────────────────────────────────────┘

┌─────────────────────────────┐  ┌─────────────────────────────┐
│  🔧 Account Settings   [ˆ]  │  │  👥 User Management    [ˆ]  │
│  (3 subsections)            │  ├─────────────────────────────┤
└─────────────────────────────┘  │                             │
                                 │  Team Members: 3/5          │
┌─────────────────────────────┐  │  ████████████░░░░░ 60%      │
│  📁 Data Management    [˅]  │  │                             │
└─────────────────────────────┘  │  ┌─────────────────────┐   │
                                 │  │ 👤 John Doe         │   │
┌─────────────────────────────┐  │  │    Admin · Active   │   │
│  ⚙️  System Settings   [˅]  │  │  │    [Edit] [Disable] │   │
└─────────────────────────────┘  │  └─────────────────────┘   │
                                 │                             │
                                 │  ┌─────────────────────┐   │
                                 │  │ 👤 Jane Smith       │   │
                                 │  │    Manager · Active │   │
                                 │  │    [Edit] [Disable] │   │
                                 │  └─────────────────────┘   │
                                 │                             │
                                 │  [+ Add Team Member]        │
                                 │                             │
                                 └─────────────────────────────┘
```

---

## 3. DESKTOP LAYOUT (1200px+)

### 3.1 Four-Column Dashboard View

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  [☰] Settings Hub                                                             [UI v2 ˅]  [Profile] │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  Welcome, John Doe                                        Acme Corp · Administrator · Core License │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  🔧 Account     │  │  👥 User        │  │  📁 Data        │  │  ⚙️  System     │
│     Settings    │  │     Management  │  │     Management  │  │     Settings    │
│           [ˆ]   │  │           [˅]   │  │           [˅]   │  │           [˅]   │
├─────────────────┤  └─────────────────┘  └─────────────────┘  └─────────────────┘
│                 │
│  📧 Email       │
│  Configuration  │
│  ┌───────────┐  │
│  │ SMTP      │  │
│  │ Connected │  │
│  │ [Config]  │  │
│  └───────────┘  │
│                 │
│  🎨 Branding    │
│  ┌───────────┐  │
│  │ Logo      │  │
│  │ Colors    │  │
│  │ [Edit]    │  │
│  └───────────┘  │
│                 │
│  💬 Survey      │
│  ┌───────────┐  │
│  │ AI Tone   │  │
│  │ Templates │  │
│  │ [Custom]  │  │
│  └───────────┘  │
│                 │
└─────────────────┘
```

**Layout Notes:**
- 4-column grid (25% each)
- All cards visible at once
- Expand/collapse individual cards
- Hover effects on card headers
- Smooth transitions (300ms ease)

---

### 3.2 Desktop Expanded Multi-Card View

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  [☰] Settings Hub                                                             [UI v2 ˅]  [Profile] │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐
│  🔧 Account Settings           [ˆ]   │  │  👥 User Management            [ˆ]   │
├──────────────────────────────────────┤  ├──────────────────────────────────────┤
│                                      │  │                                      │
│  ┌─────────────────────────────┐    │  │  Team Members: 3/5 users             │
│  │  📧 Email Configuration     │    │  │  ████████████░░░░░ 60%               │
│  │  ───────────────────────────│    │  │                                      │
│  │  SMTP Host: mail.acme.com   │    │  │  ┌──────────────────────────────┐   │
│  │  Port: 587 · TLS: ✓         │    │  │  │ 👤 John Doe  john@acme.com   │   │
│  │  From: noreply@acme.com     │    │  │  │    Role: Admin · Active      │   │
│  │  Status: ✓ Connected        │    │  │  │    Last login: 2 hours ago   │   │
│  │                             │    │  │  │    [Edit] [Deactivate] [Logs]│   │
│  │  [Test Connection]          │    │  │  └──────────────────────────────┘   │
│  │  [Save Configuration]       │    │  │                                      │
│  └─────────────────────────────┘    │  │  ┌──────────────────────────────┐   │
│                                      │  │  │ 👤 Jane Smith jane@acme.com  │   │
│  ┌─────────────────────────────┐    │  │  │    Role: Manager · Active    │   │
│  │  🎨 Brand Configuration     │    │  │  │    Last login: 1 day ago     │   │
│  │  ───────────────────────────│    │  │  │    [Edit] [Deactivate] [Logs]│   │
│  │  Logo: [acme-logo.png]      │    │  │  └──────────────────────────────┘   │
│  │  [📤 Upload New Logo]       │    │  │                                      │
│  │                             │    │  │  ┌──────────────────────────────┐   │
│  │  Primary Color: #E13A44 ⬛  │    │  │  │ 👤 Bob Johnson bob@acme.com  │   │
│  │  Secondary: #1a1a1a ⬛      │    │  │  │    Role: Viewer · Active     │   │
│  │                             │    │  │  │    Last login: 3 days ago    │   │
│  │  [Preview] [Save Changes]   │    │  │  │    [Edit] [Deactivate] [Logs]│   │
│  └─────────────────────────────┘    │  │  └──────────────────────────────┘   │
│                                      │  │                                      │
│  ┌─────────────────────────────┐    │  │  [+ Add New Team Member]             │
│  │  💬 Survey Customization    │    │  │                                      │
│  │  ───────────────────────────│    │  └──────────────────────────────────────┘
│  │  AI Tone: [Professional ˅]  │    │
│  │  Question Style: [Open ˅]   │    │  ┌──────────────────────────────────────┐
│  │  Templates: 3 active        │    │  │  📁 Data Management            [˅]   │
│  │                             │    │  └──────────────────────────────────────┘
│  │  [Customize Templates]      │    │
│  │  [Save Settings]            │    │  ┌──────────────────────────────────────┐
│  └─────────────────────────────┘    │  │  ⚙️  System Settings           [˅]   │
│                                      │  └──────────────────────────────────────┘
└──────────────────────────────────────┘
```

**Interaction Notes:**
- Left side: Account Settings (2 columns wide)
- Right side: User Management (2 columns wide)
- Bottom right: Collapsed cards stacked
- Can have multiple expanded cards
- Sticky section headers on scroll

---

## 4. ACCORDION INTERACTION STATES

### 4.1 Collapsed State
```
┌─────────────────────────────────────┐
│  🔧 Account Settings          [˅]   │ ← Chevron down, light gray bg
│  3 configuration sections           │ ← Subtitle hint
└─────────────────────────────────────┘
```

**Visual Specs:**
- Background: `var(--primary-white)`
- Border: `1px solid var(--light-gray)`
- Border-radius: `var(--radius-2xl)` (16px)
- Padding: `var(--spacing-xl)` (24px)
- Cursor: `pointer`
- Transition: `all 0.3s ease`

---

### 4.2 Hover State
```
┌─────────────────────────────────────┐
│  🔧 Account Settings          [˅]   │ ← Red accent border
│  3 configuration sections           │
└─────────────────────────────────────┘
```

**Visual Specs:**
- Border-color: `var(--primary-red)` (#E13A44)
- Transform: `translateY(-2px)`
- Box-shadow: `0 8px 25px rgba(0,0,0,0.1)`
- Background: `rgba(225, 58, 68, 0.02)` (subtle red tint)

---

### 4.3 Expanded State
```
┌─────────────────────────────────────┐
│  🔧 Account Settings          [ˆ]   │ ← Chevron up, red accent
├─────────────────────────────────────┤
│                                     │
│  [Content Area]                     │
│  - Email Configuration              │
│  - Brand Configuration              │
│  - Survey Customization             │
│                                     │
└─────────────────────────────────────┘
```

**Visual Specs:**
- Border-color: `var(--primary-red)`
- Background: White
- Content max-height: `auto` (from 0)
- Animation: Slide down (300ms ease-out)
- Header background: `var(--red-light)` (light red)

---

## 5. COMPONENT DETAIL VIEWS

### 5.1 Email Configuration Subsection
```
┌─────────────────────────────────────────────────┐
│  📧 Email Configuration                         │
│  ───────────────────────────────────────────────│
│                                                 │
│  SMTP Server                                    │
│  ┌───────────────────────────────────────────┐ │
│  │ mail.acme.com                             │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  Port         Encryption                        │
│  ┌─────┐     ┌─────┐ TLS ☑  SSL ☐             │
│  │ 587 │     └─────┘                           │
│  └─────┘                                        │
│                                                 │
│  From Email                                     │
│  ┌───────────────────────────────────────────┐ │
│  │ noreply@acme.com                          │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  Username                                       │
│  ┌───────────────────────────────────────────┐ │
│  │ smtp-user@acme.com                        │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  Password                                       │
│  ┌───────────────────────────────────────────┐ │
│  │ ••••••••••••                              │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  Connection Status: ✓ Connected                │
│  Last tested: 2 hours ago                      │
│                                                 │
│  [Test Connection]  [Save Configuration]       │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

### 5.2 License Information Display
```
┌─────────────────────────────────────────────────┐
│  📜 License Information                         │
│  ───────────────────────────────────────────────│
│                                                 │
│  ┌─────────────┐  ┌─────────────┐              │
│  │ 🎫 Core     │  │ ✓ Active    │              │
│  │             │  │             │              │
│  │ License     │  │ 245 days    │              │
│  │ Type        │  │ remaining   │              │
│  └─────────────┘  └─────────────┘              │
│                                                 │
│  Usage Limits                                   │
│                                                 │
│  Campaigns: 3/5                                 │
│  ████████████░░░░░ 60%                          │
│  2 campaigns remaining                          │
│                                                 │
│  Team Members: 3/5                              │
│  ████████████░░░░░ 60%                          │
│  2 users remaining                              │
│                                                 │
│  Participants: Unlimited                        │
│  ∞ (500 per campaign)                           │
│                                                 │
│  [View Full Details]  [Upgrade License]        │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

### 5.3 Data Export Section
```
┌─────────────────────────────────────────────────┐
│  📤 Export Data                                 │
│  ───────────────────────────────────────────────│
│                                                 │
│  Export all survey data, responses, and         │
│  participant information in JSON format.        │
│                                                 │
│  Last export: Jan 15, 2025 at 3:45 PM          │
│  File size: 2.3 MB (1,247 responses)            │
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │  [📥 Export All Data]                     │ │
│  │                                           │ │
│  │  ⚙️ Export Options:                       │ │
│  │  ☑ Include campaign details               │ │
│  │  ☑ Include participant data               │ │
│  │  ☑ Include email delivery logs            │ │
│  │  ☑ Include AI analysis results            │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  Recent Exports:                                │
│  • Jan 15, 2025 - voïa_export_2025-01-15.json  │
│  • Jan 10, 2025 - voïa_export_2025-01-10.json  │
│  • Jan 05, 2025 - voïa_export_2025-01-05.json  │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 6. COLOR PALETTE & THEMING

### Primary Colors
```
VOÏA Red (Primary):    #E13A44  ⬛
Red Hover:             #C82D37  ⬛
Red Light (10% tint):  #FCE8EA  ⬛
```

### Neutral Colors
```
Primary Black:         #1a1a1a  ⬛
Gray Dark:             #4a4a4a  ⬛
Medium Gray:           #9ca3af  ⬛
Light Gray:            #e5e7eb  ⬛
Primary White:         #ffffff  ⬛
```

### Status Colors
```
Success Green:         #22c55e  ⬛
Warning Yellow:        #fbbf24  ⬛
Error Red:             #ef4444  ⬛
Info Blue:             #3b82f6  ⬛
```

### Gradients
```
Header Gradient:  linear-gradient(135deg, #E13A44 0%, #C82D37 100%)
Card Hover:       linear-gradient(135deg, rgba(225,58,68,0.05) 0%, rgba(200,45,55,0.08) 100%)
Sidebar (v2):     linear-gradient(180deg, #1a1a1a 0%, #2d2d2d 100%)
```

---

## 7. TYPOGRAPHY SCALE

```
Page Title (H1):      var(--font-size-4xl)   2.25rem  36px
Section Title (H2):   var(--font-size-2xl)   1.5rem   24px
Subsection (H3):      var(--font-size-xl)    1.25rem  20px
Body Text:            var(--font-size-base)  1rem     16px
Small Text:           var(--font-size-sm)    0.875rem 14px
Tiny Text:            var(--font-size-xs)    0.75rem  12px

Font Families:
Headings: var(--font-family-headings)  (e.g., Inter, system-ui)
Body:     var(--font-family-base)      (e.g., -apple-system, sans-serif)
```

---

## 8. SPACING SYSTEM

```
xs:   0.25rem   4px
sm:   0.5rem    8px
md:   1rem      16px
lg:   1.5rem    24px
xl:   2rem      32px
2xl:  3rem      48px
3xl:  4rem      64px
```

---

## 9. RESPONSIVE BREAKPOINTS

```
xs:  0px    (Mobile small)
sm:  576px  (Mobile large)
md:  768px  (Tablet portrait)
lg:  992px  (Tablet landscape)
xl:  1200px (Desktop)
2xl: 1400px (Large desktop)
```

---

## 10. ACCESSIBILITY FEATURES

### Keyboard Navigation
```
Tab         → Move to next focusable element
Shift+Tab   → Move to previous focusable element
Enter/Space → Activate button or toggle accordion
Escape      → Close modal/dropdown
↑/↓ Arrow   → Navigate within accordion sections
```

### Focus States
```
Default Focus Ring:  3px solid var(--primary-red) with 2px offset
Skip Link:          Visible only on :focus
Aria Labels:        All interactive elements labeled
```

### Screen Reader Announcements
```
Accordion state:    "Account Settings, expanded" / "collapsed"
Button actions:     "Save Email Configuration"
Progress bars:      "3 of 5 users, 60 percent"
Status indicators:  "Email configuration, connected"
```

---

## 11. ANIMATION SPECIFICATIONS

### Accordion Expand/Collapse
```
Duration:     300ms
Easing:       ease-out
Property:     max-height, transform
Initial:      max-height: 0, opacity: 0
Expanded:     max-height: [calculated], opacity: 1
```

### Card Hover
```
Duration:     200ms
Easing:       ease
Property:     transform, box-shadow, border-color
Transform:    translateY(-4px)
Shadow:       0 12px 30px rgba(0,0,0,0.15)
```

### Button Click
```
Duration:     150ms
Easing:       ease-in-out
Property:     transform, background-color
Active:       scale(0.95)
```

### Loading Spinner
```
Duration:     1s
Easing:       linear
Property:     transform (rotate)
Animation:    infinite rotation
```

---

## 12. ICON SYSTEM (Font Awesome)

### Section Icons
```
Account Settings:   fa-cog
User Management:    fa-users
Data Management:    fa-folder-open
System Settings:    fa-sliders-h
```

### Subsection Icons
```
Email:              fa-envelope
Brand:              fa-paint-brush
Survey:             fa-comments
License:            fa-certificate
Export:             fa-download
Audit:              fa-clipboard-list
Performance:        fa-tachometer-alt
Scheduler:          fa-clock
```

### Status Icons
```
Success:            fa-check-circle
Warning:            fa-exclamation-triangle
Error:              fa-times-circle
Info:               fa-info-circle
Connected:          fa-plug
Disconnected:       fa-unlink
```

---

## SUMMARY

### Total Wireframes Created: 12
- Mobile layouts: 2
- Tablet layouts: 2
- Desktop layouts: 2
- Component details: 3
- Interaction states: 3

### Design System Defined:
- ✅ Color palette (10 colors + gradients)
- ✅ Typography scale (6 sizes)
- ✅ Spacing system (7 sizes)
- ✅ Responsive breakpoints (6 breakpoints)
- ✅ Accessibility features (WCAG 2.1 AA)
- ✅ Animation specs (4 types)
- ✅ Icon system (20+ icons)

### Implementation Ready:
All wireframes include pixel-perfect specifications, color codes, spacing values, and interaction behaviors for direct translation to HTML/CSS/JavaScript.

**Next Step:** Phase 2 - Layout Foundation (Create admin_panel_v2.html)
