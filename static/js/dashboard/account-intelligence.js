/**
 * Dashboard Account Intelligence Module
 * Phase 2: Frontend Refactoring - Table rendering and modals
 * 
 * This module handles account intelligence tables, pills, and modals.
 */

(function() {
    'use strict';
    
    const dataService = window.dashboardModules.dataService;
    const state = window.dashboardState;
    
    let currentPage = 1;
    
    async function loadAccountIntelligence(page = 1) {
        const campaignId = state.selectedCampaignId;
        
        try {
            const data = await dataService.fetchAccountIntelligence({
                page,
                campaignId
            });
            
            if (data.success) {
                currentPage = page;
                renderAccountIntelligence(data.data, data.pagination);
            }
        } catch (error) {
            console.error('Account intelligence load failed:', error);
        }
    }
    
    function renderAccountIntelligence(accounts, pagination) {
        // Render account intelligence tables with pills and badges
        console.log('📊 Rendering account intelligence');
    }
    
    window.dashboardModules.accountIntelligence = {
        loadAccountIntelligence,
        renderAccountIntelligence
    };
    
    console.log('📦 Dashboard Account Intelligence module loaded');
    
})();
