// Survey JavaScript functionality

let currentStep = 1;
let selectedNpsScore = null;

// Initialize the survey
document.addEventListener('DOMContentLoaded', function() {
    updateProgress();
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
            
            if (!companyName || !respondentName || !respondentEmail) {
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
    // Show loading state
    document.getElementById('surveyForm').classList.add('d-none');
    document.getElementById('loadingState').classList.remove('d-none');
    
    // Collect all form data
    const formData = {
        company_name: document.getElementById('companyName').value.trim(),
        respondent_name: document.getElementById('respondentName').value.trim(),
        respondent_email: document.getElementById('respondentEmail').value.trim(),
        nps_score: selectedNpsScore,
        satisfaction_rating: document.getElementById('satisfactionRating').value || null,
        product_value_rating: document.getElementById('productValueRating').value || null,
        service_rating: document.getElementById('serviceRating').value || null,
        pricing_rating: document.getElementById('pricingRating').value || null,
        improvement_feedback: document.getElementById('improvementFeedback').value.trim() || null,
        recommendation_reason: document.getElementById('recommendationReason').value.trim() || null,
        additional_comments: document.getElementById('additionalComments').value.trim() || null
    };
    
    // Submit to server
    fetch('/submit_survey', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
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
        
        console.log('Survey submitted successfully:', data);
    })
    .catch(error => {
        console.error('Error submitting survey:', error);
        
        // Hide loading state and show form again
        document.getElementById('loadingState').classList.add('d-none');
        document.getElementById('surveyForm').classList.remove('d-none');
        
        alert('There was an error submitting your survey. Please try again.');
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
        
        // Optionally restore to saved step
        // currentStep = data.current_step || 1;
    }
}

// Add event listeners for auto-save
document.getElementById('companyName').addEventListener('input', autoSave);
document.getElementById('respondentName').addEventListener('input', autoSave);
document.getElementById('respondentEmail').addEventListener('input', autoSave);

// Clear saved data on successful submission
function clearSavedData() {
    localStorage.removeItem('surveyDraft');
}

// Load saved data when page loads
loadSavedData();
