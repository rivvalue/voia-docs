// Executive Summary JavaScript - Extracted from dashboard.js
// This file contains only the functionality needed for the Executive Summary page

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

// HTML escape function to prevent XSS vulnerabilities
function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize global translations object and load executive summary translations
window.translations = window.translations || {};

// Helper function to convert string keys to camelCase property names
function toCamelCase(str) {
    // Special cases for common patterns
    const specialCases = {
        // Status keys - matching exact grep results
        'Draft': 'draft',
        'Ready': 'ready',
        'Active': 'active',
        'Completed': 'completed',
        'Unknown': 'unknown',
        // Campaign selection
        'Select first campaign': 'selectFirstCampaign',
        'Select second campaign': 'selectSecondCampaign',
        // Loading states
        'Loading comparison...': 'loadingComparison',
        'Loading comparison data...': 'loadingComparisonData',
        // Error messages - matching exact property names
        'Error Loading Comparison': 'errorLoadingComparison',
        'Error loading KPI overview data': 'errorLoadingKpiData',  // FIXED: was errorLoadingKpiOverviewData
        'Failed to fetch comparison data': 'failedToFetchComparisonData',
        'Failed to load comparison data. Please try again.': 'failedToLoadComparisonData',
        'Failed to load campaign options': 'failedToLoadCampaignOptions',
        // No data messages
        'No campaign data available': 'noCampaignDataAvailable',
        // Metric names - matching exact grep results
        'Risk-Heavy Accounts': 'riskHeavyAccounts',
        'Opportunity-Heavy Accounts': 'opportunityHeavyAccounts',
        'Satisfaction': 'satisfactionRating',
        'Product Value': 'productValueRating',
        'Pricing': 'pricingRating',
        'Service': 'serviceRating',
        'Critical Risk': 'criticalRiskCompanies',
        // Chart labels
        'Total Responses': 'totalResponses',
        'NPS Score': 'npsScore',
        'Companies Analyzed': 'companiesAnalyzed'
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
        // Campaign selection
        selectFirstCampaign: 'Select first campaign',
        selectSecondCampaign: 'Select second campaign',
        // Comparison keys
        loadingComparison: 'Loading comparison...',
        loadingComparisonData: 'Loading comparison data...',
        failedToFetchComparisonData: 'Failed to fetch comparison data',
        failedToLoadComparisonData: 'Failed to load comparison data. Please try again.',
        errorLoadingComparison: 'Error Loading Comparison',
        // Metric names used in executive summary
        riskHeavyAccounts: 'Risk-Heavy Accounts',
        opportunityHeavyAccounts: 'Opportunity-Heavy Accounts',
        satisfactionRating: 'Satisfaction',
        productValueRating: 'Product Value',
        pricingRating: 'Pricing',
        serviceRating: 'Service',
        criticalRiskCompanies: 'Critical Risk',
        // Chart labels
        totalResponses: 'Total Responses',
        npsScore: 'NPS Score',
        companiesAnalyzed: 'Companies Analyzed',
        // Error messages
        errorLoadingKpiData: 'Error loading KPI overview data',
        failedToLoadCampaignOptions: 'Failed to load campaign options',
        // No data messages
        noCampaignDataAvailable: 'No campaign data available',
        // KPI sparkline row & headline
        trends: 'Trends',
        clickToViewFullTrends: 'Click to view full trends',
        activeCampaign: 'active campaign',
        activeCampaigns: 'active campaigns',
        npsRange: 'NPS range',
        campaignHasCriticalRisk: 'campaign has critical-risk accounts',
        campaignsHaveCriticalRisk: 'campaigns have critical-risk accounts'
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
        
        // CRITICAL: Merge fallback for any keys still missing
        // This ensures NO undefined values even in success path
        for (const [key, value] of Object.entries(fallbackTranslations)) {
            if (window.translations[key] === undefined) {
                window.translations[key] = value;
            }
        }
        
        console.log('✅ Executive Summary translations loaded:', Object.keys(window.translations).length, 'keys');
        
        // Fire translationsLoaded event
        window.dispatchEvent(new Event('translationsLoaded'));
    } catch (error) {
        console.error('❌ Failed to load executive summary translations:', error);
        // Apply all fallback translations on fetch failure
        Object.assign(window.translations, fallbackTranslations);
        
        // Fire event anyway to unblock UI
        window.dispatchEvent(new Event('translationsLoaded'));
    }
})();

// Utility functions
function formatDate(dateString) {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

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

// Helper function to generate pagination pages with smart ellipsis
function generatePaginationPages(currentPage, totalPages) {
    if (totalPages <= 7) {
        return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    
    const pages = [];
    pages.push(1);
    
    if (currentPage > 3) {
        pages.push(null); // Ellipsis
    }
    
    for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) {
        pages.push(i);
    }
    
    if (currentPage < totalPages - 2) {
        pages.push(null); // Ellipsis
    }
    
    pages.push(totalPages);
    
    return pages;
}

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

let comparisonCampaigns = [];
let currentComparisonData = null;
let currentComparisonPage = 1;
const comparisonPerPage = 10;
let sparklineCharts = {};
let globalKpiData = null;
let modalCharts = {};

// ============================================================================
// CAMPAIGN COMPARISON FUNCTIONALITY
// ============================================================================

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
        // Normalize status to lowercase for consistent logic
        const rawStatus = (campaign.status || '').toLowerCase();
        const displayStatus = formatCampaignStatus(rawStatus);
        const optionText = `${campaign.name} (${formatDate(campaign.start_date)} - ${formatDate(campaign.end_date)}) - ${displayStatus}`;
        
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
            // Clear existing content
            messageDiv.textContent = '';
            
            // Create icon
            const icon = document.createElement('i');
            icon.className = 'fas fa-exclamation-triangle fa-4x mb-3';
            icon.style.color = '#E13A44';
            
            // Create heading
            const heading = document.createElement('h5');
            heading.style.color = '#E13A44';
            heading.textContent = translations.errorLoadingComparison;
            
            // Create paragraph
            const paragraph = document.createElement('p');
            paragraph.className = 'text-muted';
            paragraph.textContent = translations.failedToLoadComparisonData;
            
            // Append all elements
            messageDiv.appendChild(icon);
            messageDiv.appendChild(heading);
            messageDiv.appendChild(paragraph);
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
            name: translations.riskHeavyAccounts,
            c1: c1.risk_heavy_accounts,
            c2: c2.risk_heavy_accounts,
            change: c2.risk_heavy_accounts - c1.risk_heavy_accounts,
            format: 'number'
        },
        {
            name: translations.opportunityHeavyAccounts,
            c1: c1.opportunity_heavy_accounts,
            c2: c2.opportunity_heavy_accounts,
            change: c2.opportunity_heavy_accounts - c1.opportunity_heavy_accounts,
            format: 'number'
        },
        {
            name: translations.satisfactionRating,
            c1: c1.average_ratings?.satisfaction || 0,
            c2: c2.average_ratings?.satisfaction || 0,
            change: (c2.average_ratings?.satisfaction || 0) - (c1.average_ratings?.satisfaction || 0),
            format: 'decimal'
        },
        {
            name: translations.productValueRating,
            c1: c1.average_ratings?.product_value || 0,
            c2: c2.average_ratings?.product_value || 0,
            change: (c2.average_ratings?.product_value || 0) - (c1.average_ratings?.product_value || 0),
            format: 'decimal'
        },
        {
            name: translations.pricingRating,
            c1: c1.average_ratings?.pricing || 0,
            c2: c2.average_ratings?.pricing || 0,
            change: (c2.average_ratings?.pricing || 0) - (c1.average_ratings?.pricing || 0),
            format: 'decimal'
        },
        {
            name: translations.serviceRating,
            c1: c1.average_ratings?.service || 0,
            c2: c2.average_ratings?.service || 0,
            change: (c2.average_ratings?.service || 0) - (c1.average_ratings?.service || 0),
            format: 'decimal'
        }
    ];
    
    // Inverse metrics: increase = bad (lower is better)
    const inverseMetrics = ['Critical Risk Companies', translations.criticalRiskCompanies, translations.riskHeavyAccounts];
    const isInverse = (name) => inverseMetrics.includes(name);
    const isNpsMetric = (name) => name === 'NPS Score' || name === translations.npsScore;

    // NPS badge color helper
    const npsColor = (score) => {
        if (score >= 30) return 'bg-success';
        if (score >= 0) return 'bg-warning text-dark';
        return 'bg-danger';
    };

    // Consistent change badge: green = improvement, red = deterioration
    // Arrow always indicates direction; color always indicates outcome
    const changeBadgeInfo = (change, format, inverse) => {
        const absVal = Math.abs(change);
        const formatted = format === 'decimal' ? absVal.toFixed(1) : absVal;
        if (change === 0) return { text: '0', cls: 'bg-secondary', arrow: '' };
        const isGood = inverse ? change < 0 : change > 0;
        const sign = change > 0 ? '+' : '\u2212';
        return {
            text: `${sign}${formatted}`,
            cls: isGood ? 'bg-success' : 'bg-danger',
            arrow: isGood ? 'fa-arrow-up' : 'fa-arrow-down'
        };
    };

    // Clear existing content
    tableBody.textContent = '';

    // Build takeaway insights from the metrics
    const takeaways = [];
    const npsMetric = metrics.find(m => m.name === 'NPS Score');
    if (npsMetric && npsMetric.change !== 0) {
        const dir = npsMetric.change > 0 ? 'improved' : 'declined';
        takeaways.push({ text: `NPS ${dir} by ${Math.abs(npsMetric.change).toFixed(1)}`, good: npsMetric.change > 0 });
    }
    const crMetric = metrics.find(m => m.name === 'Critical Risk Companies');
    if (crMetric && crMetric.change !== 0) {
        const dir = crMetric.change > 0 ? 'increased' : 'decreased';
        takeaways.push({ text: `Critical risk accounts ${dir} by ${Math.abs(crMetric.change)}`, good: crMetric.change < 0 });
    }
    const ratingsMetrics = metrics.filter(m => m.format === 'decimal' && m.name !== 'NPS Score');
    const improvedRatings = ratingsMetrics.filter(m => m.change > 0.1);
    const declinedRatings = ratingsMetrics.filter(m => m.change < -0.1);
    if (improvedRatings.length > 0) {
        takeaways.push({ text: `${improvedRatings.length} rating${improvedRatings.length > 1 ? 's' : ''} improved`, good: true });
    }
    if (declinedRatings.length > 0) {
        takeaways.push({ text: `${declinedRatings.length} rating${declinedRatings.length > 1 ? 's' : ''} declined`, good: false });
    }

    // Render takeaway
    const takeawayEl = document.getElementById('metricsComparisonTakeaway');
    if (takeawayEl && takeaways.length > 0) {
        takeawayEl.style.display = 'block';
        takeawayEl.innerHTML = '';
        const container = document.createElement('div');
        container.className = 'd-flex flex-wrap gap-2 align-items-center';
        container.style.fontSize = '0.85rem';
        const label = document.createElement('span');
        label.className = 'text-muted fw-semibold me-1';
        label.innerHTML = '<i class="fas fa-lightbulb me-1" style="color: #E13A44;"></i>Key shifts:';
        container.appendChild(label);
        takeaways.forEach(t => {
            const badge = document.createElement('span');
            badge.className = `badge ${t.good ? 'bg-success' : 'bg-danger'}`;
            badge.style.fontSize = '0.8rem';
            badge.textContent = t.text;
            container.appendChild(badge);
        });
        takeawayEl.appendChild(container);
    } else if (takeawayEl) {
        takeawayEl.style.display = 'none';
    }

    // Track whether we need a separator (inserted before first rating row)
    let separatorInserted = false;
    const ratingNames = [translations.satisfactionRating, translations.productValueRating, translations.pricingRating, translations.serviceRating];

    metrics.forEach(metric => {
        const c1Display = metric.format === 'decimal' ? parseFloat(metric.c1).toFixed(1) : metric.c1;
        const c2Display = metric.format === 'decimal' ? parseFloat(metric.c2).toFixed(1) : metric.c2;

        const inverse = isInverse(metric.name);
        const badge = changeBadgeInfo(metric.change, metric.format, inverse);

        // Insert separator row before ratings section
        if (!separatorInserted && ratingNames.includes(metric.name)) {
            separatorInserted = true;
            const sepRow = document.createElement('tr');
            const sepCell = document.createElement('td');
            sepCell.setAttribute('colspan', '4');
            sepCell.style.borderTop = '2px solid #E9E8E4';
            sepCell.style.padding = '2px 0';
            sepCell.innerHTML = '<small class="text-muted" style="font-size: 0.75rem;"><em>Ratings (1-5 scale)</em></small>';
            sepRow.appendChild(sepCell);
            tableBody.appendChild(sepRow);
        }

        // Create row
        const row = document.createElement('tr');

        // Subtle row tint: green for good changes, red for bad changes
        if (metric.change !== 0) {
            const isGood = inverse ? metric.change < 0 : metric.change > 0;
            if (isGood) {
                row.style.backgroundColor = 'rgba(25, 135, 84, 0.04)';
            } else {
                row.style.backgroundColor = 'rgba(220, 53, 69, 0.04)';
            }
        }
        
        // Name column — add "(lower is better)" hint for inverse metrics
        const nameCell = document.createElement('td');
        const nameStrong = document.createElement('strong');
        nameStrong.textContent = metric.name;
        nameCell.appendChild(nameStrong);
        if (inverse) {
            const hint = document.createElement('small');
            hint.className = 'text-muted d-block';
            hint.style.fontSize = '0.7rem';
            hint.textContent = '(lower is better)';
            nameCell.appendChild(hint);
        }
        
        // C1 column — NPS gets badge treatment
        const c1Cell = document.createElement('td');
        c1Cell.className = 'text-center';
        if (isNpsMetric(metric.name)) {
            const npsBadge = document.createElement('span');
            npsBadge.className = `badge ${npsColor(metric.c1)}`;
            npsBadge.textContent = c1Display;
            c1Cell.appendChild(npsBadge);
        } else {
            c1Cell.textContent = c1Display;
        }
        
        // C2 column — NPS gets badge treatment
        const c2Cell = document.createElement('td');
        c2Cell.className = 'text-center';
        if (isNpsMetric(metric.name)) {
            const npsBadge = document.createElement('span');
            npsBadge.className = `badge ${npsColor(metric.c2)}`;
            npsBadge.textContent = c2Display;
            c2Cell.appendChild(npsBadge);
        } else {
            c2Cell.textContent = c2Display;
        }
        
        // Change column — consistent badge: green arrow up = improvement, red arrow down = deterioration
        const changeCell = document.createElement('td');
        changeCell.className = 'text-center';
        const changeBadgeEl = document.createElement('span');
        changeBadgeEl.className = `badge ${badge.cls}`;
        changeBadgeEl.style.fontSize = '0.8rem';
        if (badge.arrow) {
            changeBadgeEl.innerHTML = `<i class="fas ${badge.arrow} me-1" style="font-size: 0.65rem;"></i>${escapeHtml(badge.text)}`;
        } else {
            changeBadgeEl.textContent = badge.text;
        }
        changeCell.appendChild(changeBadgeEl);
        
        // Append all cells to row
        row.appendChild(nameCell);
        row.appendChild(c1Cell);
        row.appendChild(c2Cell);
        row.appendChild(changeCell);
        
        // Append row to table body
        tableBody.appendChild(row);
    });
}

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

    // Balance badge styling helper
    const balanceBadge = (balance) => {
        if (!balance || balance === 'N/A') return { cls: 'bg-secondary', text: 'N/A' };
        if (balance === 'risk_heavy') return { cls: 'bg-danger', text: 'Risk Heavy' };
        if (balance === 'opportunity_heavy') return { cls: 'bg-success', text: 'Opp Heavy' };
        if (balance === 'balanced') return { cls: 'bg-primary', text: 'Balanced' };
        return { cls: 'bg-secondary', text: formatBalance(balance) };
    };

    // Status badge styling helper
    const statusBadge = (status, statusType) => {
        const map = {
            'Improved':   'bg-success',
            'Less Risk':  'bg-success',
            'More Opps':  'bg-success',
            'Worsened':   'bg-danger',
            'Changed':    'bg-warning text-dark',
            'No Change':  'bg-secondary',
            'New in C2':  'bg-info text-dark',
            'Not in C2':  'bg-secondary',
            'N/A':        'bg-light text-muted'
        };
        return map[status] || 'bg-secondary';
    };

    // Count statuses across ALL companies for summary headline
    const allCompanies = data.company_details || [];
    let improvedCount = 0, worsenedCount = 0, noChangeCount = 0, newCount = 0, riskHeavyC2Count = 0;
    allCompanies.forEach(company => {
        const c1 = company.campaign1;
        const c2 = company.campaign2;
        if (c1.participated && c2.participated) {
            if (c1.balance !== c2.balance) {
                if ((c2.balance === 'opportunity_heavy' && c1.balance !== 'opportunity_heavy') ||
                    (c2.balance === 'balanced' && c1.balance === 'risk_heavy')) {
                    improvedCount++;
                } else if (c2.balance === 'risk_heavy' && c1.balance !== 'risk_heavy') {
                    worsenedCount++;
                } else {
                    noChangeCount++;
                }
            } else if (c2.risk_count < c1.risk_count || c2.opportunity_count > c1.opportunity_count) {
                improvedCount++;
            } else {
                noChangeCount++;
            }
        } else if (!c1.participated && c2.participated) {
            newCount++;
        }
        if (c2.participated && c2.balance === 'risk_heavy') {
            riskHeavyC2Count++;
        }
    });

    // Populate comparison summary headline
    const headlineEl = document.getElementById('comparisonHeadline');
    if (headlineEl && allCompanies.length > 0) {
        headlineEl.style.display = 'block';
        headlineEl.innerHTML = '';
        const container = document.createElement('div');
        container.className = 'd-flex flex-wrap gap-2 align-items-center';
        container.style.fontSize = '0.85rem';
        const pills = [];
        if (improvedCount > 0) pills.push({ text: `${improvedCount} improved`, cls: 'bg-success' });
        if (worsenedCount > 0) pills.push({ text: `${worsenedCount} worsened`, cls: 'bg-danger' });
        if (noChangeCount > 0) pills.push({ text: `${noChangeCount} stable`, cls: 'bg-secondary' });
        if (newCount > 0) pills.push({ text: `${newCount} new`, cls: 'bg-info text-dark' });
        if (riskHeavyC2Count > 0) pills.push({ text: `${riskHeavyC2Count} currently risk-heavy`, cls: 'bg-danger' });
        const summaryLabel = document.createElement('span');
        summaryLabel.className = 'text-muted fw-semibold me-1';
        summaryLabel.textContent = `${allCompanies.length} accounts:`;
        container.appendChild(summaryLabel);
        pills.forEach(p => {
            const badge = document.createElement('span');
            badge.className = `badge ${p.cls}`;
            badge.style.fontSize = '0.8rem';
            badge.textContent = p.text;
            container.appendChild(badge);
        });
        headlineEl.appendChild(container);
    }

    paginatedCompanies.forEach(company => {
        const c1 = company.campaign1;
        const c2 = company.campaign2;
        
        // Helper function to display value or N/A
        const displayValue = (value) => {
            return (value === null || value === undefined) ? 'N/A' : value;
        };
        
        // Determine status - only compare if both campaigns have data
        let status = 'N/A';
        
        if (c1.participated && c2.participated) {
            status = 'No Change';
            
            if (c1.balance !== c2.balance) {
                if (c2.balance === 'opportunity_heavy' && c1.balance !== 'opportunity_heavy') {
                    status = 'Improved';
                } else if (c2.balance === 'risk_heavy' && c1.balance !== 'risk_heavy') {
                    status = 'Worsened';
                } else if (c2.balance === 'balanced' && c1.balance === 'risk_heavy') {
                    status = 'Improved';
                } else {
                    status = 'Changed';
                }
            } else if (c2.risk_count < c1.risk_count) {
                status = 'Less Risk';
            } else if (c2.opportunity_count > c1.opportunity_count) {
                status = 'More Opps';
            }
        } else if (!c1.participated && c2.participated) {
            status = 'New in C2';
        } else if (c1.participated && !c2.participated) {
            status = 'Not in C2';
        }
        
        // Create table row using safe DOM methods
        const row = document.createElement('tr');

        // Subtle row tint for worsened accounts
        if (status === 'Worsened') {
            row.style.backgroundColor = 'rgba(220, 53, 69, 0.06)';
        } else if (status === 'Improved' || status === 'Less Risk' || status === 'More Opps') {
            row.style.backgroundColor = 'rgba(25, 135, 84, 0.04)';
        }
        
        // Company name column
        const nameCell = document.createElement('td');
        const nameStrong = document.createElement('strong');
        nameStrong.textContent = company.company_name;
        nameCell.appendChild(nameStrong);
        
        // Helper: create a risk/opp count cell with color hint
        const createCountCell = (value, isRisk) => {
            const cell = document.createElement('td');
            cell.className = 'text-center';
            const val = displayValue(value);
            if (val === 'N/A' || val === 0) {
                cell.textContent = val;
                if (val === 0 && isRisk) cell.classList.add('text-success');
            } else if (isRisk && val > 0) {
                const badge = document.createElement('span');
                badge.className = 'badge bg-danger';
                badge.textContent = val;
                cell.appendChild(badge);
            } else if (!isRisk && val > 0) {
                const badge = document.createElement('span');
                badge.className = 'badge bg-success';
                badge.textContent = val;
                cell.appendChild(badge);
            } else {
                cell.textContent = val;
            }
            return cell;
        };

        // Helper: create a balance cell as badge
        const createBalanceCell = (balance) => {
            const cell = document.createElement('td');
            cell.className = 'text-center';
            const info = balanceBadge(balance);
            const badge = document.createElement('span');
            badge.className = `badge ${info.cls}`;
            badge.style.fontSize = '0.75rem';
            badge.textContent = info.text;
            cell.appendChild(badge);
            return cell;
        };

        // Campaign 1 cells (light red tint to match C1 header)
        const c1RiskCell = createCountCell(c1.risk_count, true);
        c1RiskCell.style.backgroundColor = 'rgba(225, 58, 68, 0.03)';
        const c1OppCell = createCountCell(c1.opportunity_count, false);
        c1OppCell.style.backgroundColor = 'rgba(225, 58, 68, 0.03)';
        const c1BalanceCell = createBalanceCell(c1.balance);
        c1BalanceCell.style.backgroundColor = 'rgba(225, 58, 68, 0.03)';
        c1BalanceCell.style.borderRight = '2px solid #dee2e6';

        // Campaign 2 cells (light blue tint to match C2 header)
        const c2RiskCell = createCountCell(c2.risk_count, true);
        c2RiskCell.style.backgroundColor = 'rgba(13, 110, 253, 0.03)';
        const c2OppCell = createCountCell(c2.opportunity_count, false);
        c2OppCell.style.backgroundColor = 'rgba(13, 110, 253, 0.03)';
        const c2BalanceCell = createBalanceCell(c2.balance);
        c2BalanceCell.style.backgroundColor = 'rgba(13, 110, 253, 0.03)';
        
        // Status column as badge
        const statusCell = document.createElement('td');
        statusCell.className = 'text-center';
        const statusBadgeEl = document.createElement('span');
        statusBadgeEl.className = `badge ${statusBadge(status)}`;
        statusBadgeEl.style.fontSize = '0.75rem';
        statusBadgeEl.textContent = status;
        statusCell.appendChild(statusBadgeEl);
        
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

// ============================================================================
// KPI OVERVIEW AND SPARKLINES
// ============================================================================

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
            // Use safe DOM methods instead of innerHTML
            tbody.textContent = '';
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.setAttribute('colspan', '9');
            td.className = 'text-center text-muted';
            td.textContent = translations.noCampaignDataAvailable;
            tr.appendChild(td);
            tbody.appendChild(tr);
            if (loadingElement) loadingElement.classList.add('d-none');
            if (contentElement) contentElement.classList.remove('d-none');
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
        
        // Helper: NPS badge HTML based on value
        const npsColor = (score) => {
            if (score >= 30) return 'bg-success';
            if (score >= 0) return 'bg-warning text-dark';
            return 'bg-danger';
        };

        // Generate data rows HTML
        tbody.innerHTML = kpiRows.map(row => `
            <tr>
                <td><strong>${escapeHtml(row.name)}</strong><br><small class="text-muted">${row.status}</small></td>
                <td class="text-center">${row.responses}</td>
                <td class="text-center"><span class="badge ${npsColor(row.nps_score)}">${row.nps_score.toFixed(1)}</span></td>
                <td class="text-center">${row.companies}</td>
                <td class="text-center"><span class="badge ${row.critical_risk > 0 ? 'bg-danger' : 'bg-success'}">${row.critical_risk}</span></td>
                <td class="text-center">${row.satisfaction.toFixed(1)}</td>
                <td class="text-center">${row.product_value.toFixed(1)}</td>
                <td class="text-center">${row.pricing.toFixed(1)}</td>
                <td class="text-center">${row.service.toFixed(1)}</td>
            </tr>
        `).join('');

        // Insert sparkline sub-row as first row of tbody (desktop only)
        const trendsLabel = translations.trends || 'Trends';
        const trendsTitle = translations.clickToViewFullTrends || 'Click to view full trends';
        const sparklineRowHtml = `
            <tr class="sparkline-row d-none d-md-table-row" style="border-bottom: 1px solid #E9E8E4;">
                <td class="text-muted" style="font-size: 0.75rem; padding-bottom: 4px;"><em>${escapeHtml(trendsLabel)}</em></td>
                <td class="text-center" style="padding: 0 4px 4px;">
                    <div class="sparkline-container" style="height: 30px; cursor: pointer;" onclick="openTrendsModal()" title="${escapeHtml(trendsTitle)}">
                        <canvas id="sparkline-responses"></canvas>
                    </div>
                </td>
                <td class="text-center" style="padding: 0 4px 4px;">
                    <div class="sparkline-container" style="height: 30px; cursor: pointer;" onclick="openTrendsModal()" title="${escapeHtml(trendsTitle)}">
                        <canvas id="sparkline-nps"></canvas>
                    </div>
                </td>
                <td class="text-center" style="padding: 0 4px 4px;">
                    <div class="sparkline-container" style="height: 30px; cursor: pointer;" onclick="openTrendsModal()" title="${escapeHtml(trendsTitle)}">
                        <canvas id="sparkline-companies"></canvas>
                    </div>
                </td>
                <td class="text-center" style="padding: 0 4px 4px;">
                    <div class="sparkline-container" style="height: 30px; cursor: pointer;" onclick="openTrendsModal()" title="${escapeHtml(trendsTitle)}">
                        <canvas id="sparkline-critical"></canvas>
                    </div>
                </td>
                <td class="text-center" style="padding: 0 4px 4px;">
                    <div class="sparkline-container" style="height: 30px; cursor: pointer;" onclick="openTrendsModal()" title="${escapeHtml(trendsTitle)}">
                        <canvas id="sparkline-satisfaction"></canvas>
                    </div>
                </td>
                <td class="text-center" style="padding: 0 4px 4px;">
                    <div class="sparkline-container" style="height: 30px; cursor: pointer;" onclick="openTrendsModal()" title="${escapeHtml(trendsTitle)}">
                        <canvas id="sparkline-product"></canvas>
                    </div>
                </td>
                <td class="text-center" style="padding: 0 4px 4px;">
                    <div class="sparkline-container" style="height: 30px; cursor: pointer;" onclick="openTrendsModal()" title="${escapeHtml(trendsTitle)}">
                        <canvas id="sparkline-pricing"></canvas>
                    </div>
                </td>
                <td class="text-center" style="padding: 0 4px 4px;">
                    <div class="sparkline-container" style="height: 30px; cursor: pointer;" onclick="openTrendsModal()" title="${escapeHtml(trendsTitle)}">
                        <canvas id="sparkline-service"></canvas>
                    </div>
                </td>
            </tr>`;
        tbody.insertAdjacentHTML('afterbegin', sparklineRowHtml);

        // Headline synthesis sentence
        const headlineEl = document.getElementById('kpiHeadline');
        if (headlineEl && kpiRows.length > 0) {
            const npsValues = kpiRows.map(r => r.nps_score);
            const npsMin = Math.min(...npsValues);
            const npsMax = Math.max(...npsValues);
            const criticalCount = kpiRows.filter(r => r.critical_risk > 0).length;
            const formatNps = (v) => (v >= 0 ? '+' : '') + v.toFixed(0);
            const campaignLabel = kpiRows.length !== 1
                ? (translations.activeCampaigns || 'active campaigns')
                : (translations.activeCampaign || 'active campaign');
            const npsRangeLabel = translations.npsRange || 'NPS range';
            let headline = `${kpiRows.length} ${campaignLabel} \u00b7 ${npsRangeLabel}: ${formatNps(npsMin)} to ${formatNps(npsMax)}`;
            if (criticalCount > 0) {
                const criticalLabel = criticalCount !== 1
                    ? (translations.campaignsHaveCriticalRisk || 'campaigns have critical-risk accounts')
                    : (translations.campaignHasCriticalRisk || 'campaign has critical-risk accounts');
                headline += ` \u00b7 ${criticalCount} ${criticalLabel}`;
            }
            headlineEl.textContent = headline;
        }

        // Create sparklines after table is populated
        createKpiSparklines(kpiRows);
        
        console.log(`KPI overview loaded successfully with ${kpiRows.length} campaigns`);
        
        // Hide loading, show content
        if (loadingElement) loadingElement.classList.add('d-none');
        if (contentElement) contentElement.classList.remove('d-none');
        
    } catch (error) {
        console.error('Error loading KPI overview:', error);
        
        // Create error row using safe DOM methods
        tbody.innerHTML = '';
        const errorRow = document.createElement('tr');
        const errorCell = document.createElement('td');
        errorCell.setAttribute('colspan', '9');
        errorCell.className = 'text-center text-danger';
        errorCell.textContent = translations.errorLoadingKpiData;
        errorRow.appendChild(errorCell);
        tbody.appendChild(errorRow);
        
        // Hide loading, show content even on error
        if (loadingElement) loadingElement.classList.add('d-none');
        if (contentElement) contentElement.classList.remove('d-none');
    }
}

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

// Open the KPI trends modal with full-size charts
function openTrendsModal() {
    if (!globalKpiData || globalKpiData.length === 0) {
        alert(translations.noCampaignDataAvailable);
        return;
    }
    
    // Show the modal using Bootstrap 5
    const modal = new bootstrap.Modal(document.getElementById('trendsModal'));
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
        { id: 'modal-chart-responses', data: metrics.responses, label: 'Responses', yLabel: translations.totalResponses },
        { id: 'modal-chart-nps', data: metrics.nps_score, label: 'NPS', yLabel: translations.npsScore },
        { id: 'modal-chart-companies', data: metrics.companies, label: 'Companies', yLabel: translations.companiesAnalyzed },
        { id: 'modal-chart-critical', data: metrics.critical_risk, label: 'Critical Risk', yLabel: translations.criticalRiskCompanies },
        { id: 'modal-chart-satisfaction', data: metrics.satisfaction, label: 'Satisfaction', yLabel: translations.satisfactionRating },
        { id: 'modal-chart-product', data: metrics.product_value, label: 'Product', yLabel: translations.productValueRating },
        { id: 'modal-chart-pricing', data: metrics.pricing, label: 'Pricing', yLabel: translations.pricingRating },
        { id: 'modal-chart-service', data: metrics.service, label: 'Service', yLabel: translations.serviceRating }
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

// Refresh data function
function refreshData() {
    location.reload();
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Executive Summary JavaScript loaded and DOM ready');
    
    // Load KPI overview data
    loadKpiOverview();
    
    // Load campaign comparison options
    loadComparisonCampaignOptions();
});
