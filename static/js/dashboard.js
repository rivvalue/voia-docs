// Dashboard JavaScript functionality

// HTML escape function to prevent XSS vulnerabilities
function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

let dashboardData = null;
let charts = {};
let campaignData = null;
let availableCampaigns = [];
let selectedCampaignId = null;
let kpiOverviewData = null;

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

// Helper function to format campaign status for display
function formatCampaignStatus(status) {
    switch (status) {
        case 'draft':
            return 'Draft';
        case 'ready':
            return 'Ready';
        case 'active':
            return 'Active';
        case 'completed':
            return 'Completed';
        default:
            return 'Unknown';
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
    
    // Check for campaign_id URL parameter first
    const urlParams = new URLSearchParams(window.location.search);
    const urlCampaignId = urlParams.get('campaign_id');
    
    // Find default campaign: URL param > active campaign > most recent
    let defaultCampaign = null;
    
    if (urlCampaignId) {
        // If URL has campaign_id, use that
        defaultCampaign = availableCampaigns.find(c => c.id === parseInt(urlCampaignId));
        console.log('📌 Using campaign from URL parameter:', urlCampaignId, defaultCampaign);
    }
    
    if (!defaultCampaign) {
        // First, look for active campaign
        const activeCampaign = availableCampaigns.find(c => c.status === 'active');
        if (activeCampaign) {
            defaultCampaign = activeCampaign;
        } else {
            // If no active campaign, get the most recent (by end_date or created_at)
            const sortedCampaigns = [...availableCampaigns].sort((a, b) => {
                const dateA = new Date(a.end_date || a.created_at);
                const dateB = new Date(b.end_date || b.created_at);
                return dateB - dateA; // Most recent first
            });
            defaultCampaign = sortedCampaigns[0];
        }
    }
    
    // Add campaign options
    availableCampaigns.forEach(campaign => {
        const option = document.createElement('option');
        option.value = campaign.id;
        
        // Determine status
        const status = formatCampaignStatus(campaign.status);
        
        // Format option text with status
        option.textContent = `${campaign.name} (${formatDate(campaign.start_date)} - ${formatDate(campaign.end_date)}) - ${status}`;
        option.setAttribute('data-name', campaign.name);
        option.setAttribute('data-start', campaign.start_date);
        option.setAttribute('data-end', campaign.end_date);
        option.setAttribute('data-status', status);
        option.setAttribute('data-description', campaign.description || '');
        
        // Set as selected if this is the default campaign
        if (defaultCampaign && campaign.id === defaultCampaign.id) {
            option.selected = true;
            selectedCampaignId = campaign.id;
        }
        
        select.appendChild(option);
    });
    
    // Update the selected campaign info display for default selection
    if (defaultCampaign) {
        updateSelectedCampaignInfo();
        // Load dashboard data for default campaign
        loadDashboardData();
    }
}

// Apply campaign filter to analytics
async function applyCampaignFilter() {
    const select = document.getElementById('campaignFilter');
    selectedCampaignId = select.value ? parseInt(select.value) : null;
    
    console.log('🎯 Campaign filter applied:', selectedCampaignId);
    
    // Reload dashboard data with campaign filter
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

// Update selected campaign info display
function updateSelectedCampaignInfo() {
    const infoDiv = document.getElementById('selectedCampaignInfo');
    const select = document.getElementById('campaignFilter');
    
    if (selectedCampaignId && select.selectedOptions.length > 0) {
        const option = select.selectedOptions[0];
        const startDate = option.getAttribute('data-start');
        const endDate = option.getAttribute('data-end');
        const status = option.getAttribute('data-status');
        
        // Update dates badge text (inline, no container refresh)
        const datesText = document.querySelector('.campaign-dates-text');
        if (datesText) {
            datesText.textContent = `${formatDate(startDate)} - ${formatDate(endDate)}`;
        }
        
        // Update status badge with proper styling
        const statusBadge = document.getElementById('selectedCampaignStatus');
        const statusText = document.querySelector('.campaign-status-text');
        if (statusBadge && statusText) {
            statusText.textContent = status;
            if (status === 'Active') {
                statusBadge.style.backgroundColor = '#28a745';
                statusBadge.style.color = 'white';
            } else {
                statusBadge.style.backgroundColor = '#6c757d';
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
            
            const daysRemaining = status === 'Active' ? Math.max(0, diffDays) : 0;
            const daysSinceEnded = status === 'Closed' ? Math.max(0, -diffDays) : 0;
            
            if (status === 'Active' && daysRemaining >= 0) {
                if (daysRemaining > 30) {
                    daysText.textContent = `${daysRemaining} days left`;
                    daysLeftSpan.className = 'badge bg-success';
                } else if (daysRemaining > 7) {
                    daysText.textContent = `${daysRemaining} days left`;
                    daysLeftSpan.className = 'badge bg-warning';
                } else {
                    daysText.textContent = `${daysRemaining} days left`;
                    daysLeftSpan.className = 'badge bg-danger';
                }
                daysLeftSpan.style.display = '';
            } else if (status === 'Closed' && daysSinceEnded > 0) {
                if (daysSinceEnded < 30) {
                    daysText.textContent = `${daysSinceEnded} days ago`;
                } else if (daysSinceEnded < 365) {
                    const months = Math.floor(daysSinceEnded / 30);
                    daysText.textContent = `${months} month${months > 1 ? 's' : ''} ago`;
                } else {
                    const years = Math.floor(daysSinceEnded / 365);
                    daysText.textContent = `${years} year${years > 1 ? 's' : ''} ago`;
                }
                daysLeftSpan.className = 'badge bg-secondary';
                daysLeftSpan.style.display = '';
            } else {
                daysLeftSpan.style.display = 'none';
            }
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
    
    // Load campaign filter options first, then initial dashboard data
    loadCampaignFilterOptions().then(() => {
        // Only load dashboard data if no default campaign was auto-selected
        if (!selectedCampaignId) {
            loadDashboardData().catch(error => {
                console.error('Initial dashboard load failed:', error);
            });
        }
    });
    
    // Load campaign comparison options
    loadComparisonCampaignOptions();
    
    // Business authentication is handled server-side
    
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
    campaign1Select.innerHTML = '<option value="">Select first campaign</option>';
    campaign2Select.innerHTML = '<option value="">Select second campaign</option>';
    
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
    
    try {
        // Fetch comparison data
        const response = await fetch(`/api/campaigns/comparison?campaign1=${campaign1Id}&campaign2=${campaign2Id}`);
        if (!response.ok) {
            throw new Error('Failed to fetch comparison data');
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
                <h5 class="text-warning">Error Loading Comparison</h5>
                <p class="text-muted">Failed to load comparison data. Please try again.</p>
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
        if (balance === 'N/A') return 'N/A';
        return balance.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
    };
    
    paginatedCompanies.forEach(company => {
        const c1 = company.campaign1;
        const c2 = company.campaign2;
        
        // Helper function to display value or N/A
        const displayValue = (value) => {
            return (value === null || value === undefined) ? 'N/A' : value;
        };
        
        // Determine status - only compare if both campaigns have data
        let status = 'N/A';
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
        c1BalanceCell.textContent = c1.balance ? formatBalance(c1.balance) : 'N/A';
        
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
        c2BalanceCell.textContent = c2.balance ? formatBalance(c2.balance) : 'N/A';
        
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
        info.textContent = `Showing ${startItem}-${endItem} of ${totalItems} companies`;
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
    
    fetch('/api/company_nps')
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
                    responseCell.textContent = company.latest_response || 'N/A';
                    row.appendChild(responseCell);
                    
                    // Latest churn risk
                    const churnCell = document.createElement('td');
                    churnCell.textContent = company.latest_churn_risk || 'N/A';
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
                errorDiv.textContent = 'Error loading dashboard data: ' + error.message;
                
                // Clear loading element and append error
                loadingElement.innerHTML = '';
                loadingElement.appendChild(errorDiv);
            }
            // Re-throw error to maintain Promise chain behavior
            throw error;
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
    // Wait for Bootstrap tab rendering to complete
    setTimeout(() => createThemesChart(), 100);
    
    // Populate high risk accounts
    populateHighRiskAccounts();
    
    // Populate unified account intelligence via API (with pagination, search, filtering)
    loadAccountIntelligence();
    
    // Load KPI overview data (Executive Summary)
    loadKpiOverview();
    
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

// Helper function to get active campaign ID
function getActiveCampaignId() {
    // Find active campaign from available campaigns
    const activeCampaign = availableCampaigns.find(c => c.status === 'active');
    return activeCampaign ? activeCampaign.id : null;
}

// Note: setupTabEventListeners function is defined later in the file with full campaign management support

function createNpsChart() {
    const chartElement = document.getElementById('npsChart');
    if (!chartElement) {
        console.warn('NPS chart element not found');
        return;
    }
    
    const ctx = chartElement.getContext('2d');
    
    // Destroy existing chart if it exists
    if (charts.npsChart) {
        charts.npsChart.destroy();
    }
    
    const npsData = dashboardData.nps_distribution || [];
    const labels = npsData.map(item => item.category);
    const data = npsData.map(item => item.count);
    
    // Professional color palette matching the design
    const chartColors = ['#E13A44', '#BDBDBD', '#8A8A8A']; // Red (Detractor), Medium Gray (Passive), Dark Gray (Promoter)
    
    // Get mobile-responsive configuration
    const config = getMobileChartConfig();
    
    charts.npsChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: chartColors,
                borderWidth: 3,
                borderColor: '#FFFFFF',
                hoverBorderWidth: 4,
                hoverBorderColor: '#E13A44'
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
                    borderColor: '#E13A44',
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
                    }
                }
            },
            elements: {
                arc: {
                    borderRadius: 4
                }
            }
        }
    });
}

function createSentimentChart() {
    const chartElement = document.getElementById('sentimentChart');
    if (!chartElement) {
        console.warn('Sentiment chart element not found');
        return;
    }
    
    const ctx = chartElement.getContext('2d');
    
    // Destroy existing chart if it exists
    if (charts.sentimentChart) {
        charts.sentimentChart.destroy();
    }
    
    const sentimentData = dashboardData.sentiment_distribution || [];
    
    // Filter out items with missing sentiment data and add null checks
    const validSentimentData = sentimentData.filter(item => item.sentiment && typeof item.sentiment === 'string');
    
    if (validSentimentData.length === 0) {
        console.warn('No valid sentiment data available for chart');
        // Create empty chart with message
        charts.sentimentChart = new Chart(ctx, {
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
    const colors = ['#8A8A8A', '#BDBDBD', '#E13A44']; // Dark Gray (Positive), Medium Gray (Neutral), Red (Negative)
    
    // Get mobile-responsive configuration
    const config = getMobileChartConfig();
    
    charts.sentimentChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Responses',
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
        }
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
    console.log('Chart Data Debug - Full dashboardData:', dashboardData);
    console.log('Chart Data Debug - ratings object:', ratings);
    console.log('Chart Data Debug - individual values:', {
        satisfaction: ratings.satisfaction,
        product_value: ratings.product_value,
        service: ratings.service,
        pricing: ratings.pricing
    });
    
    const labels = ['Satisfaction', 'Product Value', 'Service', 'Pricing'];
    const data = [
        ratings.satisfaction || 0,
        ratings.product_value || 0,
        ratings.service || 0,
        ratings.pricing || 0
    ];
    
    console.log('Chart Data Debug - final data array:', data);
    console.log('Chart Data Debug - data types:', data.map(v => typeof v));
    
    // Get mobile-responsive configuration
    const config = getMobileChartConfig();
    
    charts.ratingsChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Rating',
                data: data,
                borderColor: '#E13A44',
                backgroundColor: 'rgba(225, 58, 68, 0.1)',
                borderWidth: 2,
                pointBackgroundColor: '#E13A44',
                pointBorderColor: '#FFFFFF',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: config.maintainAspectRatio,
            plugins: {
                legend: {
                    position: config.legendPosition,
                    labels: {
                        color: '#000000',
                        padding: config.legendPadding,
                        font: {
                            size: config.legendFontSize
                        }
                    }
                }
            },
            scales: {
                r: {
                    beginAtZero: true,
                    max: 5,
                    ticks: {
                        color: '#000000',
                        stepSize: 1,
                        font: {
                            size: config.fontSize
                        }
                    },
                    grid: {
                        color: '#BDBDBD'
                    },
                    pointLabels: {
                        color: '#000000',
                        font: {
                            size: config.fontSize
                        }
                    }
                }
            }
        }
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
    
    // Get mobile-responsive configuration
    const config = getMobileChartConfig();
    
    charts.themesChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Mentions',
                data: data,
                backgroundColor: '#BDBDBD',
                borderWidth: 1,
                borderColor: '#E9E8E4'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: config.maintainAspectRatio,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
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
}

function createTenureChart() {
    const chartElement = document.getElementById('tenureChart');
    if (!chartElement) {
        console.warn('Tenure chart element not found');
        return;
    }
    
    const ctx = chartElement.getContext('2d');
    
    // Destroy existing chart if it exists
    if (charts.tenure) {
        charts.tenure.destroy();
    }
    
    if (!dashboardData.tenure_distribution || dashboardData.tenure_distribution.length === 0) {
        ctx.canvas.parentNode.innerHTML = '<div class="alert alert-info">No tenure data available yet. This will populate as surveys are completed.</div>';
        return;
    }
    
    const labels = dashboardData.tenure_distribution.map(item => item.tenure);
    const data = dashboardData.tenure_distribution.map(item => item.count);
    
    // Get mobile-responsive configuration  
    const config = getMobileChartConfig();
    
    charts.tenure = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                label: 'Customers',
                data: data,
                backgroundColor: [
                    '#E13A44',
                    '#BDBDBD', 
                    '#E9E8E4',
                    '#000000',
                    'rgba(225, 58, 68, 0.6)'
                ],
                borderColor: '#FFFFFF',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: config.maintainAspectRatio,
            plugins: {
                legend: {
                    position: config.legendPosition,
                    labels: {
                        color: '#000000',
                        padding: config.legendPadding,
                        font: {
                            size: config.legendFontSize
                        }
                    }
                }
            }
        }
    });
}

function createGrowthFactorChart() {
    const chartElement = document.getElementById('growthFactorChart');
    if (!chartElement) {
        console.warn('Growth factor chart element not found');
        return;
    }
    
    const ctx = chartElement.getContext('2d');
    
    // Destroy existing chart if it exists
    if (charts.growthFactor) {
        charts.growthFactor.destroy();
    }
    
    if (!dashboardData.growth_factor_analysis || 
        !dashboardData.growth_factor_analysis.distribution || 
        dashboardData.growth_factor_analysis.distribution.length === 0) {
        ctx.canvas.parentNode.innerHTML = '<div class="alert alert-info">No growth factor data available yet. This will populate as surveys are completed.</div>';
        return;
    }
    
    const distribution = dashboardData.growth_factor_analysis.distribution;
    const labels = distribution.map(item => `${item.nps_range} (${item.growth_rate})`);
    const data = distribution.map(item => item.count);
    const colors = ['#E13A44', '#BDBDBD', '#E9E8E4', '#000000', '#FFFFFF'];
    
    // Get mobile-responsive configuration  
    const config = getMobileChartConfig();
    
    charts.growthFactor = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Customers',
                data: data,
                backgroundColor: colors.slice(0, data.length),
                borderColor: '#FFFFFF',
                borderWidth: 1
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
                    callbacks: {
                        afterLabel: function(context) {
                            const item = distribution[context.dataIndex];
                            return [`Growth Factor: ${item.avg_factor}`, `Expected Growth: ${item.growth_rate}`];
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#000000',
                        stepSize: 1,
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
        }
    });
}

function populateHighRiskAccounts() {
    const container = document.getElementById('highRiskAccounts');
    const highRiskAccounts = dashboardData.high_risk_accounts || [];
    
    if (highRiskAccounts.length === 0) {
        container.innerHTML = '<p class="text-muted">No high-risk accounts identified.</p>';
        return;
    }
    
    const html = highRiskAccounts.map(account => `
        <div class="risk-card p-3 mb-3 rounded">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h6 class="mb-1">${escapeHtml(account.company_name)}</h6>
                    <small class="text-muted">NPS Score: ${escapeHtml(account.nps_score)}</small>
                </div>
                <div class="text-end">
                    <span class="badge bg-danger">${escapeHtml(account.risk_level || 'High')} Risk</span>
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
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
        <div class="account-health-legend mb-4 p-3 rounded" style="background-color: #f8f9fa; border: 1px solid #dee2e6;">
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
                    <div class="account-details mb-3 p-2 rounded" style="background-color: #f8f9fa; border: 1px solid #dee2e6;">
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
    
    // FORCE override any yellow colors by applying inline styles
    setTimeout(() => {
        // Override any warning icons or badges that might still be yellow
        const warningElements = container.querySelectorAll('.text-warning, .bg-warning, .border-warning, .fa-exclamation-triangle, [class*="warning"]');
        warningElements.forEach(el => {
            if (el.classList.contains('fa-exclamation-triangle')) {
                el.style.color = '#E13A44';
            } else if (el.classList.contains('bg-warning')) {
                el.style.backgroundColor = '#BDBDBD';
                el.style.color = '#000000';
            } else if (el.classList.contains('text-warning')) {
                el.style.color = '#E13A44';
            } else if (el.classList.contains('border-warning')) {
                el.style.borderColor = '#BDBDBD';
            }
        });
        
        // Also check for any hardcoded yellow colors
        const allElements = container.querySelectorAll('*');
        allElements.forEach(el => {
            const computedStyle = window.getComputedStyle(el);
            const color = computedStyle.color;
            const backgroundColor = computedStyle.backgroundColor;
            const borderColor = computedStyle.borderColor;
            
            // If any yellow colors are detected, force change them
            if (color.includes('rgb(255, 193, 7)') || color.includes('#ffc107') || color.includes('#FFC107')) {
                el.style.color = '#E13A44';
            }
            if (backgroundColor.includes('rgb(255, 193, 7)') || backgroundColor.includes('#ffc107') || backgroundColor.includes('#FFC107')) {
                el.style.backgroundColor = '#BDBDBD';
            }
            if (borderColor.includes('rgb(255, 193, 7)') || borderColor.includes('#ffc107') || borderColor.includes('#FFC107')) {
                el.style.borderColor = '#BDBDBD';
            }
        });
    }, 100);
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
                container.innerHTML = '<div class="alert alert-danger">Error loading account intelligence</div>';
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
        <div class="account-health-legend mb-4 p-3 rounded" style="background-color: #f8f9fa; border: 1px solid #dee2e6;">
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
                    
                    <div class="account-details mb-3 p-2 rounded" style="background-color: #f8f9fa; border: 1px solid #dee2e6;">
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
            <a class="page-link" href="#" onclick="loadAccountIntelligence(${pagination.page - 1}); return false;" aria-label="Previous">
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
            <a class="page-link" href="#" onclick="loadAccountIntelligence(${pagination.page + 1}); return false;" aria-label="Next">
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
    countElement.textContent = `Showing ${start}-${end} of ${total} accounts`;
    
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
                const riskClass = riskLevel === 'High' ? 'risk-high' : 
                                 riskLevel === 'Medium' ? 'risk-medium' : 
                                 riskLevel === 'Low' ? 'risk-low' : 'risk-minimal';
                
                const sentimentClass = response.sentiment_label === 'positive' ? 'theme-positive' :
                                      response.sentiment_label === 'negative' ? 'theme-negative' : 'theme-neutral';
                
                // Use backend-provided can_view flag to determine access
                const canView = response.can_view !== undefined ? response.can_view : false;
                const detailsButton = canView ? 
                    `<a href="/survey-response/${response.id}" class="btn btn-outline-primary btn-sm" title="View Details">
                        <i class="fas fa-eye"></i>
                    </a>` :
                    `<span class="text-muted" title="Authentication required">
                        <i class="fas fa-lock"></i>
                    </span>`;
                
                return `
                    <tr>
                        <td>${escapeHtml(response.company_name)}</td>
                        <td>${escapeHtml(response.tenure_with_fc) || 'N/A'}</td>
                        <td>
                            <span class="badge ${response.nps_score >= 9 ? 'bg-success' : 
                                                response.nps_score >= 7 ? 'bg-secondary' : 'bg-danger'}">
                                ${escapeHtml(response.nps_score)}
                            </span>
                        </td>
                        <td>${escapeHtml(response.nps_category)}</td>
                        <td class="${sentimentClass}">${escapeHtml(response.sentiment_label) || 'N/A'}</td>
                        <td class="${riskClass}">
                            ${escapeHtml(riskLevel)}
                        </td>
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
                '<tr><td colspan="8" class="text-center text-danger">Error loading responses.</td></tr>';
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
        info.textContent = `Showing ${startItem}-${endItem} of ${totalItems} responses`;
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
        info.textContent = `Showing ${startItem}-${endItem} of ${totalItems} companies`;
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
        info.textContent = `Showing ${startItem}-${endItem} of ${totalItems} tenure groups`;
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
                '<tr><td colspan="8" class="text-center text-danger">Network error loading tenure data</td></tr>';
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
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No tenure data available yet</td></tr>';
        return;
    }
    
    console.log('Rendering', tenureData.length, 'tenure groups to table');
    
    tbody.innerHTML = tenureData.map(tenure => {
        // Risk level badge styling
        let riskBadgeClass = 'bg-secondary';
        if (tenure.risk_level === 'Low') riskBadgeClass = 'bg-success';
        else if (tenure.risk_level === 'Medium') riskBadgeClass = 'bg-secondary';
        else if (tenure.risk_level === 'High') riskBadgeClass = 'bg-danger';
        else if (tenure.risk_level === 'Critical') riskBadgeClass = 'bg-dark';
        else if (tenure.risk_level === 'Insufficient Data') riskBadgeClass = 'bg-secondary';
        
        // Tenure NPS badge styling
        let npsBadgeClass = 'bg-secondary';
        if (tenure.tenure_nps > 20) npsBadgeClass = 'bg-success';
        else if (tenure.tenure_nps >= -20) npsBadgeClass = 'bg-secondary'; 
        else npsBadgeClass = 'bg-danger';
        
        // Distribution breakdown
        const distributionText = `${tenure.promoters}P / ${tenure.passives}Pa / ${tenure.detractors}D`;
        
        // Churn risk display
        const churnRiskDisplay = tenure.latest_churn_risk || 'N/A';
        
        return `
            <tr>
                <td><strong>${escapeHtml(tenure.tenure_group)}</strong></td>
                <td>${escapeHtml(tenure.total_responses)}</td>
                <td>${escapeHtml(tenure.avg_nps)}</td>
                <td><span class="badge ${npsBadgeClass}">${tenure.tenure_nps > 0 ? '+' : ''}${escapeHtml(tenure.tenure_nps)}</span></td>
                <td><small>${distributionText}</small></td>
                <td><span class="badge ${riskBadgeClass}">${escapeHtml(tenure.risk_level)}</span></td>
                <td>${escapeHtml(tenure.latest_response) || 'N/A'}</td>
                <td>${escapeHtml(churnRiskDisplay)}</td>
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
                '<tr><td colspan="8" class="text-center text-danger">Network error loading company data</td></tr>';
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
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No company data available yet</td></tr>';
        return;
    }
    
    console.log('Rendering', companyData.length, 'companies to table');
    
    tbody.innerHTML = companyData.map(company => {
        // Risk level badge styling
        let riskBadgeClass = 'bg-secondary';
        if (company.risk_level === 'Low') riskBadgeClass = 'bg-success';
        else if (company.risk_level === 'Medium') riskBadgeClass = 'bg-secondary';
        else if (company.risk_level === 'High') riskBadgeClass = 'bg-danger';
        else if (company.risk_level === 'Critical') riskBadgeClass = 'bg-dark';
        
        // Company NPS badge styling
        let npsBadgeClass = 'bg-secondary';
        if (company.company_nps > 20) npsBadgeClass = 'bg-success';
        else if (company.company_nps >= -20) npsBadgeClass = 'bg-secondary'; 
        else npsBadgeClass = 'bg-danger';
        
        // Distribution breakdown
        const distributionText = `${company.promoters}P / ${company.passives}Pa / ${company.detractors}D`;
        
        // Churn risk display
        const churnRiskDisplay = company.latest_churn_risk || 'N/A';
        
        return `
            <tr>
                <td><strong>${escapeHtml(company.company_name)}</strong></td>
                <td>${escapeHtml(company.total_responses)}</td>
                <td>${escapeHtml(company.avg_nps)}</td>
                <td><span class="badge ${npsBadgeClass}">${company.company_nps > 0 ? '+' : ''}${escapeHtml(company.company_nps)}</span></td>
                <td><small>${distributionText}</small></td>
                <td><span class="badge ${riskBadgeClass}">${escapeHtml(company.risk_level)}</span></td>
                <td>${escapeHtml(company.latest_response) || 'N/A'}</td>
                <td>${escapeHtml(churnRiskDisplay)}</td>
            </tr>
        `;
    }).join('');
}

// Load KPI overview data for Executive Summary
async function loadKpiOverview() {
    console.log('Loading KPI overview data...');
    const tbody = document.getElementById('kpiOverviewTableBody');
    
    if (!tbody) {
        console.error('kpiOverviewTableBody element not found!');
        return;
    }
    
    try {
        // First, load available campaigns
        const campaignResponse = await fetch('/api/campaigns/filter-options');
        if (!campaignResponse.ok) {
            throw new Error('Failed to load campaign options');
        }
        
        const campaignData = await campaignResponse.json();
        const campaigns = campaignData.campaigns || [];
        
        if (campaigns.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No campaign data available</td></tr>';
            return;
        }
        
        // Build rows for each campaign with their individual KPI data
        let kpiRows = [];
        
        for (const campaign of campaigns) {
            // For each campaign, we'll extract KPI data from dashboard data or use comparison with self
            // This leverages the fact that comparison endpoint provides comprehensive KPI metrics
            
            let campaignKpis = null;
            
            // Try to get KPI data by calling comparison endpoint with same campaign twice
            if (campaigns.length >= 1) {
                try {
                    const comparisonResponse = await fetch(`/api/campaigns/comparison?campaign1=${campaign.id}&campaign2=${campaign.id}`);
                    if (comparisonResponse.ok) {
                        const comparisonData = await comparisonResponse.json();
                        campaignKpis = comparisonData.campaign1?.data; // Same campaign data
                    }
                } catch (error) {
                    console.warn(`Failed to load KPI data for campaign ${campaign.name}:`, error);
                }
            }
            
            // Format the row with available data or defaults
            const row = {
                name: campaign.name || 'Unknown',
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
            
            kpiRows.push(row);
        }
        
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
        
    } catch (error) {
        console.error('Error loading KPI overview:', error);
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-danger">Error loading KPI overview data</td></tr>';
    }
}

// Store sparkline chart instances to destroy them before recreating
let sparklineCharts = {};

// Create sparklines for KPI metrics using approved color palette only
function createKpiSparklines(kpiData) {
    if (!kpiData || kpiData.length === 0) return;
    
    // Destroy existing charts to prevent memory leaks
    Object.values(sparklineCharts).forEach(chart => {
        if (chart) chart.destroy();
    });
    sparklineCharts = {};
    
    // Approved color palette
    const PRIMARY_RED = '#E13A44';
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
        return trend >= 0 ? PRIMARY_RED : MEDIUM_GRAY;
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
                pointBackgroundColor: PRIMARY_RED,
                pointBorderColor: PRIMARY_RED,
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

document.addEventListener('DOMContentLoaded', function() {
    // Only run dashboard JavaScript on dashboard pages
    if (!document.body.classList.contains('page-dashboard') && 
        !window.location.pathname.includes('/dashboard')) {
        return;
    }
    
    loadCampaignFilterOptions();
});


















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
                createNpsChart();
                createSentimentChart();
                createRatingsChart();
                createTenureChart();
                createGrowthFactorChart();
            }
            
            // Re-initialize themes chart when Overview tab is shown - immediate rendering
            if (targetTab === '#overview') {
                createThemesChart();
            }
            
            // Campaign management access will be handled by server-side business authentication
        });
    });
}









// Two-tier navigation functionality
function switchPrimarySection(section) {
    // Remove active class from all primary navigation buttons
    document.querySelectorAll("#primaryNavigation .nav-link").forEach(link => {
        link.classList.remove("active");
    });
    
    // Add active class to clicked primary navigation button
    document.getElementById(section + "-primary").classList.add("active");
    
    // Hide all secondary navigation sections
    document.querySelectorAll(".secondary-nav").forEach(nav => {
        nav.classList.add("d-none");
    });
    
    // Show the appropriate secondary navigation and related sections
    if (section === "insights") {
        const insightsSection = document.getElementById("insightsSection");
        if (insightsSection) insightsSection.classList.remove("d-none");
        // Also show the insights secondary nav specifically
        const insightsSecondaryNav = document.getElementById("insightsSecondaryNav");
        if (insightsSecondaryNav) insightsSecondaryNav.classList.remove("d-none");
    } else {
        // Hide insights section when not in insights
        const insightsSection = document.getElementById("insightsSection");
        if (insightsSection) insightsSection.classList.add("d-none");
        
        const targetSecondaryNav = document.getElementById(section + "SecondaryNav");
        if (targetSecondaryNav) {
            targetSecondaryNav.classList.remove("d-none");
        }
    }
    
    // Handle tab content based on section
    switch(section) {
        case "insights":
            // Show overview tab by default for insights
            showTab("overview-tab", "overview");
            break;
        case "admin":
            // Show admin tools tab by default
            showTab("admin-tools-tab", "admin-tools");
            break;
    }
}

// Helper function to show a specific tab
function showTab(tabId, contentId) {
    // Hide all tab content
    document.querySelectorAll(".tab-pane").forEach(pane => {
        pane.classList.remove("show", "active");
    });
    
    // Remove active from all secondary nav links
    document.querySelectorAll(".secondary-nav .nav-link").forEach(link => {
        link.classList.remove("active");
        link.setAttribute("aria-selected", "false");
    });
    
    // Show target tab content
    const targetContent = document.getElementById(contentId);
    if (targetContent) {
        targetContent.classList.add("show", "active");
    }
    
    // Activate target tab
    const targetTab = document.getElementById(tabId);
    if (targetTab) {
        targetTab.classList.add("active");
        targetTab.setAttribute("aria-selected", "true");
    }
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
            ratings.push(`<span class="badge bg-info me-1" title="Satisfaction">S: ${response.satisfaction_rating}/10</span>`);
        }
        if (response.product_value_rating) {
            ratings.push(`<span class="badge bg-info me-1" title="Value">V: ${response.product_value_rating}/10</span>`);
        }
        if (response.service_rating) {
            ratings.push(`<span class="badge bg-info me-1" title="Service">Svc: ${response.service_rating}/10</span>`);
        }
        if (response.pricing_rating) {
            ratings.push(`<span class="badge bg-info me-1" title="Pricing">P: ${response.pricing_rating}/10</span>`);
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
            actionCell.innerHTML = `
                <a href="/survey-response/${response.id}" class="btn btn-sm btn-outline-primary" title="View Full Response">
                    <i class="fas fa-eye"></i>
                </a>
            `;
        } else {
            // User cannot view this response - authentication required
            actionCell.innerHTML = `
                <span class="text-muted" title="Authentication required">
                    <i class="fas fa-lock"></i>
                </span>
            `;
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
