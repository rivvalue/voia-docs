/**
 * Translation Loader - Async JSON translation file loader with caching
 * Replaces inline translation objects to reduce page weight
 * @version 1.0.0
 */

class TranslationLoader {
    constructor(locale = 'en') {
        this.locale = locale;
        this.cache = {};
        this.loading = {};
        this.listeners = [];
    }
    
    /**
     * Load translation namespace asynchronously
     * @param {string} namespace - Translation namespace (e.g., 'dashboard', 'common')
     * @returns {Promise<Object>} - Translation object
     */
    async load(namespace) {
        // Check cache first
        if (this.cache[namespace]) {
            return this.cache[namespace];
        }
        
        // Prevent duplicate fetches
        if (this.loading[namespace]) {
            return this.loading[namespace];
        }
        
        // Fetch with timeout and retry
        this.loading[namespace] = this.fetchWithRetry(namespace);
        
        try {
            const translations = await this.loading[namespace];
            this.cache[namespace] = translations;
            this.notifyLoaded(namespace);
            return translations;
        } finally {
            delete this.loading[namespace];
        }
    }
    
    /**
     * Fetch translation file with retry logic
     * @param {string} namespace - Translation namespace
     * @param {number} retries - Number of retry attempts
     * @returns {Promise<Object>} - Translation object
     */
    async fetchWithRetry(namespace, retries = 3) {
        const url = `/static/i18n/${this.locale}/${namespace}.json`;
        
        for (let i = 0; i < retries; i++) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 5000);
                
                const response = await fetch(url, {
                    signal: controller.signal,
                    cache: 'force-cache' // Use browser cache aggressively
                });
                
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                return await response.json();
                
            } catch (error) {
                if (i === retries - 1) {
                    console.error(`❌ Failed to load ${namespace} translations after ${retries} attempts:`, error);
                    return this.getFallbackTranslations(namespace);
                }
                
                // Exponential backoff
                await this.delay(1000 * (i + 1));
            }
        }
    }
    
    /**
     * Get fallback translations (empty object - uses English keys)
     * @param {string} namespace - Translation namespace
     * @returns {Object} - Empty object for fallback
     */
    getFallbackTranslations(namespace) {
        console.warn(`⚠️  Using fallback for ${namespace} - English text will display`);
        return {};
    }
    
    /**
     * Helper: Delay for retry backoff
     * @param {number} ms - Milliseconds to delay
     * @returns {Promise<void>}
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * Translate a key with fallback
     * @param {string} key - Translation key
     * @param {string} fallback - Fallback text (defaults to key)
     * @param {string} namespace - Namespace to use (optional)
     * @returns {string} - Translated text or fallback
     */
    t(key, fallback = key, namespace = null) {
        if (namespace && this.cache[namespace]) {
            return this.cache[namespace][key] || fallback;
        }
        
        // Search all cached namespaces
        for (const ns in this.cache) {
            if (this.cache[ns][key]) {
                return this.cache[ns][key];
            }
        }
        
        return fallback;
    }
    
    /**
     * Add event listener for translation loaded event
     * @param {Function} callback - Callback function
     */
    onLoaded(callback) {
        this.listeners.push(callback);
    }
    
    /**
     * Notify listeners that translations are loaded
     * @param {string} namespace - Loaded namespace
     */
    notifyLoaded(namespace) {
        this.listeners.forEach(callback => {
            try {
                callback(namespace);
            } catch (error) {
                console.error('Translation listener error:', error);
            }
        });
    }
    
    /**
     * Check if namespace is loaded
     * @param {string} namespace - Namespace to check
     * @returns {boolean} - True if loaded
     */
    isLoaded(namespace) {
        return !!this.cache[namespace];
    }
    
    /**
     * Get current locale
     * @returns {string} - Current locale code
     */
    getLocale() {
        return this.locale;
    }
}

// Initialize global translation loader
// Detect locale from HTML lang attribute
window.translationLoader = new TranslationLoader(
    document.documentElement.lang || 'en'
);

// Helper function for quick translation access
window.t = function(key, fallback = key) {
    return window.translationLoader.t(key, fallback);
};

console.log(`✅ Translation loader initialized (locale: ${window.translationLoader.getLocale()})`);
