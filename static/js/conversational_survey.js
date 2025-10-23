// Conversational AI Survey JavaScript
// V2 Utility Functions for Show/Hide
function hideElement(id) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.add("v2-hidden");
        el.classList.remove("v2-visible");
    }
}

function showElement(id) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.add("v2-visible");
        el.classList.remove("v2-hidden");
    }
}
console.log('=== CONVERSATIONAL_SURVEY.JS LOADED SUCCESSFULLY ===');

let conversationState = {
    authToken: null,
    conversationId: null,
    messages: [],
    surveyData: {},
    currentStep: 'setup',
    isComplete: false
};

// Initialize the conversational survey
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing conversational survey...');
    console.log('isAuthenticated:', window.isAuthenticated);
    console.log('userEmail:', window.userEmail);
    
    // Force setup regardless of authentication status for debugging
    setupEventListeners();
    
    // Initialize authentication
    initializeAuthentication();
});

function initializeAuthentication() {
    console.log('Checking authentication status...');
    
    // Check if user is authenticated via server-side template
    if (window.isAuthenticated) {
        console.log('User is authenticated');
        conversationState.authToken = 'server-authenticated'; // Flag for server-auth
        // Pre-fill email if available
        if (document.getElementById('respondentEmail') && window.userEmail) {
            document.getElementById('respondentEmail').value = window.userEmail;
        }
        // Form should already be visible from template
    } else {
        console.log('User not authenticated, showing auth required');
        showAuthRequired();
    }
}

function showAuthRequired() {
    showElement('authCheck');
    hideElement('surveySetup');
}

function showSurveySetup() {
    hideElement('authCheck');
    showElement('surveySetup');
}

function setupEventListeners() {
    // Setup form submission - ensure form exists first
    const setupForm = document.getElementById('setupForm');
    if (setupForm) {
        setupForm.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log('Form submitted, starting conversation...');
            startConversation();
        });
        console.log('Setup form event listener attached successfully');
    } else {
        console.error('Setup form not found!');
    }
    
    // Send message on button click
    const sendButton = document.getElementById('sendButton');
    if (sendButton) {
        sendButton.addEventListener('click', function() {
            sendMessage();
        });
    }
    
    // Send message on Enter key (but allow Shift+Enter for new lines)
    const userInput = document.getElementById('userInput');
    if (userInput) {
        userInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
}

function startConversation() {
    console.log('startConversation called');
    
    const companyName = document.getElementById('companyName').value.trim();
    const respondentName = document.getElementById('respondentName').value.trim();
    const respondentEmail = document.getElementById('respondentEmail').value.trim();
    const tenureWithFc = document.getElementById('tenureWithFc').value;
    
    console.log('Form values:', {companyName, respondentName, respondentEmail, tenureWithFc});
    
    if (!companyName || !respondentName || !respondentEmail || !tenureWithFc) {
        // Show error in UI instead of alert
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger mt-3';
        errorDiv.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Please fill in all required fields.';
        const form = document.getElementById('setupForm');
        form.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 4000);
        return;
    }
    
    // Store survey data
    conversationState.surveyData = {
        company_name: companyName,
        respondent_name: respondentName,
        respondent_email: respondentEmail,
        tenure_with_fc: tenureWithFc
    };
    
    // Show loading state
    showLoadingState();
    
    // Get CSRF token
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;
    
    // Start conversation with AI
    fetch('/api/start_conversation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
            // No Authorization header needed - server uses session
        },
        body: JSON.stringify({
            company_name: companyName,
            respondent_name: respondentName,
            respondent_email: respondentEmail,
            tenure_with_fc: tenureWithFc
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        conversationState.conversationId = data.conversation_id;
        conversationState.currentStep = data.step;
        
        // Initialize extracted_data with data from server
        if (data.extracted_data) {
            conversationState.surveyData.extracted_data = data.extracted_data;
            console.log('Initial extracted data from server:', data.extracted_data);
        }
        
        // Show conversation interface
        showConversationInterface();
        
        // Add AI's first message
        addMessage('ai', data.message);
        updateProgress(data.progress || 0);
        
    })
    .catch(error => {
        console.error('Error starting conversation:', error);
        // Show error in UI instead of alert
        showSurveySetup();
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger mt-3';
        
        // Safely construct error message to prevent XSS
        const icon = document.createElement('i');
        icon.className = 'fas fa-exclamation-triangle me-2';
        errorDiv.appendChild(icon);
        
        const errorText = document.createTextNode('Error starting conversation: ' + error.message);
        errorDiv.appendChild(errorText);
        
        const form = document.getElementById('setupForm');
        form.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 4000);
    });
}

function sendMessage() {
    const userInput = document.getElementById('userInput');
    const message = userInput.value.trim();
    
    if (!message) {
        return;
    }
    
    // Add user message to chat
    addMessage('user', message);
    
    // Clear input
    userInput.value = '';
    
    // Show loading state
    showTypingIndicator();
    
    // Get CSRF token
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;
    
    // Send message to AI
    fetch('/api/conversation_response', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
            // No Authorization header needed - server uses session
        },
        body: JSON.stringify({
            conversation_id: conversationState.conversationId,
            user_input: message,
            survey_data: {
                ...conversationState.surveyData,
                conversation_history: conversationState.messages,
                extracted_data: conversationState.surveyData.extracted_data || {},
                step_count: conversationState.messages.filter(m => m.sender === 'user').length,
                company_name: conversationState.surveyData.company_name,
                respondent_name: conversationState.surveyData.respondent_name
            }
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Remove typing indicator
        removeTypingIndicator();
        
        // Add AI response
        addMessage('ai', data.message);
        
        // Update progress
        updateProgress(data.progress || 0);
        
        // Update extracted data if provided by AI
        if (data.extracted_data) {
            conversationState.surveyData.extracted_data = {
                ...conversationState.surveyData.extracted_data || {},
                ...data.extracted_data
            };
            console.log('Updated extracted data:', conversationState.surveyData.extracted_data);
        }
        
        // Check if survey is complete
        if (data.is_complete) {
            finalizeSurvey();
        }
        
    })
    .catch(error => {
        console.error('Error sending message:', error);
        removeTypingIndicator();
        addMessage('ai', 'I apologize, but I encountered an error. Could you please try again?');
    });
}

function addMessage(sender, message) {
    const chatMessages = document.getElementById('chatMessages');
    const messageElement = document.createElement('div');
    messageElement.className = `chat-message ${sender === 'ai' ? 'assistant' : 'user'}`;
    
    // Safe DOM manipulation - use textContent then apply formatting
    const formattedContent = formatMessageSafe(message);
    messageElement.appendChild(formattedContent);
    
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Store message in conversation state
    conversationState.messages.push({
        sender: sender,
        message: message,
        timestamp: new Date().toISOString()
    });
}

function formatMessage(message) {
    // Convert markdown-style formatting to HTML (legacy function - use formatMessageSafe instead)
    return message
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
}

function formatMessageSafe(message) {
    // Safe formatting using DOM methods to prevent XSS
    const container = document.createElement('span');
    
    // Split message by newlines and handle each line
    const lines = message.split('\n');
    
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i];
        const lineContainer = document.createElement('span');
        
        // Process bold and italic formatting safely
        const parts = [];
        let currentIndex = 0;
        
        // Find bold patterns (**text**)
        const boldRegex = /\*\*(.*?)\*\*/g;
        let match;
        while ((match = boldRegex.exec(line)) !== null) {
            // Add text before the match
            if (match.index > currentIndex) {
                parts.push({
                    type: 'text',
                    content: line.slice(currentIndex, match.index)
                });
            }
            // Add bold content
            parts.push({
                type: 'bold',
                content: match[1]
            });
            currentIndex = match.index + match[0].length;
        }
        
        // Add remaining text
        if (currentIndex < line.length) {
            parts.push({
                type: 'text',
                content: line.slice(currentIndex)
            });
        }
        
        // If no formatting found, treat entire line as text
        if (parts.length === 0) {
            parts.push({
                type: 'text',
                content: line
            });
        }
        
        // Process italic patterns within each part
        const processedParts = [];
        parts.forEach(part => {
            if (part.type === 'text') {
                const italicRegex = /\*(.*?)\*/g;
                let italicMatch;
                let lastIndex = 0;
                while ((italicMatch = italicRegex.exec(part.content)) !== null) {
                    // Add text before italic
                    if (italicMatch.index > lastIndex) {
                        processedParts.push({
                            type: 'text',
                            content: part.content.slice(lastIndex, italicMatch.index)
                        });
                    }
                    // Add italic content
                    processedParts.push({
                        type: 'italic',
                        content: italicMatch[1]
                    });
                    lastIndex = italicMatch.index + italicMatch[0].length;
                }
                // Add remaining text
                if (lastIndex < part.content.length) {
                    processedParts.push({
                        type: 'text',
                        content: part.content.slice(lastIndex)
                    });
                }
            } else {
                processedParts.push(part);
            }
        });
        
        // Create DOM elements for each part
        processedParts.forEach(part => {
            let element;
            switch (part.type) {
                case 'bold':
                    element = document.createElement('strong');
                    element.textContent = part.content;
                    break;
                case 'italic':
                    element = document.createElement('em');
                    element.textContent = part.content;
                    break;
                default:
                    element = document.createTextNode(part.content);
                    break;
            }
            lineContainer.appendChild(element);
        });
        
        container.appendChild(lineContainer);
        
        // Add line break if not the last line
        if (i < lines.length - 1) {
            container.appendChild(document.createElement('br'));
        }
    }
    
    return container;
}

// Add missing helper functions
function showLoadingState() {
    hideElement('surveySetup');
    hideElement('conversationInterface');
    showElement('loadingState');
    hideElement('surveyComplete');
}

function showConversationInterface() {
    hideElement('surveySetup');
    showElement('conversationInterface');
    hideElement('loadingState');
    hideElement('surveyComplete');
}

function showTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    const typingElement = document.createElement('div');
    typingElement.className = 'chat-message assistant typing-indicator';
    typingElement.id = 'typingIndicator';
    typingElement.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
    chatMessages.appendChild(typingElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

function updateProgress(progress) {
    const progressBar = document.getElementById('progressBar');
    if (progressBar) {
        progressBar.style.width = progress + '%';
        progressBar.setAttribute('aria-valuenow', progress);
    }
}

function finalizeSurvey() {
    hideElement('surveySetup');
    hideElement('conversationInterface');
    hideElement('loadingState');
    showElement('surveyComplete');
}

function showTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    const typingElement = document.createElement('div');
    typingElement.id = 'typingIndicator';
    typingElement.className = 'typing-indicator';
    typingElement.innerHTML = `
        <div class="spinner-border spinner-border-sm" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        VOÏA is typing...
    `;
    
    chatMessages.appendChild(typingElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
    const typingElement = document.getElementById('typingIndicator');
    if (typingElement) {
        typingElement.remove();
    }
}

function updateProgress(progress) {
    const progressBar = document.getElementById('progressBar');
    progressBar.style.width = `${progress}%`;
    progressBar.setAttribute('aria-valuenow', progress);
}

function showConversationInterface() {
    hideElement('surveySetup');
    hideElement('loadingState');
    showElement('conversationInterface');
}

function showLoadingState() {
    hideElement('surveySetup');
    hideElement('conversationInterface');
    showElement('loadingState');
}

function finalizeSurvey() {
    console.log('=== FINALIZE CONVERSATIONAL SURVEY CALLED ===');
    // Hide input area
    hideElement('inputArea');
    
    // Show loading state
    showLoadingState();
    
    // Get CSRF token
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;
    
    // Finalize survey
    fetch('/api/finalize_conversation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + conversationState.authToken,
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            conversation_id: conversationState.conversationId,
            survey_data: conversationState.surveyData,
            messages: conversationState.messages
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Show completion state
        showSurveyComplete();
        
        // Token invalidation happens server-side automatically
        console.log('Conversational survey finalized successfully:', data);
        console.log('Token has been invalidated server-side for security');
    })
    .catch(error => {
        console.error('Error finalizing survey:', error);
        // Show error message in UI instead of alert
        addMessage('ai', 'I apologize, but there was an error finalizing your survey. Please try refreshing the page or contact support if the issue persists.');
        showElement('inputArea'); // Re-enable input
    });
}

function showSurveyComplete() {
    hideElement('loadingState');
    hideElement('conversationInterface');
    showElement('surveyComplete');
    
    // Update progress to 100%
    updateProgress(100);
}

// Clear authentication session and redirect to get new token  
function clearAuthenticationAndRedirect(message) {
    console.log('conversational clearAuthenticationAndRedirect called with message:', message);
    
    // Clear session data by making a logout request
    fetch('/api/logout_session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        console.log('Conversational logout response:', response);
        return response.json();
    })
    .then(data => {
        console.log('Conversational logout successful:', data);
        // Redirect without alert
        console.log('Redirecting to /server-auth from conversational survey');
        window.location.href = '/server-auth';
    })
    .catch(error => {
        console.log('Conversational logout failed, redirecting anyway:', error);
        // Even if logout fails, redirect anyway
        console.log('Logout failed, redirecting anyway:', message);
        window.location.href = '/server-auth';
    });
}

// CSS for styling (add to your CSS file)
const styles = `
<style>
.ai-bubble {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    max-width: 80%;
}

.user-bubble {
    background-color: #007bff;
    color: white;
    max-width: 80%;
}

.avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background-color: #f8f9fa;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
}

.typing-indicator {
    display: flex;
    align-items: center;
    gap: 4px;
}

.typing-indicator span {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #6c757d;
    animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(1) {
    animation-delay: 0s;
}

.typing-indicator span:nth-child(2) {
    animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
    animation-delay: 0.4s;
}

@keyframes typing {
    0%, 60%, 100% {
        transform: scale(0.8);
        opacity: 0.5;
    }
    30% {
        transform: scale(1);
        opacity: 1;
    }
}
</style>
`;

// Add styles to head
document.head.insertAdjacentHTML('beforeend', styles);

// Function to start a new session
function startNewSession() {
    console.log('Starting new session - clearing state and redirecting');
    
    // Clear current conversation state
    conversationState = {
        authToken: null,
        conversationId: null,
        messages: [],
        surveyData: {},
        currentStep: 'setup',
        isComplete: false
    };
    
    // Redirect to get new token
    window.location.href = '/server-auth';
}