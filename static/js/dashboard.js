// Dashboard JavaScript functionality

let dashboardData = null;
let charts = {};
let campaignData = null;
let availableCampaigns = [];
let selectedCampaignId = null;

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

// Force yellow color override function
function forceRemoveYellowColors() {
    console.log('Running yellow color override...');
    
    // Target ALL possible warning elements on the entire page
    const yellowSelectors = [
        '.text-warning', '.bg-warning', '.border-warning', '.badge.bg-warning',
        '.btn-warning', '.btn-outline-warning', '.alert-warning',
        '.fa-exclamation-triangle', '.fas.fa-exclamation-triangle',
        '[class*="warning"]'
    ];
    
    yellowSelectors.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        console.log(`Found ${elements.length} elements with selector ${selector}`);
        elements.forEach(el => {
            // Force inline styles that override everything
            if (el.classList.contains('fa-exclamation-triangle') || el.classList.contains('fas')) {
                el.style.setProperty('color', '#E13A44', 'important');
                console.log('Fixed icon color');
            } else if (el.classList.contains('bg-warning') || el.classList.contains('badge')) {
                el.style.setProperty('background-color', '#BDBDBD', 'important');
                el.style.setProperty('color', '#000000', 'important');
                el.style.setProperty('border-color', '#BDBDBD', 'important');
                console.log('Fixed badge/background color');
            } else if (el.classList.contains('text-warning')) {
                el.style.setProperty('color', '#E13A44', 'important');
                console.log('Fixed text color');
            } else if (el.classList.contains('border-warning')) {
                el.style.setProperty('border-color', '#BDBDBD', 'important');
                console.log('Fixed border color');
            } else {
                // Generic warning class
                el.style.setProperty('color', '#E13A44', 'important');
                el.style.setProperty('background-color', '#BDBDBD', 'important');
                el.style.setProperty('border-color', '#BDBDBD', 'important');
                console.log('Fixed generic warning');
            }
        });
    });
}

// ============================================================================
// CAMPAIGN ANALYTICS FILTERING
// ============================================================================

// Load campaign options for analytics filtering
async function loadCampaignFilterOptions() {
    try {
        const response = await fetch('/api/campaigns/filter-options');
        if (response.ok) {
            const data = await response.json();
            availableCampaigns = data.campaigns;
            populateCampaignFilterDropdown();
        }
    } catch (error) {
        console.error('Error loading campaign filter options:', error);
    }
}

// Update active campaign banner display
function updateActiveCampaignBanner(data) {
    const banner = document.getElementById('activeCampaignBanner');
    const nameSpan = document.getElementById('activeCampaignName');
    const datesSpan = document.getElementById('activeCampaignDates');
    
    if (data.active_campaign && banner && nameSpan && datesSpan) {
        nameSpan.textContent = data.active_campaign.name;
        datesSpan.textContent = `${formatDate(data.active_campaign.start_date)} - ${formatDate(data.active_campaign.end_date)}`;
        banner.style.display = 'block';
        console.log('Active campaign banner displayed:', data.active_campaign.name);
    } else if (banner) {
        banner.style.display = 'none';
        console.log('Active campaign banner hidden - showing all data');
    }
}

// Populate campaign filter dropdown
function populateCampaignFilterDropdown() {
    const select = document.getElementById('campaignFilter');
    if (!select) return;
    
    // Clear existing options except "All Campaigns"
    select.innerHTML = '<option value="">All Campaigns</option>';
    
    // Add campaign options
    availableCampaigns.forEach(campaign => {
        const option = document.createElement('option');
        option.value = campaign.id;
        option.textContent = `${campaign.name} (${formatDate(campaign.start_date)} - ${formatDate(campaign.end_date)})`;
        option.setAttribute('data-name', campaign.name);
        option.setAttribute('data-start', campaign.start_date);
        option.setAttribute('data-end', campaign.end_date);
        select.appendChild(option);
    });
}

// Apply campaign filter to analytics
async function applyCampaignFilter() {
    const select = document.getElementById('campaignFilter');
    selectedCampaignId = select.value ? parseInt(select.value) : null;
    
    // Update selected campaign info display
    updateSelectedCampaignInfo();
    
    // Reload dashboard data with campaign filter
    await loadDashboardData();
    
    // Refresh all charts in Analytics tab
    setTimeout(() => {
        createNpsChart();
        createSentimentChart();
        createRatingsChart();
        createTenureChart();
        createGrowthFactorChart();
    }, 100);
}

// Clear campaign filter
function clearCampaignFilter() {
    document.getElementById('campaignFilter').value = '';
    applyCampaignFilter();
}

// Update selected campaign info display
function updateSelectedCampaignInfo() {
    const infoDiv = document.getElementById('selectedCampaignInfo');
    const select = document.getElementById('campaignFilter');
    
    if (selectedCampaignId && select.selectedOptions.length > 0) {
        const option = select.selectedOptions[0];
        const campaignName = option.getAttribute('data-name');
        const startDate = option.getAttribute('data-start');
        const endDate = option.getAttribute('data-end');
        
        // Find full campaign data for description
        const campaign = availableCampaigns.find(c => c.id === selectedCampaignId);
        
        document.getElementById('selectedCampaignName').textContent = campaignName;
        document.getElementById('selectedCampaignDates').textContent = 
            `${formatDate(startDate)} - ${formatDate(endDate)}`;
        document.getElementById('selectedCampaignDesc').textContent = 
            campaign?.description || 'No description available';
        
        infoDiv.style.display = 'block';
    } else {
        infoDiv.style.display = 'none';
    }
}

// Update active campaign banner display
function updateActiveCampaignBanner(data) {
    const banner = document.getElementById('activeCampaignBanner');
    const nameSpan = document.getElementById('activeCampaignName');
    const datesSpan = document.getElementById('activeCampaignDates');
    
    if (data.active_campaign && banner && nameSpan && datesSpan) {
        nameSpan.textContent = data.active_campaign.name;
        datesSpan.textContent = `${formatDate(data.active_campaign.start_date)} - ${formatDate(data.active_campaign.end_date)}`;
        banner.style.display = 'block';
        console.log('Active campaign banner displayed:', data.active_campaign.name);
    } else if (banner) {
        banner.style.display = 'none';
        console.log('Active campaign banner hidden - showing all data');
    }
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard JavaScript loaded and DOM ready');
    
    // Force remove yellow colors immediately
    forceRemoveYellowColors();
    
    // Immediate fallback for company NPS data
    setTimeout(function() {
        console.log('Fallback: Loading company NPS data directly');
        loadCompanyNpsDataDirect();
    }, 1000);
    
    loadDashboardData();
    
    // Check admin status on page load
    checkAdminStatus();
    
    // Run color override multiple times to catch dynamically loaded content
    setTimeout(forceRemoveYellowColors, 100);
    setTimeout(forceRemoveYellowColors, 500);
    setTimeout(forceRemoveYellowColors, 1000);
    setTimeout(forceRemoveYellowColors, 2000);
    setTimeout(forceRemoveYellowColors, 5000);
});

// Direct company NPS data loading as fallback
function loadCompanyNpsDataDirect() {
    console.log('Direct loading of company NPS data...');
    
    // Check if we're in the Survey Insights tab or if element exists
    const tbody = document.getElementById('companyNpsTable');
    if (!tbody) {
        console.log('companyNpsTable element not found - probably in different tab, skipping...');
        return;
    }
    
    fetch('/api/company_nps')
        .then(response => response.json())
        .then(data => {
            console.log('Direct API response:', data);
            if (data.success && data.data) {
                console.log('Found table, populating with', data.data.length, 'companies');
                tbody.innerHTML = data.data.map(company => `
                    <tr>
                        <td><strong>${company.company_name}</strong></td>
                        <td>${company.total_responses}</td>
                        <td>${company.avg_nps}</td>
                        <td><span class="badge bg-primary">${company.company_nps}</span></td>
                        <td><small>${company.promoters}P / ${company.passives}Pa / ${company.detractors}D</small></td>
                        <td><span class="badge" style="background-color: #8A8A8A; color: white;">${company.risk_level}</span></td>
                        <td>${company.latest_response || 'N/A'}</td>
                        <td>${company.latest_churn_risk || 'N/A'}</td>
                    </tr>
                `).join('');
            }
        })
        .catch(error => {
            console.error('Direct loading error:', error);
        });
}

function loadDashboardData() {
    console.log('loadDashboardData called');
    const loadingElement = document.getElementById('loadingIndicator');
    const contentElement = document.getElementById('dashboardContent');
    
    if (loadingElement) loadingElement.classList.remove('d-none');
    if (contentElement) contentElement.classList.add('d-none');
    
    // Build URL with campaign filter if selected
    let url = '/api/dashboard_data';
    if (selectedCampaignId) {
        url += `?campaign_id=${selectedCampaignId}`;
    }
    
    fetch(url)
        .then(response => {
            console.log('API response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Dashboard data received:', Object.keys(data));
            if (data.error) {
                throw new Error(data.error);
            }
            
            dashboardData = data;
            
            // Display active campaign banner if showing active campaign data
            updateActiveCampaignBanner(data);
            
            populateDashboard();
            
            if (loadingElement) loadingElement.classList.add('d-none');
            if (contentElement) contentElement.classList.remove('d-none');
        })
        .catch(error => {
            console.error('Error loading dashboard data:', error);
            if (loadingElement) {
                loadingElement.innerHTML = 
                    '<div class="alert alert-danger">Error loading dashboard data: ' + error.message + '</div>';
            }
        });
}

function populateDashboard() {
    console.log('populateDashboard called with data:', dashboardData);
    // Update key metrics
    document.getElementById('totalResponses').textContent = dashboardData.total_responses || 0;
    document.getElementById('npsScore').textContent = dashboardData.nps_score || 0;
    document.getElementById('recentResponses').textContent = dashboardData.recent_responses || 0;
    document.getElementById('highRiskCount').textContent = dashboardData.high_risk_accounts?.length || 0;
    
    // Growth potential as percentage
    const growthPotential = dashboardData.growth_factor_analysis?.total_growth_potential || 0;
    document.getElementById('growthPotential').textContent = Math.round(growthPotential * 100) + '%';
    
    // Only create charts for the active (Overview) tab initially
    // Other charts will be created when their tabs are shown
    createThemesChart();
    
    // Populate high risk accounts
    populateHighRiskAccounts();
    
    // Populate unified account intelligence
    populateAccountIntelligence();
    
    // Skip legacy functions that don't work with new tab structure
    // populateGrowthOpportunities(); // Removed - element doesn't exist in new tabs
    // populateAccountRiskFactors();  // Removed - element doesn't exist in new tabs
    
    // Load survey responses table
    loadSurveyResponses();
    
    // Load company NPS data
    console.log('About to call loadCompanyNpsData...');
    loadCompanyNpsData();
    
    // Load tenure NPS data
    console.log('About to call loadTenureNpsData...');
    loadTenureNpsData();
    
    // Set up tab event listeners for chart initialization
    setupTabEventListeners();
}

function setupTabEventListeners() {
    // Get all tab buttons
    const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
    
    tabButtons.forEach(button => {
        button.addEventListener('shown.bs.tab', function (event) {
            const targetTab = event.target.getAttribute('data-bs-target');
            console.log('Tab shown:', targetTab);
            
            // Re-initialize charts when Analytics tab is shown
            if (targetTab === '#analytics') {
                setTimeout(() => {
                    createNpsChart();
                    createSentimentChart();
                    createRatingsChart();
                    createTenureChart();
                    createGrowthFactorChart();
                }, 100);
            }
            
            // Re-initialize themes chart when Overview tab is shown
            if (targetTab === '#overview') {
                setTimeout(() => {
                    createThemesChart();
                }, 100);
            }
        });
    });
}

// ============================================================================
// CAMPAIGN ANALYTICS FILTERING
// ============================================================================

// Load campaign options for analytics filtering
async function loadCampaignFilterOptions() {
    try {
        const response = await fetch('/api/campaigns/filter-options');
        if (response.ok) {
            const data = await response.json();
            availableCampaigns = data.campaigns;
            populateCampaignFilterDropdown();
        }
    } catch (error) {
        console.error('Error loading campaign filter options:', error);
    }
}

// Update active campaign banner display
function updateActiveCampaignBanner(data) {
    const banner = document.getElementById('activeCampaignBanner');
    const nameSpan = document.getElementById('activeCampaignName');
    const datesSpan = document.getElementById('activeCampaignDates');
    
    if (data.active_campaign && banner && nameSpan && datesSpan) {
        nameSpan.textContent = data.active_campaign.name;
        datesSpan.textContent = `${formatDate(data.active_campaign.start_date)} - ${formatDate(data.active_campaign.end_date)}`;
        banner.style.display = 'block';
        console.log('Active campaign banner displayed:', data.active_campaign.name);
    } else if (banner) {
        banner.style.display = 'none';
        console.log('Active campaign banner hidden - showing all data');
    }
}

// Populate campaign filter dropdown

function populateCampaignFilterDropdown() {
    const select = document.getElementById("campaignFilter");
    if (!select) return;
    
    select.innerHTML = "<option value=\"\">All Campaigns</option>";
    
    availableCampaigns.forEach(campaign => {
        const option = document.createElement("option");
        option.value = campaign.id;
        option.textContent = `${campaign.name} (${formatDate(campaign.start_date)} - ${formatDate(campaign.end_date)})`;
        option.setAttribute("data-name", campaign.name);
        option.setAttribute("data-start", campaign.start_date);
        option.setAttribute("data-end", campaign.end_date);
        select.appendChild(option);
    });
}

async function applyCampaignFilter() {
    const select = document.getElementById("campaignFilter");
    selectedCampaignId = select.value ? parseInt(select.value) : null;
    
    updateSelectedCampaignInfo();
    await loadDashboardData();
    
    setTimeout(() => {
        createNpsChart();
        createSentimentChart();
        createRatingsChart();
        createTenureChart();
        createGrowthFactorChart();
    }, 100);
}

function clearCampaignFilter() {
    document.getElementById("campaignFilter").value = "";
    applyCampaignFilter();
}

function updateSelectedCampaignInfo() {
    const infoDiv = document.getElementById("selectedCampaignInfo");
    const select = document.getElementById("campaignFilter");
    
    if (selectedCampaignId && select.selectedOptions.length > 0) {
        const option = select.selectedOptions[0];
        const campaignName = option.getAttribute("data-name");
        const startDate = option.getAttribute("data-start");
        const endDate = option.getAttribute("data-end");
        const campaign = availableCampaigns.find(c => c.id === selectedCampaignId);
        
        document.getElementById("selectedCampaignName").textContent = campaignName;
        document.getElementById("selectedCampaignDates").textContent = 
            `${formatDate(startDate)} - ${formatDate(endDate)}`;
        document.getElementById("selectedCampaignDesc").textContent = 
            campaign?.description || "No description available";
        
        infoDiv.style.display = "block";
    } else {
        infoDiv.style.display = "none";
    }
}
