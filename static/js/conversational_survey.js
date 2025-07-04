// Conversational AI Survey JavaScript

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
    checkAuthentication();
    setupEventListeners();
});

function checkAuthentication() {
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
                conversationState.authToken = token;
                // Pre-fill email if available
                if (document.getElementById('respondentEmail')) {
                    document.getElementById('respondentEmail').value = email;
                }
                showSurveySetup();
            } else {
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
    document.getElementById('authCheck').style.display = 'block';
    document.getElementById('surveySetup').style.display = 'none';
}

function showSurveySetup() {
    document.getElementById('authCheck').style.display = 'none';
    document.getElementById('surveySetup').style.display = 'block';
}

function setupEventListeners() {
    // Setup form submission
    document.getElementById('setupForm').addEventListener('submit', function(e) {
        e.preventDefault();
        startConversation();
    });
    
    // Send message on button click
    document.getElementById('sendButton').addEventListener('click', function() {
        sendMessage();
    });
    
    // Send message on Enter key (but allow Shift+Enter for new lines)
    document.getElementById('userInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

function startConversation() {
    const companyName = document.getElementById('companyName').value.trim();
    const respondentName = document.getElementById('respondentName').value.trim();
    const respondentEmail = document.getElementById('respondentEmail').value.trim();
    
    if (!companyName || !respondentName || !respondentEmail) {
        alert('Please fill in all required fields.');
        return;
    }
    
    // Store survey data
    conversationState.surveyData = {
        company_name: companyName,
        respondent_name: respondentName,
        respondent_email: respondentEmail
    };
    
    // Show loading state
    showLoadingState();
    
    // Start conversation with AI
    fetch('/api/start_conversation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + conversationState.authToken
        },
        body: JSON.stringify({
            company_name: companyName,
            respondent_name: respondentName,
            respondent_email: respondentEmail
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        conversationState.conversationId = data.conversation_id;
        conversationState.currentStep = data.step;
        
        // Show conversation interface
        showConversationInterface();
        
        // Add AI's first message
        addMessage('ai', data.message);
        updateProgress(data.progress || 0);
        
    })
    .catch(error => {
        console.error('Error starting conversation:', error);
        alert('Error starting conversation: ' + error.message);
        showSurveySetup();
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
    
    // Send message to AI
    fetch('/api/conversation_response', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + conversationState.authToken
        },
        body: JSON.stringify({
            conversation_id: conversationState.conversationId,
            user_input: message,
            survey_data: conversationState.surveyData
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
    messageElement.className = `message ${sender}-message mb-3`;
    
    if (sender === 'ai') {
        messageElement.innerHTML = `
            <div class="d-flex align-items-start">
                <div class="avatar me-3">
                    <i class="fas fa-robot text-primary"></i>
                </div>
                <div class="message-content">
                    <div class="message-bubble ai-bubble p-3 rounded">
                        ${formatMessage(message)}
                    </div>
                    <small class="text-muted">AI Assistant</small>
                </div>
            </div>
        `;
    } else {
        messageElement.innerHTML = `
            <div class="d-flex align-items-start justify-content-end">
                <div class="message-content text-end">
                    <div class="message-bubble user-bubble p-3 rounded">
                        ${formatMessage(message)}
                    </div>
                    <small class="text-muted">You</small>
                </div>
                <div class="avatar ms-3">
                    <i class="fas fa-user text-secondary"></i>
                </div>
            </div>
        `;
    }
    
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
    // Convert markdown-style formatting to HTML
    return message
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
}

function showTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    const typingElement = document.createElement('div');
    typingElement.id = 'typingIndicator';
    typingElement.className = 'message ai-message mb-3';
    typingElement.innerHTML = `
        <div class="d-flex align-items-start">
            <div class="avatar me-3">
                <i class="fas fa-robot text-primary"></i>
            </div>
            <div class="message-content">
                <div class="message-bubble ai-bubble p-3 rounded">
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
                <small class="text-muted">AI is typing...</small>
            </div>
        </div>
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
    document.getElementById('surveySetup').style.display = 'none';
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('conversationInterface').style.display = 'block';
}

function showLoadingState() {
    document.getElementById('surveySetup').style.display = 'none';
    document.getElementById('conversationInterface').style.display = 'none';
    document.getElementById('loadingState').style.display = 'block';
}

function finalizeSurvey() {
    // Hide input area
    document.getElementById('inputArea').style.display = 'none';
    
    // Show loading state
    showLoadingState();
    
    // Finalize survey
    fetch('/api/finalize_conversation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + conversationState.authToken
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
        
    })
    .catch(error => {
        console.error('Error finalizing survey:', error);
        alert('Error finalizing survey: ' + error.message);
    });
}

function showSurveyComplete() {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('conversationInterface').style.display = 'none';
    document.getElementById('surveyComplete').style.display = 'block';
    
    // Update progress to 100%
    updateProgress(100);
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