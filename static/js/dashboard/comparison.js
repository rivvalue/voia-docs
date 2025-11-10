/**
 * Dashboard Comparison Module
 * Phase 3: Frontend Refactoring - Sprint 3
 * 
 * This module handles campaign comparison functionality including dropdowns,
 * executive summary, company comparison table, search, and pagination.
 * Migrated from dashboard.js (~630 lines total)
 */

(function() {
    'use strict';
    
    // Import utilities from bootstrap
    const { escapeHtml, formatCampaignStatus, formatDate } = window.dashboardModules.bootstrap.utils;
    
    // Module-level state
    let comparisonCampaigns = [];
    let currentComparisonData = null;
    let currentComparisonPage = 1;
    const comparisonPerPage = 20;
    
    /**
     * Populate comparison campaign dropdowns
     */
    function populateComparisonDropdowns() {
        const translations = window.translations || {};
        const campaign1Select = document.getElementById('campaign1Select');
        const campaign2Select = document.getElementById('campaign2Select');
        
        if (!campaign1Select || !campaign2Select) return;
        
        // Clear existing options
        campaign1Select.innerHTML = `<option value="">${translations.selectFirstCampaign || 'Select first campaign...'}</option>`;
        campaign2Select.innerHTML = `<option value="">${translations.selectSecondCampaign || 'Select second campaign...'}</option>`;
        
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
    
    /**
     * Update comparison when selections change
     */
    async function updateComparison() {
        const translations = window.translations || {};
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
                        <span class="visually-hidden">${translations.loadingComparison || 'Loading comparison...'}</span>
                    </div>
                    <p class="text-muted mt-3 mb-0">${translations.loadingComparisonData || 'Loading comparison data...'}</p>
                </div>
            `;
            messageDiv.style.display = 'block';
        }
        if (resultsDiv) resultsDiv.style.display = 'none';
        
        try {
            // Fetch comparison data
            const response = await fetch(`/api/campaigns/comparison?campaign1=${campaign1Id}&campaign2=${campaign2Id}`);
            if (!response.ok) {
                throw new Error(translations.failedToFetchComparisonData || 'Failed to fetch comparison data');
            }
            
            const comparisonData = await response.json();
            currentComparisonData = comparisonData;
            
            // Update headers
            document.getElementById('campaign1Header').textContent = comparisonData.campaign1.name;
            document.getElementById('campaign2Header').textContent = comparisonData.campaign2.name;
            
            // Update campaign identifiers in company table
            const c1Name = document.getElementById('c1CampaignName');
            const c2Name = document.getElementById('c2CampaignName');
            if (c1Name) c1Name.textContent = comparisonData.campaign1.name;
            if (c2Name) c2Name.textContent = comparisonData.campaign2.name;
            
            // Populate summary and comparison tables
            populateExecutiveSummary(comparisonData);
            populateCompanyComparison(comparisonData, 1);
            
            // Hide message and show results
            if (messageDiv) messageDiv.style.display = 'none';
            if (resultsDiv) resultsDiv.style.display = 'block';
        } catch (error) {
            console.error('Error loading comparison:', error);
            if (messageDiv) {
                messageDiv.innerHTML = `<div class="alert alert-danger">${translations.errorLoadingComparison || 'Error loading comparison'}: ${error.message}</div>`;
                messageDiv.style.display = 'block';
            }
        }
    }
    
    /**
     * Populate executive summary table
     */
    function populateExecutiveSummary(data) {
        const translations = window.translations || {};
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
            nameCell.textContent = metric.name;
            
            // Campaign 1 value
            const c1Cell = document.createElement('td');
            c1Cell.className = 'text-center';
            c1Cell.textContent = c1Display;
            
            // Campaign 2 value
            const c2Cell = document.createElement('td');
            c2Cell.className = 'text-center';
            c2Cell.textContent = c2Display;
            
            // Change column
            const changeCell = document.createElement('td');
            changeCell.className = `text-center ${changeClass}`;
            const changeStrong = document.createElement('strong');
            changeStrong.textContent = changeDisplay;
            changeCell.appendChild(changeStrong);
            
            row.appendChild(nameCell);
            row.appendChild(c1Cell);
            row.appendChild(c2Cell);
            row.appendChild(changeCell);
            
            tableBody.appendChild(row);
        });
    }
    
    /**
     * Populate company comparison table
     */
    function populateCompanyComparison(data, page = 1) {
        const translations = window.translations || {};
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
            if (balance === 'N/A') return translations.na || 'N/A';
            return balance.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        };
        
        paginatedCompanies.forEach(company => {
            const c1 = company.campaign1;
            const c2 = company.campaign2;
            
            // Helper function to display value or N/A
            const displayValue = (value) => {
                return (value === null || value === undefined) ? (translations.na || 'N/A') : value;
            };
            
            // Determine status - only compare if both campaigns have data
            let status = translations.na || 'N/A';
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
            c1BalanceCell.textContent = c1.balance ? formatBalance(c1.balance) : (translations.na || 'N/A');
            
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
            c2BalanceCell.textContent = c2.balance ? formatBalance(c2.balance) : (translations.na || 'N/A');
            
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
            
            tableBody.appendChild(row);
        });
    }
    
    /**
     * Search and filter comparison table
     */
    function searchComparisonTable() {
        if (!currentComparisonData) return;
        
        const searchQuery = document.getElementById('comparisonSearch')?.value.trim().toLowerCase() || '';
        const balanceFilter = document.getElementById('comparisonBalanceFilter')?.value || '';
        
        let filteredCompanies = currentComparisonData.company_details || [];
        
        // Apply search filter
        if (searchQuery) {
            filteredCompanies = filteredCompanies.filter(company => 
                company.company_name.toLowerCase().includes(searchQuery)
            );
        }
        
        // Apply balance filter
        if (balanceFilter) {
            filteredCompanies = filteredCompanies.filter(company => {
                const c1Balance = company.campaign1.balance;
                const c2Balance = company.campaign2.balance;
                
                if (balanceFilter === 'improved') {
                    return (c2Balance === 'opportunity_heavy' && c1Balance !== 'opportunity_heavy') ||
                           (c2Balance === 'balanced' && c1Balance === 'risk_heavy');
                } else if (balanceFilter === 'worsened') {
                    return c2Balance === 'risk_heavy' && c1Balance !== 'risk_heavy';
                } else {
                    return c2Balance === balanceFilter || c1Balance === balanceFilter;
                }
            });
        }
        
        // Create filtered data object and render
        const filteredData = {
            ...currentComparisonData,
            company_details: filteredCompanies
        };
        
        populateCompanyComparison(filteredData, 1);
    }
    
    /**
     * Update pagination info text
     */
    function updateComparisonPaginationInfo(currentPage, totalPages, totalItems) {
        const translations = window.translations || {};
        const infoElement = document.getElementById('comparisonPaginationInfo');
        if (!infoElement) return;
        
        const startItem = (currentPage - 1) * comparisonPerPage + 1;
        const endItem = Math.min(currentPage * comparisonPerPage, totalItems);
        
        infoElement.textContent = `${translations.showing || 'Showing'} ${startItem}-${endItem} ${translations.of || 'of'} ${totalItems} ${translations.companies || 'companies'}`;
    }
    
    /**
     * Update pagination controls
     */
    function updateComparisonPaginationControls(pagination) {
        const translations = window.translations || {};
        const controls = document.getElementById('comparisonPaginationControls');
        if (!controls) return;
        
        let html = '';
        
        // Previous button
        if (pagination.has_prev) {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="window.dashboardModules.comparison.loadComparisonPage(${pagination.page - 1}); return false;"><i class="fas fa-chevron-left"></i></a></li>`;
        } else {
            html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-left"></i></span></li>';
        }
        
        // Page numbers
        const maxPagesToShow = 5;
        let startPage = Math.max(1, pagination.page - Math.floor(maxPagesToShow / 2));
        let endPage = Math.min(pagination.pages, startPage + maxPagesToShow - 1);
        
        if (endPage - startPage < maxPagesToShow - 1) {
            startPage = Math.max(1, endPage - maxPagesToShow + 1);
        }
        
        for (let i = startPage; i <= endPage; i++) {
            if (i === pagination.page) {
                html += `<li class="page-item active"><span class="page-link">${i}</span></li>`;
            } else {
                html += `<li class="page-item"><a class="page-link" href="#" onclick="window.dashboardModules.comparison.loadComparisonPage(${i}); return false;">${i}</a></li>`;
            }
        }
        
        // Next button
        if (pagination.has_next) {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="window.dashboardModules.comparison.loadComparisonPage(${pagination.page + 1}); return false;"><i class="fas fa-chevron-right"></i></a></li>`;
        } else {
            html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-right"></i></span></li>';
        }
        
        controls.innerHTML = html;
    }
    
    /**
     * Load specific comparison page
     */
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
    
    /**
     * Set comparison campaigns data
     */
    function setComparisonCampaigns(campaigns) {
        comparisonCampaigns = campaigns || [];
    }
    
    // Export public functions
    window.dashboardModules.comparison = {
        populateComparisonDropdowns,
        updateComparison,
        populateExecutiveSummary,
        populateCompanyComparison,
        searchComparisonTable,
        loadComparisonPage,
        setComparisonCampaigns
    };
    
    console.log('📦 Dashboard Comparison module loaded');
    
})();
