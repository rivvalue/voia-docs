/**
 * Dashboard Data Service Module
 * Phase 2: Frontend Refactoring - Centralized API data fetching
 * 
 * This module owns ALL fetch/API calls and is the sole writer to dashboardState.
 * It exposes promise-returning helpers that never touch the DOM.
 * Other modules consume these helpers to avoid duplicated fetch logic.
 */

(function() {
    'use strict';
    
    const state = window.dashboardState;
    
    // ============================================================================
    // CAMPAIGN FILTER DATA
    // ============================================================================
    
    /**
     * Load campaign filter options
     * @returns {Promise<Array>} Campaign list
     */
    async function fetchCampaignFilterOptions() {
        try {
            const response = await fetch('/api/campaigns/filter-options');
            if (response.ok) {
                const data = await response.json();
                // API returns availableCampaigns (fallback to campaigns for backward compatibility)
                const campaigns = data.availableCampaigns || data.campaigns;
                
                if (!campaigns) {
                    console.error('API response missing campaigns data:', data);
                    throw new Error('Invalid API response: missing campaign data');
                }
                
                state.availableCampaigns = campaigns;
                console.log('✅ Loaded campaigns:', campaigns.length, 'campaigns');
                return campaigns;
            }
            throw new Error('Failed to load campaign options');
        } catch (error) {
            console.error('Error loading campaign filter options:', error);
            throw error;
        }
    }
    
    // ============================================================================
    // DASHBOARD DATA
    // ============================================================================
    
    /**
     * Load main dashboard data
     * @param {number|null} campaignId - Optional campaign filter
     * @returns {Promise<Object>} Dashboard data
     */
    async function fetchDashboardData(campaignId = null) {
        const urlParams = new URLSearchParams();
        
        if (campaignId) {
            urlParams.append('campaign_id', campaignId);
        }
        urlParams.append('_t', Date.now()); // Cache-busting
        
        const url = '/api/dashboard_data?' + urlParams.toString();
        
        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            state.data = data;
            return data;
            
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            throw error;
        }
    }
    
    // ============================================================================
    // CAMPAIGN COMPARISON DATA
    // ============================================================================
    
    /**
     * Load campaign comparison data
     * @param {number} campaign1Id - First campaign ID
     * @param {number} campaign2Id - Second campaign ID
     * @returns {Promise<Object>} Comparison data
     */
    async function fetchCampaignComparison(campaign1Id, campaign2Id) {
        try {
            const response = await fetch(`/api/campaigns/comparison?campaign1=${campaign1Id}&campaign2=${campaign2Id}`);
            
            if (!response.ok) {
                throw new Error('Failed to fetch comparison data');
            }
            
            const data = await response.json();
            return data;
            
        } catch (error) {
            console.error('Error loading comparison data:', error);
            throw error;
        }
    }
    
    // ============================================================================
    // ACCOUNT INTELLIGENCE DATA
    // ============================================================================
    
    /**
     * Load account intelligence data with pagination and filters
     * @param {Object} options - Query options
     * @returns {Promise<Object>} Account intelligence data with pagination
     */
    async function fetchAccountIntelligence(options = {}) {
        const params = new URLSearchParams({
            page: options.page || 1,
            per_page: options.perPage || 10
        });
        
        if (options.search) params.append('search', options.search);
        if (options.balance) params.append('balance', options.balance);
        if (options.riskLevel) params.append('risk_level', options.riskLevel);
        if (options.hasOpportunities) params.append('has_opportunities', options.hasOpportunities);
        if (options.hasRisks) params.append('has_risks', options.hasRisks);
        if (options.campaignId) params.append('campaign', options.campaignId);
        
        try {
            const response = await fetch(`/api/account_intelligence?${params}`);
            const data = await response.json();
            
            if (!data.success) {
                throw new Error('Failed to load account intelligence');
            }
            
            return data;
            
        } catch (error) {
            console.error('Error loading account intelligence:', error);
            throw error;
        }
    }
    
    // ============================================================================
    // SURVEY RESPONSES DATA
    // ============================================================================
    
    /**
     * Load survey responses with pagination and filters
     * @param {Object} options - Query options
     * @returns {Promise<Object>} Survey responses data
     */
    async function fetchSurveyResponses(options = {}) {
        const params = new URLSearchParams({
            page: options.page || 1
        });
        
        if (options.search) params.append('search', options.search);
        if (options.npsFilter) params.append('nps_filter', options.npsFilter);
        if (options.campaignId) params.append('campaign_id', options.campaignId);
        
        const url = `/api/survey_responses?${params}`;
        
        try {
            const response = await fetch(url);
            const data = await response.json();
            return data;
            
        } catch (error) {
            console.error('Error loading survey responses:', error);
            throw error;
        }
    }
    
    // ============================================================================
    // TENURE NPS DATA
    // ============================================================================
    
    /**
     * Load tenure-based NPS data
     * @param {Object} options - Query options
     * @returns {Promise<Object>} Tenure NPS data
     */
    async function fetchTenureNpsData(options = {}) {
        const params = new URLSearchParams({
            page: options.page || 1
        });
        
        if (options.campaignId) params.append('campaign_id', options.campaignId);
        
        const url = `/api/tenure_nps?${params}`;
        
        try {
            const response = await fetch(url);
            const data = await response.json();
            return data;
            
        } catch (error) {
            console.error('Error loading tenure NPS data:', error);
            throw error;
        }
    }
    
    // ============================================================================
    // COMPANY NPS DATA
    // ============================================================================
    
    /**
     * Load company-based NPS data
     * @param {Object} options - Query options
     * @returns {Promise<Object>} Company NPS data
     */
    async function fetchCompanyNpsData(options = {}) {
        const params = new URLSearchParams({
            page: options.page || 1
        });
        
        if (options.search) params.append('search', options.search);
        if (options.npsFilter) params.append('nps_filter', options.npsFilter);
        if (options.campaignId) params.append('campaign_id', options.campaignId);
        
        const url = `/api/company_nps?${params}`;
        
        try {
            const response = await fetch(url);
            const data = await response.json();
            return data;
            
        } catch (error) {
            console.error('Error loading company NPS data:', error);
            throw error;
        }
    }
    
    // ============================================================================
    // KPI OVERVIEW DATA
    // ============================================================================
    
    /**
     * Load KPI overview data for executive summary
     * @returns {Promise<Object>} KPI overview data
     */
    async function fetchKpiOverview() {
        try {
            const campaignResponse = await fetch('/api/campaigns/filter-options');
            if (!campaignResponse.ok) {
                throw new Error('Failed to load campaigns for KPI overview');
            }
            
            const campaignData = await campaignResponse.json();
            const campaigns = campaignData.campaigns;
            
            if (!campaigns || campaigns.length === 0) {
                return { campaigns: [], kpiData: [] };
            }
            
            // Fetch comparison data for each campaign (comparing with itself for single-campaign KPIs)
            const kpiPromises = campaigns.map(campaign =>
                fetch(`/api/campaigns/comparison?campaign1=${campaign.id}&campaign2=${campaign.id}`)
                    .then(r => r.json())
                    .catch(err => {
                        console.warn(`Failed to load KPI for campaign ${campaign.id}:`, err);
                        return null;
                    })
            );
            
            const kpiResults = await Promise.all(kpiPromises);
            const kpiData = kpiResults.filter(result => result !== null);
            
            state.kpiOverviewData = { campaigns, kpiData };
            return { campaigns, kpiData };
            
        } catch (error) {
            console.error('Error loading KPI overview:', error);
            throw error;
        }
    }
    
    // ============================================================================
    // COMPANY RESPONSES DATA
    // ============================================================================
    
    /**
     * Load company-specific responses
     * @param {string} companyName - Company name to filter
     * @param {Object} options - Query options
     * @returns {Promise<Object>} Company responses data
     */
    async function fetchCompanyResponses(companyName, options = {}) {
        const params = new URLSearchParams({
            company: companyName
        });
        
        if (options.campaignId) params.append('campaign_id', options.campaignId);
        
        const url = `/api/company_responses?${params}`;
        
        try {
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            return data;
            
        } catch (error) {
            console.error('Error loading company responses:', error);
            throw error;
        }
    }
    
    // ============================================================================
    // EXPORT FUNCTIONS
    // ============================================================================
    
    /**
     * Export dashboard data
     * @returns {Promise<Blob>} CSV file blob
     */
    async function exportDashboardData() {
        try {
            const response = await fetch('/api/export_data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
                },
                body: JSON.stringify({})
            });
            
            if (!response.ok) {
                throw new Error('Export failed');
            }
            
            const blob = await response.blob();
            return blob;
            
        } catch (error) {
            console.error('Error exporting data:', error);
            throw error;
        }
    }
    
    /**
     * Export user-specific response data
     * @returns {Promise<Blob>} CSV file blob
     */
    async function exportUserData() {
        try {
            const response = await fetch('/api/export_user_data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
                }
            });
            
            if (!response.ok) {
                throw new Error('Export failed');
            }
            
            const blob = await response.blob();
            return blob;
            
        } catch (error) {
            console.error('Error exporting user data:', error);
            throw error;
        }
    }
    
    // ============================================================================
    // MODULE EXPORTS
    // ============================================================================
    
    window.dashboardModules.dataService = {
        fetchCampaignFilterOptions,
        fetchDashboardData,
        fetchCampaignComparison,
        fetchAccountIntelligence,
        fetchSurveyResponses,
        fetchTenureNpsData,
        fetchCompanyNpsData,
        fetchKpiOverview,
        fetchCompanyResponses,
        exportDashboardData,
        exportUserData
    };
    
    console.log('📦 Dashboard Data Service module loaded');
    
})();
