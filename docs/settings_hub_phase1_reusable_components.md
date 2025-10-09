# Settings Hub - Phase 1: Reusable Components

## 🧩 Component Library for Settings Hub V2

### 1. CSS COMPONENTS (From Current Admin Panel)

#### 1.1 Stat Card Component
**Current Usage:** Statistics Overview, Email Stats, License Info  
**Reusability:** HIGH  
**Location:** Lines 36-94 in admin_panel.html

```css
.stat-card {
    background: var(--primary-white);
    border-radius: var(--radius-2xl);
    padding: var(--spacing-xl);
    box-shadow: var(--shadow-lg);
    border: 1px solid var(--light-gray);
    margin-bottom: var(--spacing-xl);
    transition: transform 0.3s ease;
}

.stat-card:hover {
    transform: translateY(-2px);
}

.stat-icon {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    margin-bottom: 1rem;
}

/* Icon variants */
.stat-icon.primary { /* Red gradient */ }
.stat-icon.success { /* Light red gradient */ }
.stat-icon.warning { /* Yellow/Red gradient */ }
.stat-icon.info { /* Transparent red */ }

.stat-number {
    font-size: var(--font-size-4xl);
    font-weight: 700;
    color: var(--primary-black);
}

.stat-label {
    color: var(--gray-dark);
    font-size: var(--font-size-sm);
}
```

**Proposed Enhancements for V2:**
- Add compact variant for smaller cards
- Add loading skeleton state
- Add error state styling
- Support for percentage badges
- Click animation for interactive cards

---

#### 1.2 Section Container Component
**Current Usage:** All major sections  
**Reusability:** HIGH  
**Location:** Lines 96-123

```css
.admin-section {
    background: var(--primary-white);
    border-radius: var(--radius-2xl);
    padding: var(--spacing-2xl);
    box-shadow: var(--shadow-lg);
    border: 1px solid var(--light-gray);
    margin-bottom: var(--spacing-2xl);
}

.section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--spacing-xl);
    padding-bottom: var(--spacing-lg);
    border-bottom: 2px solid var(--light-gray);
}

.section-title {
    font-size: var(--font-size-2xl);
    font-weight: 600;
    color: var(--primary-black);
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}
```

**Proposed Enhancements for V2:**
- Collapsible/accordion variant
- Loading state for async content
- Error boundary styling
- Sticky header option for long sections

---

#### 1.3 Status Badge Component
**Current Usage:** Campaign status, Account type  
**Reusability:** HIGH  
**Location:** Lines 275-345

```css
.campaign-status {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.375rem 0.875rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    white-space: nowrap;
}

/* Status variants */
.status-active {
    background-color: rgba(34, 197, 94, 0.1);
    color: rgb(22, 163, 74);
    border: 1px solid rgba(34, 197, 94, 0.2);
}

.status-ready {
    background-color: rgba(59, 130, 246, 0.1);
    color: rgb(37, 99, 235);
    border: 1px solid rgba(59, 130, 246, 0.2);
}

.status-draft {
    background-color: rgba(251, 191, 36, 0.1);
    color: rgb(217, 119, 6);
    border: 1px solid rgba(251, 191, 36, 0.2);
}

.status-completed {
    background-color: var(--light-gray);
    color: var(--primary-black);
    border: 1px solid var(--medium-gray);
}

/* Account badges */
.account-badge {
    display: inline-block;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
}

.account-demo {
    background-color: var(--red-light);
    color: var(--primary-red);
    border: 1px solid var(--primary-red);
}
```

**Proposed Enhancements for V2:**
- Additional status types (pending, error, warning)
- Pulse animation for "live" statuses
- Icon support in badges
- Size variants (sm, md, lg)

---

#### 1.4 Button Component
**Current Usage:** All action buttons  
**Reusability:** HIGH  
**Location:** Lines 315-324

```css
.btn-admin {
    border-radius: 8px;
    padding: 0.5rem 1rem;
    font-weight: 500;
    transition: all 0.3s ease;
}

.btn-admin:hover {
    transform: translateY(-1px);
}

/* Campaign-specific buttons */
.campaign-primary-btn {
    background: var(--primary-red);
    color: var(--primary-white);
    border-color: var(--primary-red) !important;
}

.campaign-secondary-btn {
    background: transparent;
    color: var(--primary-red);
    border-color: var(--primary-red) !important;
}
```

**Proposed Enhancements for V2:**
- Loading state with spinner
- Disabled state styling
- Icon + text combinations
- Size variants (sm, md, lg, xl)
- Full-width option for mobile

---

#### 1.5 Empty State Component
**Current Usage:** No campaigns, No responses  
**Reusability:** MEDIUM  
**Location:** Lines 373-384

```css
.empty-state {
    text-align: center;
    padding: var(--spacing-3xl) var(--spacing-lg);
    color: var(--gray-dark);
}

.empty-state i {
    font-size: 3rem;
    margin-bottom: 1rem;
    opacity: 0.5;
}
```

**Proposed Enhancements for V2:**
- Action button in empty state
- Illustration/SVG support
- Multiple size variants
- Contextual messaging system

---

### 2. JAVASCRIPT COMPONENTS

#### 2.1 Session Status Checker
**Current Usage:** Admin panel background monitoring  
**Reusability:** HIGH  
**Location:** Lines 1031-1046

```javascript
function checkSessionStatus() {
    fetch('{{ url_for("business_auth.session_status") }}')
        .then(response => response.json())
        .then(data => {
            if (!data.authenticated) {
                alert('Your session has expired. Please log in again.');
                window.location.href = '{{ url_for("business_auth.login") }}';
            }
        })
        .catch(error => {
            console.error('Session check failed:', error);
        });
}

// Check session every 30 minutes
setInterval(checkSessionStatus, 30 * 60 * 1000);
```

**Proposed Enhancements for V2:**
- Visual countdown timer (optional)
- Activity-based refresh (extend on user interaction)
- Graceful warning before expiry (5 min notice)

---

#### 2.2 Button Loading State Manager
**Current Usage:** Quick action buttons  
**Reusability:** HIGH  
**Location:** Lines 1048-1059

```javascript
document.querySelectorAll('.quick-action-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const icon = this.querySelector('i');
        const originalClass = icon.className;
        icon.className = 'fas fa-spinner fa-spin d-block mb-2';
        
        setTimeout(() => {
            icon.className = originalClass;
        }, 3000);
    });
});
```

**Proposed V2 Component:**
```javascript
class LoadingButtonManager {
    static setLoading(button, text = 'Loading...') {
        button.dataset.originalHtml = button.innerHTML;
        button.disabled = true;
        button.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>${text}`;
    }
    
    static resetLoading(button) {
        button.disabled = false;
        button.innerHTML = button.dataset.originalHtml || button.innerHTML;
    }
}
```

---

#### 2.3 Accordion/Collapse Manager
**Current Usage:** Campaign details toggle  
**Reusability:** HIGH  
**Location:** Lines 1061-1081

```javascript
function toggleCampaignDetails(campaignId) {
    const detailsElement = document.getElementById(campaignId + '-details');
    const toggleButton = document.querySelector(`[onclick*="${campaignId}"] .campaign-details-toggle i`);
    
    const isExpanded = detailsElement.classList.contains('show');
    
    if (isExpanded) {
        detailsElement.classList.remove('show');
        toggleButton.className = 'fas fa-chevron-down';
        detailsElement.style.maxHeight = '0';
    } else {
        detailsElement.classList.add('show');
        toggleButton.className = 'fas fa-chevron-up';
        detailsElement.style.maxHeight = detailsElement.scrollHeight + 'px';
    }
}
```

**Proposed V2 Component:**
```javascript
class AccordionManager {
    constructor(accordionElement) {
        this.accordion = accordionElement;
        this.items = this.accordion.querySelectorAll('.accordion-item');
        this.init();
    }
    
    init() {
        this.items.forEach(item => {
            const header = item.querySelector('.accordion-header');
            header.addEventListener('click', () => this.toggle(item));
        });
    }
    
    toggle(item) {
        const content = item.querySelector('.accordion-content');
        const icon = item.querySelector('.accordion-icon');
        const isOpen = item.classList.contains('open');
        
        // Close all other items (single-open mode)
        if (!isOpen) {
            this.closeAll();
        }
        
        // Toggle current item
        item.classList.toggle('open');
        content.style.maxHeight = isOpen ? '0' : content.scrollHeight + 'px';
        icon.classList.toggle('fa-chevron-down', isOpen);
        icon.classList.toggle('fa-chevron-up', !isOpen);
    }
    
    closeAll() {
        this.items.forEach(item => {
            item.classList.remove('open');
            item.querySelector('.accordion-content').style.maxHeight = '0';
            item.querySelector('.accordion-icon').className = 'fas fa-chevron-down';
        });
    }
}
```

---

#### 2.4 Export Data Handler
**Current Usage:** Full data export  
**Reusability:** MEDIUM  
**Location:** Lines 1104-1163

```javascript
function exportAllData() {
    const btn = document.getElementById('exportAllBtn');
    const originalHTML = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Exporting...';
    btn.disabled = true;
    
    fetch('/api/export_data', {
        method: 'GET',
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return response.json();
    })
    .then(result => {
        const dataStr = JSON.stringify(result.data || result, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const fileName = `voïa_full_export_${new Date().toISOString().split('T')[0]}.json`;
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', url);
        linkElement.setAttribute('download', fileName);
        linkElement.click();
        
        setTimeout(() => URL.revokeObjectURL(url), 100);
    })
    .catch(error => {
        console.error('Error exporting data:', error);
        alert(`Error exporting data: ${error.message}`);
    })
    .finally(() => {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
    });
}
```

**Proposed V2 Component:**
```javascript
class DataExporter {
    static async export(endpoint, filename, options = {}) {
        const button = options.button;
        const onProgress = options.onProgress || (() => {});
        
        try {
            if (button) LoadingButtonManager.setLoading(button, 'Exporting...');
            
            const response = await fetch(endpoint, {
                method: 'GET',
                credentials: 'include'
            });
            
            if (!response.ok) throw new Error(`Export failed: ${response.status}`);
            
            const result = await response.json();
            const dataStr = JSON.stringify(result.data || result, null, 2);
            const blob = new Blob([dataStr], { type: 'application/json' });
            
            this.downloadBlob(blob, filename);
            
            return { success: true, data: result };
        } catch (error) {
            console.error('Export error:', error);
            throw error;
        } finally {
            if (button) LoadingButtonManager.resetLoading(button);
        }
    }
    
    static downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 100);
    }
}
```

---

#### 2.5 Card Hover Animations
**Current Usage:** Campaign cards  
**Reusability:** HIGH  
**Location:** Lines 1084-1094

```javascript
document.querySelectorAll('.campaign-item').forEach(card => {
    card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-2px)';
    });
    
    card.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
    });
});
```

**Proposed V2 Component:**
```javascript
class CardInteractionManager {
    static enableHoverEffects(selector = '.settings-card') {
        document.querySelectorAll(selector).forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-4px)';
                card.style.boxShadow = '0 12px 30px rgba(0,0,0,0.15)';
            });
            
            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0)';
                card.style.boxShadow = '';
            });
        });
    }
    
    static enableClickFeedback(selector = '.btn') {
        document.querySelectorAll(selector).forEach(btn => {
            btn.addEventListener('click', function(e) {
                const ripple = document.createElement('span');
                ripple.className = 'ripple-effect';
                this.appendChild(ripple);
                setTimeout(() => ripple.remove(), 600);
            });
        });
    }
}
```

---

### 3. TEMPLATE MACROS (Proposed)

#### 3.1 Stat Card Macro
```jinja2
{% macro stat_card(icon, number, label, color='primary', tooltip='') %}
<div class="stat-card" {% if tooltip %}title="{{ tooltip }}"{% endif %}>
    <div class="stat-icon {{ color }}">
        <i class="fas fa-{{ icon }}"></i>
    </div>
    <h3 class="stat-number">{{ number }}</h3>
    <p class="stat-label">{{ label }}</p>
</div>
{% endmacro %}

<!-- Usage -->
{{ stat_card('chart-line', admin_data.stats.total_responses, 'Total Responses', 'primary') }}
```

---

#### 3.2 Section Header Macro
```jinja2
{% macro section_header(title, icon, action_button=None) %}
<div class="section-header">
    <h3 class="section-title">
        <i class="fas fa-{{ icon }}"></i>
        {{ title }}
    </h3>
    {% if action_button %}
    <div class="section-actions">
        {{ action_button }}
    </div>
    {% endif %}
</div>
{% endmacro %}

<!-- Usage -->
{{ section_header('Account Settings', 'cog', '<a href="#" class="btn btn-primary">Configure</a>') }}
```

---

#### 3.3 Status Badge Macro
```jinja2
{% macro status_badge(status, text=None) %}
{% set badge_config = {
    'active': {'icon': 'play-circle', 'class': 'status-active'},
    'ready': {'icon': 'check-circle', 'class': 'status-ready'},
    'draft': {'icon': 'edit', 'class': 'status-draft'},
    'completed': {'icon': 'flag-checkered', 'class': 'status-completed'}
} %}
{% set config = badge_config.get(status, {'icon': 'info-circle', 'class': 'status-default'}) %}
<span class="campaign-status {{ config.class }}">
    <i class="fas fa-{{ config.icon }}"></i>
    {{ text or status|title }}
</span>
{% endmacro %}

<!-- Usage -->
{{ status_badge('active', 'Currently Active') }}
```

---

#### 3.4 Empty State Macro
```jinja2
{% macro empty_state(icon, title, message, action_url=None, action_text='Get Started') %}
<div class="empty-state">
    <i class="fas fa-{{ icon }}"></i>
    <h5>{{ title }}</h5>
    <p>{{ message }}</p>
    {% if action_url %}
    <a href="{{ action_url }}" class="btn btn-primary mt-3">{{ action_text }}</a>
    {% endif %}
</div>
{% endmacro %}

<!-- Usage -->
{{ empty_state('users', 'No Team Members', 'Add your first team member to get started', 
   url_for('business_auth.manage_users'), 'Add User') }}
```

---

#### 3.5 Accordion Item Macro
```jinja2
{% macro accordion_item(id, title, content, icon='chevron-down', expanded=false) %}
<div class="accordion-item {{ 'open' if expanded else '' }}" data-accordion-id="{{ id }}">
    <div class="accordion-header">
        <span class="accordion-title">{{ title }}</span>
        <i class="accordion-icon fas fa-{{ icon }}"></i>
    </div>
    <div class="accordion-content" style="max-height: {{ 'auto' if expanded else '0' }}">
        {{ content }}
    </div>
</div>
{% endmacro %}

<!-- Usage -->
{{ accordion_item('email-config', 'Email Configuration', email_config_form) }}
```

---

#### 3.6 Progress Bar Macro
```jinja2
{% macro progress_bar(current, total, show_label=true, color='primary') %}
{% set percentage = (current / total * 100) if total > 0 else 0 %}
<div class="progress-wrapper">
    {% if show_label %}
    <div class="progress-label">
        <span>{{ current }}/{{ total }}</span>
        <span>{{ percentage|int }}%</span>
    </div>
    {% endif %}
    <div class="progress">
        <div class="progress-bar bg-{{ color }}" 
             role="progressbar" 
             style="width: {{ percentage }}%" 
             aria-valuenow="{{ current }}" 
             aria-valuemin="0" 
             aria-valuemax="{{ total }}">
        </div>
    </div>
</div>
{% endmacro %}

<!-- Usage -->
{{ progress_bar(admin_data.license_info.users_used, admin_data.license_info.users_limit) }}
```

---

### 4. UTILITY FUNCTIONS

#### 4.1 Form Validation Helper
```javascript
class FormValidator {
    static validateEmail(email) {
        const pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        return pattern.test(email);
    }
    
    static validateRequired(value) {
        return value && value.trim().length > 0;
    }
    
    static showError(inputElement, message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback d-block';
        errorDiv.textContent = message;
        inputElement.classList.add('is-invalid');
        inputElement.parentElement.appendChild(errorDiv);
    }
    
    static clearErrors(formElement) {
        formElement.querySelectorAll('.invalid-feedback').forEach(el => el.remove());
        formElement.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    }
}
```

---

#### 4.2 Toast Notification System
```javascript
class ToastNotification {
    static show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${type}`;
        toast.innerHTML = `
            <i class="fas fa-${this.getIcon(type)} me-2"></i>
            <span>${message}</span>
            <button class="toast-close">&times;</button>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => toast.classList.add('show'), 10);
        
        toast.querySelector('.toast-close').addEventListener('click', () => {
            this.hide(toast);
        });
        
        setTimeout(() => this.hide(toast), duration);
    }
    
    static hide(toast) {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }
    
    static getIcon(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || icons.info;
    }
}
```

---

#### 4.3 Debounce/Throttle Utility
```javascript
class PerformanceUtils {
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    static throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}
```

---

### 5. RESPONSIVE GRID SYSTEM

#### 5.1 Settings Card Grid
```css
.settings-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--spacing-xl);
    margin-bottom: var(--spacing-2xl);
}

/* Tablet: 2 columns */
@media (min-width: 768px) {
    .settings-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

/* Desktop: 4 columns */
@media (min-width: 1200px) {
    .settings-grid {
        grid-template-columns: repeat(4, 1fr);
    }
}

/* Full-width cards on mobile */
@media (max-width: 767px) {
    .settings-card {
        margin-left: calc(-1 * var(--spacing-lg));
        margin-right: calc(-1 * var(--spacing-lg));
        border-radius: 0;
    }
}
```

---

### 6. ACCESSIBILITY COMPONENTS

#### 6.1 Skip to Content Link
```html
<a href="#main-content" class="skip-link">Skip to main content</a>

<style>
.skip-link {
    position: absolute;
    top: -40px;
    left: 0;
    background: var(--primary-red);
    color: white;
    padding: 8px;
    z-index: 100;
}

.skip-link:focus {
    top: 0;
}
</style>
```

---

#### 6.2 Screen Reader Only Text
```css
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border-width: 0;
}
```

---

### 7. LOADING STATES

#### 7.1 Skeleton Loader
```css
.skeleton {
    background: linear-gradient(
        90deg,
        var(--light-gray) 25%,
        var(--medium-gray) 50%,
        var(--light-gray) 75%
    );
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s ease-in-out infinite;
}

@keyframes skeleton-loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

.skeleton-card {
    height: 120px;
    border-radius: var(--radius-xl);
}

.skeleton-text {
    height: 1rem;
    border-radius: 4px;
    margin-bottom: 0.5rem;
}
```

---

## SUMMARY

### Highly Reusable (Priority 1)
- ✅ Stat Card Component
- ✅ Section Container & Header
- ✅ Status Badge Component
- ✅ Button Component
- ✅ Accordion Manager
- ✅ Loading Button Manager
- ✅ Session Status Checker

### Moderately Reusable (Priority 2)
- ⚠️ Empty State Component
- ⚠️ Progress Bar Component
- ⚠️ Toast Notification System
- ⚠️ Export Data Handler
- ⚠️ Form Validator

### Custom for Settings Hub (Priority 3)
- 🔧 Settings Card Grid
- 🔧 Responsive Breakpoints
- 🔧 Accessibility Helpers
- 🔧 Skeleton Loaders

### Total Reusable Components: 20+
- **CSS Components:** 7
- **JavaScript Classes:** 6
- **Template Macros:** 6
- **Utility Functions:** 4
- **Accessibility:** 2

All components follow VOÏA branding (red accent #E13A44) and existing design system variables.
