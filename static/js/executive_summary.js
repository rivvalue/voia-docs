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
    
    // Clear existing content
    tableBody.textContent = '';
    
    metrics.forEach(metric => {
        const c1Display = metric.format === 'decimal' ? parseFloat(metric.c1).toFixed(1) : metric.c1;
        const c2Display = metric.format === 'decimal' ? parseFloat(metric.c2).toFixed(1) : metric.c2;
        
        let changeDisplay = '';
        let changeClass = '';
        if (metric.change > 0) {
            changeDisplay = `+${metric.format === 'decimal' ? metric.change.toFixed(1) : metric.change}`;
            changeClass = metric.name === translations.criticalRiskCompanies || metric.name === translations.riskHeavyAccounts ? 'text-danger' : 'text-success';
        } else if (metric.change < 0) {
            changeDisplay = metric.format === 'decimal' ? metric.change.toFixed(1) : metric.change;
            changeClass = metric.name === translations.criticalRiskCompanies || metric.name === translations.riskHeavyAccounts ? 'text-success' : 'text-danger';
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
