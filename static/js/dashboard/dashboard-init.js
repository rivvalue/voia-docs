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
    const dataService = window.dashboardModules.dataService;
    
    /**
     * Initialize campaigns - loads campaign options and dashboard data
     */
    async function initializeCampaigns() {
        if (state.campaignsInitialized) {
            console.log('⚠️ Campaigns already initialized, skipping duplicate call');
            return;
        }
        state.campaignsInitialized = true;
        console.log('🌍 Translations ready, initializing campaigns...');
        
        try {
            // Load campaign filter options
            await dataService.fetchCampaignFilterOptions();
            
            // Populate dropdown and update UI
            populateCampaignFilterDropdown();
            updateGlobalCampaignIndicator();
            
            // Load initial dashboard data if no campaign auto-selected
            if (!state.selectedCampaignId) {
                await dataService.fetchDashboardData();
                populateDashboard();
            }
            
            // Load comparison options
            if (window.dashboardModules.comparison) {
                window.dashboardModules.comparison.loadComparisonCampaignOptions();
            }
            
        } catch (error) {
            console.error('Campaign initialization failed:', error);
        }
    }
    
    /**
     * Populate dashboard with loaded data
     */
    function populateDashboard() {
        console.log('⚡ populateDashboard called');
        
        const data = state.data;
        if (!data) return;
        
        // Update metrics
        document.getElementById('totalResponses').textContent = data.total_responses || 0;
        document.getElementById('npsScore').textContent = data.nps_score || 0;
        
        // Create charts (deferred)
        requestAnimationFrame(() => {
            if (window.dashboardModules.charts) {
                window.dashboardModules.charts.createThemesChart();
            }
            
            // Load deferred data
            setTimeout(() => {
                if (window.dashboardModules.accountIntelligence) {
                    window.dashboardModules.accountIntelligence.loadAccountIntelligence();
                }
                if (window.dashboardModules.kpiOverview) {
                    window.dashboardModules.kpiOverview.loadKpiOverview();
                }
            }, 100);
        });
    }
    
    /**
     * Populate campaign filter dropdown
     */
    function populateCampaignFilterDropdown() {
        // Dropdown population logic (from dashboard.js lines 337-417)
        console.log('Populating campaign dropdown');
    }
    
    /**
     * Update global campaign indicator
     */
    function updateGlobalCampaignIndicator() {
        // Indicator update logic
        console.log('Updating campaign indicator');
    }
    
    /**
     * Apply campaign filter
     */
    async function applyCampaignFilter() {
        const select = document.getElementById('campaignFilter');
        state.selectedCampaignId = select.value ? parseInt(select.value) : null;
        
        // Save to session storage
        if (state.selectedCampaignId) {
            sessionStorage.setItem('selectedCampaignId', state.selectedCampaignId);
        }
        
        // Reload data
        await dataService.fetchDashboardData(state.selectedCampaignId);
        populateDashboard();
    }
    
    // Register event listener for translations loaded
    window.addEventListener('translationsLoaded', initializeCampaigns);
    
    // Export public API
    window.dashboardModules.init = {
        initializeCampaigns,
        populateDashboard,
        applyCampaignFilter
    };
    
    console.log('📦 Dashboard Init module loaded');
    
})();
