/**
 * Dashboard Initialization Module
 * Phase 2: Frontend Refactoring - Module orchestration entry point
 * 
 * This module orchestrates all dashboard modules and initializes the dashboard.
 * Load order: bootstrap → data-service → (charts/comparison/account-intelligence/kpi) → this file
 */

(function() {
    'use strict';
    
    const state = window.dashboardState;
    
    /**
     * Initialize campaigns - loads campaign options and dashboard data
     * This is called when all critical modules are ready (dashboardReady event)
     */
    async function initializeCampaigns() {
        if (state.campaignsInitialized) {
            console.log('⚠️ Campaigns already initialized, skipping duplicate call');
            return;
        }
        state.campaignsInitialized = true;
        console.log('🚀 All modules ready, initializing campaigns...');
        
        // Resolve module references (guaranteed to be available after dashboardReady event)
        const dataService = window.dashboardModules.dataService;
        const kpiOverview = window.dashboardModules.kpiOverview;
        
        try {
            // Load campaign filter options
            await dataService.fetchCampaignFilterOptions();
            
            // Populate dropdown and update UI
            populateCampaignFilterDropdown();
            updateGlobalCampaignIndicator();
            
            // Load initial dashboard data
            await kpiOverview.loadDashboardData();
            
            // Initialize auto-refresh (1 hour interval)
            kpiOverview.initializeAutoRefresh();
            
            console.log('✅ Dashboard initialization complete');
            
        } catch (error) {
            console.error('❌ Campaign initialization failed:', error);
        }
    }
    
    /**
     * Populate campaign filter dropdown
     */
    function populateCampaignFilterDropdown() {
        // Resolve utils at runtime to avoid race conditions
        const { escapeHtml, formatCampaignStatus, formatDate } = window.dashboardModules.bootstrap.utils;
        const translations = window.translations || {};
        const select = document.getElementById('campaignFilter');
        if (!select) return;
        
        const availableCampaigns = state.availableCampaigns || [];
        
        // Clear existing options
        select.innerHTML = '';
        
        // Check for campaign_id URL parameter first
        const urlParams = new URLSearchParams(window.location.search);
        const urlCampaignId = urlParams.get('campaign_id');
        
        // Find default campaign: URL param > session storage > active campaign > most recent
        let defaultCampaign = null;
        
        if (urlCampaignId) {
            defaultCampaign = availableCampaigns.find(c => c.id === parseInt(urlCampaignId));
            console.log('📌 Using campaign from URL parameter:', urlCampaignId, defaultCampaign);
        }
        
        // Check session storage if no URL param
        if (!defaultCampaign) {
            const storedCampaignId = sessionStorage.getItem('selectedCampaignId');
            if (storedCampaignId) {
                defaultCampaign = availableCampaigns.find(c => c.id === parseInt(storedCampaignId));
                if (defaultCampaign) {
                    console.log('🔄 Restored campaign from session storage:', storedCampaignId);
                }
            }
        }
        
        if (!defaultCampaign && availableCampaigns.length > 0) {
            // First, look for active campaign (case-insensitive comparison)
            const activeCampaign = availableCampaigns.find(c => (c.status || '').toLowerCase() === 'active');
            if (activeCampaign) {
                defaultCampaign = activeCampaign;
                console.log('✅ Found active campaign:', activeCampaign.name, activeCampaign.id);
            } else {
                // If no active campaign, get the most recent (by end_date or created_at)
                const sortedCampaigns = [...availableCampaigns].sort((a, b) => {
                    const dateA = new Date(a.end_date || a.created_at);
                    const dateB = new Date(b.end_date || b.created_at);
                    return dateB - dateA; // Most recent first
                });
                defaultCampaign = sortedCampaigns[0];
                console.log('✅ No active campaign, using most recent:', defaultCampaign.name, defaultCampaign.id);
            }
        }
        
        // Validation: warn if campaigns exist but no default was set
        if (availableCampaigns.length > 0 && !defaultCampaign) {
            console.warn('⚠️ Campaigns available but no default selected!', availableCampaigns);
        }
        
        // Debug logging
        console.log('📋 Populating dropdown with', availableCampaigns.length, 'campaigns');
        console.log('📋 Default campaign:', defaultCampaign);
        
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
            
            // Set as selected if this is the default campaign
            if (defaultCampaign && campaign.id === defaultCampaign.id) {
                option.selected = true;
                state.selectedCampaignId = campaign.id;
                console.log('✅ Selected campaign:', campaign.name, campaign.id);
                
                // Save raw values to sessionStorage for global indicator
                sessionStorage.setItem('selectedCampaignId', campaign.id);
                sessionStorage.setItem('selectedCampaignName', campaign.name);
                sessionStorage.setItem('selectedCampaignStartDate', campaign.start_date);
                sessionStorage.setItem('selectedCampaignEndDate', campaign.end_date);
                sessionStorage.setItem('selectedCampaignStatus', rawStatus);
            }
            
            select.appendChild(option);
        });
        
        // Update the selected campaign info display
        if (defaultCampaign) {
            updateSelectedCampaignInfo();
        }
        
        // Return whether a default campaign was set (used by initializeCampaigns)
        return !!defaultCampaign;
    }
    
    /**
     * Update selected campaign info display
     */
    function updateSelectedCampaignInfo() {
        const select = document.getElementById('campaignFilter');
        
        if (state.selectedCampaignId && select && select.selectedOptions.length > 0) {
            const option = select.selectedOptions[0];
            const startDate = option.getAttribute('data-start');
            const endDate = option.getAttribute('data-end');
            const rawStatus = option.getAttribute('data-status');
            const displayStatus = option.getAttribute('data-status-display');
            
            // Update dates badge text
            const datesText = document.querySelector('.campaign-dates-text');
            if (datesText) {
                datesText.textContent = `${formatDate(startDate)} - ${formatDate(endDate)}`;
            }
            
            // Update status badge with proper styling
            const statusBadge = document.getElementById('selectedCampaignStatus');
            const statusText = document.querySelector('.campaign-status-text');
            if (statusBadge && statusText) {
                statusText.textContent = displayStatus;
                if (rawStatus === 'active') {
                    statusBadge.style.backgroundColor = '#28a745';
                    statusBadge.style.color = 'white';
                } else {
                    statusBadge.style.backgroundColor = '#6c757d';
                    statusBadge.style.color = 'white';
                }
            }
        }
    }
    
    /**
     * Update global campaign indicator
     */
    function updateGlobalCampaignIndicator() {
        // Resolve utils at runtime to avoid race conditions
        const { escapeHtml, formatDate } = window.dashboardModules.bootstrap.utils;
        const translations = window.translations || {};
        const indicator = document.getElementById('globalCampaignIndicator');
        if (!indicator) return; // Not on a page with the indicator
        
        const campaignId = sessionStorage.getItem('selectedCampaignId');
        const campaignName = sessionStorage.getItem('selectedCampaignName');
        const campaignStartDate = sessionStorage.getItem('selectedCampaignStartDate');
        const campaignEndDate = sessionStorage.getItem('selectedCampaignEndDate');
        
        if (campaignId && campaignName) {
            // Format dates for display
            const formattedDates = `${formatDate(campaignStartDate)} - ${formatDate(campaignEndDate)}`;
            
            indicator.innerHTML = `
                <div class="campaign-filter-badge">
                    <i class="fas fa-filter me-2"></i>
                    <strong>${translations.filteredBy || 'Filtered by'}</strong> ${escapeHtml(campaignName)}
                    <span class="badge bg-light text-dark ms-2">${escapeHtml(formattedDates)}</span>
                    <button class="btn btn-sm btn-link text-danger ms-2 p-0" onclick="window.dashboardModules.init.clearGlobalCampaignFilter()" title="${translations.clearFilter || 'Clear filter'}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            indicator.style.display = 'block';
        } else {
            indicator.style.display = 'none';
        }
    }
    
    /**
     * Clear global campaign filter
     */
    function clearGlobalCampaignFilter() {
        sessionStorage.removeItem('selectedCampaignId');
        sessionStorage.removeItem('selectedCampaignName');
        sessionStorage.removeItem('selectedCampaignStartDate');
        sessionStorage.removeItem('selectedCampaignEndDate');
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
    
    /**
     * Apply campaign filter
     */
    async function applyCampaignFilter() {
        const select = document.getElementById('campaignFilter');
        state.selectedCampaignId = select.value ? parseInt(select.value) : null;
        
        console.log('🎯 Campaign filter applied:', state.selectedCampaignId);
        
        // Save raw values to session storage for persistence across pages
        if (state.selectedCampaignId && select.selectedOptions.length > 0) {
            const option = select.selectedOptions[0];
            sessionStorage.setItem('selectedCampaignId', state.selectedCampaignId);
            sessionStorage.setItem('selectedCampaignName', option.getAttribute('data-name'));
            sessionStorage.setItem('selectedCampaignStartDate', option.getAttribute('data-start'));
            sessionStorage.setItem('selectedCampaignEndDate', option.getAttribute('data-end'));
            sessionStorage.setItem('selectedCampaignStatus', option.getAttribute('data-status'));
        } else {
            sessionStorage.removeItem('selectedCampaignId');
            sessionStorage.removeItem('selectedCampaignName');
            sessionStorage.removeItem('selectedCampaignStartDate');
            sessionStorage.removeItem('selectedCampaignEndDate');
            sessionStorage.removeItem('selectedCampaignStatus');
        }
        
        // Update selected campaign info
        updateSelectedCampaignInfo();
        
        // Reload data using kpiOverview module
        if (window.dashboardModules.kpiOverview) {
            await window.dashboardModules.kpiOverview.loadDashboardData();
        }
        
        // Update global indicator
        updateGlobalCampaignIndicator();
    }
    
    // Register event listener for dashboard ready (all critical modules loaded)
    window.addEventListener('dashboardReady', initializeCampaigns);
    
    // Export public API
    window.dashboardModules.init = {
        initializeCampaigns,
        applyCampaignFilter,
        populateCampaignFilterDropdown,
        updateGlobalCampaignIndicator,
        updateSelectedCampaignInfo,
        clearGlobalCampaignFilter
    };
    
    console.log('📦 Dashboard Init module loaded');
    
})();
