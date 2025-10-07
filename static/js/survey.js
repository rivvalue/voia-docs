// Survey JavaScript functionality
console.log('=== SURVEY.JS LOADED SUCCESSFULLY ===');

let currentStep = 1;
let selectedNpsScore = null;
let authToken = null;

// Initialize the survey
document.addEventListener('DOMContentLoaded', function() {
    console.log('Survey form loaded');
    
    // Check for user email mismatch and clear conflicting data before loading
    if (window.userEmail) {
        const storedEmail = localStorage.getItem('auth_email') || '';
        if (storedEmail && storedEmail !== window.userEmail) {
            console.log('Detected different authenticated user - clearing old localStorage data');
            localStorage.clear(); // Clear all localStorage to prevent cross-user data pollution
        }
    }
    
    updateProgress();
    loadSavedData();
    
    // Check if user is authenticated via server-side template
    if (window.isAuthenticated === false) {
        showAuthRequired();
    }
});

function nextStep(stepNumber) {
    // Validate current step
    if (!validateCurrentStep()) {
        return;
    }
    
    // Hide current step
    document.getElementById(`step${currentStep}`).classList.add('d-none');
    
    // Show next step
    document.getElementById(`step${stepNumber}`).classList.remove('d-none');
    
    currentStep = stepNumber;
    updateProgress();
}

function previousStep(stepNumber) {
    // Hide current step
    document.getElementById(`step${currentStep}`).classList.add('d-none');
    
    // Show previous step
    document.getElementById(`step${stepNumber}`).classList.remove('d-none');
    
    currentStep = stepNumber;
    updateProgress();
}

function validateCurrentStep() {
    switch(currentStep) {
        case 1:
            const companyName = document.getElementById('companyName').value.trim();
            const respondentName = document.getElementById('respondentName').value.trim();
            const respondentEmail = document.getElementById('respondentEmail').value.trim();
            const tenureWithFc = document.getElementById('tenureWithFc').value;
            
            if (!companyName || !respondentName || !respondentEmail || !tenureWithFc) {
                showValidationError('Please fill in all required fields.');
                return false;
            }
            
            // Basic email validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(respondentEmail)) {
                showValidationError('Please enter a valid email address.');
                return false;
            }
            break;
            
        case 2:
            const npsScore = document.querySelector('input[name="npsScore"]:checked');
            if (!npsScore) {
                showValidationError('Please select an NPS score.');
                return false;
            }
            selectedNpsScore = parseInt(npsScore.value);
            break;
            
        case 3:
            // Validate that at least satisfaction and service ratings are filled
            const satisfactionRating = document.getElementById('satisfactionRating').value;
            const serviceRating = document.getElementById('serviceRating').value;
            
            if (!satisfactionRating || !serviceRating) {
                showValidationError('Please provide ratings for satisfaction and Archelo Group service delivery.');
                return false;
            }
            break;
    }
    
    return true;
}

function updateProgress() {
    const progressBar = document.getElementById('progressBar');
    const progress = (currentStep / 4) * 100;
    progressBar.style.width = `${progress}%`;
}

function handleNpsSelection() {
    if (!validateCurrentStep()) {
        return;
    }
    
    // Update follow-up question based on NPS score
    const reasonLabel = document.getElementById('reasonLabel');
    
    if (selectedNpsScore >= 9) {
        reasonLabel.textContent = 'What do you like most about our service?';
    } else if (selectedNpsScore >= 7) {
        reasonLabel.textContent = 'What would make you more likely to recommend us?';
    } else {
        reasonLabel.textContent = 'What are the main reasons for your score?';
    }
    
    nextStep(3);
}

function submitSurvey() {
    console.log('=== SUBMIT SURVEY CALLED ===');
    // Check authentication via server-side status
    if (window.isAuthenticated === false) {
        alert('Authentication required. Please get a token first.');
        window.location.href = '/server-auth';
        return;
    }
    
    // Show loading state
    document.getElementById('surveyForm').classList.add('d-none');
    document.getElementById('loadingState').classList.remove('d-none');
    
    // Collect all form data (email will be overridden by authenticated email)
    const formData = {
        company_name: document.getElementById('companyName').value.trim(),
        respondent_name: document.getElementById('respondentName').value.trim(),
        tenure_with_fc: document.getElementById('tenureWithFc').value,
        nps_score: selectedNpsScore,
        satisfaction_rating: document.getElementById('satisfactionRating').value || null,
        product_value_rating: document.getElementById('productValueRating').value || null,
        service_rating: document.getElementById('serviceRating').value || null,
        pricing_rating: document.getElementById('pricingRating').value || null,
        improvement_feedback: document.getElementById('improvementFeedback').value.trim() || null,
        recommendation_reason: document.getElementById('recommendationReason').value.trim() || null,
        additional_comments: document.getElementById('additionalComments').value.trim() || null
    };
    
    // Get CSRF token from the form
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;
    
    // Submit to server with session-based authentication
    fetch('/submit_survey', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(formData)
    })
    .then(response => {
        // Store response status before consuming the response
        const status = response.status;
        return response.json().then(data => ({ data, status }));
    })
    .then(({ data, status }) => {
        console.log('Survey response received:', data, 'Status:', status);
        if (data.error) {
            // Handle specific error cases
            if (data.code === 'AUTH_ERROR' || data.code === 'MISSING_AUTH') {
                console.log('Authentication failed, redirecting to auth page');
                window.location.href = '/auth';
                return;
            }
            throw new Error(data.error);
        }
        
        // Show success state
        document.getElementById('loadingState').classList.add('d-none');
        document.getElementById('successState').classList.remove('d-none');
        
        // Clear stored data
        clearSavedData();
        
        // Token invalidation happens server-side automatically
        console.log('Traditional survey completed successfully:', data);
        console.log('Token has been invalidated server-side for security');
    })
    .catch(error => {
        console.error('Error submitting survey:', error);
        
        // Hide loading state and show form again
        document.getElementById('loadingState').classList.add('d-none');
        document.getElementById('surveyForm').classList.remove('d-none');
        
        // Show error message in UI instead of alert
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger mt-3';
        
        // Use safe DOM methods instead of innerHTML to prevent XSS
        const icon = document.createElement('i');
        icon.className = 'fas fa-exclamation-triangle me-2';
        errorDiv.appendChild(icon);
        
        const errorText = document.createTextNode('Error submitting survey: ' + error.message);
        errorDiv.appendChild(errorText);
        
        document.getElementById('surveyForm').appendChild(errorDiv);
        
        // Remove error message after 5 seconds
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    });
}

// Handle form submission with Enter key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        
        const activeStep = document.querySelector('.survey-step:not(.d-none)');
        const nextButton = activeStep.querySelector('.btn-primary');
        
        if (nextButton && nextButton.textContent.includes('Next')) {
            nextButton.click();
        } else if (nextButton && nextButton.textContent.includes('Submit')) {
            nextButton.click();
        }
    }
});

// Auto-save functionality (optional)
function autoSave() {
    const formData = {
        company_name: document.getElementById('companyName').value,
        respondent_name: document.getElementById('respondentName').value,
        respondent_email: document.getElementById('respondentEmail').value,
        tenure_with_fc: document.getElementById('tenureWithFc').value,
        current_step: currentStep
    };
    
    localStorage.setItem('surveyDraft', JSON.stringify(formData));
}

// Function to start a new traditional session
function startNewTraditionalSession() {
    console.log('Starting new traditional session - clearing state and redirecting');
    
    // Clear form data and current state
    currentStep = 1;
    selectedNpsScore = null;
    authToken = null;
    clearSavedData();
    
    // Redirect to get new token
    window.location.href = '/server-auth';
}

// Show validation error in UI instead of alert
function showValidationError(message) {
    // Remove any existing error messages
    const existingError = document.querySelector('.validation-error');
    if (existingError) {
        existingError.remove();
    }
    
    // Create error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-warning validation-error mt-3';
    errorDiv.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>${message}`;
    
    // Add to current step
    const currentStepDiv = document.getElementById(`step${currentStep}`);
    currentStepDiv.appendChild(errorDiv);
    
    // Remove error message after 4 seconds
    setTimeout(() => {
        errorDiv.remove();
    }, 4000);
}

// Load saved data on page load
function loadSavedData() {
    const currentUserEmail = window.userEmail || '';
    
    // First, pre-populate email if user is authenticated
    if (currentUserEmail) {
        console.log('Pre-populating email for authenticated user:', currentUserEmail);
        document.getElementById('respondentEmail').value = currentUserEmail;
        document.getElementById('respondentEmail').readOnly = true; // Make it read-only since it's authenticated
    }
    
    const savedData = localStorage.getItem('surveyDraft');
    if (savedData) {
        const data = JSON.parse(savedData);
        
        // Check if the current authenticated user is different from saved data
        const savedUserEmail = data.respondent_email || '';
        
        // If different user is authenticated, clear old data and don't load it
        if (currentUserEmail && savedUserEmail && currentUserEmail !== savedUserEmail) {
            console.log('Different user detected - clearing previous user data');
            clearSavedData();
            return;
        }
        
        // Only load data if it's for the same user or if no user is specified
        document.getElementById('companyName').value = data.company_name || '';
        document.getElementById('respondentName').value = data.respondent_name || '';
        // Only override email if no authenticated user (shouldn't happen but safety check)
        if (!currentUserEmail) {
            document.getElementById('respondentEmail').value = data.respondent_email || '';
        }
        document.getElementById('tenureWithFc').value = data.tenure_with_fc || '';
        
        // Optionally restore to saved step
        // currentStep = data.current_step || 1;
    }
}

// Add event listeners for auto-save
document.getElementById('companyName').addEventListener('input', autoSave);
document.getElementById('respondentName').addEventListener('input', autoSave);
document.getElementById('respondentEmail').addEventListener('input', autoSave);
document.getElementById('tenureWithFc').addEventListener('change', autoSave);

// Clear saved data on successful submission
function clearSavedData() {
    localStorage.removeItem('surveyDraft');
    // Also clear any old authentication data that might be lingering
    const currentUserEmail = window.userEmail || '';
    const storedEmail = localStorage.getItem('auth_email') || '';
    
    // If the current session email doesn't match stored email, clear auth data
    if (currentUserEmail && storedEmail && currentUserEmail !== storedEmail) {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_email');
    }
}

// Clear authentication session and redirect to get new token
function clearAuthenticationAndRedirect(message) {
    console.log('clearAuthenticationAndRedirect called with message:', message);
    
    // Clear session data by making a logout request
    fetch('/api/logout_session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        console.log('Logout response:', response);
        return response.json();
    })
    .then(data => {
        console.log('Logout successful:', data);
        // Show message and redirect
        alert(message);
        console.log('About to redirect to /server-auth');
        window.location.href = '/server-auth';
    })
    .catch(error => {
        console.log('Logout failed, redirecting anyway:', error);
        // Even if logout fails, redirect anyway
        alert(message);
        window.location.href = '/server-auth';
    });
}

// Authentication functions
function checkAuthentication() {
    // Get token from localStorage
    const token = localStorage.getItem('auth_token');
    const email = localStorage.getItem('auth_email');
    
    if (token && email) {
        // Verify token is still valid
        fetch('/auth/verify-token', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + token
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.valid) {
                authToken = token;
                // Pre-fill email field if available
                if (document.getElementById('respondentEmail')) {
                    document.getElementById('respondentEmail').value = email;
                    document.getElementById('respondentEmail').readOnly = true;
                }
                console.log('Authenticated as:', email);
            } else {
                // Token is invalid, remove it
                localStorage.removeItem('auth_token');
                localStorage.removeItem('auth_email');
                showAuthRequired();
            }
        })
        .catch(error => {
            console.error('Token verification failed:', error);
            showAuthRequired();
        });
    } else {
        showAuthRequired();
    }
}

function showAuthRequired() {
    // Show authentication requirement
    const authAlert = document.createElement('div');
    authAlert.className = 'alert alert-warning alert-dismissible fade show';
    authAlert.innerHTML = `
        <i class="fas fa-key me-2"></i>
        <strong>Authentication Required:</strong> You need a valid token to submit surveys.
        <a href="/auth" class="btn btn-sm btn-outline-warning ms-2">Get Token</a>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert at the top of the form
    const formContainer = document.querySelector('.card-body');
    formContainer.insertBefore(authAlert, formContainer.firstChild);
}


// Load saved data when page loads
loadSavedData();
