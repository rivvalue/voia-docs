/**
 * Participant Form Validation and UI Logic
 * Extracted from inline scripts in participants/list.html and participants/campaign_participants.html
 * Phase 1: Frontend Refactoring - Extracted inline JavaScript for better caching and maintainability
 */

/**
 * Email Validation Helper
 * @param {string} email - Email address to validate
 * @returns {boolean} - True if email is valid
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Participant Form Validation
 * Basic validation for participant create/edit forms
 */
function validateParticipantForm(formElement) {
    const emailInput = formElement.querySelector('input[name="email"]');
    const companyInput = formElement.querySelector('input[name="company_name"]');
    
    if (emailInput && emailInput.value && !isValidEmail(emailInput.value)) {
        alert('Please enter a valid email address.');
        emailInput.focus();
        return false;
    }
    
    if (companyInput && !companyInput.value.trim()) {
        alert('Company name is required.');
        companyInput.focus();
        return false;
    }
    
    return true;
}

/**
 * Initialize Participant Form Features
 * Call this function when the DOM is ready
 */
function initializeParticipantForm() {
    const forms = document.querySelectorAll('form[data-participant-form]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateParticipantForm(this)) {
                e.preventDefault();
            }
        });
    });
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeParticipantForm);
} else {
    initializeParticipantForm();
}
