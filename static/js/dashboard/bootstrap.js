/**
 * Dashboard Bootstrap Module
 * Phase 2: Frontend Refactoring - Shared globals, translations, and utilities
 * 
 * This module must load FIRST before all other dashboard modules.
 * Contains: global state, translation system, utility functions, feature detection
 */

// ============================================================================
// GLOBAL STATE VARIABLES (shared across all dashboard modules)
// ============================================================================
window.dashboardState = {
    data: null,           // Main dashboard data from /api/dashboard_data (legacy: dashboardData)
    charts: {},           // Chart.js instances managed by charts module
    campaignData: null,
    availableCampaigns: [],
    selectedCampaignId: null,
    kpiOverviewData: null,
    campaignsInitialized: false,
    isBusinessAuthenticated: window.isBusinessAuthenticated || false
};

// Backward compatibility alias for data → dashboardData
Object.defineProperty(window.dashboardState, 'dashboardData', {
    get() { return this.data; },
    set(value) { this.data = value; }
});

// Initialize global translations object
window.translations = window.translations || {};

// Module exports registry (each module registers its public API here)
window.dashboardModules = {};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * HTML escape function to prevent XSS vulnerabilities
 */
function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Helper function to convert string keys to camelCase property names
 */
function toCamelCase(str) {
    // Special cases for common patterns
    const specialCases = {
        // Status keys
        'N/A': 'na',
        'Draft': 'draft',
        'Ready': 'ready',
        'Active': 'active',
        'Completed': 'completed',
        'Unknown': 'unknown',
        // Time keys
        'days left': 'daysLeft',
        'days ago': 'daysAgo',
        'month': 'month',
        'months': 'months',
        'year': 'year',
        'years': 'years',
        'ago': 'ago',
        // Filter and campaign selection
        'Filtered by:': 'filteredBy',
        'Clear filter': 'clearFilter',
        'Select first campaign': 'selectFirstCampaign',
        'Select second campaign': 'selectSecondCampaign',
        // Loading states
        'Loading...': 'loading',
        'Loading comparison...': 'loadingComparison',
        'Loading comparison data...': 'loadingComparisonData',
        // Error messages
        'Error Loading Comparison': 'errorLoadingComparison',
        'Error loading comparison data': 'errorLoadingComparisonData',
        'Error loading dashboard data:': 'errorLoadingDashboardData',
        'Error loading KPI overview data': 'errorLoadingKpiData',
        'Error loading responses.': 'errorLoadingResponses',
        'Error loading account intelligence': 'errorLoadingAccountIntelligence',
        'Failed to fetch comparison data': 'failedToFetchComparisonData',
        'Failed to load comparison data. Please try again.': 'failedToLoadComparisonData',
        'Failed to load campaign options': 'failedToLoadCampaignOptions',
        'Network error loading tenure data': 'networkErrorLoadingTenureData',
        'Network error loading company data': 'networkErrorLoadingCompanyData',
        // No data messages
        'No campaign data available': 'noCampaignDataAvailable',
        'No tenure data available yet': 'noTenureDataAvailable',
        'No company data available yet': 'noCompanyDataAvailable',
        // Ratings and metrics
        'Satisfaction': 'satisfaction',
        'Product Value': 'productValue',
        'Service': 'service',
        'Pricing': 'pricing',
        'Average Rating': 'averageRating',
        'Critical Risk': 'criticalRisk',
        // Pagination and display
        'Showing': 'showing',
        'of': 'of',
        'Previous': 'previous',
        'Next': 'next',
        // Actions
        'View Details': 'viewDetails',
        'View Full Response': 'viewFullResponse',
        'Close': 'close',
        'Authentication required': 'authenticationRequired',
        // Collections
        'companies': 'companies',
        'accounts': 'accounts',
        'responses': 'responses',
        'tenure groups': 'tenureGroups'
    };
    
    if (specialCases[str]) return specialCases[str];
    
    // Generic camelCase conversion
    return str
        .replace(/[^a-zA-Z0-9 ]/g, '')
        .split(/\s+/)
        .map((word, index) => {
            word = word.toLowerCase();
            return index === 0 ? word : word.charAt(0).toUpperCase() + word.slice(1);
        })
        .join('');
}

/**
 * Mobile detection helper
 */
function isMobile() {
    return window.innerWidth <= 768;
}

/**
 * Get responsive chart configuration based on screen size
 * Used by chart modules for mobile-friendly visualizations
 */
function getMobileChartConfig() {
    const isMob = isMobile();
    const isSmallMobile = window.innerWidth <= 576;
    
    return {
        fontSize: isSmallMobile ? 12 : (isMob ? 14 : 16),
        legendFontSize: isSmallMobile ? 11 : (isMob ? 13 : 14),
        titleFontSize: isSmallMobile ? 14 : (isMob ? 16 : 18),
        legendPosition: 'bottom',
        legendPadding: isMob ? 15 : 20,
        maintainAspectRatio: false,
        chartHeight: isSmallMobile ? '220px' : (isMob ? '280px' : '320px'),
        elements: {
            point: {
                radius: isMob ? 6 : 4,
                hoverRadius: isMob ? 8 : 6
            },
            bar: {
                borderWidth: isMob ? 2 : 1
            }
        },
        layout: {
            padding: {
                left: isMob ? 10 : 20,
                right: isMob ? 10 : 20,
                top: isMob ? 15 : 20,
                bottom: isMob ? 15 : 20
            }
        }
    };
}

// ============================================================================
// TRANSLATION SYSTEM
// ============================================================================

/**
 * Load dashboard translations and initialize translation system
 */
(async function loadDashboardTranslations() {
    // Fallback translations covering all possible property accesses
    const fallbackTranslations = {
        draft: 'Draft', ready: 'Ready', active: 'Active', completed: 'Completed', unknown: 'Unknown',
        daysLeft: 'days left', daysAgo: 'days ago', month: 'month', months: 'months', year: 'year', years: 'years', ago: 'ago',
        filteredBy: 'Filtered by:', clearFilter: 'Clear filter', selectFirstCampaign: 'Select first campaign', selectSecondCampaign: 'Select second campaign',
        loading: 'Loading...', loadingComparison: 'Loading comparison...', loadingComparisonData: 'Loading comparison data...',
        failedToFetchComparisonData: 'Failed to fetch comparison data', failedToLoadComparisonData: 'Failed to load comparison data. Please try again.',
        errorLoadingComparison: 'Error Loading Comparison', errorLoadingComparisonData: 'Error loading comparison data',
        previous: 'Previous', next: 'Next', showing: 'Showing', of: 'of',
        companies: 'companies', accounts: 'accounts', responses: 'responses', tenureGroups: 'tenure groups',
        viewDetails: 'View Details', close: 'Close', authenticationRequired: 'Authentication required', viewFullResponse: 'View Full Response',
        satisfaction: 'Satisfaction', productValue: 'Product Value', service: 'Service', pricing: 'Pricing', averageRating: 'Average Rating',
        satisfactionBadge: 'Satisfaction Rating', valueBadge: 'Product Value Rating', serviceBadge: 'Service Rating', pricingBadge: 'Pricing Rating',
        errorLoadingDashboardData: 'Error loading dashboard data: ', errorLoadingAccountIntelligence: 'Error loading account intelligence',
        errorLoadingResponses: 'Error loading responses.', networkErrorLoadingTenureData: 'Network error loading tenure data',
        networkErrorLoadingCompanyData: 'Network error loading company data', errorLoadingKpiData: 'Error loading KPI overview data',
        failedToLoadCampaignOptions: 'Failed to load campaign options', noCampaignDataAvailable: 'No campaign data available',
        noTenureDataAvailable: 'No tenure data available yet', noCompanyDataAvailable: 'No company data available yet', na: 'N/A'
    };
    
    try {
        // Wait for translationLoader to be available (max 5 seconds)
        if (!window.translationLoader) {
            console.warn('⚠️ Translation loader not yet available, waiting...');
            await new Promise((resolve) => {
                const checkInterval = setInterval(() => {
                    if (window.translationLoader) {
                        clearInterval(checkInterval);
                        resolve();
                    }
                }, 50);
                // Timeout after 5 seconds
                setTimeout(() => {
                    clearInterval(checkInterval);
                    resolve();
                }, 5000);
            });
        }
        
        if (window.translationLoader) {
            const dashboardTranslations = await window.translationLoader.load('dashboard');
            Object.assign(window.translations, dashboardTranslations);
            
            // Create camelCase aliases for loaded keys
            for (const [key, value] of Object.entries(dashboardTranslations)) {
                const camelKey = toCamelCase(key);
                if (camelKey && camelKey !== key) {
                    window.translations[camelKey] = value;
                }
            }
            
            // Apply fallbacks for missing keys
            for (const [key, value] of Object.entries(fallbackTranslations)) {
                if (!window.translations[key]) {
                    window.translations[key] = value;
                }
            }
            
            console.log('✅ Dashboard translations loaded successfully');
        } else {
            console.warn('⚠️ Translation loader unavailable after timeout, using fallbacks only');
            Object.assign(window.translations, fallbackTranslations);
        }
        
        window.dispatchEvent(new Event('translationsLoaded'));
        
    } catch (error) {
        console.warn('⚠️ Failed to load dashboard translations, using fallbacks:', error);
        Object.assign(window.translations, fallbackTranslations);
        window.dispatchEvent(new Event('translationsLoaded'));
    }
})();

/**
 * Format campaign status for display
 */
function formatCampaignStatus(status) {
    if (!status) return 'Unknown';
    const statusMap = {
        'draft': 'Draft',
        'ready': 'Ready',
        'active': 'Active',
        'completed': 'Completed',
        'archived': 'Archived'
    };
    return statusMap[status] || status;
}

/**
 * Format date string for display
 */
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch (error) {
        return 'N/A';
    }
}

// ============================================================================
// MODULE EXPORTS - Shared utilities available to other dashboard modules
// ============================================================================
window.dashboardModules.bootstrap = {
    utils: {
        escapeHtml,
        getMobileChartConfig,
        isMobile,
        toCamelCase,
        formatCampaignStatus,
        formatDate
    }
};

console.log('📦 Dashboard Bootstrap module loaded');
