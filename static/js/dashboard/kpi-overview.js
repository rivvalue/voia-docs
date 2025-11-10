/**
 * Dashboard KPI Overview Module  
 * Phase 3: Frontend Refactoring - Sprint 4
 * 
 * This module handles data loading, dashboard population, KPI metrics, and export functionality.
 * Migrated from dashboard.js (~441 lines total)
 */

(function() {
    'use strict';
    
    // Import utilities from bootstrap
    const { escapeHtml } = window.dashboardModules.bootstrap.utils;
    
    /**
     * Load dashboard data from API
     */
    function loadDashboardData() {
        const { selectedCampaignId } = window.dashboardState;
        const translations = window.translations || {};
        
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
                
                // Store in global state (both data and dashboardData for compatibility)
                window.dashboardState.data = data;
                
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
                const pageOverlay = document.getElementById('page-overlay');
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
                    errorDiv.textContent = (translations.errorLoadingDashboardData || 'Error loading dashboard data: ') + error.message;
                    
                    // Clear loading element and append error
                    loadingElement.innerHTML = '';
                    loadingElement.appendChild(errorDiv);
                }
                // Re-throw error to maintain Promise chain behavior
                throw error;
            });
    }
    
    /**
     * Populate dashboard with KPIs and charts (orchestration layer)
     */
    function populateDashboard() {
        const { data: dashboardData } = window.dashboardState;
        
        console.log('⚡ populateDashboard called - OPTIMIZED PROGRESSIVE LOADING');
        
        // ========== CRITICAL PATH: Immediate rendering (unblock browser) ==========
        // Update key metrics (visible immediately)
        document.getElementById('totalResponses').textContent = dashboardData.total_responses || 0;
        document.getElementById('npsScore').textContent = dashboardData.nps_score || 0;
        document.getElementById('recentResponses').textContent = dashboardData.recent_responses || 0;
        document.getElementById('highRiskCount').textContent = dashboardData.high_risk_accounts?.length || 0;
        
        // Growth potential as percentage
        const growthPotential = dashboardData.growth_factor_analysis?.total_growth_potential || 0;
        document.getElementById('growthPotential').textContent = Math.round(growthPotential * 100) + '%';
        
        // Populate high risk accounts (visible on Overview tab) - from account-intelligence module
        if (window.dashboardModules.accountIntelligence?.populateHighRiskAccounts) {
            window.dashboardModules.accountIntelligence.populateHighRiskAccounts();
        }
        
        // Create themes chart (visible on Overview tab) - defer slightly for smooth rendering
        if (window.dashboardModules.charts?.createThemesChart) {
            setTimeout(() => window.dashboardModules.charts.createThemesChart(), 50);
        }
        
        // Set up tab event listeners immediately (needed for tab switching)
        if (typeof setupTabEventListeners === 'function') {
            setupTabEventListeners();
        }
        
        // ========== DEFERRED PATH: Load non-visible data asynchronously (unblock UI) ==========
        // Use requestAnimationFrame to defer heavy operations to next frame
        requestAnimationFrame(() => {
            console.log('⏳ Loading deferred data (non-blocking)...');
            
            // Defer account intelligence (Analytics tab - not visible initially)
            if (window.dashboardModules.accountIntelligence?.loadAccountIntelligence) {
                setTimeout(() => window.dashboardModules.accountIntelligence.loadAccountIntelligence(), 100);
            }
            
            // Defer KPI overview (Executive Summary section - below the fold initially)
            setTimeout(() => loadKpiOverview(), 150);
            
            // Defer survey responses (Survey Insights tab - not visible initially)
            if (window.dashboardModules.surveyInsights?.loadSurveyResponses) {
                setTimeout(() => window.dashboardModules.surveyInsights.loadSurveyResponses(), 200);
            }
            
            // Defer company NPS data (Analytics tab - not visible initially)
            if (window.dashboardModules.surveyInsights?.loadCompanyNpsData) {
                setTimeout(() => {
                    console.log('About to call loadCompanyNpsData...');
                    window.dashboardModules.surveyInsights.loadCompanyNpsData();
                }, 250);
            }
            
            // Defer tenure NPS data (Analytics tab - not visible initially)
            if (window.dashboardModules.surveyInsights?.loadTenureNpsData) {
                setTimeout(() => {
                    console.log('About to call loadTenureNpsData...');
                    window.dashboardModules.surveyInsights.loadTenureNpsData();
                }, 300);
            }
            
            console.log('✅ Deferred data loading scheduled');
        });
        
        console.log('✅ Critical path complete - page interactive');
    }
    
    /**
     * Load KPI overview section
     */
    function loadKpiOverview() {
        console.log('📊 Loading KPI overview section');
        // KPI overview rendering logic here (placeholder for future implementation)
    }
    
    /**
     * Helper function to get active campaign ID
     */
    function getActiveCampaignId() {
        const { availableCampaigns } = window.dashboardState;
        // Find active campaign from available campaigns
        const activeCampaign = availableCampaigns.find(c => c.status === 'active');
        return activeCampaign ? activeCampaign.id : null;
    }
    
    /**
     * Refresh dashboard data
     */
    function refreshData() {
        loadDashboardData().catch(error => {
            console.error('Dashboard reload after tab switch failed:', error);
        });
        
        // Also reload company NPS data if available
        if (window.dashboardModules.surveyInsights?.loadCompanyNpsData) {
            window.dashboardModules.surveyInsights.loadCompanyNpsData();
        }
    }
    
    /**
     * Export all survey data (admin functionality)
     */
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
    
    /**
     * Export user-specific data (current user's responses only)
     */
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
    
    /**
     * Redirect to business login
     */
    function redirectToBusinessLogin() {
        window.location.href = '/business/login';
    }
    
    /**
     * Business logout
     */
    function businessLogout() {
        window.location.href = '/business/logout';
    }
    
    /**
     * Initialize auto-refresh (every 1 hour)
     */
    function initializeAutoRefresh() {
        setInterval(refreshData, 60 * 60 * 1000);
    }
    
    // Export public functions
    window.dashboardModules.kpiOverview = {
        loadDashboardData,
        populateDashboard,
        loadKpiOverview,
        getActiveCampaignId,
        refreshData,
        exportData,
        exportUserData,
        redirectToBusinessLogin,
        businessLogout,
        initializeAutoRefresh
    };
    
    console.log('📦 Dashboard KPI Overview module loaded');
    
})();
