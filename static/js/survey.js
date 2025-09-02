// Survey JavaScript functionality

let currentStep = 1;
let selectedNpsScore = null;
let authToken = null;

// Initialize the survey
document.addEventListener('DOMContentLoaded', function() {
    updateProgress();
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
                alert('Please fill in all required fields.');
                return false;
            }
            
            // Basic email validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(respondentEmail)) {
                alert('Please enter a valid email address.');
                return false;
            }
            break;
            
        case 2:
            const npsScore = document.querySelector('input[name="npsScore"]:checked');
            if (!npsScore) {
                alert('Please select an NPS score.');
                return false;
            }
            selectedNpsScore = parseInt(npsScore.value);
            break;
            
        case 3:
            // Validate that at least satisfaction and service ratings are filled
            const satisfactionRating = document.getElementById('satisfactionRating').value;
            const serviceRating = document.getElementById('serviceRating').value;
            
            if (!satisfactionRating || !serviceRating) {
                alert('Please provide ratings for satisfaction and FC inc service delivery.');
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
    
    // Submit to server with session-based authentication
    fetch('/submit_survey', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            // Handle specific error cases
            if (data.code === 'AUTH_ERROR' || data.code === 'MISSING_AUTH') {
                alert('Authentication failed. Please get a new token.');
                window.location.href = '/auth';
                return;
            } else if (response.status === 409) {
                // Duplicate response
                const overwrite = confirm(
                    'You have already submitted a response. Would you like to overwrite it?'
                );
                if (overwrite) {
                    submitSurveyOverwrite(formData);
                    return;
                } else {
                    throw new Error('You have already submitted a response.');
                }
            }
            throw new Error(data.error);
        }
        
        // Show success state
        document.getElementById('loadingState').classList.add('d-none');
        document.getElementById('successState').classList.remove('d-none');
        
        // Clear stored data
        clearSavedData();
        
        // Clear session and redirect after successful submission
        setTimeout(() => {
            clearAuthenticationAndRedirect('Survey submitted successfully! Please get a new token for another survey.');
        }, 3000);  // Wait 3 seconds to show success message
        
        console.log('Survey submitted successfully:', data);
    })
    .catch(error => {
        console.error('Error submitting survey:', error);
        
        // Hide loading state and show form again
        document.getElementById('loadingState').classList.add('d-none');
        document.getElementById('surveyForm').classList.remove('d-none');
        
        alert('Error: ' + error.message);
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

// Load saved data on page load
function loadSavedData() {
    const savedData = localStorage.getItem('surveyDraft');
    if (savedData) {
        const data = JSON.parse(savedData);
        
        document.getElementById('companyName').value = data.company_name || '';
        document.getElementById('respondentName').value = data.respondent_name || '';
        document.getElementById('respondentEmail').value = data.respondent_email || '';
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
}

// Clear authentication session and redirect to get new token
function clearAuthenticationAndRedirect(message) {
    // Clear session data by making a logout request
    fetch('/api/logout_session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(() => {
        // Show message and redirect
        alert(message);
        window.location.href = '/server-auth';
    })
    .catch(() => {
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

function submitSurveyOverwrite(formData) {
    if (!authToken) {
        alert('Authentication required. Please get a token first.');
        window.location.href = '/auth';
        return;
    }
    
    // Show loading state again
    document.getElementById('surveyForm').classList.add('d-none');
    document.getElementById('loadingState').classList.remove('d-none');
    
    // Submit to overwrite endpoint
    fetch('/submit_survey_overwrite', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + authToken
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Show success state
        document.getElementById('loadingState').classList.add('d-none');
        document.getElementById('successState').classList.remove('d-none');
        
        // Update success message to indicate overwrite
        const successDiv = document.getElementById('successState');
        const heading = successDiv.querySelector('h5');
        if (heading && data.action === 'updated') {
            heading.textContent = 'Survey Updated Successfully!';
        }
        
        // Clear stored data
        clearSavedData();
        
        // Clear session and redirect after successful overwrite
        setTimeout(() => {
            clearAuthenticationAndRedirect('Survey updated successfully! Please get a new token for another survey.');
        }, 3000);  // Wait 3 seconds to show success message
        
        console.log('Survey overwritten successfully:', data);
    })
    .catch(error => {
        console.error('Error overwriting survey:', error);
        
        // Hide loading state and show form again
        document.getElementById('loadingState').classList.add('d-none');
        document.getElementById('surveyForm').classList.remove('d-none');
        
        alert('Error: ' + error.message);
    });
}

// Load saved data when page loads
loadSavedData();
