// Dashboard JavaScript functionality

// HTML escape function to prevent XSS vulnerabilities
function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Get confidence level badge for response rate metrics
function getConfidenceBadge(level) {
    const badges = {
        'high': { color: '#000000', bg: '#00000010', label: 'High', labelFr: 'Élevé' },
        'medium': { color: '#BDBDBD', bg: '#BDBDBD20', label: 'Medium', labelFr: 'Moyen' },
        'low': { color: '#E13A44', bg: '#E13A4420', label: 'Low', labelFr: 'Faible' },
        'insufficient': { color: '#BDBDBD', bg: '#BDBDBD20', label: 'Insufficient', labelFr: 'Insuffisant' }
    };
    
    const badge = badges[level] || badges['insufficient'];
    const lang = document.documentElement.lang || 'en';
    const label = lang.startsWith('fr') ? badge.labelFr : badge.label;
    
    return `<span class="badge" style="background-color: ${badge.bg}; color: ${badge.color}; border: 1px solid ${badge.color}; font-size: 0.7em;">${label}</span>`;
}

let dashboardData = null;
let charts = {};
let campaignData = null;
let availableCampaigns = [];
let selectedCampaignId = null;
let kpiOverviewData = null;

// Initialize global translations object and load dashboard translations
window.translations = window.translations || {};

// Campaign initialization flag (must be global to prevent race conditions)
let campaignsInitialized = false;

// Helper function to convert string keys to camelCase property names
function toCamelCase(str) {
    // Special cases for common patterns
    const specialCases = {
        // Status keys - matching exact grep results
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
        // Error messages - matching exact property names
        'Error Loading Comparison': 'errorLoadingComparison',
        'Error loading comparison data': 'errorLoadingComparisonData',
        'Error loading dashboard data:': 'errorLoadingDashboardData',
        'Error loading KPI overview data': 'errorLoadingKpiData',  // FIXED: was errorLoadingKpiOverviewData
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
        // Remove all non-alphanumeric chars except spaces
        .replace(/[^a-zA-Z0-9 ]/g, '')
        // Split into words
        .split(/\s+/)
        // Capitalize each word except the first
        .map((word, index) => {
            word = word.toLowerCase();
            return index === 0 ? word : word.charAt(0).toUpperCase() + word.slice(1);
        })
        .join('');
}

// ============================================================================
// CRITICAL: Campaign initialization function (must be defined BEFORE IIFE)
// ============================================================================
function initializeCampaigns() {
    if (campaignsInitialized) {
        console.log('⚠️ Campaigns already initialized, skipping duplicate call');
        return;
    }
    campaignsInitialized = true;
    console.log('🌍 Translations ready, initializing campaigns...');
    
    // Load campaign filter options first, then initial dashboard data
    loadCampaignFilterOptions().then(() => {
        // Update global campaign indicator after filter is populated
        updateGlobalCampaignIndicator();
        
        // Only load dashboard data if no default campaign was auto-selected
        if (!selectedCampaignId) {
            loadDashboardData().catch(error => {
                console.error('Initial dashboard load failed:', error);
            });
        }
    });
    
    // Load campaign comparison options
    loadComparisonCampaignOptions();
}

// ============================================================================
// CRITICAL: Register event listener BEFORE IIFE to prevent race condition
// ============================================================================
window.addEventListener('translationsLoaded', initializeCampaigns);

// Load translations immediately when script loads
(async function() {
    // Define fallback translations that cover ALL possible property accesses
    const fallbackTranslations = {
        // Status keys
        draft: 'Draft',
        ready: 'Ready',
        active: 'Active',
        completed: 'Completed',
        unknown: 'Unknown',
        // Time keys
        daysLeft: 'days left',
        daysAgo: 'days ago',
        month: 'month',
        months: 'months',
        year: 'year',
        years: 'years',
        ago: 'ago',
        // Campaign filter keys
        filteredBy: 'Filtered by:',
        clearFilter: 'Clear filter',
        selectFirstCampaign: 'Select first campaign',
        selectSecondCampaign: 'Select second campaign',
        // Comparison keys
        loading: 'Loading...',
        loadingComparison: 'Loading comparison...',
        loadingComparisonData: 'Loading comparison data...',
        failedToFetchComparisonData: 'Failed to fetch comparison data',
        failedToLoadComparisonData: 'Failed to load comparison data. Please try again.',
        errorLoadingComparison: 'Error Loading Comparison',
        errorLoadingComparisonData: 'Error loading comparison data',
        // Pagination keys
        previous: 'Previous',
        next: 'Next',
        showing: 'Showing',
        of: 'of',
        // Collection type keys
        companies: 'companies',
        accounts: 'accounts',
        responses: 'responses',
        tenureGroups: 'tenure groups',
        // Action keys
        viewDetails: 'View Details',
        close: 'Close',
        authenticationRequired: 'Authentication required',
        viewFullResponse: 'View Full Response',
        // Chart/Rating keys
        satisfaction: 'Satisfaction',
        productValue: 'Product Value',
        service: 'Service',
        pricing: 'Pricing',
        averageRating: 'Average Rating',
        // Badge tooltips (may not be in JSON)
        satisfactionBadge: 'Satisfaction Rating',
        valueBadge: 'Product Value Rating',
        serviceBadge: 'Service Rating',
        pricingBadge: 'Pricing Rating',
        // Error messages
        errorLoadingDashboardData: 'Error loading dashboard data: ',
        errorLoadingAccountIntelligence: 'Error loading account intelligence',
        errorLoadingResponses: 'Error loading responses.',
        networkErrorLoadingTenureData: 'Network error loading tenure data',
        networkErrorLoadingCompanyData: 'Network error loading company data',
        errorLoadingKpiData: 'Error loading KPI overview data',
        failedToLoadCampaignOptions: 'Failed to load campaign options',
        // No data messages
        noCampaignDataAvailable: 'No campaign data available',
        noCampaignsAvailable: 'No campaigns available',
        noTenureDataAvailable: 'No tenure data available yet',
        noCompanyDataAvailable: 'No company data available yet',
        // Other
        na: 'N/A'
    };
    
    try {
        const dashboardTranslations = await window.translationLoader.load('dashboard');
        
        // First, populate with loaded translations
        Object.assign(window.translations, dashboardTranslations);
        
        // Create camelCase aliases for ALL loaded keys
        for (const [key, value] of Object.entries(dashboardTranslations)) {
            const camelKey = toCamelCase(key);
            if (camelKey && camelKey !== key) {
                window.translations[camelKey] = value;
            }
        }
        
        // CRITICAL: Merge fallback for any keys still missing (e.g., badge tooltips not in JSON)
        // This ensures NO undefined values even in success path
        for (const [key, value] of Object.entries(fallbackTranslations)) {
            if (window.translations[key] === undefined) {
                window.translations[key] = value;
            }
        }
        
        console.log('✅ Dashboard translations loaded:', Object.keys(window.translations).length, 'keys');
        
        // Fire translationsLoaded event
        window.dispatchEvent(new Event('translationsLoaded'));
    } catch (error) {
        console.error('❌ Failed to load dashboard translations:', error);
        // Apply all fallback translations on fetch failure
        Object.assign(window.translations, fallbackTranslations);
        
        // Fire event anyway to unblock UI
        window.dispatchEvent(new Event('translationsLoaded'));
    }
})();

// Mobile detection and responsive configuration
function isMobile() {
    return window.innerWidth <= 768;
}

function getMobileChartConfig() {
    const isMob = isMobile();
    const isSmallMobile = window.innerWidth <= 576;
    
    return {
        fontSize: isSmallMobile ? 12 : (isMob ? 14 : 16),
        legendFontSize: isSmallMobile ? 11 : (isMob ? 13 : 14),
        titleFontSize: isSmallMobile ? 14 : (isMob ? 16 : 18),
        legendPosition: 'bottom',
        legendPadding: isMob ? 15 : 20,
        maintainAspectRatio: false, // Allow charts to be more flexible
        chartHeight: isSmallMobile ? '220px' : (isMob ? '280px' : '320px'),
        // Enhanced mobile options
        elements: {
            point: {
                radius: isMob ? 6 : 4,
                hoverRadius: isMob ? 8 : 6
            },
            bar: {
                borderWidth: isMob ? 2 : 1
            }
        },
        // Better spacing for mobile
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

// Color override function - now using shared utility from utils/color-override.js
// Legacy wrapper maintained for backward compatibility
function forceRemoveYellowColors() {
    if (typeof applyColorOverrides === 'function') {
        applyColorOverrides(document, 0);
    } else {
        console.warn('Color override utility not loaded');
    }
}

// ============================================================================
// CAMPAIGN ANALYTICS FILTERING
// ============================================================================

// Helper function to format campaign status for display
function formatCampaignStatus(status) {
    switch (status) {
        case 'draft':
            return translations.draft;
        case 'ready':
            return translations.ready;
        case 'active':
            return translations.active;
        case 'completed':
            return translations.completed;
        default:
            return translations.unknown;
    }
}

// Load campaign options for analytics filtering
async function loadCampaignFilterOptions() {
    try {
        const response = await fetch('/api/campaigns/filter-options');
        if (response.ok) {
            const data = await response.json();
            availableCampaigns = data.campaigns;
            populateCampaignFilterDropdown();
            return true;
        }
        return false;
    } catch (error) {
        console.error('Error loading campaign filter options:', error);
        return false;
    }
}

// Populate campaign filter dropdown
function populateCampaignFilterDropdown() {
    const select = document.getElementById('campaignFilter');
    if (!select) return;
    
    // Clear existing options
    select.innerHTML = '';
    
    // Handle zero campaigns - show empty state
    if (!availableCampaigns || availableCampaigns.length === 0) {
        console.log('⚠️ No campaigns available - showing empty state');
        select.disabled = true;
        const emptyOption = document.createElement('option');
        emptyOption.textContent = translations.noCampaignsAvailable || 'No campaigns available';
        emptyOption.disabled = true;
        select.appendChild(emptyOption);
        
        // Hide campaign filter section and show empty state message
        const filterSection = select.closest('.border.rounded');
        if (filterSection) {
            filterSection.style.display = 'none';
        }
        return;
    }
    
    // Enable select and ensure filter section is visible
    select.disabled = false;
    const filterSection = select.closest('.border.rounded');
    if (filterSection) {
        filterSection.style.display = '';
    }
    
    // Check for campaign_id URL parameter first
    const urlParams = new URLSearchParams(window.location.search);
    const urlCampaignId = urlParams.get('campaign_id');
    
    // Find default campaign: URL param > session storage > active > completed > most recent
    let defaultCampaign = null;
    
    if (urlCampaignId) {
        // If URL has campaign_id, use that
        defaultCampaign = availableCampaigns.find(c => c.id === parseInt(urlCampaignId));
        console.log('📌 Using campaign from URL parameter:', urlCampaignId, defaultCampaign);
    }
    
    // Check session storage if no URL param (respects user's last selection)
    if (!defaultCampaign) {
        const storedCampaignId = sessionStorage.getItem('selectedCampaignId');
        if (storedCampaignId) {
            defaultCampaign = availableCampaigns.find(c => c.id === parseInt(storedCampaignId));
            if (defaultCampaign) {
                console.log('🔄 Restored campaign from session storage:', storedCampaignId);
            }
        }
    }
    
    // Smart default selection if no URL param or session storage
    if (!defaultCampaign) {
        // Priority 1: Active campaigns
        const activeCampaign = availableCampaigns.find(c => c.status === 'active');
        if (activeCampaign) {
            defaultCampaign = activeCampaign;
            console.log('✅ Selected active campaign:', activeCampaign.name);
        } else {
            // Priority 2: Completed campaigns (most recent)
            const completedCampaigns = availableCampaigns.filter(c => c.status === 'completed');
            if (completedCampaigns.length > 0) {
                const sortedCompleted = [...completedCampaigns].sort((a, b) => {
                    const dateA = new Date(a.end_date || a.created_at);
                    const dateB = new Date(b.end_date || b.created_at);
                    return dateB - dateA; // Most recent first
                });
                defaultCampaign = sortedCompleted[0];
                console.log('✅ Selected most recent completed campaign:', defaultCampaign.name);
            } else {
                // Priority 3: Any campaign (most recent by created_at)
                const sortedCampaigns = [...availableCampaigns].sort((a, b) => {
                    const dateA = new Date(a.created_at);
                    const dateB = new Date(b.created_at);
                    return dateB - dateA; // Most recent first
                });
                defaultCampaign = sortedCampaigns[0];
                console.log('✅ Selected most recently created campaign:', defaultCampaign.name);
            }
        }
    }
    
    // Add campaign options
    availableCampaigns.forEach(campaign => {
        const option = document.createElement('option');
        option.value = campaign.id;
        
        // Normalize status to lowercase for consistent logic
        const rawStatus = (campaign.status || '').toLowerCase();
        const displayStatus = formatCampaignStatus(rawStatus);
        
        // Format option text with status
        option.textContent = `${campaign.name} (${formatDate(campaign.start_date)} - ${formatDate(campaign.end_date)}) - ${displayStatus}`;
        option.setAttribute('data-name', campaign.name);
        option.setAttribute('data-start', campaign.start_date);
        option.setAttribute('data-end', campaign.end_date);
        option.setAttribute('data-status', rawStatus);  // Store raw status for logic
        option.setAttribute('data-status-display', displayStatus);  // Store translated for display
        option.setAttribute('data-description', campaign.description || '');
        option.setAttribute('data-survey-type', campaign.survey_type || 'conversational');
        
        // Set as selected if this is the default campaign
        if (defaultCampaign && campaign.id === defaultCampaign.id) {
            option.selected = true;
            selectedCampaignId = campaign.id;
        }
        
        select.appendChild(option);
    });
    
    // Attach change event listener to campaign filter BEFORE loading data
    // Remove existing listener first to prevent duplicates
    const newSelect = select.cloneNode(true);
    select.parentNode.replaceChild(newSelect, select);
    
    // Re-apply selected value after cloneNode (cloneNode may not preserve programmatic .selected property)
    if (defaultCampaign) {
        newSelect.value = String(defaultCampaign.id);
        selectedCampaignId = defaultCampaign.id;
    }
    
    // Attach the event listener
    newSelect.addEventListener('change', () => {
        console.log('📍 Campaign filter changed via dropdown');
        applyCampaignFilter();
    });
    console.log('✅ Campaign filter change listener attached');
    
    // SECURITY FIX: Load ALL dashboard data (including Survey Insights) for default campaign
    // This prevents the race condition where Survey Insights APIs are called without campaign_id
    if (defaultCampaign) {
        console.log('🔒 Loading all data for default campaign:', defaultCampaign.name);
        applyCampaignFilter(); // This loads dashboard + Survey Insights + Recent Responses
    }
}

// Apply campaign filter to analytics
async function applyCampaignFilter() {
    const select = document.getElementById('campaignFilter');
    selectedCampaignId = select.value ? parseInt(select.value) : null;
    
    console.log('🎯 Campaign filter applied:', selectedCampaignId);
    
    // Save to session storage for persistence across pages
    if (selectedCampaignId) {
        const option = select.selectedOptions[0];
        sessionStorage.setItem('selectedCampaignId', selectedCampaignId);
        sessionStorage.setItem('selectedCampaignName', option.text);
        sessionStorage.setItem('selectedCampaignDates', `${option.getAttribute('data-start')} - ${option.getAttribute('data-end')}`);
        sessionStorage.setItem('selectedCampaignStatus', option.getAttribute('data-status'));
    } else {
        sessionStorage.removeItem('selectedCampaignId');
        sessionStorage.removeItem('selectedCampaignName');
        sessionStorage.removeItem('selectedCampaignDates');
        sessionStorage.removeItem('selectedCampaignStatus');
    }
    
    // Update URL query parameter so bookmarking/sharing preserves campaign selection
    const url = new URL(window.location);
    if (selectedCampaignId) {
        url.searchParams.set('campaign_id', selectedCampaignId);
    } else {
        url.searchParams.delete('campaign_id');
    }
    window.history.replaceState({}, '', url);
    
    // Update global campaign indicator if on filtered pages
    updateGlobalCampaignIndicator();
    
    // Reload dashboard data with campaign filter
    // NOTE: UI clearing now happens inside loadDashboardData() for all code paths
    console.log('📡 Loading dashboard data for campaign:', selectedCampaignId);
    await loadDashboardData();
    
    // Update selected campaign info display after data loads
    updateSelectedCampaignInfo();
    
    // Refresh all charts immediately after data loads - no setTimeout delay
    createNpsChart();
    createSentimentChart();
    createRatingsChart();
    createTenureChart();
    createGrowthFactorChart();
    
    // CRITICAL: Reload Survey Insights tables with campaign-specific data
    console.log('📊 Reloading Survey Insights tables for campaign:', selectedCampaignId);
    loadCompanyNpsData(1); // Reset to page 1 when campaign changes
    loadTenureNpsData(1);  // Reset to page 1 when campaign changes
    loadAccountIntelligence(1); // Reset to page 1 when campaign changes
    
    // CRITICAL: Reload Recent Survey Responses with campaign-specific data
    console.log('📊 Reloading Recent Survey Responses for campaign:', selectedCampaignId);
    loadSurveyResponses(1); // Reset to page 1 when campaign changes
    
    // Also refresh Overview tab chart if visible - but wait for data to load
    console.log('🎨 About to call createThemesChart from applyCampaignFilter');
    // Use a longer delay and verify data exists before creating chart
    setTimeout(() => {
        if (dashboardData && dashboardData.key_themes) {
            createThemesChart();
        } else {
            console.log('⏳ Dashboard data not ready, retrying themes chart...');
            setTimeout(() => createThemesChart(), 500);
        }
    }, 200);
}

// Clear campaign filter
function clearCampaignFilter() {
    document.getElementById('campaignFilter').value = '';
    applyCampaignFilter();
}

// Update global campaign indicator (for persistent display across pages)
function updateGlobalCampaignIndicator() {
    const indicator = document.getElementById('globalCampaignIndicator');
    if (!indicator) return; // Not on a page with the indicator
    
    const campaignId = sessionStorage.getItem('selectedCampaignId');
    const campaignName = sessionStorage.getItem('selectedCampaignName');
    const campaignDates = sessionStorage.getItem('selectedCampaignDates');
    
    if (campaignId && campaignName) {
        indicator.innerHTML = `
            <div class="campaign-filter-badge">
                <i class="fas fa-filter me-2"></i>
                <strong>${translations.filteredBy}</strong> ${escapeHtml(campaignName)}
                <span class="badge bg-light text-dark ms-2">${escapeHtml(campaignDates)}</span>
                <button class="btn btn-sm btn-link text-danger ms-2 p-0" onclick="clearGlobalCampaignFilter()" title="${translations.clearFilter}">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        indicator.style.display = 'block';
    } else {
        indicator.style.display = 'none';
    }
}

// Clear global campaign filter
function clearGlobalCampaignFilter() {
    sessionStorage.removeItem('selectedCampaignId');
    sessionStorage.removeItem('selectedCampaignName');
    sessionStorage.removeItem('selectedCampaignDates');
    sessionStorage.removeItem('selectedCampaignStatus');
    
    // Clear the filter select if on dashboard
    const select = document.getElementById('campaignFilter');
    if (select) {
        select.value = '';
        applyCampaignFilter();
    } else {
        // Just update indicator and reload page
        updateGlobalCampaignIndicator();
        location.reload();
    }
}

// Restore campaign selection from session storage
function restoreCampaignSelection() {
    const campaignId = sessionStorage.getItem('selectedCampaignId');
    const select = document.getElementById('campaignFilter');
    
    if (campaignId && select) {
        select.value = campaignId;
        selectedCampaignId = parseInt(campaignId);
        console.log('🔄 Restored campaign selection:', campaignId);
        return true;
    }
    return false;
}

// Update selected campaign info display
function updateSelectedCampaignInfo() {
    const infoDiv = document.getElementById('selectedCampaignInfo');
    const select = document.getElementById('campaignFilter');
    
    if (selectedCampaignId && select.selectedOptions.length > 0) {
        const option = select.selectedOptions[0];
        const startDate = option.getAttribute('data-start');
        const endDate = option.getAttribute('data-end');
        const rawStatus = option.getAttribute('data-status');  // Get raw status for logic
        const displayStatus = option.getAttribute('data-status-display');  // Get display status for UI
        
        // Update dates badge text (inline, no container refresh)
        const datesText = document.querySelector('.campaign-dates-text');
        if (datesText) {
            datesText.textContent = `${formatDate(startDate)} - ${formatDate(endDate)}`;
        }
        
        // Update status badge with proper styling
        const statusBadge = document.getElementById('selectedCampaignStatus');
        const statusText = document.querySelector('.campaign-status-text');
        if (statusBadge && statusText) {
            statusText.textContent = displayStatus;  // Use display status for UI
            if (rawStatus === 'active') {  // Use raw status for logic
                statusBadge.style.backgroundColor = '#000000';
                statusBadge.style.color = 'white';
            } else {
                statusBadge.style.backgroundColor = '#BDBDBD';
                statusBadge.style.color = 'white';
            }
        }
        
        // Update days remaining/since ended
        const daysLeftSpan = document.getElementById('selectedCampaignDaysLeft');
        const daysText = document.querySelector('.campaign-days-text');
        if (daysLeftSpan && daysText && endDate) {
            const today = new Date();
            const campaignEndDate = new Date(endDate);
            const diffTime = campaignEndDate - today;
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            const daysRemaining = rawStatus === 'active' ? Math.max(0, diffDays) : 0;  // Use raw status
            const daysSinceEnded = rawStatus === 'completed' ? Math.max(0, -diffDays) : 0;  // Use raw status
            
            if (rawStatus === 'active' && daysRemaining >= 0) {  // Use raw status
                if (daysRemaining > 30) {
                    daysText.textContent = `${daysRemaining} ${translations.daysLeft}`;
                    daysLeftSpan.className = 'badge bg-success';
                } else if (daysRemaining > 7) {
                    daysText.textContent = `${daysRemaining} ${translations.daysLeft}`;
                    daysLeftSpan.className = 'badge bg-warning';
                } else {
                    daysText.textContent = `${daysRemaining} ${translations.daysLeft}`;
                    daysLeftSpan.className = 'badge bg-danger';
                }
                daysLeftSpan.style.display = '';
            } else if (rawStatus === 'completed' && daysSinceEnded > 0) {  // Use raw status
                if (daysSinceEnded < 30) {
                    daysText.textContent = `${daysSinceEnded} ${translations.daysAgo}`;
                } else if (daysSinceEnded < 365) {
                    const months = Math.floor(daysSinceEnded / 30);
                    daysText.textContent = `${months} ${months > 1 ? translations.months : translations.month} ${translations.ago}`;
                } else {
                    const years = Math.floor(daysSinceEnded / 365);
                    daysText.textContent = `${years} ${years > 1 ? translations.years : translations.year} ${translations.ago}`;
                }
                daysLeftSpan.className = 'badge bg-secondary';
                daysLeftSpan.style.display = '';
            } else {
                daysLeftSpan.style.display = 'none';
            }
        }
        
        // Update survey type badge
        const surveyTypeBadge = document.getElementById('selectedCampaignSurveyType');
        const surveyTypeText = document.querySelector('.campaign-survey-type-text');
        const surveyType = option.getAttribute('data-survey-type') || 'conversational';
        if (surveyTypeBadge && surveyTypeText) {
            if (surveyType === 'classic') {
                surveyTypeText.textContent = translations.classicSurvey || 'Classic Survey';
                surveyTypeBadge.style.backgroundColor = '#6f42c1';
                surveyTypeBadge.style.color = 'white';
            } else {
                surveyTypeText.textContent = translations.conversationalAI || 'Conversational AI';
                surveyTypeBadge.style.backgroundColor = '#0d6efd';
                surveyTypeBadge.style.color = 'white';
            }
            surveyTypeBadge.style.display = '';
        }
        
        // Show the inline badges (smooth transition)
        infoDiv.style.display = 'flex';
    } else {
        infoDiv.style.display = 'none';
    }
}



// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Only run dashboard JavaScript on dashboard pages
    if (!document.body.classList.contains('page-dashboard') && 
        !window.location.pathname.includes('/dashboard')) {
        console.log('Dashboard JavaScript skipped - not on dashboard page');
        return;
    }
    
    console.log('Dashboard JavaScript loaded and DOM ready');
    
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Force remove yellow colors immediately
    forceRemoveYellowColors();
    
    // Immediate fallback for company NPS data
    setTimeout(function() {
        console.log('Fallback: Loading company NPS data directly');
        loadCompanyNpsDataDirect();
    }, 1000);
    
    // Setup tab event listeners
    setupTabEventListeners();
});

// ============================================================================
// CAMPAIGN COMPARISON FUNCTIONALITY
// ============================================================================

// Global variables for comparison
let comparisonCampaigns = [];

// Load campaign options for comparison dropdowns
async function loadComparisonCampaignOptions() {
    try {
        const response = await fetch('/api/campaigns/filter-options');
        if (response.ok) {
            const data = await response.json();
            comparisonCampaigns = data.campaigns;
            populateComparisonDropdowns();
        }
    } catch (error) {
        console.error('Error loading comparison campaign options:', error);
    }
}

// Populate both comparison dropdowns
function populateComparisonDropdowns() {
    const campaign1Select = document.getElementById('campaign1Select');
    const campaign2Select = document.getElementById('campaign2Select');
    
    if (!campaign1Select || !campaign2Select) return;
    
    // Clear existing options
    campaign1Select.innerHTML = `<option value="">${translations.selectFirstCampaign}</option>`;
    campaign2Select.innerHTML = `<option value="">${translations.selectSecondCampaign}</option>`;
    
    // Add campaign options to both dropdowns
    comparisonCampaigns.forEach(campaign => {
        const status = formatCampaignStatus(campaign.status);
        const optionText = `${campaign.name} (${formatDate(campaign.start_date)} - ${formatDate(campaign.end_date)}) - ${status}`;
        
        // Campaign 1 dropdown
        const option1 = document.createElement('option');
        option1.value = campaign.id;
        option1.textContent = optionText;
        campaign1Select.appendChild(option1);
        
        // Campaign 2 dropdown
        const option2 = document.createElement('option');
        option2.value = campaign.id;
        option2.textContent = optionText;
        campaign2Select.appendChild(option2);
    });
}

// Update comparison when selections change
async function updateComparison() {
    const campaign1Id = document.getElementById('campaign1Select')?.value;
    const campaign2Id = document.getElementById('campaign2Select')?.value;
    
    const resultsDiv = document.getElementById('comparisonResults');
    const messageDiv = document.getElementById('noComparisonMessage');
    
    if (!campaign1Id || !campaign2Id || campaign1Id === campaign2Id) {
        // Hide results and show message
        if (resultsDiv) resultsDiv.style.display = 'none';
        if (messageDiv) messageDiv.style.display = 'block';
        return;
    }
    
    // Show loading state
    if (messageDiv) {
        messageDiv.innerHTML = `
            <div class="text-center">
                <div class="spinner-border" style="color: #E13A44;" role="status">
                    <span class="visually-hidden">${translations.loadingComparison}</span>
                </div>
                <p class="text-muted mt-3 mb-0">${translations.loadingComparisonData}</p>
            </div>
        `;
        messageDiv.style.display = 'block';
    }
    if (resultsDiv) resultsDiv.style.display = 'none';
    
    try {
        // Fetch comparison data
        const response = await fetch(`/api/campaigns/comparison?campaign1=${campaign1Id}&campaign2=${campaign2Id}`);
        if (!response.ok) {
            throw new Error(translations.failedToFetchComparisonData);
        }
        
        const comparisonData = await response.json();
        
        // Update headers
        document.getElementById('campaign1Header').textContent = comparisonData.campaign1.name;
        document.getElementById('campaign2Header').textContent = comparisonData.campaign2.name;
        
        // Update campaign identifiers in company table
        const c1Name = document.getElementById('c1CampaignName');
        const c2Name = document.getElementById('c2CampaignName');
        if (c1Name) c1Name.textContent = comparisonData.campaign1.name;
        if (c2Name) c2Name.textContent = comparisonData.campaign2.name;
        
        // Store data globally for filtering
        currentComparisonData = comparisonData;
        
        // Populate executive summary table
        populateExecutiveSummary(comparisonData);
        
        // Populate company comparison table
        populateCompanyComparison(comparisonData);
        
        // Show results and hide message
        if (resultsDiv) resultsDiv.style.display = 'block';
        if (messageDiv) messageDiv.style.display = 'none';
        
    } catch (error) {
        console.error('Error loading comparison data:', error);
        // Show error message or fallback
        if (messageDiv) {
            messageDiv.innerHTML = `
                <i class="fas fa-exclamation-triangle fa-4x text-warning mb-3"></i>
                <h5 class="text-warning">${translations.errorLoadingComparison}</h5>
                <p class="text-muted">${translations.failedToLoadComparisonData}</p>
            `;
            messageDiv.style.display = 'block';
        }
        if (resultsDiv) resultsDiv.style.display = 'none';
    }
}

// Populate executive summary table
function populateExecutiveSummary(data) {
    const tableBody = document.getElementById('summaryTable');
    if (!tableBody) return;
    
    const c1 = data.campaign1.data;
    const c2 = data.campaign2.data;
    
    // Calculate changes
    const metrics = [
        {
            name: 'Total Responses',
            c1: c1.total_responses,
            c2: c2.total_responses,
            change: c2.total_responses - c1.total_responses,
            format: 'number'
        },
        {
            name: 'NPS Score',
            c1: c1.nps_score,
            c2: c2.nps_score,
            change: c2.nps_score - c1.nps_score,
            format: 'decimal'
        },
        {
            name: 'Companies Analyzed',
            c1: c1.companies_analyzed,
            c2: c2.companies_analyzed,
            change: c2.companies_analyzed - c1.companies_analyzed,
            format: 'number'
        },
        {
            name: 'Critical Risk Companies',
            c1: c1.critical_risk_companies,
            c2: c2.critical_risk_companies,
            change: c2.critical_risk_companies - c1.critical_risk_companies,
            format: 'number'
        },
        {
            name: 'Risk-Heavy Accounts',
            c1: c1.risk_heavy_accounts,
            c2: c2.risk_heavy_accounts,
            change: c2.risk_heavy_accounts - c1.risk_heavy_accounts,
            format: 'number'
        },
        {
            name: 'Opportunity-Heavy Accounts',
            c1: c1.opportunity_heavy_accounts,
            c2: c2.opportunity_heavy_accounts,
            change: c2.opportunity_heavy_accounts - c1.opportunity_heavy_accounts,
            format: 'number'
        },
        {
            name: 'Satisfaction Rating',
            c1: c1.average_ratings?.satisfaction || 0,
            c2: c2.average_ratings?.satisfaction || 0,
            change: (c2.average_ratings?.satisfaction || 0) - (c1.average_ratings?.satisfaction || 0),
            format: 'decimal'
        },
        {
            name: 'Product Value Rating',
            c1: c1.average_ratings?.product_value || 0,
            c2: c2.average_ratings?.product_value || 0,
            change: (c2.average_ratings?.product_value || 0) - (c1.average_ratings?.product_value || 0),
            format: 'decimal'
        },
        {
            name: 'Pricing Rating',
            c1: c1.average_ratings?.pricing || 0,
            c2: c2.average_ratings?.pricing || 0,
            change: (c2.average_ratings?.pricing || 0) - (c1.average_ratings?.pricing || 0),
            format: 'decimal'
        },
        {
            name: 'Service Rating',
            c1: c1.average_ratings?.service || 0,
            c2: c2.average_ratings?.service || 0,
            change: (c2.average_ratings?.service || 0) - (c1.average_ratings?.service || 0),
            format: 'decimal'
        }
    ];
    
    // Clear existing content
    tableBody.textContent = '';
    
    metrics.forEach(metric => {
        const c1Display = metric.format === 'decimal' ? parseFloat(metric.c1).toFixed(1) : metric.c1;
        const c2Display = metric.format === 'decimal' ? parseFloat(metric.c2).toFixed(1) : metric.c2;
        
        let changeDisplay = '';
        let changeClass = '';
        if (metric.change > 0) {
            changeDisplay = `+${metric.format === 'decimal' ? metric.change.toFixed(1) : metric.change}`;
            changeClass = metric.name === 'Critical Risk Companies' || metric.name === 'Risk-Heavy Accounts' ? 'text-danger' : 'text-success';
        } else if (metric.change < 0) {
            changeDisplay = metric.format === 'decimal' ? metric.change.toFixed(1) : metric.change;
            changeClass = metric.name === 'Critical Risk Companies' || metric.name === 'Risk-Heavy Accounts' ? 'text-success' : 'text-danger';
        } else {
            changeDisplay = '0';
            changeClass = 'text-muted';
        }
        
        // Create row using safe DOM methods
        const row = document.createElement('tr');
        
        // Name column
        const nameCell = document.createElement('td');
        const nameStrong = document.createElement('strong');
        nameStrong.textContent = metric.name;
        nameCell.appendChild(nameStrong);
        
        // C1 column
        const c1Cell = document.createElement('td');
        c1Cell.className = 'text-center';
        c1Cell.textContent = c1Display;
        
        // C2 column
        const c2Cell = document.createElement('td');
        c2Cell.className = 'text-center';
        c2Cell.textContent = c2Display;
        
        // Change column
        const changeCell = document.createElement('td');
        changeCell.className = `text-center ${changeClass}`;
        const changeStrong = document.createElement('strong');
        changeStrong.textContent = changeDisplay;
        changeCell.appendChild(changeStrong);
        
        // Append all cells to row
        row.appendChild(nameCell);
        row.appendChild(c1Cell);
        row.appendChild(c2Cell);
        row.appendChild(changeCell);
        
        // Append row to table body
        tableBody.appendChild(row);
    });
}

// Store comparison data globally for filtering
let currentComparisonData = null;
let currentComparisonPage = 1;
const comparisonPerPage = 10;

// Populate company comparison table with pagination
function populateCompanyComparison(data, page = 1) {
    const tableBody = document.getElementById('companyTable');
    if (!tableBody) return;
    
    const companies = data.company_details || [];
    const totalCompanies = companies.length;
    const totalPages = Math.ceil(totalCompanies / comparisonPerPage);
    const startIndex = (page - 1) * comparisonPerPage;
    const endIndex = startIndex + comparisonPerPage;
    const paginatedCompanies = companies.slice(startIndex, endIndex);
    
    // Update pagination info and controls
    updateComparisonPaginationInfo(page, totalPages, totalCompanies);
    updateComparisonPaginationControls({
        page: page,
        pages: totalPages,
        total: totalCompanies,
        has_prev: page > 1,
        has_next: page < totalPages
    });
    
    // Clear existing table content
    tableBody.innerHTML = '';
    
    // Format balance for display
    const formatBalance = (balance) => {
        if (balance === 'N/A') return translations.na;
        return balance.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
    };
    
    paginatedCompanies.forEach(company => {
        const c1 = company.campaign1;
        const c2 = company.campaign2;
        
        // Helper function to display value or N/A
        const displayValue = (value) => {
            return (value === null || value === undefined) ? translations.na : value;
        };
        
        // Determine status - only compare if both campaigns have data
        let status = translations.na;
        let statusClass = 'text-muted';
        
        if (c1.participated && c2.participated) {
            // Both campaigns have data - can compare
            status = 'No Change';
            
            if (c1.balance !== c2.balance) {
                if (c2.balance === 'opportunity_heavy' && c1.balance !== 'opportunity_heavy') {
                    status = 'Improved';
                    statusClass = 'text-success';
                } else if (c2.balance === 'risk_heavy' && c1.balance !== 'risk_heavy') {
                    status = 'Worsened';
                    statusClass = 'text-danger';
                } else if (c2.balance === 'balanced' && c1.balance === 'risk_heavy') {
                    status = 'Improved';
                    statusClass = 'text-success';
                } else {
                    status = 'Changed';
                    statusClass = 'text-warning';
                }
            } else if (c2.risk_count < c1.risk_count) {
                status = 'Less Risk';
                statusClass = 'text-success';
            } else if (c2.opportunity_count > c1.opportunity_count) {
                status = 'More Opps';
                statusClass = 'text-success';
            }
        } else if (!c1.participated && c2.participated) {
            status = 'New in C2';
            statusClass = 'text-secondary';
        } else if (c1.participated && !c2.participated) {
            status = 'Not in C2';
            statusClass = 'text-secondary';
        }
        
        // Create table row using safe DOM methods
        const row = document.createElement('tr');
        
        // Company name column
        const nameCell = document.createElement('td');
        const nameStrong = document.createElement('strong');
        nameStrong.textContent = company.company_name;
        nameCell.appendChild(nameStrong);
        
        // Campaign 1 - Risk count
        const c1RiskCell = document.createElement('td');
        c1RiskCell.className = 'text-center';
        c1RiskCell.textContent = displayValue(c1.risk_count);
        
        // Campaign 1 - Opportunity count
        const c1OppCell = document.createElement('td');
        c1OppCell.className = 'text-center';
        c1OppCell.textContent = displayValue(c1.opportunity_count);
        
        // Campaign 1 - Balance
        const c1BalanceCell = document.createElement('td');
        c1BalanceCell.className = 'text-center';
        c1BalanceCell.textContent = c1.balance ? formatBalance(c1.balance) : translations.na;
        
        // Campaign 2 - Risk count
        const c2RiskCell = document.createElement('td');
        c2RiskCell.className = 'text-center';
        c2RiskCell.textContent = displayValue(c2.risk_count);
        
        // Campaign 2 - Opportunity count
        const c2OppCell = document.createElement('td');
        c2OppCell.className = 'text-center';
        c2OppCell.textContent = displayValue(c2.opportunity_count);
        
        // Campaign 2 - Balance
        const c2BalanceCell = document.createElement('td');
        c2BalanceCell.className = 'text-center';
        c2BalanceCell.textContent = c2.balance ? formatBalance(c2.balance) : translations.na;
        
        // Status column
        const statusCell = document.createElement('td');
        statusCell.className = `text-center ${statusClass}`;
        const statusStrong = document.createElement('strong');
        statusStrong.textContent = status;
        statusCell.appendChild(statusStrong);
        
        // Append all cells to row
        row.appendChild(nameCell);
        row.appendChild(c1RiskCell);
        row.appendChild(c1OppCell);
        row.appendChild(c1BalanceCell);
        row.appendChild(c2RiskCell);
        row.appendChild(c2OppCell);
        row.appendChild(c2BalanceCell);
        row.appendChild(statusCell);
        
        // Append row to table body
        tableBody.appendChild(row);
    });
}

// Search and filter comparison table
function searchComparisonTable() {
    if (!currentComparisonData) return;
    
    const searchQuery = document.getElementById('comparisonSearch')?.value.trim().toLowerCase() || '';
    const balanceFilter = document.getElementById('comparisonBalanceFilter')?.value || '';
    
    // Reset to page 1 when performing a new search
    currentComparisonPage = 1;
    
    // Filter company details
    const filteredData = {
        ...currentComparisonData,
        company_details: currentComparisonData.company_details.filter(company => {
            // Search filter
            const matchesSearch = !searchQuery || 
                company.company_name.toLowerCase().includes(searchQuery);
            
            // Balance filter (check both campaigns)
            const matchesBalance = !balanceFilter || 
                company.campaign1.balance === balanceFilter || 
                company.campaign2.balance === balanceFilter;
            
            return matchesSearch && matchesBalance;
        })
    };
    
    // Update table with pagination
    populateCompanyComparison(filteredData, currentComparisonPage);
    
    // Update search info
    let infoText = '';
    if (searchQuery && balanceFilter) {
        const balanceLabel = balanceFilter.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        infoText = `Search: "${searchQuery}" | Balance: ${balanceLabel}`;
    } else if (searchQuery) {
        infoText = `Search: "${searchQuery}"`;
    } else if (balanceFilter) {
        const balanceLabel = balanceFilter.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        infoText = `Balance: ${balanceLabel}`;
    }
    
    const infoElement = document.getElementById('comparisonSearchInfo');
    if (infoElement) {
        infoElement.textContent = infoText;
    }
}

// Clear comparison search and filters
function clearComparisonSearch() {
    const searchInput = document.getElementById('comparisonSearch');
    if (searchInput) {
        searchInput.value = '';
    }
    
    const balanceFilter = document.getElementById('comparisonBalanceFilter');
    if (balanceFilter) {
        balanceFilter.value = '';
    }
    
    const infoElement = document.getElementById('comparisonSearchInfo');
    if (infoElement) {
        infoElement.textContent = '';
    }
    
    // Reset to page 1 and reload original data
    currentComparisonPage = 1;
    if (currentComparisonData) {
        populateCompanyComparison(currentComparisonData, 1);
    }
}

// Update comparison pagination info
function updateComparisonPaginationInfo(currentPage, totalPages, totalItems) {
    const info = document.getElementById('comparisonPaginationInfo');
    if (!info) return;
    
    if (totalItems === 0) {
        info.textContent = 'No companies found';
    } else {
        const startItem = (currentPage - 1) * comparisonPerPage + 1;
        const endItem = Math.min(currentPage * comparisonPerPage, totalItems);
        info.textContent = `${translations.showing} ${startItem}-${endItem} ${translations.of} ${totalItems} ${translations.companies}`;
    }
}

// Update comparison pagination controls
function updateComparisonPaginationControls(pagination) {
    const controls = document.getElementById('comparisonPaginationControls');
    
    if (!controls) {
        return;
    }
    
    if (!pagination || pagination.pages <= 1) {
        controls.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Previous button
    if (pagination.has_prev) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadComparisonPage(${pagination.page - 1}); return false;">
                    <i class="fas fa-chevron-left"></i>
                </a>
            </li>
        `;
    } else {
        html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-left"></i></span></li>';
    }
    
    // Page numbers with smart ellipsis
    const pages = generatePaginationPages(pagination.page, pagination.pages);
    for (const pageNum of pages) {
        if (pageNum === null) {
            html += '<li class="page-item disabled"><span class="page-link">…</span></li>';
        } else if (pageNum === pagination.page) {
            html += `<li class="page-item active"><span class="page-link">${pageNum}</span></li>`;
        } else {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="loadComparisonPage(${pageNum}); return false;">${pageNum}</a></li>`;
        }
    }
    
    // Next button
    if (pagination.has_next) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadComparisonPage(${pagination.page + 1}); return false;">
                    <i class="fas fa-chevron-right"></i>
                </a>
            </li>
        `;
    } else {
        html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-right"></i></span></li>';
    }
    
    controls.innerHTML = html;
}

// Load comparison page
function loadComparisonPage(page) {
    currentComparisonPage = page;
    
    // If there's an active search/filter, apply it with new page
    const searchQuery = document.getElementById('comparisonSearch')?.value.trim().toLowerCase() || '';
    const balanceFilter = document.getElementById('comparisonBalanceFilter')?.value || '';
    
    if (searchQuery || balanceFilter) {
        searchComparisonTable();
    } else if (currentComparisonData) {
        populateCompanyComparison(currentComparisonData, page);
    }
}

// Run color override multiple times to catch dynamically loaded content
function runColorOverride() {
    setTimeout(forceRemoveYellowColors, 100);
    setTimeout(forceRemoveYellowColors, 500);
    setTimeout(forceRemoveYellowColors, 1000);
    setTimeout(forceRemoveYellowColors, 2000);
    setTimeout(forceRemoveYellowColors, 5000);
}

// Direct company NPS data loading as fallback
function loadCompanyNpsDataDirect() {
    console.log('Direct loading of company NPS data...');
    
    // Check if we're in the Survey Insights tab or if element exists
    const tbody = document.getElementById('companyNpsTable');
    if (!tbody) {
        console.log('companyNpsTable element not found - probably in different tab, skipping...');
        return;
    }

    // If the table already has server-rendered rows, skip the fallback fetch
    // (fetching without a campaign_id returns empty for demo accounts with no active campaign)
    if (tbody.querySelectorAll('tr').length > 0) {
        console.log('companyNpsTable already has data, skipping direct fetch.');
        return;
    }

    // Build URL with campaign_id if available
    const campaignSelect = document.getElementById('campaignFilter');
    const campaignParam = (campaignSelect && campaignSelect.value) ? `?campaign=${campaignSelect.value}` : '';

    fetch('/api/company_nps' + campaignParam)
        .then(response => response.json())
        .then(data => {
            console.log('Direct API response:', data);
            if (data.success && data.data) {
                console.log('Found table, populating with', data.data.length, 'companies');
                // Clear existing content safely
                tbody.innerHTML = '';
                
                // Create rows using safe DOM methods
                data.data.forEach(company => {
                    const row = document.createElement('tr');
                    
                    // Company name with bold formatting
                    const nameCell = document.createElement('td');
                    const nameStrong = document.createElement('strong');
                    nameStrong.textContent = company.company_name;
                    nameCell.appendChild(nameStrong);
                    row.appendChild(nameCell);
                    
                    // Total responses
                    const responsesCell = document.createElement('td');
                    responsesCell.textContent = company.total_responses;
                    row.appendChild(responsesCell);
                    
                    // Average NPS
                    const avgNpsCell = document.createElement('td');
                    avgNpsCell.textContent = company.avg_nps;
                    row.appendChild(avgNpsCell);
                    
                    // Company NPS badge
                    const npsCell = document.createElement('td');
                    const npsBadge = document.createElement('span');
                    npsBadge.className = 'badge bg-primary';
                    npsBadge.textContent = company.company_nps;
                    npsCell.appendChild(npsBadge);
                    row.appendChild(npsCell);
                    
                    // Distribution (P/Pa/D)
                    const distCell = document.createElement('td');
                    const distSmall = document.createElement('small');
                    distSmall.textContent = `${company.promoters}P / ${company.passives}Pa / ${company.detractors}D`;
                    distCell.appendChild(distSmall);
                    row.appendChild(distCell);
                    
                    // Risk level badge
                    const riskCell = document.createElement('td');
                    const riskBadge = document.createElement('span');
                    riskBadge.className = 'badge';
                    riskBadge.style.backgroundColor = '#8A8A8A';
                    riskBadge.style.color = 'white';
                    riskBadge.textContent = company.risk_level;
                    riskCell.appendChild(riskBadge);
                    row.appendChild(riskCell);
                    
                    // Latest response
                    const responseCell = document.createElement('td');
                    responseCell.textContent = company.latest_response || translations.na;
                    row.appendChild(responseCell);
                    
                    // Latest churn risk
                    const churnCell = document.createElement('td');
                    churnCell.textContent = company.latest_churn_risk || translations.na;
                    row.appendChild(churnCell);
                    
                    tbody.appendChild(row);
                });
            }
        })
        .catch(error => {
            console.error('Direct loading error:', error);
        });
}

function loadDashboardData() {
    console.log('loadDashboardData called');
    
    // SECURITY FIX: Clear ALL stale UI elements FIRST to prevent cross-tenant data flash
    // This runs for ALL code paths (initial load, refreshData, applyCampaignFilter, etc.)
    console.log('🔒 Clearing ALL stale dashboard UI to prevent cross-tenant exposure');
    
    // Clear cached dashboard data
    dashboardData = null;
    
    // Clear KPI cards immediately with loading placeholders
    const kpiElements = {
        'totalResponsesValue': '...',
        'totalCompaniesValue': '...',
        'avgNpsValue': '...',
        'totalPromotersValue': '...',
        'totalDetractorsValue': '...',
        'avgSatisfactionValue': '...',
        'avgProductValueValue': '...',
        'avgSupportQualityValue': '...',
        'avgProfessionalServicesValue': '...'
    };
    
    for (const [elementId, placeholderValue] of Object.entries(kpiElements)) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = placeholderValue;
        }
    }
    
    // Clear chart canvases
    const chartIds = ['npsChart', 'sentimentChartGrowth', 'sentimentChart', 'ratingsChart', 'tenureChart', 'growthFactorChart', 'themesChart'];
    for (const chartId of chartIds) {
        const chartElement = document.getElementById(chartId);
        if (chartElement) {
            const ctx = chartElement.getContext('2d');
            ctx.clearRect(0, 0, chartElement.width, chartElement.height);
        }
    }
    
    // Clear Survey Insights tables with loading indicators
    const loadingHtml = `<tr><td colspan="7" class="text-center"><div class="spinner-border spinner-border-sm text-primary" role="status"><span class="visually-hidden">Loading...</span></div> ${translations.loading || 'Loading...'}</td></tr>`;
    const companyNpsTableBody = document.querySelector('#companyNpsTable tbody');
    const tenureNpsTableBody = document.querySelector('#tenureNpsTable tbody');
    const accountIntelligenceTableBody = document.querySelector('#accountIntelligenceTable tbody');
    const surveyResponsesTableBody = document.querySelector('#surveyResponsesTable tbody');
    
    if (companyNpsTableBody) companyNpsTableBody.innerHTML = loadingHtml;
    if (tenureNpsTableBody) tenureNpsTableBody.innerHTML = loadingHtml;
    if (accountIntelligenceTableBody) accountIntelligenceTableBody.innerHTML = `<tr><td colspan="6" class="text-center"><div class="spinner-border spinner-border-sm text-primary" role="status"><span class="visually-hidden">Loading...</span></div> ${translations.loading || 'Loading...'}</td></tr>`;
    if (surveyResponsesTableBody) surveyResponsesTableBody.innerHTML = `<tr><td colspan="8" class="text-center"><div class="spinner-border spinner-border-sm text-primary" role="status"><span class="visually-hidden">Loading...</span></div> ${translations.loading || 'Loading...'}</td></tr>`;
    
    // Clear segmentation analytics
    const segmentationContainer = document.getElementById('segmentationAnalyticsContent');
    if (segmentationContainer) {
        segmentationContainer.innerHTML = `<div class="text-center p-4"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">${translations.loading || 'Loading...'}</p></div>`;
    }
    
    // Now proceed with normal loading flow
    const loadingElement = document.getElementById('loadingIndicator');
    const contentElement = document.getElementById('dashboardContent');
    
    if (loadingElement) loadingElement.classList.remove('d-none');
    if (contentElement) contentElement.classList.add('d-none');
    
    // Build URL with campaign filter if selected
    let url = '/api/dashboard_data';
    const urlParams = new URLSearchParams();
    
    if (selectedCampaignId) {
        urlParams.append('campaign_id', selectedCampaignId);
    }
    
    // Add cache-busting timestamp
    urlParams.append('_t', Date.now());
    
    url += '?' + urlParams.toString();
    
    console.log('🔍 Frontend Debug - Calling URL:', url);
    console.log('🔍 Frontend Debug - selectedCampaignId:', selectedCampaignId);
    
    // Return the Promise to enable proper await behavior
    return fetch(url, {
        method: 'GET',
        headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    })
        .then(response => {
            console.log('API response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Dashboard data received:', Object.keys(data));
            console.log('🔍 Frontend Debug - Raw API Response average_ratings:', data.average_ratings);
            if (data.error) {
                throw new Error(data.error);
            }
            
            dashboardData = data;
            
            // Show content BEFORE creating charts
            if (loadingElement) loadingElement.classList.add('d-none');
            if (contentElement) contentElement.classList.remove('d-none');
            
            // Now populate dashboard with charts AFTER content is visible
            populateDashboard();
            
            // Return the data for chaining if needed
            return data;
        })
        .catch(error => {
            console.error('Error loading dashboard data:', error);
            
            // Hide page loading overlay on error
            if (pageOverlay) {
                pageOverlay.classList.add('hidden');
                setTimeout(() => {
                    if (pageOverlay && pageOverlay.classList.contains('hidden')) {
                        pageOverlay.style.display = 'none';
                    }
                }, 300);
            }
            
            if (loadingElement) {
                // Create error element safely using DOM methods
                const errorDiv = document.createElement('div');
                errorDiv.className = 'alert alert-danger';
                errorDiv.textContent = translations.errorLoadingDashboardData + error.message;
                
                // Clear loading element and append error
                loadingElement.innerHTML = '';
                loadingElement.appendChild(errorDiv);
            }
            // Re-throw error to maintain Promise chain behavior
            throw error;
        });
}

function populateDashboard() {
    console.log('⚡ populateDashboard called - OPTIMIZED PROGRESSIVE LOADING');
    
    // ========== CRITICAL PATH: Immediate rendering (unblock browser) ==========
    // Update key metrics (visible immediately)
    document.getElementById('totalResponses').textContent = dashboardData.total_responses || 0;
    document.getElementById('npsScore').textContent = dashboardData.nps_score || 0;
    document.getElementById('recentResponses').textContent = dashboardData.recent_responses || 0;
    document.getElementById('highRiskCount').textContent = dashboardData.high_risk_accounts?.length || 0;
    
    // Response Rate - show percentage or N/A if not available
    const responseRateEl = document.getElementById('responseRate');
    if (responseRateEl) {
        if (dashboardData.participation_rate !== null && dashboardData.participation_rate !== undefined) {
            responseRateEl.textContent = dashboardData.participation_rate + '%';
        } else {
            responseRateEl.textContent = 'N/A';
        }
    }
    
    // Growth potential as percentage
    const growthPotential = dashboardData.growth_factor_analysis?.total_growth_potential || 0;
    document.getElementById('growthPotential').textContent = Math.round(growthPotential * 100) + '%';
    
    // Populate high risk accounts (visible on Overview tab)
    populateHighRiskAccounts();
    
    // Create themes chart (visible on Overview tab) - defer slightly for smooth rendering
    setTimeout(() => createThemesChart(), 50);
    
    // Set up tab event listeners immediately (needed for tab switching)
    setupTabEventListeners();
    
    // ========== DEFERRED PATH: Load non-visible data asynchronously (unblock UI) ==========
    // Use requestAnimationFrame to defer heavy operations to next frame
    requestAnimationFrame(() => {
        console.log('⏳ Loading deferred data (non-blocking)...');
        
        // Defer account intelligence (Analytics tab - not visible initially)
        setTimeout(() => loadAccountIntelligence(), 100);
        
        // Defer KPI overview (Executive Summary section - below the fold initially)
        setTimeout(() => loadKpiOverview(), 150);
        
        // Defer survey responses (Survey Insights tab - not visible initially)
        setTimeout(() => loadSurveyResponses(), 200);
        
        // Defer company NPS data (Analytics tab - not visible initially)
        setTimeout(() => {
            console.log('About to call loadCompanyNpsData...');
            loadCompanyNpsData();
        }, 250);
        
        // Defer tenure NPS data (Analytics tab - not visible initially)
        setTimeout(() => {
            console.log('About to call loadTenureNpsData...');
            loadTenureNpsData();
        }, 300);
        
        // Defer segmentation insights (Segmentation tab - not visible initially)
        setTimeout(() => {
            console.log('About to call renderSegmentationInsights...');
            if (typeof renderSegmentationInsights === 'function') {
                renderSegmentationInsights(dashboardData);
            }
        }, 350);
        
        // Defer classic survey analytics (Analytics tab - not visible initially)
        setTimeout(() => {
            if (typeof checkAndLoadClassicAnalytics === 'function') {
                checkAndLoadClassicAnalytics(dashboardData);
            }
        }, 400);
        
        console.log('✅ Deferred data loading scheduled');
    });
    
    console.log('✅ Critical path complete - page interactive');
}

// Helper function to get active campaign ID
function getActiveCampaignId() {
    // Find active campaign from available campaigns
    const activeCampaign = availableCampaigns.find(c => c.status === 'active');
    return activeCampaign ? activeCampaign.id : null;
}

// Note: setupTabEventListeners function is defined later in the file with full campaign management support

// ─── Brand Palette Helper ───────────────────────────────────────────────────
// Reads window.brandColors (emitted by the template) and returns a palette
// object. `configured` is true only when the brand palette was actually set
// by the template. Chart functions use this flag to decide whether to apply
// brand colors or fall back to their original hardcoded defaults, ensuring
// zero visual regression for accounts without configured branding.
function getBrandPalette() {
    const bc = window.brandColors || {};
    const primary   = (bc.primary   && bc.primary   !== '') ? bc.primary   : null;
    const secondary = (bc.secondary && bc.secondary !== '') ? bc.secondary : null;
    const accent    = (bc.accent    && bc.accent    !== '') ? bc.accent    : null;
    const configured = !!(primary || secondary || accent);

    // Parse a hex color to [r, g, b]
    function hexToRgb(hex) {
        const h = hex.replace('#', '');
        return [
            parseInt(h.substring(0, 2), 16),
            parseInt(h.substring(2, 4), 16),
            parseInt(h.substring(4, 6), 16)
        ];
    }

    // Blend a color toward white by `amount` (0–1)
    function tintHex(hex, amount) {
        const [r, g, b] = hexToRgb(hex);
        const tr = Math.round(r + (255 - r) * amount);
        const tg = Math.round(g + (255 - g) * amount);
        const tb = Math.round(b + (255 - b) * amount);
        return '#' + [tr, tg, tb].map(v => v.toString(16).padStart(2, '0')).join('');
    }

    // Generate n evenly-spaced tinted variants from baseHex
    // Steps go from the base color (darkest) to a light tint.
    function tintSequence(baseHex, n) {
        const result = [];
        for (let i = 0; i < n; i++) {
            result.push(tintHex(baseHex, i * (0.55 / Math.max(n - 1, 1))));
        }
        return result;
    }

    return { primary, secondary, accent, configured, tintSequence };
}
// ────────────────────────────────────────────────────────────────────────────

function createNpsChart() {
    // Support campaign_insights.html (npsChart on Overview) and dashboard.html (npsChart)
    const chartElement = document.getElementById('npsChart') || document.getElementById('npsChartGrowth');
    if (!chartElement) {
        console.warn('NPS chart element not found');
        return;
    }
    const chartKey = chartElement.id;
    
    const ctx = chartElement.getContext('2d');
    
    // Destroy existing chart if it exists
    if (charts[chartKey]) {
        charts[chartKey].destroy();
    }
    
    const npsData = dashboardData.nps_distribution || [];
    const labels = npsData.map(item => item.category);
    const data = npsData.map(item => item.count);
    const total = data.reduce((a, b) => a + b, 0);

    // Semantic colours mapped by label name (case-insensitive)
    const NPS_COLOUR_MAP = {
        promoter:  '#22C55E', // green
        passive:   '#F59E0B', // amber
        detractor: '#EF4444'  // red
    };
    const chartColors = labels.map(lbl => {
        const key = lbl.toLowerCase();
        for (const k of Object.keys(NPS_COLOUR_MAP)) {
            if (key.includes(k)) return NPS_COLOUR_MAP[k];
        }
        return '#BDBDBD';
    });

    // Centre-text plugin: shows NPS score
    const npsScore = dashboardData.nps_score ?? null;
    const npsCentrePlugin = {
        id: 'npsCentre',
        afterDraw(chart) {
            if (npsScore === null) return;
            const { ctx: c, chartArea: { left, top, right, bottom } } = chart;
            const cx = (left + right) / 2;
            const cy = (top + bottom) / 2;
            c.save();
            c.textAlign = 'center';
            c.textBaseline = 'middle';
            c.font = 'bold 22px Montserrat, sans-serif';
            c.fillStyle = '#000000';
            c.fillText(npsScore > 0 ? '+' + npsScore : npsScore, cx, cy - 8);
            c.font = '12px Karla, sans-serif';
            c.fillStyle = '#BDBDBD';
            c.fillText('NPS', cx, cy + 12);
            c.restore();
        }
    };

    // Arc % labels plugin
    const npsArcLabelPlugin = {
        id: 'npsArcLabels',
        afterDatasetDraw(chart) {
            if (total === 0) return;
            const { ctx: c, data: d } = chart;
            const dataset = chart.getDatasetMeta(0);
            dataset.data.forEach((arc, i) => {
                const pct = Math.round((d.datasets[0].data[i] / total) * 100);
                if (pct === 0) return;
                const { x, y } = arc.tooltipPosition();
                c.save();
                c.textAlign = 'center';
                c.textBaseline = 'middle';
                c.font = 'bold 11px Karla, sans-serif';
                c.fillStyle = '#FFFFFF';
                c.fillText(pct + '%', x, y);
                c.restore();
            });
        }
    };
    
    // Get mobile-responsive configuration
    const config = getMobileChartConfig();
    
    charts[chartKey] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: chartColors,
                borderWidth: 3,
                borderColor: '#FFFFFF',
                hoverBorderWidth: 4,
                hoverBorderColor: '#333333'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: config.maintainAspectRatio,
            cutout: '60%',
            plugins: {
                legend: {
                    position: config.legendPosition,
                    labels: {
                        color: '#000000',
                        usePointStyle: true,
                        padding: config.legendPadding,
                        font: {
                            family: 'Karla',
                            size: config.legendFontSize,
                            weight: '500'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: '#000000',
                    titleColor: '#FFFFFF',
                    bodyColor: '#FFFFFF',
                    borderColor: '#333333',
                    borderWidth: 1,
                    cornerRadius: 8,
                    titleFont: {
                        family: 'Montserrat',
                        size: config.fontSize,
                        weight: '600'
                    },
                    bodyFont: {
                        family: 'Karla',
                        size: config.fontSize - 1,
                        weight: '500'
                    },
                    callbacks: {
                        label(context) {
                            const count = context.parsed;
                            const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                            return ` ${count} responses (${pct}%)`;
                        }
                    }
                }
            },
            elements: {
                arc: {
                    borderRadius: 4
                }
            }
        },
        plugins: [npsCentrePlugin, npsArcLabelPlugin]
    });
}

function createSentimentChart() {
    // Support both campaign_insights.html (sentimentChartGrowth) and dashboard.html (sentimentChart)
    const chartElement = document.getElementById('sentimentChartGrowth') || document.getElementById('sentimentChart');
    if (!chartElement) {
        console.warn('Sentiment chart element not found');
        return;
    }
    const chartKey = chartElement.id === 'sentimentChartGrowth' ? 'sentimentChartGrowth' : 'sentimentChart';
    
    const ctx = chartElement.getContext('2d');
    
    // Destroy existing chart if it exists
    if (charts[chartKey]) {
        charts[chartKey].destroy();
    }
    
    const sentimentData = dashboardData.sentiment_distribution || [];
    
    // Filter out items with missing sentiment data and add null checks
    const validSentimentData = sentimentData.filter(item => item.sentiment && typeof item.sentiment === 'string');
    
    if (validSentimentData.length === 0) {
        console.warn('No valid sentiment data available for chart');
        const calloutClr = document.getElementById('sentimentCallout');
        if (calloutClr) { calloutClr.style.display = 'none'; calloutClr.innerHTML = ''; }
        // Create empty chart with message
        charts[chartKey] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['No Data'],
                datasets: [{
                    label: 'Responses',
                    data: [0],
                    backgroundColor: ['#E9E8E4'],
                    borderWidth: 1,
                    borderColor: '#E9E8E4'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: getMobileChartConfig().maintainAspectRatio,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                },
                scales: {
                    y: { beginAtZero: true, max: 1 },
                    x: { display: false }
                }
            }
        });
        return;
    }
    
    const labels = validSentimentData.map(item => item.sentiment.charAt(0).toUpperCase() + item.sentiment.slice(1));
    const data = validSentimentData.map(item => item.count || 0);
    const sentTotal = data.reduce((a, b) => a + b, 0);

    // Semantic colours by label name (V2: brand gray for neutral)
    const SENTIMENT_COLOUR_MAP = {
        positive: '#22C55E',
        neutral:  '#BDBDBD',
        negative: '#EF4444'
    };
    const colors = labels.map(lbl => {
        const key = lbl.toLowerCase();
        return SENTIMENT_COLOUR_MAP[key] || '#BDBDBD';
    });

    // Dominant sentiment callout
    const sentimentCalloutEl = document.getElementById('sentimentCallout');
    if (sentimentCalloutEl) {
        if (sentTotal > 0) {
            const maxIdx = data.indexOf(Math.max(...data));
            const domLabel = labels[maxIdx];
            const domPct = Math.round((data[maxIdx] / sentTotal) * 100);
            const domColour = colors[maxIdx];
            sentimentCalloutEl.innerHTML = `<div class="d-flex align-items-center gap-2 mt-2 p-2 rounded" style="background:#F8F9FA; border-left: 3px solid ${domColour};">
            <i class="fas fa-circle" style="color:${domColour}; font-size:0.65rem;"></i>
            <small class="text-muted">Dominant sentiment: <strong style="color:${domColour};">${domLabel}</strong> at <strong>${domPct}%</strong> of responses</small>
        </div>`;
            sentimentCalloutEl.style.display = 'block';
        } else {
            sentimentCalloutEl.style.display = 'none';
            sentimentCalloutEl.innerHTML = '';
        }
    }

    // % label above bar plugin
    const sentimentBarLabelPlugin = {
        id: 'sentimentBarLabels',
        afterDatasetDraw(chart) {
            if (sentTotal === 0) return;
            const { ctx: c, data: d } = chart;
            chart.getDatasetMeta(0).data.forEach((bar, i) => {
                const pct = Math.round((d.datasets[0].data[i] / sentTotal) * 100);
                const { x, y } = bar.getProps(['x', 'y'], true);
                c.save();
                c.textAlign = 'center';
                c.textBaseline = 'bottom';
                c.font = 'bold 11px Karla, sans-serif';
                c.fillStyle = '#000000';
                c.fillText(pct + '%', x, y - 2);
                c.restore();
            });
        }
    };
    
    // Get mobile-responsive configuration
    const config = getMobileChartConfig();
    
    charts[chartKey] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: translations.responses,
                data: data,
                backgroundColor: colors,
                borderWidth: 1,
                borderColor: '#E9E8E4'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: config.maintainAspectRatio,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: '#000000',
                    titleColor: '#FFFFFF',
                    bodyColor: '#FFFFFF',
                    borderColor: '#333333',
                    borderWidth: 1,
                    cornerRadius: 8,
                    titleFont: { family: 'Montserrat', size: config.fontSize, weight: '600' },
                    bodyFont: { family: 'Karla', size: config.fontSize - 1, weight: '500' },
                    callbacks: {
                        label(context) {
                            const count = context.parsed.y;
                            const pct = sentTotal > 0 ? Math.round((count / sentTotal) * 100) : 0;
                            return ` ${count} responses (${pct}%)`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#000000',
                        font: {
                            size: config.fontSize
                        }
                    },
                    grid: {
                        color: '#E9E8E4'
                    }
                },
                x: {
                    ticks: {
                        color: '#000000',
                        font: {
                            size: config.fontSize
                        }
                    },
                    grid: {
                        color: '#E9E8E4'
                    }
                }
            }
        },
        plugins: [sentimentBarLabelPlugin]
    });
}

function createRatingsChart() {
    const chartElement = document.getElementById('ratingsChart');
    if (!chartElement) {
        console.warn('Ratings chart element not found');
        return;
    }
    
    const ctx = chartElement.getContext('2d');
    
    // Destroy existing chart if it exists
    if (charts.ratingsChart) {
        charts.ratingsChart.destroy();
    }
    
    const ratings = dashboardData.average_ratings || {};
    
    const labels = [translations.satisfaction, translations.productValue, translations.service, translations.pricing];
    const data = [
        ratings.satisfaction || 0,
        ratings.product_value || 0,
        ratings.service || 0,
        ratings.pricing || 0
    ];
    
    // Semantic threshold colours: green=good, amber=moderate, red=poor.
    // Charts always use the red/green/yellow pattern for data meaning.
    const nonZeroData = data.filter(v => v > 0);
    const barColors = data.map(v => {
        if (v >= 4) return '#22C55E';
        if (v >= 3) return '#F59E0B';
        return '#EF4444';
    });

    // Weakest metric callout
    const ratingsCalloutEl = document.getElementById('ratingsCallout');
    if (ratingsCalloutEl) {
        if (nonZeroData.length > 0) {
            const minVal = Math.min(...data.filter((_, i) => data[i] > 0));
            const minIdx = data.indexOf(minVal);
            const minLabel = labels[minIdx];
            const minColour = barColors[minIdx];
            ratingsCalloutEl.innerHTML = `<div class="d-flex align-items-center gap-2 mt-2 p-2 rounded" style="background:#F8F9FA; border-left: 3px solid ${minColour};">
            <i class="fas fa-exclamation-circle" style="color:${minColour}; font-size:0.8rem;"></i>
            <small class="text-muted">Weakest metric: <strong style="color:${minColour};">${minLabel}</strong> scored <strong>${minVal.toFixed(1)} / 5</strong></small>
        </div>`;
            ratingsCalloutEl.style.display = 'block';
        } else {
            ratingsCalloutEl.style.display = 'none';
            ratingsCalloutEl.innerHTML = '';
        }
    }

    // Value label at end of each bar plugin
    const ratingsBarLabelPlugin = {
        id: 'ratingsBarLabels',
        afterDatasetDraw(chart) {
            const { ctx: c, data: d } = chart;
            chart.getDatasetMeta(0).data.forEach((bar, i) => {
                const val = d.datasets[0].data[i];
                if (!val) return;
                const { x, y } = bar.getProps(['x', 'y'], true);
                c.save();
                c.textAlign = 'left';
                c.textBaseline = 'middle';
                c.font = 'bold 11px Karla, sans-serif';
                c.fillStyle = '#000000';
                c.fillText(val.toFixed(1) + ' / 5', x + 6, y);
                c.restore();
            });
        }
    };
    
    // Get mobile-responsive configuration
    const config = getMobileChartConfig();
    
    charts.ratingsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: translations.averageRating,
                data: data,
                backgroundColor: barColors,
                borderWidth: 0,
                borderRadius: 4,
                barThickness: 28
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: config.maintainAspectRatio,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: '#000000',
                    titleColor: '#FFFFFF',
                    bodyColor: '#FFFFFF',
                    borderColor: '#333333',
                    borderWidth: 1,
                    cornerRadius: 8,
                    titleFont: { family: 'Montserrat', size: config.fontSize, weight: '600' },
                    bodyFont: { family: 'Karla', size: config.fontSize - 1, weight: '500' },
                    callbacks: {
                        label(context) {
                            const v = context.parsed.x;
                            return ` ${v.toFixed(1)} / 5`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    max: 5,
                    ticks: {
                        color: '#000000',
                        stepSize: 1,
                        font: { size: config.fontSize }
                    },
                    grid: { color: '#E9E8E4' }
                },
                y: {
                    ticks: {
                        color: '#000000',
                        font: { size: config.fontSize }
                    },
                    grid: { display: false }
                }
            }
        },
        plugins: [ratingsBarLabelPlugin]
    });
}

function createThemesChart() {
    console.log('🎨 createThemesChart() called');
    console.log('📊 dashboardData available:', !!dashboardData);
    console.log('📊 dashboardData.key_themes:', dashboardData?.key_themes?.length || 'undefined');
    
    // Ensure we have dashboard data before proceeding
    if (!dashboardData) {
        console.warn('⚠️ Dashboard data not loaded yet, skipping themes chart');
        return;
    }
    
    const chartElement = document.getElementById('themesChart');
    console.log('🎯 Chart element found:', !!chartElement);
    
    if (!chartElement) {
        console.warn('❌ Themes chart element not found');
        return;
    }
    
    const ctx = chartElement.getContext('2d');
    
    // Destroy existing chart if it exists
    if (charts.themesChart) {
        console.log('🗑️ Destroying existing chart');
        charts.themesChart.destroy();
    }
    
    const themes = dashboardData.key_themes || [];
    console.log('📋 Themes data:', themes.length, themes.slice(0, 2));
    
    if (themes.length === 0) {
        console.log('❌ No themes found - creating empty chart to preserve canvas');
        // Hide/clear callout when there is no data
        const themesCalloutElEmpty = document.getElementById('themesCallout');
        if (themesCalloutElEmpty) { themesCalloutElEmpty.style.display = 'none'; themesCalloutElEmpty.innerHTML = ''; }
        // Create an empty chart instead of destroying the canvas element
        charts.themesChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['No Data'],
                datasets: [{
                    label: 'Mentions',
                    data: [0],
                    backgroundColor: '#E9E8E4',
                    borderWidth: 1,
                    borderColor: '#E9E8E4'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: getMobileChartConfig().maintainAspectRatio,
                indexAxis: 'y',
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                },
                scales: {
                    y: { display: false },
                    x: { 
                        beginAtZero: true,
                        max: 1,
                        display: false
                    }
                }
            }
        });
        return;
    }
    
    // Sort themes by count (descending) and take top 10
    const sortedThemes = themes.sort((a, b) => b.count - a.count).slice(0, 10);
    
    const labels = sortedThemes.map(item => item.theme.charAt(0).toUpperCase() + item.theme.slice(1));
    const data = sortedThemes.map(item => item.count);
    const totalResponses = dashboardData.total_responses || 1;

    // Derive per-bar color from dominant sentiment
    function themeBarColor(item) {
        const sb = item.sentiment_breakdown;
        if (!sb) return '#BDBDBD';
        const pos = sb.positive || 0;
        const neg = sb.negative || 0;
        const total = pos + neg + (sb.neutral || 0);
        if (total === 0) return '#BDBDBD';
        if (pos / total > 0.6) return '#22C55E';   // green — predominantly positive
        if (neg / total > 0.6) return '#EF4444';   // red — predominantly negative
        return '#F59E0B';                           // amber — mixed / neutral
    }
    const backgroundColors = sortedThemes.map(themeBarColor);

    // Value label plugin: "12 · 38%" at end of each bar
    const themesValueLabelPlugin = {
        id: 'themesValueLabels',
        afterDatasetsDraw(chart) {
            const { ctx: c, data: d, chartArea } = chart;
            const dataset = d.datasets[0];
            const meta = chart.getDatasetMeta(0);
            meta.data.forEach((bar, i) => {
                const count = dataset.data[i];
                const pct = Math.round((count / totalResponses) * 100);
                const label = `${count} · ${pct}%`;
                const { x, y } = bar.getProps(['x', 'y'], true);
                c.save();
                c.textAlign = 'left';
                c.textBaseline = 'middle';
                c.fillStyle = '#000000';
                c.font = `bold 11px sans-serif`;
                c.fillText(label, x + 6, y);
                c.restore();
            });
        }
    };

    // Get mobile-responsive configuration
    const config = getMobileChartConfig();
    
    charts.themesChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Mentions',
                data: data,
                backgroundColor: backgroundColors,
                borderWidth: 1,
                borderColor: '#E9E8E4'
            }]
        },
        plugins: [themesValueLabelPlugin],
        options: {
            responsive: true,
            maintainAspectRatio: config.maintainAspectRatio,
            indexAxis: 'y',
            layout: {
                padding: { right: 80 }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(items) {
                            return items[0].label;
                        },
                        label: function(context) {
                            const i = context.dataIndex;
                            const item = sortedThemes[i];
                            const count = item.count;
                            const pct = Math.round((count / totalResponses) * 100);
                            const lines = [
                                `Mentions: ${count} (${pct}% of responses)`
                            ];
                            const sb = item.sentiment_breakdown;
                            if (sb) {
                                const tot = (sb.positive || 0) + (sb.negative || 0) + (sb.neutral || 0);
                                if (tot > 0) {
                                    lines.push(`Positive: ${sb.positive || 0} (${Math.round(((sb.positive || 0) / tot) * 100)}%)`);
                                    lines.push(`Neutral: ${sb.neutral || 0} (${Math.round(((sb.neutral || 0) / tot) * 100)}%)`);
                                    lines.push(`Negative: ${sb.negative || 0} (${Math.round(((sb.negative || 0) / tot) * 100)}%)`);
                                }
                            }
                            return lines;
                        }
                    }
                }
            },
            scales: {
                y: {
                    ticks: {
                        color: '#000000',
                        font: {
                            size: config.fontSize - 1
                        },
                        maxTicksLimit: false,
                        autoSkip: false,
                        maxRotation: 0,
                        minRotation: 0
                    },
                    grid: {
                        color: '#E9E8E4'
                    }
                },
                x: {
                    beginAtZero: true,
                    ticks: {
                        color: '#000000',
                        font: {
                            size: config.fontSize
                        }
                    },
                    grid: {
                        color: '#E9E8E4'
                    }
                }
            }
        }
    });

    // Populate interpretive callout
    const themesCalloutEl = document.getElementById('themesCallout');
    if (themesCalloutEl && sortedThemes.length > 0) {
        const topTheme = sortedThemes[0];
        const topPct = Math.round((topTheme.count / totalResponses) * 100);

        function dominantSentimentLabel(item) {
            const sb = item.sentiment_breakdown;
            if (!sb) return 'mixed';
            const pos = sb.positive || 0;
            const neg = sb.negative || 0;
            const tot = pos + neg + (sb.neutral || 0);
            if (tot === 0) return 'mixed';
            if (pos / tot > 0.6) return 'positive';
            if (neg / tot > 0.6) return 'negative';
            return 'mixed';
        }

        function escapeHtml(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        const topTone = dominantSentimentLabel(topTheme);
        const topName = escapeHtml(topTheme.theme.charAt(0).toUpperCase() + topTheme.theme.slice(1));

        let calloutHtml = `<div class="alert alert-light border-start border-3 py-2 px-3 mb-2" style="border-color:#E13A44!important;font-size:0.85rem;">
            <i class="fas fa-lightbulb me-2" style="color:#E13A44;"></i>
            Customers most frequently mentioned <strong>${topName}</strong> — cited in <strong>${topPct}%</strong> of responses, with a predominantly <strong>${escapeHtml(topTone)}</strong> tone.
        </div>`;

        // Watch signal: highest-negative theme (if different from top theme)
        if (sortedThemes.length > 1) {
            let mostNegTheme = null;
            let mostNegRatio = 0;
            sortedThemes.forEach(item => {
                const sb = item.sentiment_breakdown;
                if (!sb) return;
                const neg = sb.negative || 0;
                const tot = (sb.positive || 0) + neg + (sb.neutral || 0);
                if (tot > 0 && neg / tot > mostNegRatio) {
                    mostNegRatio = neg / tot;
                    mostNegTheme = item;
                }
            });
            if (mostNegTheme && mostNegTheme.theme.toLowerCase() !== topTheme.theme.toLowerCase()) {
                const watchName = escapeHtml(mostNegTheme.theme.charAt(0).toUpperCase() + mostNegTheme.theme.slice(1));
                calloutHtml += `<div class="alert alert-warning border-start border-3 py-2 px-3" style="border-color:#EF4444!important;font-size:0.85rem;">
                    <i class="fas fa-exclamation-triangle me-2" style="color:#EF4444;"></i>
                    Watch: <strong>${watchName}</strong> carries the strongest negative signal.
                </div>`;
            }
        }

        themesCalloutEl.innerHTML = calloutHtml;
        themesCalloutEl.style.display = 'block';
    } else if (themesCalloutEl) {
        themesCalloutEl.style.display = 'none';
        themesCalloutEl.innerHTML = '';
    }
}

function createTenureChart() {
    // Strategic cohort definitions — maps the 7 controlled tenure strings from
    // map_tenure_years_to_category() into 5 meaningful business cohorts
    // When brand primary is configured, derive a 5-step tint sequence from it.
    // When no brand is configured, fall back to the original hardcoded palette.
    const _tenureBp = getBrandPalette();
    const _TENURE_DEFAULTS = ['#E13A44', '#000000', '#8A8A8A', '#BDBDBD', '#E9E8E4'];
    const _tenureColors = (_tenureBp.configured && _tenureBp.primary)
        ? _tenureBp.tintSequence(_tenureBp.primary, 5)
        : _TENURE_DEFAULTS;
    const TENURE_COHORTS = [
        { label: 'New (<1 yr)',          keys: ['Less than 6 months', '6 months - 1 year'],  color: _tenureColors[0] },
        { label: 'Growing (1–3 yr)',     keys: ['1-2 years', '2-3 years'],                   color: _tenureColors[1] },
        { label: 'Established (3–5 yr)', keys: ['3-5 years'],                                color: _tenureColors[2] },
        { label: 'Mature (5–10 yr)',     keys: ['5-10 years'],                               color: _tenureColors[3] },
        { label: 'Strategic (10+ yr)',   keys: ['More than 10 years'],                       color: _tenureColors[4] }
    ];

    let chartElement = document.getElementById('tenureChart');
    if (!chartElement) {
        const containers = document.querySelectorAll('.chart-container');
        for (const c of containers) {
            if (c.querySelector('.alert-info') && c.textContent.includes('tenure data')) {
                c.innerHTML = '<canvas id="tenureChart"></canvas>';
                chartElement = document.getElementById('tenureChart');
                break;
            }
        }
    }
    if (!chartElement) { console.warn('Tenure chart element not found'); return; }

    const ctx = chartElement.getContext('2d');
    if (charts.tenure) { charts.tenure.destroy(); }

    const calloutEl = document.getElementById('tenureCallout');

    if (!dashboardData.tenure_distribution || dashboardData.tenure_distribution.length === 0) {
        ctx.canvas.parentNode.innerHTML = '<div class="alert alert-info">No tenure data available yet. This will populate as surveys are completed.</div>';
        if (calloutEl) calloutEl.style.display = 'none';
        return;
    }

    // Normalize old-format tenure strings to standardized cohort keys
    function normalizeTenureString(s) {
        if (!s) return s;
        const t = s.trim();
        // Old format: "< 1 year" or "<1 year"
        if (/^<\s*1\s*year$/i.test(t)) return 'Less than 6 months';
        // Old format: "N years" (single integer year values)
        const singleYearMatch = t.match(/^(\d+)\s*years?$/i);
        if (singleYearMatch) {
            const n = parseInt(singleYearMatch[1], 10);
            if (n < 1) return 'Less than 6 months';
            if (n === 1) return '1-2 years';
            if (n === 2) return '2-3 years';
            if (n <= 4) return '3-5 years';
            if (n <= 9) return '5-10 years';
            return 'More than 10 years';
        }
        return t;
    }

    // Aggregate raw counts by cohort
    const distMap = {};
    (dashboardData.tenure_distribution || []).forEach(item => {
        const key = normalizeTenureString(item.tenure);
        distMap[key] = (distMap[key] || 0) + item.count;
    });

    // Aggregate NPS per cohort using tenure_nps_data (weighted average)
    const npsWeightedSum = {};
    const npsWeightTotal = {};
    (dashboardData.tenure_nps_data || []).forEach(item => {
        const key = normalizeTenureString(item.tenure_group);
        const n = item.total_responses || 0;
        const nps = item.tenure_nps ?? item.avg_nps ?? null;
        if (nps !== null && n > 0) {
            npsWeightedSum[key] = (npsWeightedSum[key] || 0) + nps * n;
            npsWeightTotal[key] = (npsWeightTotal[key] || 0) + n;
        }
    });

    // Build cohort-level data arrays
    const cohorts = TENURE_COHORTS.map(cohort => {
        let count = 0;
        let npsSum = 0;
        let npsN = 0;
        cohort.keys.forEach(key => {
            count += distMap[key] || 0;
            npsSum += npsWeightedSum[key] || 0;
            npsN += npsWeightTotal[key] || 0;
        });
        return {
            label: cohort.label,
            color: cohort.color,
            count,
            avgNps: npsN > 0 ? Math.round(npsSum / npsN) : null
        };
    }).filter(c => c.count > 0);

    if (cohorts.length === 0) {
        // Fallback: if distMap has entries but none matched standard cohort keys,
        // render a simple chart using the raw tenure strings as labels
        const rawKeys = Object.keys(distMap);
        if (rawKeys.length === 0) {
            ctx.canvas.parentNode.innerHTML = '<div class="alert alert-info">No tenure data available yet.</div>';
            if (calloutEl) calloutEl.style.display = 'none';
            return;
        }
        const rawTotal = rawKeys.reduce((s, k) => s + distMap[k], 0);
        const _fbBp = getBrandPalette();
        const _fbColor = (_fbBp.configured && _fbBp.primary) ? _fbBp.primary : '#E13A44';
        const fallbackConfig = getMobileChartConfig();
        charts.tenure = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: rawKeys,
                datasets: [{
                    label: 'Respondents',
                    data: rawKeys.map(k => distMap[k]),
                    backgroundColor: _fbColor,
                    borderColor: '#ffffff',
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: fallbackConfig.maintainAspectRatio,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: ctx => ` ${ctx.raw} respondents (${Math.round(ctx.raw / rawTotal * 100)}%)`
                        }
                    }
                },
                scales: {
                    x: { beginAtZero: true, ticks: { color: '#000000' }, grid: { color: '#f1f5f9' } },
                    y: { ticks: { color: '#000000' }, grid: { color: '#f1f5f9' } }
                }
            }
        });
        if (calloutEl) calloutEl.style.display = 'none';
        return;
    }

    const total = cohorts.reduce((s, c) => s + c.count, 0);
    const labels     = cohorts.map(c => c.label);
    const pctData    = cohorts.map(c => Math.round((c.count / total) * 100));
    const npsData    = cohorts.map(c => c.avgNps);
    const barColors  = cohorts.map(c => c.color);
    const rawCounts  = cohorts.map(c => c.count);

    const config = getMobileChartConfig();

    // Inline plugin: draw % label at right end of each horizontal bar,
    // and NPS value above each line point
    const pctLabelPlugin = {
        id: 'tenurePctLabels',
        afterDraw(chart) {
            const ctx = chart.ctx;
            // Draw % labels on bars (dataset 0)
            const barMeta = chart.getDatasetMeta(0);
            barMeta.data.forEach((bar, i) => {
                const val = pctData[i];
                if (val > 0) {
                    ctx.save();
                    ctx.fillStyle = '#000000';
                    ctx.font = 'bold 11px Arial, sans-serif';
                    ctx.textAlign = 'left';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(val + '%', bar.x + 4, bar.y);
                    ctx.restore();
                }
            });
            // Draw NPS value labels above each line point (dataset 1)
            const lineMeta = chart.getDatasetMeta(1);
            lineMeta.data.forEach((point, i) => {
                const val = npsData[i];
                if (val !== null && val !== undefined) {
                    const label = (val >= 0 ? '+' : '') + val;
                    ctx.save();
                    ctx.fillStyle = '#1e293b';
                    ctx.font = 'bold 11px Arial, sans-serif';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'bottom';
                    ctx.fillText(label, point.x, point.y - 6);
                    ctx.restore();
                }
            });
        }
    };

    charts.tenure = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    type: 'bar',
                    label: 'Share of Accounts (%)',
                    data: pctData,
                    backgroundColor: barColors,
                    borderColor: barColors,
                    borderWidth: 1,
                    xAxisID: 'xPct',
                    order: 2
                },
                {
                    type: 'line',
                    label: 'NPS Score',
                    data: npsData,
                    borderColor: '#1e293b',
                    backgroundColor: 'rgba(30,41,59,0.15)',
                    pointBackgroundColor: '#1e293b',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    borderWidth: 2,
                    tension: 0.3,
                    spanGaps: true,
                    xAxisID: 'xNps',
                    order: 1
                }
            ]
        },
        plugins: [pctLabelPlugin],
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#000000',
                        padding: config.legendPadding,
                        font: { size: config.legendFontSize },
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            if (context.dataset.label === 'Share of Accounts (%)') {
                                const i = context.dataIndex;
                                return ` ${context.dataset.label}: ${pctData[i]}% (${rawCounts[i]} accounts)`;
                            }
                            const val = context.parsed.x;
                            return val !== null ? ` NPS Score: ${val}` : ' NPS Score: n/a';
                        }
                    }
                }
            },
            scales: {
                y: {
                    ticks: { color: '#000000', font: { size: config.fontSize } },
                    grid: { color: '#f1f5f9' }
                },
                xPct: {
                    type: 'linear',
                    position: 'bottom',
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        color: '#6b7280',
                        font: { size: config.fontSize },
                        callback: v => v + '%'
                    },
                    grid: { color: '#f1f5f9' },
                    title: { display: true, text: '% of Accounts', color: '#6b7280', font: { size: 11 } }
                },
                xNps: {
                    type: 'linear',
                    position: 'top',
                    min: -100,
                    max: 100,
                    ticks: {
                        color: '#1e293b',
                        font: { size: config.fontSize }
                    },
                    grid: { drawOnChartArea: false },
                    title: { display: true, text: 'NPS Score', color: '#1e293b', font: { size: 11 } }
                }
            }
        }
    });

    // Interpretive callout
    if (calloutEl) {
        const campaignNps = dashboardData.nps_score ?? null;
        const withNps = cohorts.filter(c => c.avgNps !== null);
        const largest = cohorts.reduce((a, b) => b.count > a.count ? b : a, cohorts[0]);
        const strategic = cohorts.find(c => c.label.startsWith('Strategic'));
        let insight = '';
        if (strategic && strategic.avgNps !== null && campaignNps !== null) {
            const diff = strategic.avgNps - campaignNps;
            const dir = diff >= 0 ? 'above' : 'below';
            const absDiff = Math.abs(diff);
            insight = `Your longest-tenured accounts (Strategic cohort) score <strong>NPS ${strategic.avgNps}</strong>, ` +
                      `<strong>${absDiff} point${absDiff !== 1 ? 's' : ''} ${dir}</strong> your campaign average of ${campaignNps}. `;
            insight += diff >= 5
                ? 'Long-term relationships are driving loyalty — prioritise retention programmes to protect this group.'
                : diff <= -5
                ? 'Long-term accounts show lower satisfaction — consider proactive executive outreach to address unmet expectations.'
                : 'Long-term accounts align closely with your overall NPS, suggesting consistent experience across the lifecycle.';
        } else if (largest) {
            insight = `Your largest cohort is <strong>${largest.label}</strong> (${Math.round((largest.count / total) * 100)}% of accounts). ` +
                      'Add tenure data to participants to see the NPS overlay and identify loyalty trends by relationship age.';
        }
        if (insight) {
            calloutEl.innerHTML = `<div class="alert alert-light border-start border-3 py-2 px-3" style="border-color:#E13A44!important;font-size:0.85rem;">
                <i class="fas fa-lightbulb me-2" style="color:#E13A44;"></i>${insight}</div>`;
            calloutEl.style.display = 'block';
        }
    }
}

function createGrowthFactorChart() {
    // NPS range → semantic classification (from calculate_growth_factor in ai_analysis.py)
    // Semantic red/yellow tones (danger/risk/passive) are always preserved.
    // Growth/champion segments use brand accent when configured; otherwise fall
    // back to semantic green defaults (#22C55E and #15803d).
    const _growthBp = getBrandPalette();
    const _growthColor  = (_growthBp.configured && _growthBp.accent)
        ? _growthBp.tintSequence(_growthBp.accent, 2)[0]
        : '#22C55E';
    const _championColor = (_growthBp.configured && _growthBp.accent)
        ? _growthBp.tintSequence(_growthBp.accent, 2)[1]
        : '#15803d';
    const NPS_RANGE_META = {
        '<0':     { label: 'Negative NPS',      color: '#991b1b',      bainGrowth: '~0%',   type: 'danger'   },
        '0-29':   { label: 'Low NPS (0–29)',     color: '#E13A44',      bainGrowth: '~5%',   type: 'risk'     },
        '30-49':  { label: 'Moderate (30–49)',   color: '#f59e0b',      bainGrowth: '~15%',  type: 'passive'  },
        '50-69':  { label: 'Good (50–69)',        color: _growthColor,  bainGrowth: '~25%',  type: 'growth'   },
        '70-100': { label: 'Excellent (70–100)', color: _championColor, bainGrowth: '~40%',  type: 'champion' }
    };

    let chartElement = document.getElementById('growthFactorChart');
    if (!chartElement) {
        const containers = document.querySelectorAll('.chart-container');
        for (const c of containers) {
            if (c.querySelector('.alert-info') && c.textContent.includes('growth factor data')) {
                c.innerHTML = '<canvas id="growthFactorChart"></canvas>';
                chartElement = document.getElementById('growthFactorChart');
                break;
            }
        }
    }
    if (!chartElement) { console.warn('Growth factor chart element not found'); return; }

    const ctx = chartElement.getContext('2d');
    if (charts.growthFactor) { charts.growthFactor.destroy(); }

    const confEl    = document.getElementById('growthConfidenceBar');
    const focusEl   = document.getElementById('growthPriorityFocus');

    if (!dashboardData.growth_factor_analysis ||
        !dashboardData.growth_factor_analysis.distribution ||
        dashboardData.growth_factor_analysis.distribution.length === 0) {
        ctx.canvas.parentNode.innerHTML = '<div class="alert alert-info">No growth factor data available yet. This will populate as surveys are completed.</div>';
        if (confEl)  confEl.style.display  = 'none';
        if (focusEl) focusEl.style.display = 'none';
        return;
    }

    const distribution = dashboardData.growth_factor_analysis.distribution;
    const total = distribution.reduce((s, d) => s + (d.count || 0), 0);

    // --- Confidence indicator ---
    if (confEl && total > 0) {
        const confLevel = total >= 30 ? 'High' : total >= 10 ? 'Medium' : 'Low';
        const confBadge = confLevel === 'High' ? 'success' : confLevel === 'Medium' ? 'warning' : 'danger';
        confEl.innerHTML = `<div class="d-flex align-items-center gap-2 flex-wrap" style="font-size:0.82rem;">
            <span class="text-muted">Confidence:</span>
            <span class="badge bg-${confBadge} text-${confLevel === 'Medium' ? 'dark' : 'white'}">${confLevel}</span>
            <span class="text-muted">Based on ${total} response${total !== 1 ? 's' : ''} &mdash; ` +
            (confLevel === 'High' ? 'statistically robust signals.' :
             confLevel === 'Medium' ? 'directionally reliable; grow sample for precision.' :
             'preliminary signal only; interpret with caution.') +
            `</span></div>`;
        confEl.style.display = 'block';
    }

    // Normalize nps_range field — very old snapshots used 'range' instead of 'nps_range'
    distribution.forEach(d => { if (!d.nps_range && d.range) d.nps_range = d.range; });

    // Compute per-bar data
    const pctData    = distribution.map(d => total > 0 ? Math.round((d.count / total) * 100) : 0);
    const maxPct = Math.max(...pctData, 1);
    const yAxisMax = Math.ceil((maxPct * 1.3) / 5) * 5;
    const barColors  = distribution.map(d => (NPS_RANGE_META[d.nps_range] || {}).color || '#BDBDBD');
    const barLabels  = distribution.map(d => {
        const meta = NPS_RANGE_META[d.nps_range];
        const gr   = d.growth_rate || null;
        return gr ? `${d.nps_range}\n(${gr} growth)` : (d.nps_range || '?');
    });

    const config = getMobileChartConfig();

    // Inline plugin: draw % above each bar
    const pctLabelPlugin = {
        id: 'growthPctLabels',
        afterDraw(chart) {
            const ctx = chart.ctx;
            const meta = chart.getDatasetMeta(0);
            meta.data.forEach((bar, i) => {
                const val = pctData[i];
                if (val > 0) {
                    ctx.save();
                    ctx.fillStyle = '#000000';
                    ctx.font = 'bold 11px Arial, sans-serif';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'bottom';
                    ctx.fillText(val + '%', bar.x, bar.y - 3);
                    ctx.restore();
                }
            });
        }
    };

    charts.growthFactor = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: barLabels,
            datasets: [{
                label: 'Accounts (%)',
                data: pctData,
                backgroundColor: barColors,
                borderColor: '#ffffff',
                borderWidth: 1
            }]
        },
        plugins: [pctLabelPlugin],
        options: {
            responsive: true,
            maintainAspectRatio: config.maintainAspectRatio,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: function(items) {
                            const d = distribution[items[0].dataIndex];
                            const meta = NPS_RANGE_META[d.nps_range];
                            return meta ? meta.label : d.nps_range;
                        },
                        label: function(context) {
                            const d = distribution[context.dataIndex];
                            const lines = [`  ${d.count} account${d.count !== 1 ? 's' : ''} (${pctData[context.dataIndex]}% of total)`];
                            if (d.growth_rate) lines.push(`  Bain expected growth: ${d.growth_rate}`);
                            if (d.avg_factor != null) lines.push(`  Avg growth factor score: ${d.avg_factor}`);
                            return lines;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    suggestedMax: yAxisMax,
                    ticks: {
                        color: '#000000',
                        font: { size: config.fontSize },
                        callback: v => v + '%'
                    },
                    grid: { color: '#f1f5f9' },
                    title: { display: true, text: '% of Accounts', color: '#6b7280', font: { size: 11 } }
                },
                x: {
                    ticks: {
                        color: '#000000',
                        font: { size: config.fontSize },
                        maxRotation: 0
                    },
                    grid: { color: '#f1f5f9' }
                }
            }
        }
    });

    // --- Priority Focus panel ---
    if (focusEl && total > 0) {
        // Classify each distribution item
        const risks     = distribution.filter(d => ['<0', '0-29'].includes(d.nps_range));
        const passives  = distribution.filter(d => ['30-49'].includes(d.nps_range));
        const biggest = arr => arr.reduce((a, b) => (b.count > a.count ? b : a), arr[0] || null);
        const riskTop    = biggest(risks);
        const passiveTop = biggest(passives);

        // Prefer the highest NPS band (70-100 > 50-69) for referral potential
        const topBand = distribution.find(d => d.nps_range === '70-100' && d.count > 0)
                     || distribution.find(d => d.nps_range === '50-69'  && d.count > 0)
                     || null;
        const championTop = topBand;

        const rows = [];

        if (riskTop && riskTop.count > 0) {
            const pct = Math.round((riskTop.count / total) * 100);
            rows.push({
                icon: 'fas fa-exclamation-triangle',
                iconColor: '#E13A44',
                priority: '1',
                title: 'Address Churn Risk',
                body: `<strong>${riskTop.count} account${riskTop.count !== 1 ? 's' : ''} (${pct}%)</strong> in the ${riskTop.nps_range} NPS band. ` +
                      `Bain research links this zone to ` + (riskTop.growth_rate ? `${riskTop.growth_rate} organic growth` : 'minimal organic growth') + `. ` +
                      `Run targeted executive outreach and resolve top pain points to prevent churn.`
            });
        }

        if (passiveTop && passiveTop.count > 0) {
            const pct = Math.round((passiveTop.count / total) * 100);
            rows.push({
                icon: 'fas fa-exchange-alt',
                iconColor: '#f59e0b',
                priority: riskTop && riskTop.count > 0 ? '2' : '1',
                title: 'Convert Passive Accounts',
                body: `<strong>${passiveTop.count} account${passiveTop.count !== 1 ? 's' : ''} (${pct}%)</strong> in the 30–49 NPS band — your conversion opportunity. ` +
                      `A shift to the 50–69 band would lift expected growth from ~15% to ~25%. ` +
                      `Focus on closing known service gaps and demonstrating new value.`
            });
        }

        if (championTop && championTop.count > 0) {
            const pct = Math.round((championTop.count / total) * 100);
            const topRange = championTop.nps_range === '70-100' ? '70–100' : '50–69';
            rows.push({
                icon: 'fas fa-star',
                iconColor: '#E13A44',
                priority: rows.length + 1,
                title: 'Activate Promoter Growth',
                body: `<strong>${championTop.count} account${championTop.count !== 1 ? 's' : ''} (${pct}%)</strong> in the ${topRange} NPS band. ` +
                      `These are your growth engine — expected organic growth of ` +
                      (championTop.growth_rate ? `${championTop.growth_rate}` : 'up to 40%') + `. ` +
                      `Engage them for referrals, case studies, and co-marketing to compound growth.`
            });
        }

        if (rows.length > 0) {
            const rowsHtml = rows.map(r => `
                <div class="d-flex gap-2 mb-2 pb-2 ${rows.indexOf(r) < rows.length - 1 ? 'border-bottom' : ''}">
                    <div class="flex-shrink-0 mt-1">
                        <i class="${r.icon}" style="color:${r.iconColor};font-size:1rem;"></i>
                    </div>
                    <div>
                        <div class="fw-semibold" style="font-size:0.82rem;color:#1e293b;">
                            <span class="badge me-1" style="background:${r.iconColor};font-size:0.7rem;">P${r.priority}</span>
                            ${r.title}
                        </div>
                        <div class="text-muted" style="font-size:0.78rem;line-height:1.45;">${r.body}</div>
                    </div>
                </div>`).join('');

            focusEl.innerHTML = `<div class="border rounded p-3" style="background:#E9E8E4;">
                <div class="fw-semibold mb-2" style="font-size:0.82rem;color:#000000;letter-spacing:0.03em;">
                    <i class="fas fa-crosshairs me-1" style="color:#E13A44;"></i>PRIORITY FOCUS
                </div>
                ${rowsHtml}
            </div>`;
            focusEl.style.display = 'block';
        }
    }
}

function populateHighRiskAccounts() {
    const container = document.getElementById('highRiskAccounts');
    const viewAllContainer = document.getElementById('highRiskViewAll');
    const viewAllLink = document.getElementById('highRiskViewAllLink');
    const noteContainer = document.getElementById('highRiskNote');
    const allAccounts = dashboardData.high_risk_accounts || [];

    if (allAccounts.length === 0) {
        container.innerHTML = '<p class="text-muted">No high-risk accounts identified.</p>';
        if (viewAllContainer) viewAllContainer.style.display = 'none';
        if (noteContainer) noteContainer.style.display = 'none';
        return;
    }

    // Sort: Critical first, then by lowest NPS score
    const RISK_PRIORITY = { 'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3 };
    const sorted = [...allAccounts].sort((a, b) => {
        const pa = RISK_PRIORITY[a.risk_level] !== undefined ? RISK_PRIORITY[a.risk_level] : 4;
        const pb = RISK_PRIORITY[b.risk_level] !== undefined ? RISK_PRIORITY[b.risk_level] : 4;
        if (pa !== pb) return pa - pb;
        const na = a.nps_score != null ? Number(a.nps_score) : Infinity;
        const nb = b.nps_score != null ? Number(b.nps_score) : Infinity;
        return na - nb;
    });

    const top3 = sorted.slice(0, 3);

    function getNpsBadge(score) {
        const n = Number(score);
        if (score == null || isNaN(n)) return `<span class="badge" style="background:#e9e8e4;color:#6c757d;border:1px solid #ccc;font-size:0.72em;">N/A</span>`;
        if (n >= 30) return `<span class="badge" style="background:#19875420;color:#198754;border:1px solid #198754;font-size:0.72em;">NPS ${n}</span>`;
        if (n >= 0)  return `<span class="badge" style="background:#fd7e1420;color:#fd7e14;border:1px solid #fd7e14;font-size:0.72em;">NPS ${n}</span>`;
        return `<span class="badge" style="background:#dc354520;color:#dc3545;border:1px solid #dc3545;font-size:0.72em;">NPS ${n}</span>`;
    }

    function getRiskBadge(level) {
        const l = level || 'High';
        const isCritical = l === 'Critical';
        const color = isCritical ? '#dc3545' : '#fd7e14';
        const bg = isCritical ? '#dc354520' : '#fd7e1420';
        return `<span class="badge" style="background:${bg};color:${color};border:1px solid ${color};font-size:0.72em;">${escapeHtml(l)}</span>`;
    }

    const html = top3.map(account => `
        <div class="d-flex justify-content-between align-items-center py-2" style="border-bottom:1px solid #eee;">
            <span class="fw-medium text-truncate me-2" style="max-width:50%;font-size:0.9rem;" title="${escapeHtml(account.company_name)}">${escapeHtml(account.company_name)}</span>
            <span class="d-flex gap-1 align-items-center flex-shrink-0">
                ${getNpsBadge(account.nps_score)}
                ${getRiskBadge(account.risk_level)}
            </span>
        </div>
    `).join('');

    container.innerHTML = html;

    // Show the explanatory note whenever there are accounts
    if (noteContainer) noteContainer.style.display = 'block';

    // Show/hide "View all" link — only when total exceeds 3
    if (viewAllContainer && viewAllLink) {
        if (allAccounts.length > 3) {
            viewAllLink.textContent = `View all ${allAccounts.length} accounts in Survey Insights \u2192`;
            viewAllLink.onclick = function(e) {
                e.preventDefault();
                const tabEl = document.getElementById('survey-insights-tab');
                if (tabEl) {
                    bootstrap.Tab.getOrCreateInstance(tabEl).show();
                }
            };
            viewAllContainer.style.display = 'block';
        } else {
            viewAllContainer.style.display = 'none';
        }
    }
}

function populateGrowthOpportunities() {
    const container = document.getElementById('growthOpportunities');
    const companiesWithOpportunities = dashboardData.growth_opportunities || [];
    
    if (companiesWithOpportunities.length === 0) {
        container.innerHTML = '<p class="text-muted">No growth opportunities identified.</p>';
        return;
    }
    
    const html = companiesWithOpportunities.map(company => {
        // Ensure company has a name and opportunities array
        const companyName = company.company_name || 'Unknown Company';
        const opportunities = company.opportunities || [];
        
        if (opportunities.length === 0) {
            return ''; // Skip companies with no opportunities
        }
        
        return `
            <div class="company-opportunities-card p-3 mb-4 rounded" style="border: 1px solid #BDBDBD;">
                <h6 class="mb-3" style="color: #E13A44; font-weight: bold;">${escapeHtml(companyName)}</h6>
                ${opportunities.map(opp => `
                    <div class="opportunity-card p-2 mb-2 rounded" style="background-color: #E9E8E4; border-left: 3px solid #E13A44;">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <p class="mb-1" style="color: #000000;">${escapeHtml(opp.description || 'No description available')}</p>
                                <small class="text-muted">${escapeHtml(opp.action || 'No action specified')}</small>
                            </div>
                            <span class="badge bg-primary">${escapeHtml(opp.type || 'unknown')}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }).filter(html => html !== '').join(''); // Remove empty entries
    
    if (html === '') {
        container.innerHTML = '<p class="text-muted">No growth opportunities identified.</p>';
        return;
    }
    
    container.innerHTML = html;
}

// Visual mapping for risk factors and opportunities using established color palette
function getVisualIndicator(type, category) {
    const riskIcons = {
        'pricing_concerns': { icon: '💰', color: '#E13A44', label: 'Pricing' },
        'product_problems': { icon: '🔧', color: '#E13A44', label: 'Product' },
        'service_issues': { icon: '📞', color: '#E13A44', label: 'Service' },
        'churn_risk': { icon: '⚠️', color: '#E13A44', label: 'Churn Risk' },
        'low_satisfaction': { icon: '📉', color: '#E13A44', label: 'Low NPS' },
        'poor_ratings': { icon: '⭐', color: '#E13A44', label: 'Poor Ratings' },
        'contract_issues': { icon: '📋', color: '#E13A44', label: 'Contract' },
        'relationship_threat': { icon: '🔗', color: '#E13A44', label: 'Relationship' },
        'critical_satisfaction': { icon: '🚨', color: '#E13A44', label: 'Critical' }
    };
    
    const opportunityIcons = {
        'upsell': { icon: '📈', color: '#8A8A8A', label: 'Upsell' },
        'cross_sell': { icon: '🎯', color: '#BDBDBD', label: 'Cross-sell' },
        'referral': { icon: '👥', color: '#8A8A8A', label: 'Referral' },
        'advocacy': { icon: '📢', color: '#BDBDBD', label: 'Advocacy' },
        'expansion': { icon: '🚀', color: '#8A8A8A', label: 'Expansion' },
        'high_satisfaction': { icon: '⭐', color: '#E9E8E4', label: 'High NPS' },
        'engagement': { icon: '🤝', color: '#BDBDBD', label: 'Engagement' }
    };
    
    if (category === 'risk') {
        return riskIcons[type] || { icon: '⚠️', color: '#E13A44', label: type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) };
    } else {
        return opportunityIcons[type] || { icon: '📈', color: '#8A8A8A', label: type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) };
    }
}



function normalizeTypeForVisual(originalType) {
    const typeMap = {
        // Risk mappings
        'pricing concerns': 'pricing_concerns',
        'pricing concern': 'pricing_concerns',
        'product problem': 'product_problems',
        'product problems': 'product_problems',
        'product issue': 'product_problems',
        'product issues': 'product_problems',
        'service issue': 'service_issues',
        'service issues': 'service_issues',
        'service problem': 'service_issues',
        'service problems': 'service_issues',
        'churn risk': 'churn_risk',
        'low satisfaction': 'low_satisfaction',
        'poor ratings': 'poor_ratings',
        'contract risk': 'contract_issues',
        'contract issue': 'contract_issues',
        'contract issues': 'contract_issues',
        'critical satisfaction': 'critical_satisfaction',
        'relationship threat': 'relationship_threat',
        
        // Opportunity mappings - including variations that come from backend
        'upsell potential': 'upsell',
        'upsell opportunity': 'upsell',
        'upsell': 'upsell',
        'cross-sell potential': 'cross_sell',
        'cross-sell opportunity': 'cross_sell',
        'cross-sell': 'cross_sell',
        'cross sell': 'cross_sell',
        'referral potential': 'referral',
        'referral opportunity': 'referral',
        'referral': 'referral',
        'advocacy potential': 'advocacy',
        'advocacy opportunity': 'advocacy',
        'advocacy': 'advocacy',
        'expansion potential': 'expansion',
        'expansion opportunity': 'expansion',
        'expansion ready': 'expansion',
        'expansion': 'expansion',
        'high satisfaction': 'high_satisfaction',
        'high nps': 'high_satisfaction',
        'engagement opportunity': 'engagement',
        'engagement potential': 'engagement',
        'engagement': 'engagement'
    };
    
    const normalized = typeMap[originalType.toLowerCase()];
    if (normalized) {
        return normalized;
    }
    
    // If no exact match, try to categorize based on keywords
    const lower = originalType.toLowerCase();
    if (lower.includes('upsell')) return 'upsell';
    if (lower.includes('cross') && lower.includes('sell')) return 'cross_sell';
    if (lower.includes('referral')) return 'referral';
    if (lower.includes('advocacy')) return 'advocacy';
    if (lower.includes('expansion')) return 'expansion';
    if (lower.includes('satisfaction') && lower.includes('high')) return 'high_satisfaction';
    if (lower.includes('engagement')) return 'engagement';
    if (lower.includes('pricing')) return 'pricing_concerns';
    if (lower.includes('product')) return 'product_problems';
    if (lower.includes('service')) return 'service_issues';
    if (lower.includes('churn')) return 'churn_risk';
    
    // Last resort: convert to snake_case
    return originalType.toLowerCase().replace(/\s+/g, '_');
}

function populateAccountIntelligence() {
    const container = document.getElementById('accountIntelligence');
    let accountData = dashboardData.account_intelligence || [];
    
    if (accountData.length === 0) {
        container.innerHTML = '<p class="text-muted">No account intelligence data available.</p>';
        return;
    }
    
    // Enrich account data with NPS from company_nps_data (for old snapshots that don't have it)
    const companyNpsData = dashboardData.company_nps_data || [];
    console.log('📊 Company NPS Data available:', companyNpsData.length, 'companies');
    console.log('📊 Account Intelligence Data:', accountData.length, 'accounts');
    
    const npsLookup = {};
    companyNpsData.forEach(company => {
        npsLookup[company.company_name.toUpperCase()] = company.company_nps;
    });
    
    // Add NPS to each account if missing
    accountData = accountData.map(account => {
        if (account.company_nps === undefined || account.company_nps === null) {
            const nps = npsLookup[account.company_name.toUpperCase()];
            console.log(`  Enriching ${account.company_name}: NPS=${nps}`);
            return { ...account, company_nps: nps !== undefined ? nps : null };
        }
        console.log(`  ${account.company_name}: NPS already set to ${account.company_nps}`);
        return account;
    });
    
    console.log('✅ Enriched account data:', accountData.slice(0, 2));
    
    // Create legend
    const legendHtml = `
        <div class="account-health-legend mb-4 p-3 rounded" style="background-color: #E9E8E4; border: 1px solid #BDBDBD;">
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-success mb-2">Growth Opportunities</h6>
                    <div class="d-flex flex-wrap gap-2">
                        <span class="badge bg-light text-dark">Upsell</span>
                        <span class="badge bg-light text-dark">Cross-sell</span>
                        <span class="badge bg-light text-dark">Referral</span>
                        <span class="badge bg-light text-dark">Advocacy</span>
                        <span class="badge bg-light text-dark">High NPS</span>
                    </div>
                </div>
                <div class="col-md-6">
                    <h6 class="text-danger mb-2">Risk Factors</h6>
                    <div class="d-flex flex-wrap gap-2">
                        <span class="badge bg-light text-dark">Pricing</span>
                        <span class="badge bg-light text-dark">Product</span>
                        <span class="badge bg-light text-dark">Service</span>
                        <span class="badge bg-light text-dark">Low NPS</span>
                        <span class="badge bg-light text-dark">Critical</span>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    const accountsHtml = accountData.map(account => {
        const balanceClass = account.balance === 'risk_heavy' ? 'border-danger' : 
                           account.balance === 'opportunity_heavy' ? 'border-secondary' : 'border-secondary';
        
        const balanceIcon = account.balance === 'risk_heavy' ? '●' : 
                          account.balance === 'opportunity_heavy' ? '●' : '●';
        
        const balanceIconColor = account.balance === 'risk_heavy' ? '#E13A44' : 
                               account.balance === 'opportunity_heavy' ? '#8A8A8A' : '#BDBDBD';
        
        const balanceLabel = account.balance === 'risk_heavy' ? 'Risk-Heavy' : 
                           account.balance === 'opportunity_heavy' ? 'High Potential' : 'Balanced';
        
        // Consolidate opportunities by type to avoid duplicates
        const opportunityMap = new Map();
        account.opportunities.forEach(opp => {
            const normalizedType = normalizeTypeForVisual(opp.type);
            
            if (opportunityMap.has(normalizedType)) {
                opportunityMap.get(normalizedType).count += (opp.count || 1);
            } else {
                opportunityMap.set(normalizedType, {
                    type: opp.type,
                    normalizedType: normalizedType,
                    count: opp.count || 1
                });
            }
        });
        
        // Create visual indicators for consolidated opportunities
        const opportunityIndicators = Array.from(opportunityMap.values()).map(opp => {
            const visual = getVisualIndicator(opp.normalizedType, 'opportunity');
            return `
                <span class="visual-indicator opportunity-indicator" 
                      style="background-color: ${visual.color}20; border: 2px solid ${visual.color}; padding: 4px 8px; margin: 2px; border-radius: 12px; display: inline-block;"
                      title="${escapeHtml(opp.type)}${opp.count > 1 ? ` (${opp.count} opportunities)` : ''}">
                    ${escapeHtml(visual.label)}${opp.count > 1 ? ` (${opp.count})` : ''}
                </span>
            `;
        }).join('');
        
        // Consolidate risks by type to avoid duplicates
        const riskMap = new Map();
        account.risk_factors.forEach(risk => {
            const normalizedType = normalizeTypeForVisual(risk.type);
            if (riskMap.has(normalizedType)) {
                riskMap.get(normalizedType).count += (risk.count || 1);
                // Keep the highest severity level
                const severityPriority = { 'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1 };
                if (severityPriority[risk.severity] > severityPriority[riskMap.get(normalizedType).severity]) {
                    riskMap.get(normalizedType).severity = risk.severity;
                }
            } else {
                riskMap.set(normalizedType, {
                    type: risk.type,
                    normalizedType: normalizedType,
                    severity: risk.severity,
                    count: risk.count || 1
                });
            }
        });
        
        // Create visual indicators for consolidated risks  
        const riskIndicators = Array.from(riskMap.values()).map(risk => {
            const visual = getVisualIndicator(risk.normalizedType, 'risk');
            const intensityMap = { 'Critical': '●●●', 'High': '●●', 'Medium': '●', 'Low': '○' };
            const intensity = intensityMap[risk.severity] || '●';
            
            return `
                <span class="visual-indicator risk-indicator" 
                      style="background-color: ${visual.color}20; border: 2px solid ${visual.color}; padding: 4px 8px; margin: 2px; border-radius: 12px; display: inline-block;"
                      title="${escapeHtml(risk.type)} - ${escapeHtml(risk.severity)}${risk.count > 1 ? ` (${risk.count} instances)` : ''}">
                    ${escapeHtml(visual.label)} ${intensity}${risk.count > 1 ? ` (${risk.count})` : ''}
                </span>
            `;
        }).join('');
        
        // Get campaign info for drill-down
        const campaignSelect = document.getElementById('campaignFilter');
        const campaignId = campaignSelect ? campaignSelect.value : null;
        const campaignName = campaignSelect && campaignId ? campaignSelect.options[campaignSelect.selectedIndex].text : 'Current Campaign';
        
        return `
            <div class="account-visual-card card mb-3 ${balanceClass}" style="border-width: 2px;">
                <div class="card-body p-3">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5 class="mb-0">
                            <a href="#" onclick="openCompanyResponsesModal('${escapeHtml(account.company_name).replace(/'/g, "\\'")}', ${campaignId}, '${escapeHtml(campaignName).replace(/'/g, "\\'")}'); return false;" 
                               style="color: #2E5090; text-decoration: none; cursor: pointer;"
                               onmouseover="this.style.textDecoration='underline';"
                               onmouseout="this.style.textDecoration='none';"
                               title="Click to view all responses from ${escapeHtml(account.company_name)}">
                                ${escapeHtml(account.company_name)}
                                <i class="fas fa-external-link-alt ms-2" style="font-size: 0.7em; color: #8A8A8A;"></i>
                            </a>
                        </h5>
                        <div class="d-flex align-items-center">
                            <span style="font-size: 1.2em; margin-right: 5px; color: ${balanceIconColor};">${balanceIcon}</span>
                            <span class="badge" style="background-color: ${balanceIconColor}20; color: ${balanceIconColor}; border: 1px solid ${balanceIconColor};">${balanceLabel}</span>
                        </div>
                    </div>
                    
                    <!-- Account Details -->
                    <div class="account-details mb-3 p-2 rounded" style="background-color: #E9E8E4; border: 1px solid #BDBDBD;">
                        <div class="row">
                            <div class="col-4">
                                <small class="text-muted">NPS:</small>
                                <div class="fw-bold" style="color: #8A8A8A;">
                                    ${account.company_nps !== undefined && account.company_nps !== null ? account.company_nps : 'N/A'}
                                </div>
                            </div>
                            <div class="col-4">
                                <small class="text-muted">Max Tenure:</small>
                                <div class="fw-bold" style="color: #8A8A8A;">
                                    ${account.max_tenure ? account.max_tenure + ' years' : 'N/A'}
                                </div>
                            </div>
                            <div class="col-4">
                                <small class="text-muted">Commercial Value:</small>
                                <div class="fw-bold" style="color: #8A8A8A;">
                                    ${account.commercial_value ? '$' + account.commercial_value.toLocaleString() : 'N/A $'}
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="account-indicators">
                        ${opportunityIndicators ? `
                            <div class="mb-2">
                                <div class="fw-bold text-success mb-1" style="font-size: 0.9em;">Growth Opportunities</div>
                                <div>${opportunityIndicators}</div>
                            </div>
                        ` : ''}
                        
                        ${riskIndicators ? `
                            <div class="mb-2">
                                <div class="fw-bold text-danger mb-1" style="font-size: 0.9em;">Risk Factors</div>
                                <div>${riskIndicators}</div>
                            </div>
                        ` : ''}
                        
                        ${!opportunityIndicators && !riskIndicators ? 
                            '<div class="text-muted text-center py-2" style="font-size: 0.9em;">No specific indicators identified</div>' : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = legendHtml + accountsHtml;
    
    // Apply color overrides using shared utility
    if (typeof applyColorOverrides === 'function') {
        applyColorOverrides(container, 100);
    }
}

// Account Intelligence API-based pagination, search, and filtering
let accountIntelCurrentPage = 1;
let accountIntelSearchTimeout = null;

function loadAccountIntelligence(page = 1) {
    const search = document.getElementById('accountIntelSearch')?.value || '';
    const balance = document.getElementById('accountBalanceFilter')?.value || '';
    const riskLevel = document.getElementById('accountRiskFilter')?.value || '';
    const hasOpp = document.getElementById('accountOppFilter')?.value || '';
    const hasRisks = document.getElementById('accountRisksFilter')?.value || '';
    
    // Build query params
    const params = new URLSearchParams({
        page: page,
        per_page: 10
    });
    
    if (search) params.append('search', search);
    if (balance) params.append('balance', balance);
    if (riskLevel) params.append('risk_level', riskLevel);
    if (hasOpp) params.append('has_opportunities', hasOpp);
    if (hasRisks) params.append('has_risks', hasRisks);
    
    // Get current campaign if set
    const campaignSelect = document.getElementById('campaignFilter');
    if (campaignSelect && campaignSelect.value) {
        params.append('campaign', campaignSelect.value);
    }
    
    // Show loading
    const container = document.getElementById('accountIntelligence');
    container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    
    fetch(`/api/account_intelligence?${params}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                accountIntelCurrentPage = page;
                renderAccountIntelligence(data.data, data.pagination);
                updateAccountIntelFiltersUI(data.pagination.total, data.filters_applied);
            } else {
                container.innerHTML = `<div class="alert alert-danger">${translations.errorLoadingAccountIntelligence}</div>`;
            }
        })
        .catch(error => {
            console.error('Error loading account intelligence:', error);
            container.innerHTML = '<div class="alert alert-danger">Error: ' + error.message + '</div>';
        });
}

function renderAccountIntelligence(accountData, pagination) {
    const container = document.getElementById('accountIntelligence');
    
    if (accountData.length === 0) {
        container.innerHTML = '<p class="text-muted">No accounts match the selected filters.</p>';
        document.getElementById('accountIntelPaginationContainer').style.display = 'none';
        return;
    }
    
    // Create legend (same as before)
    const legendHtml = `
        <div class="account-health-legend mb-4 p-3 rounded" style="background-color: #E9E8E4; border: 1px solid #BDBDBD;">
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-success mb-2">Growth Opportunities</h6>
                    <div class="d-flex flex-wrap gap-2">
                        <span class="badge bg-light text-dark">Upsell</span>
                        <span class="badge bg-light text-dark">Cross-sell</span>
                        <span class="badge bg-light text-dark">Referral</span>
                        <span class="badge bg-light text-dark">Advocacy</span>
                        <span class="badge bg-light text-dark">High NPS</span>
                    </div>
                </div>
                <div class="col-md-6">
                    <h6 class="text-danger mb-2">Risk Factors</h6>
                    <div class="d-flex flex-wrap gap-2">
                        <span class="badge bg-light text-dark">Pricing</span>
                        <span class="badge bg-light text-dark">Product</span>
                        <span class="badge bg-light text-dark">Service</span>
                        <span class="badge bg-light text-dark">Low NPS</span>
                        <span class="badge bg-light text-dark">Critical</span>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Render accounts (reuse existing rendering logic)
    const accountsHtml = accountData.map(account => {
        const balanceClass = account.balance === 'risk_heavy' ? 'border-danger' : 
                           account.balance === 'opportunity_heavy' ? 'border-secondary' : 'border-secondary';
        
        const balanceIcon = '●';
        const balanceIconColor = account.balance === 'risk_heavy' ? '#E13A44' : 
                               account.balance === 'opportunity_heavy' ? '#8A8A8A' : '#BDBDBD';
        
        const balanceLabel = account.balance === 'risk_heavy' ? 'Risk-Heavy' : 
                           account.balance === 'opportunity_heavy' ? 'High Potential' : 'Balanced';
        
        // Consolidate opportunities
        const opportunityMap = new Map();
        account.opportunities.forEach(opp => {
            const normalizedType = normalizeTypeForVisual(opp.type);
            if (opportunityMap.has(normalizedType)) {
                opportunityMap.get(normalizedType).count += (opp.count || 1);
            } else {
                opportunityMap.set(normalizedType, {
                    type: opp.type,
                    normalizedType: normalizedType,
                    count: opp.count || 1
                });
            }
        });
        
        const opportunityIndicators = Array.from(opportunityMap.values()).map(opp => {
            const visual = getVisualIndicator(opp.normalizedType, 'opportunity');
            return `
                <span class="visual-indicator opportunity-indicator" 
                      style="background-color: ${visual.color}20; border: 2px solid ${visual.color}; padding: 4px 8px; margin: 2px; border-radius: 12px; display: inline-block;"
                      title="${escapeHtml(opp.type)}${opp.count > 1 ? ` (${opp.count} opportunities)` : ''}">
                    ${escapeHtml(visual.label)}${opp.count > 1 ? ` (${opp.count})` : ''}
                </span>
            `;
        }).join('');
        
        // Consolidate risks
        const riskMap = new Map();
        account.risk_factors.forEach(risk => {
            const normalizedType = normalizeTypeForVisual(risk.type);
            if (riskMap.has(normalizedType)) {
                riskMap.get(normalizedType).count += (risk.count || 1);
                const severityPriority = { 'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1 };
                if (severityPriority[risk.severity] > severityPriority[riskMap.get(normalizedType).severity]) {
                    riskMap.get(normalizedType).severity = risk.severity;
                }
            } else {
                riskMap.set(normalizedType, {
                    type: risk.type,
                    normalizedType: normalizedType,
                    severity: risk.severity,
                    count: risk.count || 1
                });
            }
        });
        
        const riskIndicators = Array.from(riskMap.values()).map(risk => {
            const visual = getVisualIndicator(risk.normalizedType, 'risk');
            const intensityMap = { 'Critical': '●●●', 'High': '●●', 'Medium': '●', 'Low': '○' };
            const intensity = intensityMap[risk.severity] || '●';
            
            return `
                <span class="visual-indicator risk-indicator" 
                      style="background-color: ${visual.color}20; border: 2px solid ${visual.color}; padding: 4px 8px; margin: 2px; border-radius: 12px; display: inline-block;"
                      title="${escapeHtml(risk.type)} - ${escapeHtml(risk.severity)}${risk.count > 1 ? ` (${risk.count} instances)` : ''}">
                    ${escapeHtml(visual.label)} ${intensity}${risk.count > 1 ? ` (${risk.count})` : ''}
                </span>
            `;
        }).join('');
        
        // Get campaign info for drill-down
        const campaignSelect = document.getElementById('campaignFilter');
        const campaignId = campaignSelect ? campaignSelect.value : null;
        const campaignName = campaignSelect && campaignId ? campaignSelect.options[campaignSelect.selectedIndex].text : 'Current Campaign';
        
        return `
            <div class="account-visual-card card mb-3 ${balanceClass}" style="border-width: 2px;">
                <div class="card-body p-3">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5 class="mb-0">
                            <a href="#" onclick="openCompanyResponsesModal('${escapeHtml(account.company_name).replace(/'/g, "\\'")}', ${campaignId}, '${escapeHtml(campaignName).replace(/'/g, "\\'")}'); return false;" 
                               style="color: #2E5090; text-decoration: none; cursor: pointer;"
                               onmouseover="this.style.textDecoration='underline';"
                               onmouseout="this.style.textDecoration='none';"
                               title="Click to view all responses from ${escapeHtml(account.company_name)}">
                                ${escapeHtml(account.company_name)}
                                <i class="fas fa-external-link-alt ms-2" style="font-size: 0.7em; color: #8A8A8A;"></i>
                            </a>
                        </h5>
                        <div class="d-flex align-items-center">
                            <span style="font-size: 1.2em; margin-right: 5px; color: ${balanceIconColor};">${balanceIcon}</span>
                            <span class="badge" style="background-color: ${balanceIconColor}20; color: ${balanceIconColor}; border: 1px solid ${balanceIconColor};">${balanceLabel}</span>
                        </div>
                    </div>
                    
                    <div class="account-details mb-3 p-2 rounded" style="background-color: #E9E8E4; border: 1px solid #BDBDBD;">
                        <div class="row">
                            <div class="col-3">
                                <small class="text-muted">NPS:</small>
                                <div class="fw-bold" style="color: #8A8A8A;">
                                    ${account.company_nps !== undefined && account.company_nps !== null ? account.company_nps : 'N/A'}
                                </div>
                            </div>
                            <div class="col-3">
                                <small class="text-muted">Max Tenure:</small>
                                <div class="fw-bold" style="color: #8A8A8A;">
                                    ${account.max_tenure ? account.max_tenure + ' years' : 'N/A'}
                                </div>
                            </div>
                            <div class="col-3">
                                <small class="text-muted">Commercial Value:</small>
                                <div class="fw-bold" style="color: #8A8A8A;">
                                    ${account.commercial_value ? '$' + account.commercial_value.toLocaleString() : 'N/A $'}
                                </div>
                            </div>
                            <div class="col-3">
                                <small class="text-muted">Response Rate:</small>
                                <div class="d-flex align-items-center">
                                    <span class="fw-bold me-2" style="color: #8A8A8A;">
                                        ${account.response_rate !== null && account.response_rate !== undefined ? account.response_rate + '%' : 'N/A'}
                                    </span>
                                    ${getConfidenceBadge(account.confidence_level)}
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="account-indicators">
                        ${opportunityIndicators ? `
                            <div class="mb-2">
                                <div class="fw-bold text-success mb-1" style="font-size: 0.9em;">Growth Opportunities</div>
                                <div>${opportunityIndicators}</div>
                            </div>
                        ` : ''}
                        
                        ${riskIndicators ? `
                            <div class="mb-2">
                                <div class="fw-bold text-danger mb-1" style="font-size: 0.9em;">Risk Factors</div>
                                <div>${riskIndicators}</div>
                            </div>
                        ` : ''}
                        
                        ${!opportunityIndicators && !riskIndicators ? 
                            '<div class="text-muted text-center py-2" style="font-size: 0.9em;">No specific indicators identified</div>' : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = legendHtml + accountsHtml;
    
    // Render pagination
    if (pagination.pages > 1) {
        renderAccountIntelPagination(pagination);
        document.getElementById('accountIntelPaginationContainer').style.display = 'block';
    } else {
        document.getElementById('accountIntelPaginationContainer').style.display = 'none';
    }
}

function renderAccountIntelPagination(pagination) {
    const paginationContainer = document.getElementById('accountIntelPagination');
    const pages = generatePaginationPages(pagination.page, pagination.pages);
    
    let paginationHtml = '';
    
    // Previous button
    paginationHtml += `
        <li class="page-item ${!pagination.has_prev ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadAccountIntelligence(${pagination.page - 1}); return false;" aria-label="${translations.previous}">
                <span aria-hidden="true">&laquo;</span>
            </a>
        </li>
    `;
    
    // Page numbers
    pages.forEach(pageNum => {
        if (pageNum === '...') {
            paginationHtml += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        } else {
            paginationHtml += `
                <li class="page-item ${pageNum === pagination.page ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="loadAccountIntelligence(${pageNum}); return false;">${pageNum}</a>
                </li>
            `;
        }
    });
    
    // Next button
    paginationHtml += `
        <li class="page-item ${!pagination.has_next ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadAccountIntelligence(${pagination.page + 1}); return false;" aria-label="${translations.next}">
                <span aria-hidden="true">&raquo;</span>
            </a>
        </li>
    `;
    
    paginationContainer.innerHTML = paginationHtml;
}

function searchAccountIntelligence() {
    // Debounce search for better UX
    clearTimeout(accountIntelSearchTimeout);
    accountIntelSearchTimeout = setTimeout(() => {
        loadAccountIntelligence(1); // Reset to page 1 when searching
    }, 300);
}

function updateAccountIntelFiltersUI(total, filtersApplied) {
    // Update count display
    const countElement = document.getElementById('accountIntelCount');
    const start = (accountIntelCurrentPage - 1) * 10 + 1;
    const end = Math.min(accountIntelCurrentPage * 10, total);
    countElement.textContent = `${translations.showing} ${start}-${end} ${translations.of} ${total} ${translations.accounts}`;
    
    // Count active filters
    const activeFilters = Object.values(filtersApplied || {}).filter(v => v).length;
    
    // Show/hide filter badge and clear button
    const filterBadge = document.getElementById('accountIntelFiltersActive');
    const clearButton = document.getElementById('accountIntelClearFilters');
    
    if (activeFilters > 0) {
        filterBadge.textContent = `${activeFilters} filter${activeFilters > 1 ? 's' : ''} active`;
        filterBadge.style.display = 'inline-block';
        clearButton.style.display = 'inline-block';
    } else {
        filterBadge.style.display = 'none';
        clearButton.style.display = 'none';
    }
}

function clearAccountIntelFilters() {
    document.getElementById('accountIntelSearch').value = '';
    document.getElementById('accountBalanceFilter').value = '';
    document.getElementById('accountRiskFilter').value = '';
    document.getElementById('accountOppFilter').value = '';
    document.getElementById('accountRisksFilter').value = '';
    loadAccountIntelligence(1);
}

function populateAccountRiskFactors() {
    const container = document.getElementById('accountRiskFactors');
    const companiesWithRiskFactors = dashboardData.account_risk_factors || [];
    
    // Clear container safely
    container.textContent = '';
    
    if (companiesWithRiskFactors.length === 0) {
        const noDataMsg = document.createElement('p');
        noDataMsg.className = 'text-muted';
        noDataMsg.textContent = 'No account risk factors identified.';
        container.appendChild(noDataMsg);
        return;
    }
    
    companiesWithRiskFactors.forEach(company => {
        // Ensure company has a name and risk factors array
        if (!company.company_name || !company.risk_factors || !Array.isArray(company.risk_factors)) {
            return;
        }
        
        // Create company container
        const companyDiv = document.createElement('div');
        companyDiv.className = 'company-risk-factors mb-4';
        
        // Create company name header
        const companyHeader = document.createElement('h6');
        companyHeader.className = 'company-name text-dark mb-3';
        companyHeader.textContent = company.company_name; // Safe text content
        companyDiv.appendChild(companyHeader);
        
        // Create risk factors
        company.risk_factors.forEach(risk => {
            const severityClass = risk.severity === 'Critical' ? 'danger' : 
                                 risk.severity === 'High' ? 'danger' : 
                                 risk.severity === 'Medium' ? 'secondary' : 'secondary';
            
            // Create risk factor container
            const riskDiv = document.createElement('div');
            riskDiv.className = 'risk-factor-item mb-3 p-3 border rounded';
            
            // Create header row with type and severity
            const headerDiv = document.createElement('div');
            headerDiv.className = 'd-flex justify-content-between align-items-start mb-2';
            
            const typeHeader = document.createElement('h6');
            typeHeader.className = 'risk-type mb-1';
            typeHeader.textContent = risk.type; // Safe text content
            
            const severityBadge = document.createElement('span');
            severityBadge.className = `badge bg-${severityClass}`;
            severityBadge.textContent = risk.severity; // Safe text content
            
            headerDiv.appendChild(typeHeader);
            headerDiv.appendChild(severityBadge);
            riskDiv.appendChild(headerDiv);
            
            // Create description
            const descriptionP = document.createElement('p');
            descriptionP.className = 'risk-description text-muted mb-2';
            descriptionP.textContent = risk.description; // Safe text content
            riskDiv.appendChild(descriptionP);
            
            // Create action
            const actionSmall = document.createElement('small');
            actionSmall.className = 'risk-action text-primary';
            const actionStrong = document.createElement('strong');
            actionStrong.textContent = 'Recommended Action: ';
            actionSmall.appendChild(actionStrong);
            actionSmall.appendChild(document.createTextNode(risk.action)); // Safe text content
            riskDiv.appendChild(actionSmall);
            
            // Add count if more than 1
            if (risk.count > 1) {
                const countDiv = document.createElement('div');
                countDiv.className = 'text-end';
                const countSmall = document.createElement('small');
                countSmall.className = 'text-muted';
                countSmall.textContent = `${risk.count} occurrences`; // Safe text content
                countDiv.appendChild(countSmall);
                riskDiv.appendChild(countDiv);
            }
            
            companyDiv.appendChild(riskDiv);
        });
        
        container.appendChild(companyDiv);
    });
}

// ============================================================================
// SURVEY INSIGHTS — ACTIONABILITY LAYER
// ============================================================================

const SI_RISK_PRIORITY = { 'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3 };

function siRiskSort(a, b) {
    const pa = SI_RISK_PRIORITY[a.risk_level] !== undefined ? SI_RISK_PRIORITY[a.risk_level] : 4;
    const pb = SI_RISK_PRIORITY[b.risk_level] !== undefined ? SI_RISK_PRIORITY[b.risk_level] : 4;
    return pa - pb;
}

let _siLastCompanyData = [];
let _siLastTenureData = [];

function siUpdatePriorityPanel() {
    const panel = document.getElementById('siPriorityPanel');
    if (!panel) return;

    const highRiskAccounts = (dashboardData && dashboardData.high_risk_accounts) ? dashboardData.high_risk_accounts : [];
    const highRiskCount = highRiskAccounts.length;

    const riskCountEl = document.getElementById('siRiskCount');
    if (riskCountEl) riskCountEl.textContent = highRiskCount;

    const lowConfCount = highRiskAccounts.filter(function(a) {
        var cl = a.confidence_level || 'insufficient';
        return cl === 'low' || cl === 'insufficient';
    }).length;
    var riskSubEl = document.getElementById('siRiskCountSub');
    if (riskSubEl) {
        if (lowConfCount > 0 && highRiskCount > 0) {
            riskSubEl.textContent = lowConfCount + ' with low/insufficient data';
            riskSubEl.style.display = 'inline';
        } else {
            riskSubEl.style.display = 'none';
        }
    }

    const showBtn = document.getElementById('siShowRiskBtn');
    if (showBtn) showBtn.style.display = highRiskCount > 0 ? '' : 'none';

    const weakestEl = document.getElementById('siWeakestTenure');
    if (weakestEl) {
        const validTenure = _siLastTenureData.filter(t => t.risk_level !== 'Insufficient Data' && t.total_responses >= 2);
        if (validTenure.length > 0) {
            const worst = validTenure.reduce((a, b) => (a.tenure_nps < b.tenure_nps ? a : b));
            const npsDisplay = (worst.tenure_nps > 0 ? '+' : '') + worst.tenure_nps;
            const npsColor = worst.tenure_nps > 20 ? '#000000' : worst.tenure_nps >= -20 ? '#BDBDBD' : '#E13A44';
            weakestEl.innerHTML = `${escapeHtml(worst.tenure_group)} <span style="color:${npsColor}">(NPS ${npsDisplay})</span>`;
        } else {
            weakestEl.textContent = '--';
        }
    }

    const campaignNpsEl = document.getElementById('siCampaignNps');
    if (campaignNpsEl && dashboardData) {
        const nps = dashboardData.nps_score;
        if (nps !== null && nps !== undefined) {
            const display = (nps > 0 ? '+' : '') + nps;
            const color = nps > 20 ? '#000000' : nps >= -20 ? '#BDBDBD' : '#E13A44';
            campaignNpsEl.innerHTML = `<span style="color:${color}">${display}</span>`;
        } else {
            campaignNpsEl.textContent = '--';
        }
    }

    panel.style.display = highRiskCount > 0 ? '' : 'none';
}

function siFilterHighRisk() {
    const tbody = document.getElementById('companyNpsTableServerSide');
    if (!tbody || !dashboardData || !dashboardData.high_risk_accounts) return;

    const highRisk = dashboardData.high_risk_accounts;
    if (highRisk.length === 0) return;

    const mapped = highRisk.map(a => ({
        company_name: a.company_name,
        risk_level: a.risk_level,
        total_responses: a.respondent_count || 0,
        avg_nps: a.nps_score != null ? String(a.nps_score) : 'N/A',
        company_nps: 0,
        promoters: 0,
        passives: 0,
        detractors: 0,
        latest_response: a.latest_response || 'N/A',
        latest_churn_risk: a.risk_level,
        confidence_level: a.confidence_level ?? 'insufficient',
        response_rate: a.response_rate ?? null,
        invited_count: a.invited_count ?? 0,
    }));
    mapped.sort(siRiskSort);

    tbody.innerHTML = mapped.map(company => {
        let riskBadgeClass = 'bg-warning text-dark';
        let riskBorderClass = 'si-risk-medium';
        if (company.risk_level === 'Low') { riskBadgeClass = 'bg-success'; riskBorderClass = 'si-risk-low'; }
        else if (company.risk_level === 'Medium') { riskBadgeClass = 'bg-warning text-dark'; riskBorderClass = 'si-risk-medium'; }
        else if (company.risk_level === 'High') { riskBadgeClass = 'bg-danger'; riskBorderClass = 'si-risk-high'; }
        else if (company.risk_level === 'Critical') { riskBadgeClass = 'bg-dark'; riskBorderClass = 'si-risk-critical'; }

        const avgNps = parseFloat(company.avg_nps) || 0;
        const avgNpsClass = avgNps >= 8 ? 'si-nps-high' : avgNps >= 6 ? 'si-nps-mid' : 'si-nps-low';

        const churnRisk = company.latest_churn_risk || 'N/A';
        const churnClass = (churnRisk === 'High' || churnRisk === 'Critical') ? 'text-danger fw-semibold' : churnRisk === 'Medium' ? 'text-warning fw-semibold' : churnRisk === 'Low' ? 'text-success' : '';

        const campaignSelectHR = document.getElementById('campaignFilter');
        const campaignIdHR = campaignSelectHR ? campaignSelectHR.value : null;
        const confidenceBadgeHR = getConfidenceBadge(company.confidence_level ?? 'insufficient');
        const rateHintHR = company.response_rate != null ? ` (${company.response_rate}% of ${company.invited_count} invited)` : '';
        return `
            <tr class="${riskBorderClass}" data-si-click="company" data-company-name="${escapeHtml(company.company_name)}">
                <td>
                    <a href="#"
                       onclick="event.stopPropagation(); openCompanyResponsesModal('${escapeHtml(company.company_name).replace(/'/g, "\\'")}', ${campaignIdHR}, ''); return false;"
                       style="color: #2E5090; text-decoration: none; cursor: pointer; font-weight: 600;"
                       onmouseover="this.style.textDecoration='underline';"
                       onmouseout="this.style.textDecoration='none';"
                       title="View all responses from ${escapeHtml(company.company_name)}">
                        ${escapeHtml(company.company_name)}
                        <i class="fas fa-external-link-alt ms-2" style="font-size: 0.7em; color: #8A8A8A;"></i>
                    </a>
                    <br><small title="Data confidence${escapeHtml(rateHintHR)}">${confidenceBadgeHR}</small>
                </td>
                <td><span class="badge ${riskBadgeClass}">${escapeHtml(company.risk_level)}</span></td>
                <td>${escapeHtml(String(company.total_responses))}</td>
                <td><span class="si-nps-score ${avgNpsClass}">${escapeHtml(company.avg_nps)}</span></td>
                <td colspan="2"><small class="text-muted">—</small></td>
                <td>${escapeHtml(company.latest_response) || 'N/A'}</td>
                <td><span class="${churnClass}">${escapeHtml(churnRisk)}</span></td>
            </tr>
        `;
    }).join('');

    const paginationInfo = document.getElementById('companyPaginationInfo');
    if (paginationInfo) {
        paginationInfo.innerHTML = '';
        const text = document.createTextNode(`Showing ${mapped.length} high-risk accounts `);
        paginationInfo.appendChild(text);
        const resetBtn = document.createElement('button');
        resetBtn.className = 'btn btn-outline-secondary btn-sm py-0 px-2';
        resetBtn.style.fontSize = '0.75rem';
        resetBtn.textContent = 'Show all';
        resetBtn.addEventListener('click', function() { loadCompanyNpsData(1); });
        paginationInfo.appendChild(resetBtn);
    }

    if (tbody) {
        tbody.closest('.data-table').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function siAttachRowClickHandlers() {
    const companyTbody = document.getElementById('companyNpsTableServerSide');
    if (companyTbody) {
        companyTbody.addEventListener('click', function(e) {
            const row = e.target.closest('tr[data-si-click="company"]');
            if (!row) return;
            const companyName = row.getAttribute('data-company-name');
            if (!companyName) return;

            row.classList.add('si-click-flash');
            setTimeout(() => row.classList.remove('si-click-flash'), 400);

            const searchInput = document.getElementById('responsesSearch');
            if (searchInput) searchInput.value = companyName;
            const nf = document.getElementById('npsFilter');
            if (nf) nf.value = '';
            loadSurveyResponses(1, companyName, '');

            setTimeout(() => {
                const responsesCard = document.getElementById('responsesTable');
                if (responsesCard) {
                    responsesCard.closest('.chart-card').scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 100);
        });
    }

    const tenureTbody = document.getElementById('tenureNpsTable');
    if (tenureTbody) {
        tenureTbody.addEventListener('click', function(e) {
            const row = e.target.closest('tr[data-si-click="tenure"]');
            if (!row) return;
            const tenureGroup = row.getAttribute('data-tenure-group');
            if (!tenureGroup) return;

            row.classList.add('si-click-flash');
            setTimeout(() => row.classList.remove('si-click-flash'), 400);

            const searchInput = document.getElementById('responsesSearch');
            if (searchInput) searchInput.value = tenureGroup;
            const nf = document.getElementById('npsFilter');
            if (nf) nf.value = '';
            loadSurveyResponses(1, tenureGroup, '');

            setTimeout(() => {
                const responsesCard = document.getElementById('responsesTable');
                if (responsesCard) {
                    responsesCard.closest('.chart-card').scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 100);
        });
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', siAttachRowClickHandlers);
} else {
    siAttachRowClickHandlers();
}

var _siTooltipEl = null;
var _siTooltipTimer = null;
var _siTooltipHideTimer = null;
var _siTooltipCache = {};
var _siTooltipCurrentRow = null;
var _siTooltipRequestId = 0;

function siShowTooltip(row, companyData) {
    siHideTooltip();
    ++_siTooltipRequestId;
    _siTooltipCurrentRow = row;

    var el = document.createElement('div');
    el.className = 'si-tooltip';
    el.setAttribute('data-si-tooltip', '1');

    var riskBadge = '';
    var rl = companyData.risk_level || '';
    if (rl === 'Critical' || rl === 'High') riskBadge = '<span class="badge bg-danger" style="font-size:0.7rem;">' + escapeHtml(rl) + '</span>';
    else if (rl === 'Medium') riskBadge = '<span class="badge bg-warning text-dark" style="font-size:0.7rem;">' + escapeHtml(rl) + '</span>';
    else if (rl === 'Low') riskBadge = '<span class="badge bg-success" style="font-size:0.7rem;">' + escapeHtml(rl) + '</span>';

    var npsVal = companyData.company_nps || 0;
    var npsBadge = 'bg-warning text-dark';
    if (npsVal > 20) npsBadge = 'bg-success';
    else if (npsVal < -20) npsBadge = 'bg-danger';

    var staticHtml = '<div class="si-tooltip-header">' +
        '<span class="si-tt-name">' + escapeHtml(companyData.company_name || '') + '</span>' + riskBadge +
        '</div><div class="si-tooltip-body">' +
        '<div class="si-tooltip-section">' +
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">' +
        '<span class="badge ' + npsBadge + '" style="font-size:0.85rem;">' + (npsVal > 0 ? '+' : '') + npsVal + ' NPS</span>' +
        '<span style="font-size:0.78rem;color:#BDBDBD;">' + escapeHtml(companyData.total_responses || 0) + ' responses</span></div>' +
        '<div style="display:flex;gap:6px;">' +
        '<span class="badge" style="background:#000000;font-size:0.7rem;">' + (companyData.promoters || 0) + ' P</span>' +
        '<span class="badge" style="background:#BDBDBD;font-size:0.7rem;">' + (companyData.passives || 0) + ' Pa</span>' +
        '<span class="badge" style="background:#E13A44;font-size:0.7rem;">' + (companyData.detractors || 0) + ' D</span>' +
        '</div></div>' +
        '<div id="siTooltipEnriched"><div style="text-align:center;padding:6px 0;"><span class="si-tt-spinner"></span></div></div>' +
        '</div>';

    el.innerHTML = staticHtml;
    row.style.position = 'relative';
    row.appendChild(el);
    _siTooltipEl = el;

    requestAnimationFrame(function() {
        el.classList.add('si-tooltip-visible');
    });

    var campaignSelect = document.getElementById('campaignFilter');
    var campaignId = campaignSelect ? campaignSelect.value : '';
    var companyName = companyData.company_name;
    var cacheKey = campaignId + '::' + (companyName || '').toUpperCase();

    if (_siTooltipCache[cacheKey]) {
        siRenderEnrichedTooltip(_siTooltipCache[cacheKey]);
        return;
    }

    if (!campaignId || !companyName) {
        var enrichDiv = document.getElementById('siTooltipEnriched');
        if (enrichDiv) enrichDiv.innerHTML = '';
        return;
    }

    var reqId = _siTooltipRequestId;

    fetch('/api/company_detail?campaign=' + encodeURIComponent(campaignId) + '&company=' + encodeURIComponent(companyName))
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (reqId !== _siTooltipRequestId) return;
            if (data.success && data.data) {
                _siTooltipCache[cacheKey] = data.data;
                siRenderEnrichedTooltip(data.data);
            } else {
                var enrichDiv = document.getElementById('siTooltipEnriched');
                if (enrichDiv) enrichDiv.innerHTML = '';
            }
        })
        .catch(function() {
            if (reqId !== _siTooltipRequestId) return;
            var enrichDiv = document.getElementById('siTooltipEnriched');
            if (enrichDiv) enrichDiv.innerHTML = '';
        });
}

function siRenderEnrichedTooltip(detail) {
    var enrichDiv = document.getElementById('siTooltipEnriched');
    if (!enrichDiv) return;

    var html = '';

    if (detail.sub_metrics && Object.keys(detail.sub_metrics).length > 0) {
        var labelMap = {satisfaction: 'Satisfaction', service: 'Service', pricing: 'Pricing', product_value: 'Product Value'};
        html += '<div class="si-tooltip-section"><div class="si-tooltip-section-label">Sub-Metrics</div>';
        Object.keys(detail.sub_metrics).forEach(function(key) {
            var val = detail.sub_metrics[key];
            var pct = Math.round((val / 5) * 100);
            var isWeakest = key === detail.weakest_metric;
            var barColor = isWeakest ? '#E13A44' : (val >= 4 ? '#000000' : val >= 3 ? '#BDBDBD' : '#E13A44');
            html += '<div class="si-tt-metric-row">' +
                '<span' + (isWeakest ? ' style="color:#E13A44;font-weight:600;"' : '') + '>' + (isWeakest ? '<i class="fas fa-exclamation-circle" style="margin-right:3px;font-size:0.7rem;"></i>' : '') + escapeHtml(labelMap[key] || key) + '</span>' +
                '<span><span class="si-tt-metric-bar"><span class="si-tt-metric-fill" style="width:' + pct + '%;background:' + barColor + ';"></span></span>' +
                '<span' + (isWeakest ? ' style="color:#E13A44;font-weight:600;"' : '') + '>' + val + '/5</span></span></div>';
        });
        html += '</div>';
    }

    if (detail.avg_churn_risk_score !== null && detail.avg_churn_risk_score !== undefined) {
        var churnPct = Math.round(detail.avg_churn_risk_score * 100);
        var churnColor = churnPct >= 70 ? '#E13A44' : churnPct >= 40 ? '#BDBDBD' : '#000000';
        html += '<div class="si-tooltip-section"><div class="si-tooltip-section-label">Avg Churn Risk</div>' +
            '<div style="display:flex;align-items:center;gap:6px;">' +
            '<div style="flex:1;height:6px;background:#E9E8E4;border-radius:3px;overflow:hidden;">' +
            '<div style="width:' + churnPct + '%;height:100%;background:' + churnColor + ';border-radius:3px;"></div></div>' +
            '<span style="font-size:0.8rem;font-weight:600;color:' + churnColor + ';">' + churnPct + '%</span></div></div>';
    }

    if (detail.top_themes && detail.top_themes.length > 0) {
        html += '<div class="si-tooltip-section"><div class="si-tooltip-section-label">Top Themes</div><div class="si-tt-themes">';
        detail.top_themes.forEach(function(t) {
            html += '<span class="si-tt-theme-pill">' + escapeHtml(t.theme) + ' <small style="color:#999;">(' + t.count + ')</small></span>';
        });
        html += '</div></div>';
    }

    if (detail.analysis_summary) {
        var summary = detail.analysis_summary;
        if (summary.length > 150) summary = summary.substring(0, 150) + '…';
        html += '<div class="si-tooltip-section"><div class="si-tooltip-section-label">AI Summary</div>' +
            '<div class="si-tt-summary">' + escapeHtml(summary) + '</div></div>';
    }

    enrichDiv.innerHTML = html;
}

function siHideTooltip() {
    if (_siTooltipEl) {
        _siTooltipEl.classList.remove('si-tooltip-visible');
        var el = _siTooltipEl;
        setTimeout(function() { if (el.parentNode) el.parentNode.removeChild(el); }, 160);
        _siTooltipEl = null;
    }
    _siTooltipCurrentRow = null;
}

function siAttachTooltipHandlers() {
    var companyTbody = document.getElementById('companyNpsTableServerSide');
    if (!companyTbody || companyTbody._siTooltipBound) return;
    companyTbody._siTooltipBound = true;

    companyTbody.addEventListener('mouseenter', function(e) {
        var row = e.target.closest('tr[data-si-click="company"]');
        if (!row) return;
        if (_siTooltipCurrentRow === row) return;

        clearTimeout(_siTooltipTimer);
        clearTimeout(_siTooltipHideTimer);

        _siTooltipTimer = setTimeout(function() {
            var companyName = row.getAttribute('data-company-name');
            if (!companyName) return;

            var rowCompanyData = null;
            if (_siLastCompanyData) {
                for (var i = 0; i < _siLastCompanyData.length; i++) {
                    if (_siLastCompanyData[i].company_name === companyName) {
                        rowCompanyData = _siLastCompanyData[i];
                        break;
                    }
                }
            }
            if (!rowCompanyData) {
                rowCompanyData = { company_name: companyName, company_nps: 0, total_responses: 0, promoters: 0, passives: 0, detractors: 0, risk_level: 'Medium' };
            }

            siShowTooltip(row, rowCompanyData);
        }, 300);
    }, true);

    companyTbody.addEventListener('mouseleave', function(e) {
        var row = e.target.closest('tr[data-si-click="company"]');
        if (!row) return;
        var related = e.relatedTarget;
        if (related && (related.closest('.si-tooltip') || related.closest('tr[data-si-click="company"]') === row)) return;

        clearTimeout(_siTooltipTimer);
        _siTooltipHideTimer = setTimeout(function() { siHideTooltip(); }, 200);
    }, true);

    document.addEventListener('click', function(e) {
        if (_siTooltipEl && !e.target.closest('.si-tooltip')) {
            siHideTooltip();
        }
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', siAttachTooltipHandlers);
} else {
    siAttachTooltipHandlers();
}

// Pagination state for all tables
let currentResponsesPage = 1;
let currentCompanyPage = 1;
let currentTenurePage = 1;
const responsesPerPage = 10;
const companiesPerPage = 10;
const tenureGroupsPerPage = 10;

function loadSurveyResponses(page = 1, searchQuery = '', npsFilter = '') {
    currentResponsesPage = page;
    
    // Build URL with search and filter parameters
    let url = `/api/survey_responses?page=${page}&per_page=${responsesPerPage}`;
    
    // CRITICAL: Get campaign filter (NPS must be campaign-specific)
    const campaignSelect = document.getElementById('campaignFilter');
    if (campaignSelect && campaignSelect.value) {
        url += `&campaign=${campaignSelect.value}`;
    }
    
    if (searchQuery.trim()) {
        url += `&search=${encodeURIComponent(searchQuery)}`;
    }
    if (npsFilter.trim()) {
        url += `&nps_category=${encodeURIComponent(npsFilter)}`;
    }
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('responsesTable');
            const responses = data.responses || data; // Handle both old and new format
            const pagination = data.pagination;
            
            // Update search info display
            const searchInfo = document.getElementById('responsesSearchInfo');
            if (data.search_query && data.search_query.trim()) {
                searchInfo.textContent = `Found ${pagination ? pagination.total : responses.length} results for "${data.search_query}"`;
                searchInfo.style.display = 'block';
            } else {
                searchInfo.textContent = '';
                searchInfo.style.display = 'none';
            }
            
            if (responses.length === 0) {
                const noResultsMsg = data.search_query && data.search_query.trim() 
                    ? 'No survey responses found matching your search criteria.'
                    : 'No survey responses yet.';
                tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">${noResultsMsg}</td></tr>`;
                updatePaginationInfo(0, 0, 0);
                updatePaginationControls(null);
                return;
            }
            
            const html = responses.map(response => {
                const riskLevel = response.churn_risk_level || 'Minimal';
                const riskColorClass = (riskLevel === 'High' || riskLevel === 'Critical') ? 'text-danger fw-semibold' : 
                                 riskLevel === 'Medium' ? 'text-warning fw-semibold' : 
                                 riskLevel === 'Low' ? 'text-success' : '';
                
                const sentimentClass = response.sentiment_label === 'positive' ? 'theme-positive' :
                                      response.sentiment_label === 'negative' ? 'theme-negative' : 'theme-neutral';
                
                const canView = response.can_view !== undefined ? response.can_view : false;
                const detailsButton = canView ? 
                    `<a href="/survey-response/${response.id}" class="btn btn-outline-primary btn-sm" title="${translations.viewDetails}">
                        <i class="fas fa-eye"></i>
                    </a>` :
                    `<span class="text-muted" title="${translations.authenticationRequired}">
                        <i class="fas fa-lock"></i>
                    </span>`;
                
                const npsScore = parseFloat(response.nps_score) || 0;
                const npsScoreClass = npsScore >= 9 ? 'si-nps-high' : npsScore >= 7 ? 'si-nps-mid' : 'si-nps-low';
                const riskBorderClass = (riskLevel === 'High' || riskLevel === 'Critical') ? 'si-risk-high' : riskLevel === 'Medium' ? 'si-risk-medium' : riskLevel === 'Low' ? 'si-risk-low' : '';
                
                return `
                    <tr class="${riskBorderClass}">
                        <td>${escapeHtml(response.company_name)}</td>
                        <td><span class="${riskColorClass}">${escapeHtml(riskLevel)}</span></td>
                        <td>
                            <span class="si-nps-score ${npsScoreClass}">
                                ${escapeHtml(response.nps_score)}
                            </span>
                        </td>
                        <td><span class="badge ${response.nps_category === 'Promoter' ? 'bg-success' : response.nps_category === 'Passive' ? 'bg-warning text-dark' : 'bg-danger'}">${escapeHtml(response.nps_category)}</span></td>
                        <td class="${sentimentClass}">${escapeHtml(response.sentiment_label) || 'N/A'}</td>
                        <td>${escapeHtml(response.tenure_with_fc) || 'N/A'}</td>
                        <td>${response.created_at ? new Date(response.created_at).toLocaleDateString() : 'N/A'}</td>
                        <td class="text-center">${detailsButton}</td>
                    </tr>
                `;
            }).join('');
            
            tbody.innerHTML = html;
            
            // Update pagination info and controls
            if (pagination) {
                updateResponsesPaginationInfo(pagination.page, pagination.pages, pagination.total);
                updateResponsesPaginationControls(pagination);
            }
        })
        .catch(error => {
            console.error('Error loading survey responses:', error);
            document.getElementById('responsesTable').innerHTML = 
                `<tr><td colspan="8" class="text-center text-danger">${translations.errorLoadingResponses}</td></tr>`;
            updateResponsesPaginationInfo(0, 0, 0);
            updateResponsesPaginationControls(null);
        });
}

// Helper function to generate smart pagination page numbers with ellipsis
function generatePaginationPages(currentPage, totalPages) {
    const pages = [];
    const leftEdge = 1;
    const leftCurrent = 2;
    const rightCurrent = 2;
    const rightEdge = 1;
    
    for (let i = 1; i <= totalPages; i++) {
        // Show first page
        if (i <= leftEdge) {
            pages.push(i);
        }
        // Show pages around current page
        else if (i >= currentPage - leftCurrent && i <= currentPage + rightCurrent) {
            pages.push(i);
        }
        // Show last page
        else if (i > totalPages - rightEdge) {
            pages.push(i);
        }
        // Add ellipsis for gaps
        else if (pages[pages.length - 1] !== null) {
            pages.push(null); // null represents ellipsis
        }
    }
    
    return pages;
}

function updateResponsesPaginationInfo(currentPage, totalPages, totalItems) {
    const info = document.getElementById('paginationInfo');
    if (totalItems === 0) {
        info.textContent = 'No responses found';
    } else {
        const startItem = (currentPage - 1) * responsesPerPage + 1;
        const endItem = Math.min(currentPage * responsesPerPage, totalItems);
        info.textContent = `${translations.showing} ${startItem}-${endItem} ${translations.of} ${totalItems} ${translations.responses}`;
    }
}



function updateResponsesPaginationControls(pagination) {
    const controls = document.getElementById('paginationControls');
    
    if (!pagination || pagination.pages <= 1) {
        controls.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Previous button
    if (pagination.has_prev) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadSurveyResponses(${pagination.page - 1}, getCurrentSearchQuery(), getCurrentNpsFilter()); return false;">
                    <i class="fas fa-chevron-left"></i>
                </a>
            </li>
        `;
    } else {
        html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-left"></i></span></li>';
    }
    
    // Page numbers with smart ellipsis
    const pages = generatePaginationPages(pagination.page, pagination.pages);
    for (const pageNum of pages) {
        if (pageNum === null) {
            html += '<li class="page-item disabled"><span class="page-link">…</span></li>';
        } else if (pageNum === pagination.page) {
            html += `<li class="page-item active"><span class="page-link">${pageNum}</span></li>`;
        } else {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="loadSurveyResponses(${pageNum}, getCurrentSearchQuery(), getCurrentNpsFilter()); return false;">${pageNum}</a></li>`;
        }
    }
    
    // Next button
    if (pagination.has_next) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadSurveyResponses(${pagination.page + 1}, getCurrentSearchQuery(), getCurrentNpsFilter()); return false;">
                    <i class="fas fa-chevron-right"></i>
                </a>
            </li>
        `;
    } else {
        html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-right"></i></span></li>';
    }
    
    controls.innerHTML = html;
}

// Company pagination functions
function updateCompanyPaginationInfo(currentPage, totalPages, totalItems) {
    const info = document.getElementById('companyPaginationInfo');
    if (totalItems === 0) {
        info.textContent = 'No companies found';
    } else {
        const startItem = (currentPage - 1) * companiesPerPage + 1;
        const endItem = Math.min(currentPage * companiesPerPage, totalItems);
        info.textContent = `${translations.showing} ${startItem}-${endItem} ${translations.of} ${totalItems} ${translations.companies}`;
    }
}



function updateCompanyPaginationControls(pagination) {
    const controls = document.getElementById('companyPaginationControls');
    
    if (!controls) {
        return;
    }
    
    if (!pagination || pagination.pages <= 1) {
        controls.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Previous button
    if (pagination.has_prev) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadCompanyNpsData(${pagination.page - 1}, getCurrentCompanySearch(), getCurrentCompanyNpsFilter()); return false;">
                    <i class="fas fa-chevron-left"></i>
                </a>
            </li>
        `;
    } else {
        html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-left"></i></span></li>';
    }
    
    // Page numbers with smart ellipsis
    const pages = generatePaginationPages(pagination.page, pagination.pages);
    for (const pageNum of pages) {
        if (pageNum === null) {
            html += '<li class="page-item disabled"><span class="page-link">…</span></li>';
        } else if (pageNum === pagination.page) {
            html += `<li class="page-item active"><span class="page-link">${pageNum}</span></li>`;
        } else {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="loadCompanyNpsData(${pageNum}, getCurrentCompanySearch(), getCurrentCompanyNpsFilter()); return false;">${pageNum}</a></li>`;
        }
    }
    
    // Next button
    if (pagination.has_next) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadCompanyNpsData(${pagination.page + 1}, getCurrentCompanySearch(), getCurrentCompanyNpsFilter()); return false;">
                    <i class="fas fa-chevron-right"></i>
                </a>
            </li>
        `;
    } else {
        html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-right"></i></span></li>';
    }
    
    controls.innerHTML = html;
}

// Tenure pagination functions
function updateTenurePaginationInfo(currentPage, totalPages, totalItems) {
    const info = document.getElementById('tenurePaginationInfo');
    if (totalItems === 0) {
        info.textContent = 'No tenure data found';
    } else {
        const startItem = (currentPage - 1) * tenureGroupsPerPage + 1;
        const endItem = Math.min(currentPage * tenureGroupsPerPage, totalItems);
        info.textContent = `${translations.showing} ${startItem}-${endItem} ${translations.of} ${totalItems} ${translations.tenureGroups}`;
    }
}



function updateTenurePaginationControls(pagination) {
    const controls = document.getElementById('tenurePaginationControls');
    
    if (!pagination || pagination.pages <= 1) {
        controls.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Previous button
    if (pagination.has_prev) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadTenureNpsData(${pagination.page - 1}); return false;">
                    <i class="fas fa-chevron-left"></i>
                </a>
            </li>
        `;
    } else {
        html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-left"></i></span></li>';
    }
    
    // Page numbers with smart ellipsis
    const pages = generatePaginationPages(pagination.page, pagination.pages);
    for (const pageNum of pages) {
        if (pageNum === null) {
            html += '<li class="page-item disabled"><span class="page-link">…</span></li>';
        } else if (pageNum === pagination.page) {
            html += `<li class="page-item active"><span class="page-link">${pageNum}</span></li>`;
        } else {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="loadTenureNpsData(${pageNum}); return false;">${pageNum}</a></li>`;
        }
    }
    
    // Next button
    if (pagination.has_next) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadTenureNpsData(${pagination.page + 1}); return false;">
                    <i class="fas fa-chevron-right"></i>
                </a>
            </li>
        `;
    } else {
        html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-right"></i></span></li>';
    }
    
    controls.innerHTML = html;
}

function loadTenureNpsData(page = 1) {
    currentTenurePage = page;
    console.log('Loading tenure NPS data...');
    
    // Build URL with campaign filter
    let url = `/api/tenure_nps?page=${page}&per_page=${tenureGroupsPerPage}`;
    
    // CRITICAL: Get campaign filter (NPS must be campaign-specific)
    const campaignSelect = document.getElementById('campaignFilter');
    if (campaignSelect && campaignSelect.value) {
        url += `&campaign=${campaignSelect.value}`;
    }
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log('Tenure NPS data received:', data);
            if (data.success) {
                console.log('Populating table with', data.data.length, 'tenure groups');
                populateTenureNpsTable(data.data);
                
                // Update pagination info and controls for tenure table
                if (data.pagination) {
                    updateTenurePaginationInfo(data.pagination.page, data.pagination.pages, data.pagination.total);
                    updateTenurePaginationControls(data.pagination);
                }
            } else {
                console.error('Error loading tenure NPS data:', data.error);
                document.getElementById('tenureNpsTable').innerHTML = 
                    '<tr><td colspan="8" class="text-center text-danger">Error: ' + (data.error || 'Unknown error') + '</td></tr>';
                updateTenurePaginationInfo(0, 0, 0);
                updateTenurePaginationControls(null);
            }
        })
        .catch(error => {
            console.error('Error fetching tenure NPS data:', error);
            document.getElementById('tenureNpsTable').innerHTML = 
                `<tr><td colspan="8" class="text-center text-danger">${translations.networkErrorLoadingTenureData}</td></tr>`;
            updateTenurePaginationInfo(0, 0, 0);
            updateTenurePaginationControls(null);
        });
}

function populateTenureNpsTable(tenureData) {
    console.log('populateTenureNpsTable called with:', tenureData);
    const tbody = document.getElementById('tenureNpsTable');
    
    if (!tbody) {
        console.error('tenureNpsTable element not found!');
        return;
    }
    
    if (!tenureData || tenureData.length === 0) {
        console.log('No tenure data to display');
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">${translations.noTenureDataAvailable}</td></tr>`;
        _siLastTenureData = [];
        siUpdatePriorityPanel();
        return;
    }
    
    const sorted = [...tenureData].sort(siRiskSort);
    _siLastTenureData = sorted;
    siUpdatePriorityPanel();
    
    console.log('Rendering', sorted.length, 'tenure groups to table');
    
    tbody.innerHTML = sorted.map(tenure => {
        let riskBadgeClass = 'bg-warning text-dark';
        let riskBorderClass = 'si-risk-medium';
        if (tenure.risk_level === 'Low') { riskBadgeClass = 'bg-success'; riskBorderClass = 'si-risk-low'; }
        else if (tenure.risk_level === 'Medium') { riskBadgeClass = 'bg-warning text-dark'; riskBorderClass = 'si-risk-medium'; }
        else if (tenure.risk_level === 'High') { riskBadgeClass = 'bg-danger'; riskBorderClass = 'si-risk-high'; }
        else if (tenure.risk_level === 'Critical') { riskBadgeClass = 'bg-dark'; riskBorderClass = 'si-risk-critical'; }
        else if (tenure.risk_level === 'Insufficient Data') { riskBadgeClass = 'bg-secondary'; riskBorderClass = ''; }
        
        let npsBadgeClass = 'bg-warning text-dark';
        if (tenure.tenure_nps > 20) npsBadgeClass = 'bg-success';
        else if (tenure.tenure_nps >= -20) npsBadgeClass = 'bg-warning text-dark'; 
        else npsBadgeClass = 'bg-danger';
        
        const avgNps = parseFloat(tenure.avg_nps) || 0;
        const avgNpsClass = avgNps >= 8 ? 'si-nps-high' : avgNps >= 6 ? 'si-nps-mid' : 'si-nps-low';
        
        const total = (tenure.promoters || 0) + (tenure.passives || 0) + (tenure.detractors || 0);
        let distHtml = '<small class="text-muted">N/A</small>';
        if (total > 0) {
            const pPct = ((tenure.promoters / total) * 100).toFixed(1);
            const paPct = ((tenure.passives / total) * 100).toFixed(1);
            const dPct = ((tenure.detractors / total) * 100).toFixed(1);
            distHtml = `<div class="si-dist-bar" title="${tenure.promoters}P / ${tenure.passives}Pa / ${tenure.detractors}D"><div class="si-dist-p" style="width:${pPct}%"></div><div class="si-dist-pa" style="width:${paPct}%"></div><div class="si-dist-d" style="width:${dPct}%"></div></div><small class="text-muted si-dist-label">${tenure.promoters}P · ${tenure.passives}Pa · ${tenure.detractors}D</small>`;
        }
        
        const churnRisk = tenure.latest_churn_risk || 'N/A';
        const churnClass = (churnRisk === 'High' || churnRisk === 'Critical') ? 'text-danger fw-semibold' : churnRisk === 'Medium' ? 'text-warning fw-semibold' : churnRisk === 'Low' ? 'text-success' : '';
        
        return `
            <tr class="${riskBorderClass}" data-si-click="tenure" data-tenure-group="${escapeHtml(tenure.tenure_group)}">
                <td><strong>${escapeHtml(tenure.tenure_group)}</strong></td>
                <td><span class="badge ${riskBadgeClass}">${escapeHtml(tenure.risk_level)}</span></td>
                <td>${escapeHtml(tenure.total_responses)}</td>
                <td><span class="si-nps-score ${avgNpsClass}">${escapeHtml(tenure.avg_nps)}</span></td>
                <td><span class="badge ${npsBadgeClass}">${tenure.tenure_nps > 0 ? '+' : ''}${escapeHtml(tenure.tenure_nps)}</span></td>
                <td>${distHtml}</td>
                <td>${escapeHtml(tenure.latest_response) || 'N/A'}</td>
                <td><span class="${churnClass}">${escapeHtml(churnRisk)}</span></td>
            </tr>
        `;
    }).join('');
}

function loadCompanyNpsData(page = 1, searchQuery = '', npsFilter = '') {
    currentCompanyPage = page;
    console.log('Loading company NPS data...');
    
    // Build URL with search and filter parameters
    let url = `/api/company_nps?page=${page}&per_page=${companiesPerPage}`;
    
    // CRITICAL: Get campaign filter (NPS must be campaign-specific)
    const campaignSelect = document.getElementById('campaignFilter');
    if (campaignSelect && campaignSelect.value) {
        url += `&campaign=${campaignSelect.value}`;
    }
    
    if (searchQuery.trim()) {
        url += `&search=${encodeURIComponent(searchQuery)}`;
    }
    if (npsFilter.trim()) {
        url += `&nps_category=${encodeURIComponent(npsFilter)}`;
    }
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log('Company NPS data received:', data);
            if (data.success) {
                console.log('Populating table with', data.data.length, 'companies');
                populateCompanyNpsTable(data.data);
                
                // Update pagination info and controls for company table
                if (data.pagination) {
                    updateCompanyPaginationInfo(data.pagination.page, data.pagination.pages, data.pagination.total);
                    updateCompanyPaginationControls(data.pagination);
                }
            } else {
                console.error('Error loading company NPS data:', data.error);
                document.getElementById('companyNpsTableServerSide').innerHTML = 
                    '<tr><td colspan="8" class="text-center text-danger">Error: ' + (data.error || 'Unknown error') + '</td></tr>';
                updateCompanyPaginationInfo(0, 0, 0);
                updateCompanyPaginationControls(null);
            }
        })
        .catch(error => {
            console.error('Error fetching company NPS data:', error);
            document.getElementById('companyNpsTableServerSide').innerHTML = 
                `<tr><td colspan="8" class="text-center text-danger">${translations.networkErrorLoadingCompanyData}</td></tr>`;
            updateCompanyPaginationInfo(0, 0, 0);
            updateCompanyPaginationControls(null);
        });
}

function populateCompanyNpsTable(companyData) {
    console.log('populateCompanyNpsTable called with:', companyData);
    const tbody = document.getElementById('companyNpsTableServerSide');
    
    if (!tbody) {
        console.error('companyNpsTable element not found!');
        return;
    }
    
    if (!companyData || companyData.length === 0) {
        console.log('No company data to display');
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">${translations.noCompanyDataAvailable}</td></tr>`;
        _siLastCompanyData = [];
        siUpdatePriorityPanel();
        return;
    }
    
    const sorted = [...companyData].sort(siRiskSort);
    _siLastCompanyData = sorted;
    siUpdatePriorityPanel();
    
    console.log('Rendering', sorted.length, 'companies to table');
    
    tbody.innerHTML = sorted.map(company => {
        let riskBadgeClass = 'bg-warning text-dark';
        let riskBorderClass = 'si-risk-medium';
        if (company.risk_level === 'Low') { riskBadgeClass = 'bg-success'; riskBorderClass = 'si-risk-low'; }
        else if (company.risk_level === 'Medium') { riskBadgeClass = 'bg-warning text-dark'; riskBorderClass = 'si-risk-medium'; }
        else if (company.risk_level === 'High') { riskBadgeClass = 'bg-danger'; riskBorderClass = 'si-risk-high'; }
        else if (company.risk_level === 'Critical') { riskBadgeClass = 'bg-dark'; riskBorderClass = 'si-risk-critical'; }
        
        let npsBadgeClass = 'bg-warning text-dark';
        if (company.company_nps > 20) npsBadgeClass = 'bg-success';
        else if (company.company_nps >= -20) npsBadgeClass = 'bg-warning text-dark'; 
        else npsBadgeClass = 'bg-danger';
        
        const avgNps = parseFloat(company.avg_nps) || 0;
        const avgNpsClass = avgNps >= 8 ? 'si-nps-high' : avgNps >= 6 ? 'si-nps-mid' : 'si-nps-low';
        
        const total = (company.promoters || 0) + (company.passives || 0) + (company.detractors || 0);
        let distHtml = '<small class="text-muted">N/A</small>';
        if (total > 0) {
            const pPct = ((company.promoters / total) * 100).toFixed(1);
            const paPct = ((company.passives / total) * 100).toFixed(1);
            const dPct = ((company.detractors / total) * 100).toFixed(1);
            distHtml = `<div class="si-dist-bar" title="${company.promoters}P / ${company.passives}Pa / ${company.detractors}D"><div class="si-dist-p" style="width:${pPct}%"></div><div class="si-dist-pa" style="width:${paPct}%"></div><div class="si-dist-d" style="width:${dPct}%"></div></div><small class="text-muted si-dist-label">${company.promoters}P · ${company.passives}Pa · ${company.detractors}D</small>`;
        }
        
        const churnRisk = company.latest_churn_risk || 'N/A';
        const churnClass = (churnRisk === 'High' || churnRisk === 'Critical') ? 'text-danger fw-semibold' : churnRisk === 'Medium' ? 'text-warning fw-semibold' : churnRisk === 'Low' ? 'text-success' : '';
        
        const campaignSelectCN = document.getElementById('campaignFilter');
        const campaignIdCN = campaignSelectCN ? campaignSelectCN.value : null;
        return `
            <tr class="${riskBorderClass}" data-si-click="company" data-company-name="${escapeHtml(company.company_name)}">
                <td>
                    <a href="#"
                       onclick="event.stopPropagation(); openCompanyResponsesModal('${escapeHtml(company.company_name).replace(/'/g, "\\'")}', ${campaignIdCN}, ''); return false;"
                       style="color: #2E5090; text-decoration: none; cursor: pointer; font-weight: 600;"
                       onmouseover="this.style.textDecoration='underline';"
                       onmouseout="this.style.textDecoration='none';"
                       title="View all responses from ${escapeHtml(company.company_name)}">
                        ${escapeHtml(company.company_name)}
                        <i class="fas fa-external-link-alt ms-2" style="font-size: 0.7em; color: #8A8A8A;"></i>
                    </a>
                </td>
                <td><span class="badge ${riskBadgeClass}">${escapeHtml(company.risk_level)}</span></td>
                <td>${escapeHtml(company.total_responses)}</td>
                <td><span class="si-nps-score ${avgNpsClass}">${escapeHtml(company.avg_nps)}</span></td>
                <td><span class="badge ${npsBadgeClass}">${company.company_nps > 0 ? '+' : ''}${escapeHtml(company.company_nps)}</span></td>
                <td>${distHtml}</td>
                <td>${escapeHtml(company.latest_response) || 'N/A'}</td>
                <td><span class="${churnClass}">${escapeHtml(churnRisk)}</span></td>
            </tr>
        `;
    }).join('');
}

// Load KPI overview data for Executive Summary
async function loadKpiOverview() {
    console.log('Loading KPI overview data...');
    const tbody = document.getElementById('kpiOverviewTableBody');
    const loadingElement = document.getElementById('executiveSummaryLoading');
    const contentElement = document.getElementById('executiveSummaryContent');
    
    if (!tbody) {
        console.error('kpiOverviewTableBody element not found!');
        return;
    }
    
    // Show loading, hide content
    if (loadingElement) loadingElement.classList.remove('d-none');
    if (contentElement) contentElement.classList.add('d-none');
    
    try {
        // First, load available campaigns
        const campaignResponse = await fetch('/api/campaigns/filter-options');
        if (!campaignResponse.ok) {
            throw new Error(translations.failedToLoadCampaignOptions);
        }
        
        const campaignData = await campaignResponse.json();
        const campaigns = campaignData.campaigns || [];
        
        if (campaigns.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted">${translations.noCampaignDataAvailable}</td></tr>`;
            return;
        }
        
        // PERFORMANCE FIX: TRUE PARALLEL LOADING WITH ISOLATED ERROR HANDLING
        // Step 1: Launch ALL fetch requests simultaneously (no blocking)
        const fetchPromises = campaigns.map(campaign => 
            fetch(`/api/campaigns/comparison?campaign1=${campaign.id}&campaign2=${campaign.id}`)
        );
        
        // Step 2: Wait for all network requests to complete (parallel execution, resilient)
        const fetchResults = await Promise.allSettled(fetchPromises);
        
        // Step 3: Process ALL results synchronously (no Promise.all to avoid all-or-nothing)
        const jsonPromises = fetchResults.map(async (result, index) => {
            const campaign = campaigns[index];
            
            // Handle network failures
            if (result.status === 'rejected') {
                console.warn(`Network error for campaign ${campaign.name}:`, result.reason);
                return null;
            }
            
            // Handle HTTP errors  
            if (!result.value.ok) {
                console.warn(`HTTP error for campaign ${campaign.name}: ${result.value.status} ${result.value.statusText}`);
                return null;
            }
            
            // Parse JSON with isolated error handling
            try {
                const data = await result.value.json();
                return data?.campaign1?.data || null;
            } catch (error) {
                console.warn(`JSON parse error for campaign ${campaign.name}:`, error);
                return null;
            }
        });
        
        // Wait for JSON parsing (still parallel but with per-campaign error isolation)
        const kpiDataArray = await Promise.allSettled(jsonPromises);
        
        // Step 4: Build final KPI rows (purely synchronous, no failures possible)
        const kpiRows = campaigns.map((campaign, index) => {
            const kpiDataResult = kpiDataArray[index];
            const campaignKpis = kpiDataResult.status === 'fulfilled' ? kpiDataResult.value : null;
            
            return {
                name: campaign.name || 'Unknown',
                end_date: campaign.end_date || null,
                status: formatCampaignStatus(campaign.status),
                responses: campaignKpis?.total_responses || 0,
                nps_score: campaignKpis?.nps_score || 0,
                companies: campaignKpis?.companies_analyzed || 0,
                critical_risk: campaignKpis?.critical_risk_companies || 0,
                satisfaction: campaignKpis?.average_ratings?.satisfaction || 0,
                product_value: campaignKpis?.average_ratings?.product_value || 0,
                pricing: campaignKpis?.average_ratings?.pricing || 0,
                service: campaignKpis?.average_ratings?.service || 0
            };
        });
        
        // Sort by campaign end date (chronological order for trend visualization)
        campaigns.sort((a, b) => new Date(a.end_date) - new Date(b.end_date));
        
        // Re-sort kpiRows to match campaign chronological order
        const campaignOrder = campaigns.map(c => c.name);
        kpiRows.sort((a, b) => campaignOrder.indexOf(a.name) - campaignOrder.indexOf(b.name));
        
        // Generate table HTML
        tbody.innerHTML = kpiRows.map(row => `
            <tr>
                <td><strong>${escapeHtml(row.name)}</strong><br><small class="text-muted">${row.status}</small></td>
                <td class="text-center">${row.responses}</td>
                <td class="text-center">${row.nps_score.toFixed(1)}</td>
                <td class="text-center">${row.companies}</td>
                <td class="text-center"><span class="badge ${row.critical_risk > 0 ? 'bg-danger' : 'bg-success'}">${row.critical_risk}</span></td>
                <td class="text-center">${row.satisfaction.toFixed(1)}</td>
                <td class="text-center">${row.product_value.toFixed(1)}</td>
                <td class="text-center">${row.pricing.toFixed(1)}</td>
                <td class="text-center">${row.service.toFixed(1)}</td>
            </tr>
        `).join('');
        
        // Create sparklines after table is populated
        createKpiSparklines(kpiRows);
        
        console.log(`KPI overview loaded successfully with ${kpiRows.length} campaigns`);
        
        // Hide loading, show content
        if (loadingElement) loadingElement.classList.add('d-none');
        if (contentElement) contentElement.classList.remove('d-none');
        
    } catch (error) {
        console.error('Error loading KPI overview:', error);
        tbody.innerHTML = `<tr><td colspan="9" class="text-center text-danger">${translations.errorLoadingKpiData}</td></tr>`;
        
        // Hide loading, show content even on error
        if (loadingElement) loadingElement.classList.add('d-none');
        if (contentElement) contentElement.classList.remove('d-none');
    }
}

// Store sparkline chart instances to destroy them before recreating
let sparklineCharts = {};

// Store KPI data globally for modal use
let globalKpiData = null;

// Store modal chart instances
let modalCharts = {};

// Create sparklines for KPI metrics using approved color palette only
function createKpiSparklines(kpiData) {
    // Store data globally for modal
    globalKpiData = kpiData;
    if (!kpiData || kpiData.length === 0) return;
    
    // Destroy existing charts to prevent memory leaks
    Object.values(sparklineCharts).forEach(chart => {
        if (chart) chart.destroy();
    });
    sparklineCharts = {};
    
    // Brand primary for sparklines when configured; fall back to original #E13A44 otherwise.
    const _sparklinesBp = getBrandPalette();
    const _sparklinesColor = (_sparklinesBp.configured && _sparklinesBp.primary)
        ? _sparklinesBp.primary
        : '#E13A44';
    const MEDIUM_GRAY = '#BDBDBD';
    
    // Extract data for each metric
    const metrics = {
        responses: kpiData.map(row => row.responses),
        nps_score: kpiData.map(row => row.nps_score),
        companies: kpiData.map(row => row.companies),
        critical_risk: kpiData.map(row => row.critical_risk),
        satisfaction: kpiData.map(row => row.satisfaction),
        product_value: kpiData.map(row => row.product_value),
        pricing: kpiData.map(row => row.pricing),
        service: kpiData.map(row => row.service)
    };
    
    // Campaign labels (for tooltips)
    const labels = kpiData.map(row => row.name);
    
    // Helper function to determine line color based on trend
    const getLineColor = (data) => {
        if (data.length < 2) return MEDIUM_GRAY;
        const trend = data[data.length - 1] - data[0];
        return trend >= 0 ? _sparklinesColor : MEDIUM_GRAY;
    };
    
    // Common sparkline configuration
    const createSparklineConfig = (data, label) => ({
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                borderColor: getLineColor(data),
                backgroundColor: 'transparent',
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
                pointBackgroundColor: _sparklinesColor,
                pointBorderColor: _sparklinesColor,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: true,
                    displayColors: false,
                    callbacks: {
                        title: (items) => items[0].label,
                        label: (context) => `${label}: ${context.parsed.y.toFixed(1)}`
                    }
                }
            },
            scales: {
                x: { display: false },
                y: { display: false }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
    
    // Create sparklines for each metric
    const sparklineConfigs = [
        { id: 'sparkline-responses', data: metrics.responses, label: 'Responses' },
        { id: 'sparkline-nps', data: metrics.nps_score, label: 'NPS' },
        { id: 'sparkline-companies', data: metrics.companies, label: 'Companies' },
        { id: 'sparkline-critical', data: metrics.critical_risk, label: 'Critical Risk' },
        { id: 'sparkline-satisfaction', data: metrics.satisfaction, label: 'Satisfaction' },
        { id: 'sparkline-product', data: metrics.product_value, label: 'Product' },
        { id: 'sparkline-pricing', data: metrics.pricing, label: 'Pricing' },
        { id: 'sparkline-service', data: metrics.service, label: 'Service' }
    ];
    
    sparklineConfigs.forEach(config => {
        const canvas = document.getElementById(config.id);
        if (canvas) {
            const ctx = canvas.getContext('2d');
            sparklineCharts[config.id] = new Chart(ctx, createSparklineConfig(config.data, config.label));
        }
    });
    
    console.log('Sparklines created successfully');
}

// Open the KPI trends modal with full-size charts
function openTrendsModal() {
    if (!globalKpiData || globalKpiData.length === 0) {
        alert(translations.noCampaignDataAvailable);
        return;
    }
    
    // Show the modal using Bootstrap 5
    const modal = new bootstrap.Modal(document.getElementById('kpiTrendsModal'));
    modal.show();
    
    // Create full-size charts after modal is shown (needed for proper rendering)
    setTimeout(() => {
        createModalCharts(globalKpiData);
    }, 300);
}

// Create full-size trend charts in modal
function createModalCharts(kpiData) {
    // Destroy existing modal charts
    Object.values(modalCharts).forEach(chart => {
        if (chart) chart.destroy();
    });
    modalCharts = {};
    
    // Approved color palette
    const PRIMARY_RED = '#E13A44';
    const MEDIUM_GRAY = '#BDBDBD';
    const BLACK = '#000000';
    
    // Extract data for each metric
    const metrics = {
        responses: kpiData.map(row => row.responses),
        nps_score: kpiData.map(row => row.nps_score),
        companies: kpiData.map(row => row.companies),
        critical_risk: kpiData.map(row => row.critical_risk),
        satisfaction: kpiData.map(row => row.satisfaction),
        product_value: kpiData.map(row => row.product_value),
        pricing: kpiData.map(row => row.pricing),
        service: kpiData.map(row => row.service)
    };
    
    // Campaign labels with end dates (Month Year)
    const labels = kpiData.map(row => {
        if (row.end_date) {
            const date = new Date(row.end_date);
            const monthYear = date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
            return `${row.name}\n(${monthYear})`;
        }
        return row.name;
    });
    
    // Common chart configuration for modal
    const createModalChartConfig = (data, label, yAxisLabel) => ({
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: yAxisLabel,
                data: data,
                borderColor: PRIMARY_RED,
                backgroundColor: 'rgba(225, 58, 68, 0.1)',
                borderWidth: 3,
                pointRadius: 5,
                pointHoverRadius: 7,
                pointBackgroundColor: PRIMARY_RED,
                pointBorderColor: '#FFFFFF',
                pointBorderWidth: 2,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { 
                    display: true,
                    labels: {
                        color: BLACK,
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#FFFFFF',
                    bodyColor: '#FFFFFF',
                    borderColor: MEDIUM_GRAY,
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        label: (context) => `${yAxisLabel}: ${context.parsed.y.toFixed(1)}`
                    }
                }
            },
            scales: {
                x: { 
                    display: true,
                    grid: { color: '#E9E8E4' },
                    ticks: { color: BLACK }
                },
                y: { 
                    display: true,
                    grid: { color: '#E9E8E4' },
                    ticks: { color: BLACK },
                    beginAtZero: true
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
    
    // Create modal charts
    const modalChartConfigs = [
        { id: 'modal-chart-responses', data: metrics.responses, label: 'Responses', yLabel: 'Total Responses' },
        { id: 'modal-chart-nps', data: metrics.nps_score, label: 'NPS', yLabel: 'NPS Score' },
        { id: 'modal-chart-companies', data: metrics.companies, label: 'Companies', yLabel: 'Companies Analyzed' },
        { id: 'modal-chart-critical', data: metrics.critical_risk, label: 'Critical Risk', yLabel: 'Critical Risk Count' },
        { id: 'modal-chart-satisfaction', data: metrics.satisfaction, label: 'Satisfaction', yLabel: 'Satisfaction Rating' },
        { id: 'modal-chart-product', data: metrics.product_value, label: 'Product', yLabel: 'Product Value Rating' },
        { id: 'modal-chart-pricing', data: metrics.pricing, label: 'Pricing', yLabel: 'Pricing Rating' },
        { id: 'modal-chart-service', data: metrics.service, label: 'Service', yLabel: 'Service Rating' }
    ];
    
    modalChartConfigs.forEach(config => {
        const canvas = document.getElementById(config.id);
        if (canvas) {
            const ctx = canvas.getContext('2d');
            modalCharts[config.id] = new Chart(ctx, createModalChartConfig(config.data, config.label, config.yLabel));
        }
    });
    
    console.log('Modal charts created successfully');
}

function refreshData() {
    loadDashboardData().catch(error => {
        console.error('Dashboard reload after tab switch failed:', error);
    });
    loadCompanyNpsData();
}

function exportData() {
    // Use business authentication - server will handle authorization
    console.log('Attempting to export data...');
    
    fetch('/api/export_data', {
        method: 'GET',
        credentials: 'include'  // Include session cookies for business authentication
    })
    .then(response => {
        console.log('Export response received:', response.status, response.statusText);
        
        if (response.status === 403) {
            alert('Admin access required. Please log in to your business account.');
            // Redirect to business login for authentication
            window.location.href = '/business/login';
            return null;
        }
        if (response.status === 401) {
            alert('Authentication required. Please log in to your business account.');
            // Redirect to business login for authentication
            window.location.href = '/business/login';
            return null;
        }
        if (!response.ok) {
            // Get error message from response if available
            return response.text().then(text => {
                console.error('Error response body:', text);
                try {
                    const err = JSON.parse(text);
                    throw new Error(err.error || `HTTP error! status: ${response.status}`);
                } catch(e) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
            });
        }
        
        // Clone response to read it twice (once for logging, once for parsing)
        return response.clone().text().then(text => {
            console.log('Response size:', text.length, 'characters');
            try {
                return JSON.parse(text);
            } catch(e) {
                console.error('JSON parse error:', e);
                console.error('Response text preview:', text.substring(0, 500));
                throw new Error('Failed to parse server response as JSON. The data might be too large.');
            }
        });
    })
    .then(result => {
        if (!result) return; // Authentication failed
        
        console.log('Export data received, total responses:', result.data?.length || 0);
        
        const data = result.data || result; // Handle both old and new format
        const dataStr = JSON.stringify(data, null, 2);
        
        // Use Blob instead of data URI to avoid size limitations
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const exportFileDefaultName = `voc_survey_data_${new Date().toISOString().split('T')[0]}.json`;
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', url);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
        
        // Clean up the URL object after download
        setTimeout(() => URL.revokeObjectURL(url), 100);
        
        // Show success message if we have export info
        if (result.export_info) {
            console.log(`Data exported successfully by ${result.export_info.exported_by}`);
            alert(`Export successful! ${result.export_info.total_responses} responses exported.`);
        }
    })
    .catch(error => {
        console.error('Error exporting data:', error);
        alert(`Error exporting data: ${error.message}\n\nPlease check the browser console for details or contact administrator.`);
    });
}

// Export user-specific data (current user's responses only)
function exportUserData() {
    // This function works based on server-side session, no client-side auth needed
    
    fetch('/api/export_user_data', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (response.status === 400) {
            // Need to get email from user
            return response.json().then(data => {
                if (data.code === 'EMAIL_REQUIRED') {
                    const email = prompt('Please enter your email address to export your survey responses:');
                    if (!email) return null;
                    
                    // Retry with email
                    return fetch('/api/export_user_data', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ email: email })
                    })
                    .then(retryResponse => {
                        if (retryResponse.status === 404) {
                            alert('No survey responses found for this email address.');
                            return null;
                        }
                        if (!retryResponse.ok) {
                            throw new Error(`HTTP error! status: ${retryResponse.status}`);
                        }
                        return retryResponse.json();
                    });
                }
                throw new Error(data.message || 'Unknown error');
            });
        }
        if (response.status === 404) {
            alert('No survey responses found for your email address.');
            return null;
        }
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(result => {
        if (!result) return; // No data found
        
        const data = result.data || result;
        const dataStr = JSON.stringify(data, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
        
        const exportFileDefaultName = `my_survey_responses_${new Date().toISOString().split('T')[0]}.json`;
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
        
        console.log('User response data exported successfully');
    })
    .catch(error => {
        console.error('Error exporting user data:', error);
        alert('Error exporting your response data. Please try again.');
    });
}

// Business authentication redirect function
function redirectToBusinessLogin() {
    window.location.href = '/business/login';
}






// Auto-refresh dashboard every 1 hour
setInterval(refreshData, 60 * 60 * 1000);








// Business logout function
function businessLogout() {
    window.location.href = '/business/logout';
}

// Removed duplicate DOMContentLoaded listener - campaign initialization
// is now handled in the main DOMContentLoaded at line ~431 after translations load


















// Utility functions
function formatDate(dateString) {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function showSuccessMessage(message) {
    // Create a temporary alert
    const alert = document.createElement('div');
    alert.className = 'alert alert-success alert-dismissible fade show position-fixed';
    alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
    alert.innerHTML = `
        <i class="fas fa-check-circle me-2"></i>${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.parentNode.removeChild(alert);
        }
    }, 5000);
}

function showErrorMessage(message) {
    // Create a temporary alert
    const alert = document.createElement('div');
    alert.className = 'alert alert-danger alert-dismissible fade show position-fixed';
    alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
    alert.innerHTML = `
        <i class="fas fa-exclamation-circle me-2"></i>${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alert);
    
    // Auto-remove after 8 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.parentNode.removeChild(alert);
        }
    }, 8000);
}

// Add campaign management to tab listeners
function setupTabEventListeners() {
    // Get all tab buttons
    const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
    
    tabButtons.forEach(button => {
        button.addEventListener('shown.bs.tab', function (event) {
            const targetTab = event.target.getAttribute('data-bs-target');
            console.log('Tab shown:', targetTab);
            
            // Re-initialize charts when Analytics tab is shown - immediate rendering
            if (targetTab === '#analytics') {
                createSentimentChart();
                createRatingsChart();
                createTenureChart();
                createGrowthFactorChart();
            }
            
            // Re-initialize NPS donut and themes chart when Overview tab is shown - immediate rendering
            if (targetTab === '#overview') {
                createNpsChart();
                createThemesChart();
            }
            
            // Campaign management access will be handled by server-side business authentication
        });
    });
}






// ============================================================================
// SURVEY RESPONSES SEARCH FUNCTIONALITY
// ============================================================================

function getCurrentSearchQuery() {
    const searchInput = document.getElementById('responsesSearch');
    return searchInput ? searchInput.value.trim() : '';
}

function getCurrentNpsFilter() {
    const npsFilter = document.getElementById('npsFilter');
    return npsFilter ? npsFilter.value : '';
}

// ============================================================================
// COMPANY NPS SEARCH FUNCTIONALITY
// ============================================================================

function getCurrentCompanySearch() {
    const searchInput = document.getElementById('companySearch');
    return searchInput ? searchInput.value.trim() : '';
}

function getCurrentCompanyNpsFilter() {
    const npsFilter = document.getElementById('companyNpsFilter');
    return npsFilter ? npsFilter.value : '';
}

function searchCompanyNPS() {
    const searchQuery = getCurrentCompanySearch();
    const npsFilter = getCurrentCompanyNpsFilter();
    
    // Reset to page 1 when performing a new search
    currentCompanyPage = 1;
    
    // Load company data with search query and NPS filter
    loadCompanyNpsData(1, searchQuery, npsFilter);
    
    // Update search info
    let infoText = '';
    if (searchQuery && npsFilter) {
        const filterLabel = {
            'promoters': 'Promoters (9-10)',
            'passives': 'Passives (7-8)',
            'detractors': 'Detractors (0-6)'
        }[npsFilter] || npsFilter;
        infoText = `Search: "${searchQuery}" | Category: ${filterLabel}`;
    } else if (searchQuery) {
        infoText = `Search: "${searchQuery}"`;
    } else if (npsFilter) {
        const filterLabel = {
            'promoters': 'Promoters (9-10)',
            'passives': 'Passives (7-8)',
            'detractors': 'Detractors (0-6)'
        }[npsFilter] || npsFilter;
        infoText = `Category: ${filterLabel}`;
    }
    const infoElement = document.getElementById('companySearchInfo');
    if (infoElement) {
        infoElement.textContent = infoText;
    }
}

function clearCompanySearch() {
    const searchInput = document.getElementById('companySearch');
    if (searchInput) {
        searchInput.value = '';
    }
    
    const npsFilter = document.getElementById('companyNpsFilter');
    if (npsFilter) {
        npsFilter.value = '';
    }
    
    const infoElement = document.getElementById('companySearchInfo');
    if (infoElement) {
        infoElement.textContent = '';
    }
    
    // Reset to page 1 and clear search
    currentCompanyPage = 1;
    
    // Load company data without search or filter
    loadCompanyNpsData(1, '', '');
}

function searchSurveyResponses() {
    const searchQuery = getCurrentSearchQuery();
    const npsFilter = getCurrentNpsFilter();
    
    // Reset to page 1 when performing a new search
    currentResponsesPage = 1;
    
    // Load responses with search query and NPS filter
    loadSurveyResponses(1, searchQuery, npsFilter);
    
    // Update search info
    let infoText = '';
    if (searchQuery && npsFilter) {
        const filterLabel = {
            'promoters': 'Promoters (9-10)',
            'passives': 'Passives (7-8)',
            'detractors': 'Detractors (0-6)'
        }[npsFilter] || npsFilter;
        infoText = `Search: "${searchQuery}" | Category: ${filterLabel}`;
    } else if (searchQuery) {
        infoText = `Search: "${searchQuery}"`;
    } else if (npsFilter) {
        const filterLabel = {
            'promoters': 'Promoters (9-10)',
            'passives': 'Passives (7-8)',
            'detractors': 'Detractors (0-6)'
        }[npsFilter] || npsFilter;
        infoText = `Category: ${filterLabel}`;
    }
    const infoElement = document.getElementById('responsesSearchInfo');
    if (infoElement) {
        infoElement.textContent = infoText;
    }
}

function clearResponsesSearch() {
    const searchInput = document.getElementById('responsesSearch');
    if (searchInput) {
        searchInput.value = '';
    }
    
    const npsFilter = document.getElementById('npsFilter');
    if (npsFilter) {
        npsFilter.value = '';
    }
    
    const infoElement = document.getElementById('responsesSearchInfo');
    if (infoElement) {
        infoElement.textContent = '';
    }
    
    // Reset to page 1 and clear search
    currentResponsesPage = 1;
    
    // Load responses without search or filter
    loadSurveyResponses(1, '', '');
}

// Add Enter key support for search inputs
document.addEventListener('DOMContentLoaded', function() {
    const responsesSearchInput = document.getElementById('responsesSearch');
    if (responsesSearchInput) {
        responsesSearchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchSurveyResponses();
            }
        });
    }
    
    const companySearchInput = document.getElementById('companySearch');
    if (companySearchInput) {
        companySearchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchCompanyNPS();
            }
        });
    }
    
    const comparisonSearchInput = document.getElementById('comparisonSearch');
    if (comparisonSearchInput) {
        comparisonSearchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchComparisonTable();
            }
        });
    }
});

// ============================================================================
// COMPANY RESPONSES DRILL-DOWN
// ============================================================================

let companyResponsesState = {
    companyName: null,
    campaignId: null,
    campaignName: null,
    page: 1,
    search: '',
    sortBy: 'created_at',
    sortOrder: 'desc'
};

function openCompanyResponsesModal(companyName, campaignId, campaignName) {
    // Navigate to dedicated company responses page instead of modal (better for mobile)
    const url = `/dashboard/company-responses/${encodeURIComponent(companyName)}?campaign=${campaignId}`;
    window.location.href = url;
}

// Legacy modal function kept for compatibility
function openCompanyResponsesModalLegacy(companyName, campaignId, campaignName) {
    // Store state
    companyResponsesState.companyName = companyName;
    companyResponsesState.campaignId = campaignId;
    companyResponsesState.campaignName = campaignName;
    companyResponsesState.page = 1;
    companyResponsesState.search = '';
    
    // Update modal header
    document.getElementById('modalCompanyName').textContent = companyName;
    document.getElementById('modalCampaignName').textContent = campaignName;
    
    // Reset UI
    document.getElementById('companyResponseSearch').value = '';
    document.getElementById('companyResponseSort').value = 'created_at_desc';
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('companyResponsesModal'));
    modal.show();
    
    // Load data
    loadCompanyResponses();
}

async function loadCompanyResponses() {
    const { companyName, campaignId, page, search, sortBy, sortOrder } = companyResponsesState;
    
    // Show loading state
    document.getElementById('companyResponsesLoading').style.display = 'block';
    document.getElementById('companyResponsesContent').style.display = 'none';
    document.getElementById('companyResponsesNoData').style.display = 'none';
    
    try {
        // Build URL with parameters
        const params = new URLSearchParams({
            page: page,
            per_page: 20,
            sort_by: sortBy,
            sort_order: sortOrder
        });
        
        if (search) {
            params.append('search', search);
        }
        
        const url = `/api/campaigns/${campaignId}/companies/${encodeURIComponent(companyName)}/responses?${params}`;
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error('Failed to load company responses');
        }
        
        const data = await response.json();
        
        // Hide loading state
        document.getElementById('companyResponsesLoading').style.display = 'none';
        
        if (data.responses && data.responses.length > 0) {
            // Show content
            document.getElementById('companyResponsesContent').style.display = 'block';
            
            // Update response count badge
            document.getElementById('modalResponseCount').textContent = data.pagination.total_count;
            
            // Render table and pagination
            renderCompanyResponsesTable(data.responses);
            renderCompanyResponsesPagination(data.pagination);
        } else {
            // Show no data state
            document.getElementById('companyResponsesNoData').style.display = 'block';
        }
        
    } catch (error) {
        console.error('Error loading company responses:', error);
        document.getElementById('companyResponsesLoading').style.display = 'none';
        document.getElementById('companyResponsesNoData').style.display = 'block';
    }
}

function renderCompanyResponsesTable(responses) {
    const tbody = document.getElementById('companyResponsesTableBody');
    tbody.innerHTML = '';
    
    responses.forEach(response => {
        const row = document.createElement('tr');
        
        // Respondent name
        const nameCell = document.createElement('td');
        nameCell.textContent = response.respondent_name || 'N/A';
        row.appendChild(nameCell);
        
        // NPS Score with color coding
        const npsCell = document.createElement('td');
        npsCell.style.textAlign = 'center';
        const npsScore = response.nps_score;
        let npsBadgeClass = 'bg-secondary';
        if (npsScore >= 9) npsBadgeClass = 'bg-success';
        else if (npsScore >= 7) npsBadgeClass = 'bg-warning';
        else npsBadgeClass = 'bg-danger';
        npsCell.innerHTML = `<span class="badge ${npsBadgeClass}">${npsScore}</span>`;
        row.appendChild(npsCell);
        
        // Ratings (Satisfaction, Product Value, Service, Pricing)
        const ratingsCell = document.createElement('td');
        ratingsCell.style.textAlign = 'center';
        const ratings = [];
        
        if (response.satisfaction_rating) {
            ratings.push(`<span class="badge bg-info me-1" title="${translations.satisfactionBadge}">S: ${response.satisfaction_rating}/10</span>`);
        }
        if (response.product_value_rating) {
            ratings.push(`<span class="badge bg-info me-1" title="${translations.valueBadge}">V: ${response.product_value_rating}/10</span>`);
        }
        if (response.service_rating) {
            ratings.push(`<span class="badge bg-info me-1" title="${translations.serviceBadge}">Svc: ${response.service_rating}/10</span>`);
        }
        if (response.pricing_rating) {
            ratings.push(`<span class="badge bg-info me-1" title="${translations.pricingBadge}">P: ${response.pricing_rating}/10</span>`);
        }
        
        ratingsCell.innerHTML = ratings.length > 0 ? ratings.join(' ') : '<span class="text-muted">No ratings</span>';
        row.appendChild(ratingsCell);
        
        // Date
        const dateCell = document.createElement('td');
        if (response.created_at) {
            const date = new Date(response.created_at);
            dateCell.textContent = date.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric' 
            });
        } else {
            dateCell.textContent = 'N/A';
        }
        row.appendChild(dateCell);
        
        // Action - Link to full response (respecting authentication rules)
        const actionCell = document.createElement('td');
        actionCell.style.textAlign = 'center';
        
        // Use backend-provided can_view flag to determine access
        const canView = response.can_view !== undefined ? response.can_view : false;
        
        if (canView) {
            // User can view this response
            const link = document.createElement('a');
            link.href = `/survey-response/${encodeURIComponent(response.id)}`;
            link.className = 'btn btn-sm btn-outline-primary';
            link.title = translations.viewFullResponse || '';
            const icon = document.createElement('i');
            icon.className = 'fas fa-eye';
            link.appendChild(icon);
            actionCell.appendChild(link);
        } else {
            // User cannot view this response - authentication required
            const span = document.createElement('span');
            span.className = 'text-muted';
            span.title = translations.authenticationRequired || '';
            const icon = document.createElement('i');
            icon.className = 'fas fa-lock';
            span.appendChild(icon);
            actionCell.appendChild(span);
        }
        
        row.appendChild(actionCell);
        
        tbody.appendChild(row);
    });
}

function renderCompanyResponsesPagination(pagination) {
    const { page, total_pages, total_count, has_prev, has_next } = pagination;
    
    // Update info text
    const start = (page - 1) * pagination.per_page + 1;
    const end = Math.min(page * pagination.per_page, total_count);
    document.getElementById('companyResponsesPaginationInfo').textContent = 
        `Showing ${start}-${end} of ${total_count} responses`;
    
    // Render pagination controls
    const paginationEl = document.getElementById('companyResponsesPagination');
    paginationEl.innerHTML = '';
    
    // Previous button
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${!has_prev ? 'disabled' : ''}`;
    prevLi.innerHTML = `<a class="page-link" href="#" onclick="companyResponsesChangePage(${page - 1}); return false;">Previous</a>`;
    paginationEl.appendChild(prevLi);
    
    // Page numbers (show max 5 pages)
    const maxPagesToShow = 5;
    let startPage = Math.max(1, page - Math.floor(maxPagesToShow / 2));
    let endPage = Math.min(total_pages, startPage + maxPagesToShow - 1);
    
    // Adjust startPage if we're near the end
    if (endPage - startPage < maxPagesToShow - 1) {
        startPage = Math.max(1, endPage - maxPagesToShow + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const pageLi = document.createElement('li');
        pageLi.className = `page-item ${i === page ? 'active' : ''}`;
        pageLi.innerHTML = `<a class="page-link" href="#" onclick="companyResponsesChangePage(${i}); return false;">${i}</a>`;
        paginationEl.appendChild(pageLi);
    }
    
    // Next button
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${!has_next ? 'disabled' : ''}`;
    nextLi.innerHTML = `<a class="page-link" href="#" onclick="companyResponsesChangePage(${page + 1}); return false;">Next</a>`;
    paginationEl.appendChild(nextLi);
}

function companyResponsesChangePage(newPage) {
    companyResponsesState.page = newPage;
    loadCompanyResponses();
}

function companyResponsesSearch() {
    const searchValue = document.getElementById('companyResponseSearch').value.trim();
    companyResponsesState.search = searchValue;
    companyResponsesState.page = 1; // Reset to first page
    loadCompanyResponses();
}

function companyResponsesSort() {
    const sortValue = document.getElementById('companyResponseSort').value;
    const [sortBy, sortOrder] = sortValue.split('_');
    companyResponsesState.sortBy = sortBy;
    companyResponsesState.sortOrder = sortOrder;
    companyResponsesState.page = 1; // Reset to first page
    loadCompanyResponses();
}

// Event listeners for search and sort
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('companyResponseSearch');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                companyResponsesSearch();
            }
        });
        
        // Debounced search on input
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(companyResponsesSearch, 500);
        });
    }
    
    const sortSelect = document.getElementById('companyResponseSort');
    if (sortSelect) {
        sortSelect.addEventListener('change', companyResponsesSort);
    }
});

// Cache bust: 1759630893
