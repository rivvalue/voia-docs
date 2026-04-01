/**
 * Campaign Form Validation and UI Logic
 * Extracted from inline scripts in campaigns/create.html and campaigns/edit.html
 * Phase 1: Frontend Refactoring - Extracted inline JavaScript for better caching and maintainability
 * 
 * LOCALIZATION: This module expects window.CampaignFormI18n to be defined with translated strings
 * Example:
 * window.CampaignFormI18n = {
 *     endDateAfterStart: "End date must be after start date.",
 *     selectDates: "Select campaign dates to see midpoint reminder timing",
 *     // ... other strings
 * };
 */

// Default English fallback strings (overridden by window.CampaignFormI18n if provided)
const defaultStrings = {
    endDateAfterStart: "End date must be after start date.",
    shortDurationWarning: "Note: Campaign duration is only {durationDays} day(s). Consider a longer campaign for better response rates.",
    selectDates: "Select campaign dates to see midpoint reminder timing",
    endDateMustBeAfter: "End date must be after start date",
    midpointLabel: "Midpoint:",
    lastChanceLabel: "Last Chance:",
    warningLastChanceBefore: "Last Chance reminder (day {lastChanceDay}) sends before or at midpoint (day {midpointDay}). Increase the offset to at least {minOffset} days.",
    warningTooClose: "Last Chance reminder (day {lastChanceDay}) and midpoint (day {midpointDay}) are very close. Consider increasing spacing.",
    warningNotEnoughTime: "Last Chance reminder only {reminderDelay} days before end - participants may not have time to respond.",
    emailPreviewTitle: "Email Preview",
    invitationEmailTitle: "Invitation Email Preview",
    lastChanceReminderTitle: "Last Chance Reminder Preview",
    midpointReminderTitle: "Midpoint Reminder Preview",
    loading: "Loading...",
    loadingPreview: "Loading preview...",
    errorLoadingPreview: "Error loading preview",
    unableToLoadPreview: "Unable to load email preview. Please try again."
};

// Get translated string with fallback
function t(key, replacements = {}) {
    const i18n = window.CampaignFormI18n || defaultStrings;
    let str = i18n[key] || defaultStrings[key] || key;
    
    // Replace placeholders like {lastChanceDay} with actual values
    Object.keys(replacements).forEach(placeholder => {
        str = str.replace(new RegExp(`\\{${placeholder}\\}`, 'g'), replacements[placeholder]);
    });
    
    return str;
}

/**
 * Date Validation: Inline feedback replacing alert()
 */
function initializeDateValidation() {
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');
    
    if (!startDateInput || !endDateInput) return;
    
    function getOrCreateFeedback() {
        let feedback = document.getElementById('end_date_feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.id = 'end_date_feedback';
            feedback.className = 'invalid-feedback';
            endDateInput.parentNode.appendChild(feedback);
        }
        return feedback;
    }
    
    function validateDates() {
        const startDate = startDateInput.value;
        const endDate = endDateInput.value;
        const feedback = getOrCreateFeedback();
        
        if (startDate && endDate) {
            const start = new Date(startDate);
            const end = new Date(endDate);
            if (end <= start) {
                endDateInput.classList.add('is-invalid');
                feedback.textContent = t('endDateAfterStart');
                feedback.style.display = 'block';
                return;
            }
            const durationDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
            if (durationDays < 7) {
                endDateInput.classList.remove('is-invalid');
                feedback.className = 'form-text text-warning';
                feedback.textContent = t('shortDurationWarning', {durationDays: durationDays});
                feedback.style.display = 'block';
                return;
            }
        }
        endDateInput.classList.remove('is-invalid');
        feedback.className = 'invalid-feedback';
        feedback.style.display = 'none';
    }
    
    endDateInput.addEventListener('change', validateDates);
    startDateInput.addEventListener('change', validateDates);
}

/**
 * Toggle Custom Email Content Fields
 */
function toggleCustomEmailContent() {
    const checkbox = document.getElementById('use_custom_email_content');
    const fieldsContainer = document.getElementById('customContentFields');
    
    if (!checkbox || !fieldsContainer) return;
    
    if (checkbox.checked) {
        fieldsContainer.style.display = 'block';
    } else {
        fieldsContainer.style.display = 'none';
    }
}

/**
 * Toggle Reminder Delay Fields
 */
function toggleReminderFields() {
    const checkbox = document.getElementById('reminder_enabled');
    const fieldsContainer = document.getElementById('reminderDelayFields');
    
    if (!checkbox || !fieldsContainer) return;
    
    if (checkbox.checked) {
        fieldsContainer.style.display = 'block';
    } else {
        fieldsContainer.style.display = 'none';
    }
}

/**
 * Calculate and Display Midpoint Reminder Timing and Last Chance Reminder
 * This function calculates dual reminder dates:
 * 1. Midpoint Reminder: Sent halfway through campaign duration
 * 2. Last Chance Reminder: Sent X days BEFORE campaign closes
 */
function updateMidpointReminderDisplay() {
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');
    const reminderDelaySelect = document.getElementById('reminder_delay_days');
    const midpointDisplay = document.getElementById('midpointDateDisplay');
    const warningAlert = document.getElementById('reminderSpacingWarning');
    const warningMessage = document.getElementById('reminderSpacingMessage');
    
    if (!startDateInput || !endDateInput || !midpointDisplay) return;
    
    const startDate = startDateInput.value;
    const endDate = endDateInput.value;
    const reminderDelay = reminderDelaySelect ? (parseInt(reminderDelaySelect.value) || 10) : 10;
    
    if (!startDate || !endDate) {
        midpointDisplay.innerHTML = `<i class="fas fa-calendar-alt me-2 text-muted"></i><span class="text-muted">${t('selectDates')}</span>`;
        if (warningAlert) warningAlert.classList.add('d-none');
        return;
    }
    
    const start = new Date(startDate);
    const end = new Date(endDate);
    
    // Validate dates
    if (end <= start) {
        midpointDisplay.innerHTML = `<i class="fas fa-exclamation-circle me-2 text-danger"></i><span class="text-danger">${t('endDateMustBeAfter')}</span>`;
        if (warningAlert) warningAlert.classList.add('d-none');
        return;
    }
    
    // Calculate campaign duration in days
    const durationMs = end - start;
    const durationDays = Math.ceil(durationMs / (1000 * 60 * 60 * 24));
    
    // Calculate midpoint date (sent first)
    const midpointMs = start.getTime() + (durationMs / 2);
    const midpointDate = new Date(midpointMs);
    const midpointDay = Math.ceil(durationDays / 2);
    
    // Calculate Last Chance date (sent X days BEFORE end)
    const lastChanceDate = new Date(end);
    lastChanceDate.setDate(lastChanceDate.getDate() - reminderDelay);
    const lastChanceDay = durationDays - reminderDelay;
    
    // Format dates for display
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    const formattedMidpoint = midpointDate.toLocaleDateString('en-US', options);
    const formattedLastChance = lastChanceDate.toLocaleDateString('en-US', options);
    
    // Update display with BOTH reminders
    midpointDisplay.innerHTML = `
        <i class="fas fa-calendar-check me-2 text-success"></i>
        <strong>${t('midpointLabel')}</strong> ${formattedMidpoint} (Day ${midpointDay})
        <br>
        <i class="fas fa-exclamation-triangle me-2 text-danger"></i>
        <strong>${t('lastChanceLabel')}</strong> ${formattedLastChance} (Day ${lastChanceDay})
    `;
    
    // Check for spacing issues and display warnings
    if (warningAlert && warningMessage) {
        let showWarning = false;
        let warningText = '';
        
        // Warning 1: Last Chance reminder BEFORE midpoint (wrong order!)
        if (lastChanceDay <= midpointDay) {
            showWarning = true;
            const minOffset = durationDays - midpointDay + 1;
            warningText = t('warningLastChanceBefore', { lastChanceDay, midpointDay, minOffset });
        }
        // Warning 2: Reminders too close together (within 3 days)
        else if (Math.abs(lastChanceDay - midpointDay) < 3) {
            showWarning = true;
            warningText = t('warningTooClose', { lastChanceDay, midpointDay });
        }
        // Warning 3: Last Chance too close to end (< 3 days)
        else if (reminderDelay < 3) {
            showWarning = true;
            warningText = t('warningNotEnoughTime', { reminderDelay });
        }
        
        if (showWarning) {
            warningMessage.textContent = warningText;
            warningAlert.classList.remove('d-none');
        } else {
            warningAlert.classList.add('d-none');
        }
    }
}

/**
 * Email Preview Function
 * Opens a modal with email preview for different email types
 * @param {string} emailType - Type of email to preview (invitation, reminder_primary, reminder_midpoint)
 * @param {number} campaignId - Campaign ID for the preview
 */
function previewEmail(emailType, campaignId) {
    const previewUrl = `/business/campaigns/${campaignId}/email-preview?email_type=${emailType}`;
    
    const modalElement = document.getElementById('emailPreviewModal');
    const contentDiv = document.getElementById('emailPreviewContent');
    const modalTitle = document.getElementById('emailPreviewModalLabel');
    
    if (!modalElement || !contentDiv) return;
    
    // Show modal
    const modal = new bootstrap.Modal(modalElement);
    
    // Reset content to loading state
    contentDiv.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">${t('loading')}</span>
            </div>
            <p class="mt-3 text-muted">${t('loadingPreview')}</p>
        </div>
    `;
    
    // Update modal title based on email type
    if (modalTitle) {
        let titleText = t('emailPreviewTitle');
        if (emailType === 'invitation') {
            titleText = `<i class="fas fa-envelope me-2"></i>${t('invitationEmailTitle')}`;
        } else if (emailType === 'reminder_primary') {
            titleText = `<i class="fas fa-bell me-2"></i>${t('lastChanceReminderTitle')}`;
        } else if (emailType === 'reminder_midpoint') {
            titleText = `<i class="fas fa-clock me-2"></i>${t('midpointReminderTitle')}`;
        }
        modalTitle.innerHTML = titleText;
    }
    
    modal.show();
    
    // Fetch preview
    fetch(previewUrl, {
        method: 'GET',
        headers: {
            'Accept': 'text/html'
        },
        cache: 'no-store'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to load preview');
        }
        return response.text();
    })
    .then(html => {
        // Display the email HTML in an iframe for better isolation
        contentDiv.innerHTML = `
            <iframe 
                id="emailPreviewFrame"
                style="width: 100%; height: 600px; border: 1px solid #dee2e6; border-radius: 8px;"
                sandbox="allow-same-origin"
                title="Email Preview">
            </iframe>
        `;
        
        // Write HTML to iframe
        const iframe = document.getElementById('emailPreviewFrame');
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        iframeDoc.open();
        iframeDoc.write(html);
        iframeDoc.close();
    })
    .catch(error => {
        console.error('Preview error:', error);
        contentDiv.innerHTML = `
            <div class="alert alert-danger m-3">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>${t('errorLoadingPreview')}</strong>
                <p class="mb-0 mt-2">${t('unableToLoadPreview')}</p>
            </div>
        `;
    });
}

/**
 * Update Survey Type Consequence Notes
 * Shows a one-line note based on the selected survey type.
 */
function updateSurveyTypeNotes() {
    const conversationalRadio = document.getElementById('survey_type_conversational');
    const noteConversational = document.getElementById('noteConversational');
    const noteClassic = document.getElementById('noteClassic');
    
    if (!conversationalRadio || (!noteConversational && !noteClassic)) return;
    
    if (conversationalRadio.checked) {
        if (noteConversational) noteConversational.classList.remove('d-none');
        if (noteClassic) noteClassic.classList.add('d-none');
    } else {
        if (noteClassic) noteClassic.classList.remove('d-none');
        if (noteConversational) noteConversational.classList.add('d-none');
    }
}

/**
 * Initialize All Campaign Form Features
 * Call this function when the DOM is ready
 */
function initializeCampaignForm() {
    // Initialize date validation
    initializeDateValidation();
    
    // Initialize custom email content toggle
    const emailCheckbox = document.getElementById('use_custom_email_content');
    if (emailCheckbox) {
        emailCheckbox.addEventListener('change', toggleCustomEmailContent);
        toggleCustomEmailContent(); // Initialize on page load
    }
    
    // Initialize reminder fields toggle
    const reminderCheckbox = document.getElementById('reminder_enabled');
    if (reminderCheckbox) {
        reminderCheckbox.addEventListener('change', toggleReminderFields);
        toggleReminderFields(); // Initialize on page load
    }
    
    // Initialize midpoint reminder display
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');
    const reminderDelaySelect = document.getElementById('reminder_delay_days');
    
    if (startDateInput && endDateInput) {
        startDateInput.addEventListener('change', updateMidpointReminderDisplay);
        endDateInput.addEventListener('change', updateMidpointReminderDisplay);
        if (reminderDelaySelect) {
            reminderDelaySelect.addEventListener('change', updateMidpointReminderDisplay);
        }
        updateMidpointReminderDisplay(); // Initialize on page load
    }
    
    // Initialize survey type consequence notes
    const conversationalCard = document.getElementById('surveyTypeConversationalCard');
    const classicCard = document.getElementById('surveyTypeClassicCard');
    if (conversationalCard) {
        conversationalCard.addEventListener('click', updateSurveyTypeNotes);
    }
    if (classicCard) {
        classicCard.addEventListener('click', updateSurveyTypeNotes);
    }
    updateSurveyTypeNotes(); // Initialize on page load
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeCampaignForm);
} else {
    initializeCampaignForm();
}
