// Simple, bulletproof authentication system
class SimpleAuth {
    constructor() {
        this.baseUrl = this.detectBaseUrl();
        this.debug = true;
    }

    detectBaseUrl() {
        // Always use current domain, no origin detection needed
        return window.location.protocol + '//' + window.location.host;
    }

    log(message, data = null) {
        if (this.debug) {
            console.log('[SimpleAuth]', message, data || '');
        }
    }

    async requestToken(email) {
        this.log('Starting token request', { email, baseUrl: this.baseUrl });

        try {
            // Use XMLHttpRequest as fallback to fetch
            return await this.makeRequest(email);
        } catch (error) {
            this.log('Request failed', error);
            throw new Error(`Token request failed: ${error.message}`);
        }
    }

    makeRequest(email) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            const url = this.baseUrl + '/auth/request-token';
            
            this.log('Making XHR request to', url);
            
            xhr.open('POST', url, true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.setRequestHeader('Accept', 'application/json');
            
            xhr.onreadystatechange = () => {
                if (xhr.readyState === 4) {
                    this.log('XHR Response', {
                        status: xhr.status,
                        statusText: xhr.statusText,
                        responseText: xhr.responseText.substring(0, 200)
                    });
                    
                    if (xhr.status >= 200 && xhr.status < 300) {
                        try {
                            const data = JSON.parse(xhr.responseText);
                            resolve(data);
                        } catch (parseError) {
                            reject(new Error(`JSON parse error: ${parseError.message}`));
                        }
                    } else {
                        reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
                    }
                }
            };
            
            xhr.onerror = () => {
                this.log('XHR Network error');
                reject(new Error('Network error occurred'));
            };
            
            xhr.ontimeout = () => {
                this.log('XHR Timeout');
                reject(new Error('Request timeout'));
            };
            
            xhr.timeout = 30000; // 30 second timeout
            
            const payload = JSON.stringify({ email: email.trim().toLowerCase() });
            this.log('Sending payload', payload);
            xhr.send(payload);
        });
    }
}

// Global instance
window.simpleAuth = new SimpleAuth();