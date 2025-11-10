/**
 * Dashboard Survey Insights Module
 * Phase 3: Frontend Refactoring - Sprint 5
 * 
 * This module handles survey response tables, company NPS data, tenure NPS data,
 * pagination, search, and filtering functionality.
 * Migrated from dashboard.js (~668 lines total)
 */

(function() {
    'use strict';
    
    // Import utilities from bootstrap
    const { escapeHtml } = window.dashboardModules.bootstrap.utils;
    
    // Module-level state for pagination
    let currentResponsesPage = 1;
    let currentCompanyPage = 1;
    let currentTenurePage = 1;
    const responsesPerPage = 10;
    const companiesPerPage = 10;
    
    /**
     * Load survey responses with pagination and filtering
     */
    function loadSurveyResponses(page = 1, searchQuery = '', npsFilter = '') {
        const translations = window.translations || {};
        const { selectedCampaignId } = window.dashboardState;
        
        const params = new URLSearchParams({
            page: page,
            per_page: responsesPerPage
        });
        
        if (searchQuery) params.append('search', searchQuery);
        if (npsFilter) params.append('nps_filter', npsFilter);
        if (selectedCampaignId) params.append('campaign_id', selectedCampaignId);
        
        const tableBody = document.getElementById('responsesTable');
        if (!tableBody) return;
        
        // Show loading
        tableBody.innerHTML = `<tr><td colspan="8" class="text-center"><div class="spinner-border" role="status"></div></td></tr>`;
        
        fetch(`/api/survey_responses?${params}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    currentResponsesPage = page;
                    renderSurveyResponses(data.responses, data.pagination);
                } else {
                    tableBody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">${translations.errorLoadingResponses || 'Error loading responses'}</td></tr>`;
                }
            })
            .catch(error => {
                console.error('Error loading survey responses:', error);
                tableBody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">${translations.errorLoadingResponses || 'Error loading responses'}</td></tr>`;
            });
    }
    
    /**
     * Render survey responses table
     */
    function renderSurveyResponses(responses, pagination) {
        const translations = window.translations || {};
        const tableBody = document.getElementById('responsesTable');
        if (!tableBody) return;
        
        tableBody.innerHTML = '';
        
        responses.forEach(response => {
            const row = document.createElement('tr');
            
            // Company name
            const companyCell = document.createElement('td');
            companyCell.textContent = response.company_name || translations.na || 'N/A';
            row.appendChild(companyCell);
            
            // Contact name
            const contactCell = document.createElement('td');
            contactCell.textContent = response.contact_name || translations.na || 'N/A';
            row.appendChild(contactCell);
            
            // NPS score badge
            const npsCell = document.createElement('td');
            npsCell.className = 'text-center';
            const npsBadge = document.createElement('span');
            npsBadge.className = 'badge bg-primary';
            npsBadge.textContent = response.nps_score || 0;
            npsCell.appendChild(npsBadge);
            row.appendChild(npsCell);
            
            // Sentiment
            const sentimentCell = document.createElement('td');
            sentimentCell.textContent = response.sentiment || translations.na || 'N/A';
            row.appendChild(sentimentCell);
            
            // Date
            const dateCell = document.createElement('td');
            dateCell.textContent = response.submitted_at || translations.na || 'N/A';
            row.appendChild(dateCell);
            
            tableBody.appendChild(row);
        });
        
        // Update pagination if container exists
        if (pagination && document.getElementById('responsesPagination')) {
            renderResponsesPagination(pagination);
        }
    }
    
    /**
     * Render pagination for survey responses
     */
    function renderResponsesPagination(pagination) {
        const translations = window.translations || {};
        const container = document.getElementById('responsesPagination');
        if (!container) return;
        
        let html = '';
        
        // Previous button
        if (pagination.has_prev) {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="window.dashboardModules.surveyInsights.loadSurveyResponses(${pagination.page - 1}); return false;">&laquo;</a></li>`;
        } else {
            html += '<li class="page-item disabled"><span class="page-link">&laquo;</span></li>';
        }
        
        // Page numbers (show max 5 pages)
        const maxPages = 5;
        let startPage = Math.max(1, pagination.page - Math.floor(maxPages / 2));
        let endPage = Math.min(pagination.pages, startPage + maxPages - 1);
        
        for (let i = startPage; i <= endPage; i++) {
            if (i === pagination.page) {
                html += `<li class="page-item active"><span class="page-link">${i}</span></li>`;
            } else {
                html += `<li class="page-item"><a class="page-link" href="#" onclick="window.dashboardModules.surveyInsights.loadSurveyResponses(${i}); return false;">${i}</a></li>`;
            }
        }
        
        // Next button
        if (pagination.has_next) {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="window.dashboardModules.surveyInsights.loadSurveyResponses(${pagination.page + 1}); return false;">&raquo;</a></li>`;
        } else {
            html += '<li class="page-item disabled"><span class="page-link">&raquo;</span></li>';
        }
        
        container.innerHTML = html;
    }
    
    /**
     * Load company NPS data with pagination and filtering
     */
    function loadCompanyNpsData(page = 1, searchQuery = '', npsFilter = '') {
        const translations = window.translations || {};
        const { selectedCampaignId } = window.dashboardState;
        
        const params = new URLSearchParams({
            page: page,
            per_page: companiesPerPage
        });
        
        if (searchQuery) params.append('search', searchQuery);
        if (npsFilter) params.append('nps_filter', npsFilter);
        if (selectedCampaignId) params.append('campaign_id', selectedCampaignId);
        
        const tableBody = document.getElementById('companyNpsTable');
        if (!tableBody) {
            console.log('companyNpsTable element not found');
            return;
        }
        
        // Show loading
        tableBody.innerHTML = `<tr><td colspan="8" class="text-center"><div class="spinner-border" role="status"></div></td></tr>`;
        
        fetch(`/api/company_nps?${params}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    currentCompanyPage = page;
                    populateCompanyNpsTable(data.data, data.pagination);
                } else {
                    tableBody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">${translations.networkErrorLoadingCompanyData || 'Error loading company data'}</td></tr>`;
                }
            })
            .catch(error => {
                console.error('Error loading company NPS data:', error);
                tableBody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">${translations.networkErrorLoadingCompanyData || 'Error loading company data'}</td></tr>`;
            });
    }
    
    /**
     * Populate company NPS table
     */
    function populateCompanyNpsTable(companyData, pagination) {
        const translations = window.translations || {};
        const tableBody = document.getElementById('companyNpsTable');
        if (!tableBody) return;
        
        tableBody.innerHTML = '';
        
        companyData.forEach(company => {
            const row = document.createElement('tr');
            
            // Company name
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
            
            // Distribution
            const distCell = document.createElement('td');
            const distSmall = document.createElement('small');
            distSmall.textContent = `${company.promoters}P / ${company.passives}Pa / ${company.detractors}D`;
            distCell.appendChild(distSmall);
            row.appendChild(distCell);
            
            // Risk level
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
            responseCell.textContent = company.latest_response || translations.na || 'N/A';
            row.appendChild(responseCell);
            
            // Churn risk
            const churnCell = document.createElement('td');
            churnCell.textContent = company.latest_churn_risk || translations.na || 'N/A';
            row.appendChild(churnCell);
            
            tableBody.appendChild(row);
        });
        
        // Render pagination
        if (pagination && document.getElementById('companyNpsPagination')) {
            renderCompanyNpsPagination(pagination);
        }
    }
    
    /**
     * Render pagination for company NPS
     */
    function renderCompanyNpsPagination(pagination) {
        const translations = window.translations || {};
        const container = document.getElementById('companyNpsPagination');
        if (!container) return;
        
        let html = '';
        
        // Previous button
        if (pagination.has_prev) {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="window.dashboardModules.surveyInsights.loadCompanyNpsData(${pagination.page - 1}); return false;">&laquo;</a></li>`;
        } else {
            html += '<li class="page-item disabled"><span class="page-link">&laquo;</span></li>';
        }
        
        // Page numbers
        const maxPages = 5;
        let startPage = Math.max(1, pagination.page - Math.floor(maxPages / 2));
        let endPage = Math.min(pagination.pages, startPage + maxPages - 1);
        
        for (let i = startPage; i <= endPage; i++) {
            if (i === pagination.page) {
                html += `<li class="page-item active"><span class="page-link">${i}</span></li>`;
            } else {
                html += `<li class="page-item"><a class="page-link" href="#" onclick="window.dashboardModules.surveyInsights.loadCompanyNpsData(${i}); return false;">${i}</a></li>`;
            }
        }
        
        // Next button
        if (pagination.has_next) {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="window.dashboardModules.surveyInsights.loadCompanyNpsData(${pagination.page + 1}); return false;">&raquo;</a></li>`;
        } else {
            html += '<li class="page-item disabled"><span class="page-link">&raquo;</span></li>';
        }
        
        container.innerHTML = html;
    }
    
    /**
     * Load tenure NPS data with pagination
     */
    function loadTenureNpsData(page = 1) {
        const translations = window.translations || {};
        const { selectedCampaignId } = window.dashboardState;
        
        const params = new URLSearchParams({
            page: page,
            per_page: companiesPerPage
        });
        
        if (selectedCampaignId) params.append('campaign_id', selectedCampaignId);
        
        const tableBody = document.getElementById('tenureNpsTable');
        if (!tableBody) {
            console.log('tenureNpsTable element not found');
            return;
        }
        
        // Show loading
        tableBody.innerHTML = `<tr><td colspan="6" class="text-center"><div class="spinner-border" role="status"></div></td></tr>`;
        
        fetch(`/api/tenure_nps?${params}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    currentTenurePage = page;
                    populateTenureNpsTable(data.data, data.pagination);
                } else {
                    tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">${translations.networkErrorLoadingTenureData || 'Error loading tenure data'}</td></tr>`;
                }
            })
            .catch(error => {
                console.error('Error loading tenure NPS data:', error);
                tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">${translations.networkErrorLoadingTenureData || 'Error loading tenure data'}</td></tr>`;
            });
    }
    
    /**
     * Populate tenure NPS table
     */
    function populateTenureNpsTable(tenureData, pagination) {
        const translations = window.translations || {};
        const tableBody = document.getElementById('tenureNpsTable');
        if (!tableBody) return;
        
        tableBody.innerHTML = '';
        
        tenureData.forEach(tenure => {
            const row = document.createElement('tr');
            
            // Tenure range
            const rangeCell = document.createElement('td');
            const rangeStrong = document.createElement('strong');
            rangeStrong.textContent = tenure.tenure_range;
            rangeCell.appendChild(rangeStrong);
            row.appendChild(rangeCell);
            
            // Total responses
            const responsesCell = document.createElement('td');
            responsesCell.textContent = tenure.total_responses;
            row.appendChild(responsesCell);
            
            // Average NPS
            const avgNpsCell = document.createElement('td');
            avgNpsCell.textContent = tenure.avg_nps;
            row.appendChild(avgNpsCell);
            
            // Tenure NPS badge
            const npsCell = document.createElement('td');
            const npsBadge = document.createElement('span');
            npsBadge.className = 'badge bg-primary';
            npsBadge.textContent = tenure.tenure_nps;
            npsCell.appendChild(npsBadge);
            row.appendChild(npsCell);
            
            // Distribution
            const distCell = document.createElement('td');
            const distSmall = document.createElement('small');
            distSmall.textContent = `${tenure.promoters}P / ${tenure.passives}Pa / ${tenure.detractors}D`;
            distCell.appendChild(distSmall);
            row.appendChild(distCell);
            
            // Risk level
            const riskCell = document.createElement('td');
            const riskBadge = document.createElement('span');
            riskBadge.className = 'badge';
            riskBadge.style.backgroundColor = '#8A8A8A';
            riskBadge.style.color = 'white';
            riskBadge.textContent = tenure.risk_level;
            riskCell.appendChild(riskBadge);
            row.appendChild(riskCell);
            
            tableBody.appendChild(row);
        });
        
        // Render pagination
        if (pagination && document.getElementById('tenureNpsPagination')) {
            renderTenureNpsPagination(pagination);
        }
    }
    
    /**
     * Render pagination for tenure NPS
     */
    function renderTenureNpsPagination(pagination) {
        const translations = window.translations || {};
        const container = document.getElementById('tenureNpsPagination');
        if (!container) return;
        
        let html = '';
        
        // Previous button
        if (pagination.has_prev) {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="window.dashboardModules.surveyInsights.loadTenureNpsData(${pagination.page - 1}); return false;">&laquo;</a></li>`;
        } else {
            html += '<li class="page-item disabled"><span class="page-link">&laquo;</span></li>';
        }
        
        // Page numbers
        const maxPages = 5;
        let startPage = Math.max(1, pagination.page - Math.floor(maxPages / 2));
        let endPage = Math.min(pagination.pages, startPage + maxPages - 1);
        
        for (let i = startPage; i <= endPage; i++) {
            if (i === pagination.page) {
                html += `<li class="page-item active"><span class="page-link">${i}</span></li>`;
            } else {
                html += `<li class="page-item"><a class="page-link" href="#" onclick="window.dashboardModules.surveyInsights.loadTenureNpsData(${i}); return false;">${i}</a></li>`;
            }
        }
        
        // Next button
        if (pagination.has_next) {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="window.dashboardModules.surveyInsights.loadTenureNpsData(${pagination.page + 1}); return false;">&raquo;</a></li>`;
        } else {
            html += '<li class="page-item disabled"><span class="page-link">&raquo;</span></li>';
        }
        
        container.innerHTML = html;
    }
    
    // Export public functions
    window.dashboardModules.surveyInsights = {
        loadSurveyResponses,
        loadCompanyNpsData,
        loadTenureNpsData,
        populateCompanyNpsTable,
        populateTenureNpsTable
    };
    
    console.log('📦 Dashboard Survey Insights module loaded');
    
})();
