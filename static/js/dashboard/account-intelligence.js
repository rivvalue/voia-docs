/**
 * Dashboard Account Intelligence Module
 * Phase 3: Frontend Refactoring - Sprint 2
 * 
 * This module handles account intelligence tables, pills, modals, pagination, and filtering.
 * Migrated from dashboard.js (~822 lines)
 */

(function() {
    'use strict';
    
    // Import shared utilities from bootstrap
    const { escapeHtml, generatePaginationPages } = window.dashboardModules.bootstrap.utils;
    
    // Module-level state
    let accountIntelCurrentPage = 1;
    let accountIntelSearchTimeout = null;
    
    /**
     * Populate high-risk accounts section (legacy snapshot-based)
     */
    function populateHighRiskAccounts() {
        const { data: dashboardData } = window.dashboardState;
        const translations = window.translations;
        
        const container = document.getElementById('highRiskAccounts');
        const highRiskAccounts = dashboardData?.high_risk_accounts || [];
        
        if (highRiskAccounts.length === 0) {
            container.innerHTML = '<p class="text-muted">No high-risk accounts identified.</p>';
            return;
        }
        
        // Get campaign info for drill-down
        const campaignSelect = document.getElementById('campaignFilter');
        const campaignId = campaignSelect && campaignSelect.value ? campaignSelect.value : null;
        const campaignName = campaignSelect && campaignId ? campaignSelect.options[campaignSelect.selectedIndex].text : 'Current Campaign';
        
        const html = highRiskAccounts.map(account => `
            <div class="risk-card p-3 mb-3 rounded">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1">
                            <a href="#" onclick="openCompanyResponsesModal('${escapeHtml(account.company_name).replace(/'/g, "\\'")}', ${campaignId ? campaignId : 'null'}, '${escapeHtml(campaignName).replace(/'/g, "\\'")}'); return false;" 
                               style="color: #2E5090; text-decoration: none; cursor: pointer;"
                               onmouseover="this.style.textDecoration='underline';"
                               onmouseout="this.style.textDecoration='none';"
                               title="Click to view all responses from ${escapeHtml(account.company_name)}">
                                ${escapeHtml(account.company_name)}
                                <i class="fas fa-external-link-alt ms-2" style="font-size: 0.7em; color: #8A8A8A;"></i>
                            </a>
                        </h6>
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
    
    /**
     * Populate growth opportunities section (legacy snapshot-based)
     */
    function populateGrowthOpportunities() {
        const { data: dashboardData } = window.dashboardState;
        
        const container = document.getElementById('growthOpportunities');
        const companiesWithOpportunities = dashboardData?.growth_opportunities || [];
        
        if (companiesWithOpportunities.length === 0) {
            container.innerHTML = '<p class="text-muted">No growth opportunities identified.</p>';
            return;
        }
        
        const html = companiesWithOpportunities.map(company => {
            const companyName = company.company_name || 'Unknown Company';
            const opportunities = company.opportunities || [];
            
            if (opportunities.length === 0) {
                return '';
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
        }).filter(html => html !== '').join('');
        
        if (html === '') {
            container.innerHTML = '<p class="text-muted">No growth opportunities identified.</p>';
            return;
        }
        
        container.innerHTML = html;
    }
    
    /**
     * Get visual indicator for risk factors and opportunities
     */
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
    
    /**
     * Normalize type strings for visual indicators
     */
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
            
            // Opportunity mappings
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
        
        // Keyword-based categorization
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
        
        // Fallback: convert to snake_case
        return originalType.toLowerCase().replace(/\s+/g, '_');
    }
    
    /**
     * Populate account intelligence (legacy snapshot-based with NPS enrichment)
     */
    function populateAccountIntelligence() {
        const { data: dashboardData } = window.dashboardState;
        
        const container = document.getElementById('accountIntelligence');
        let accountData = dashboardData?.account_intelligence || [];
        
        if (accountData.length === 0) {
            container.innerHTML = '<p class="text-muted">No account intelligence data available.</p>';
            return;
        }
        
        // Enrich account data with NPS from company_nps_data
        const companyNpsData = dashboardData?.company_nps_data || [];
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
            <div class="account-health-legend mb-4 p-3 rounded" style="background-color: #E9E8E4; border: 1px solid #BDBDBD;">
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
            
            const balanceIcon = '●';
            const balanceIconColor = account.balance === 'risk_heavy' ? '#E13A44' : 
                                   account.balance === 'opportunity_heavy' ? '#8A8A8A' : '#BDBDBD';
            
            const balanceLabel = account.balance === 'risk_heavy' ? 'Risk-Heavy' : 
                               account.balance === 'opportunity_heavy' ? 'High Potential' : 'Balanced';
            
            // Consolidate opportunities by type
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
            
            // Create visual indicators for opportunities
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
            
            // Consolidate risks by type
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
            
            // Create visual indicators for risks
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
                        
                        <div class="account-details mb-3 p-2 rounded" style="background-color: #E9E8E4; border: 1px solid #BDBDBD;">
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
        
        // Apply color overrides if available
        if (typeof applyColorOverrides === 'function') {
            applyColorOverrides(container, 100);
        }
    }
    
    /**
     * Load account intelligence via API (with pagination and filtering)
     */
    function loadAccountIntelligence(page = 1) {
        const translations = window.translations || {};
        
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
                    container.innerHTML = `<div class="alert alert-danger">${translations.errorLoadingAccountIntelligence}</div>`;
                }
            })
            .catch(error => {
                console.error('Error loading account intelligence:', error);
                container.innerHTML = '<div class="alert alert-danger">Error: ' + error.message + '</div>';
            });
    }
    
    /**
     * Render account intelligence data with pagination
     */
    function renderAccountIntelligence(accountData, pagination) {
        const container = document.getElementById('accountIntelligence');
        
        if (accountData.length === 0) {
            container.innerHTML = '<p class="text-muted">No accounts match the selected filters.</p>';
            document.getElementById('accountIntelPaginationContainer').style.display = 'none';
            return;
        }
        
        // Create legend (same as snapshot version)
        const legendHtml = `
            <div class="account-health-legend mb-4 p-3 rounded" style="background-color: #E9E8E4; border: 1px solid #BDBDBD;">
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
        
        // Render accounts
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
                        
                        <div class="account-details mb-3 p-2 rounded" style="background-color: #E9E8E4; border: 1px solid #BDBDBD;">
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
    
    /**
     * Render pagination controls for account intelligence
     */
    function renderAccountIntelPagination(pagination) {
        const translations = window.translations || {};
        const paginationContainer = document.getElementById('accountIntelPagination');
        const pages = generatePaginationPages(pagination.page, pagination.pages);
        
        let paginationHtml = '';
        
        // Previous button
        paginationHtml += `
            <li class="page-item ${!pagination.has_prev ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="loadAccountIntelligence(${pagination.page - 1}); return false;" aria-label="${translations.previous}">
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
                <a class="page-link" href="#" onclick="loadAccountIntelligence(${pagination.page + 1}); return false;" aria-label="${translations.next}">
                    <span aria-hidden="true">&raquo;</span>
                </a>
            </li>
        `;
        
        paginationContainer.innerHTML = paginationHtml;
    }
    
    /**
     * Debounced search for account intelligence
     */
    function searchAccountIntelligence() {
        clearTimeout(accountIntelSearchTimeout);
        accountIntelSearchTimeout = setTimeout(() => {
            loadAccountIntelligence(1); // Reset to page 1 when searching
        }, 300);
    }
    
    /**
     * Update filter UI with counts and active filter badges
     */
    function updateAccountIntelFiltersUI(total, filtersApplied) {
        const translations = window.translations || {};
        
        // Update count display
        const countElement = document.getElementById('accountIntelCount');
        const start = (accountIntelCurrentPage - 1) * 10 + 1;
        const end = Math.min(accountIntelCurrentPage * 10, total);
        countElement.textContent = `${translations.showing} ${start}-${end} ${translations.of} ${total} ${translations.accounts}`;
        
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
    
    /**
     * Clear all account intelligence filters
     */
    function clearAccountIntelFilters() {
        document.getElementById('accountIntelSearch').value = '';
        document.getElementById('accountBalanceFilter').value = '';
        document.getElementById('accountRiskFilter').value = '';
        document.getElementById('accountOppFilter').value = '';
        document.getElementById('accountRisksFilter').value = '';
        loadAccountIntelligence(1);
    }
    
    /**
     * Populate account risk factors (legacy snapshot-based, DOM-safe)
     */
    function populateAccountRiskFactors() {
        const { data: dashboardData } = window.dashboardState;
        
        const container = document.getElementById('accountRiskFactors');
        const companiesWithRiskFactors = dashboardData?.account_risk_factors || [];
        
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
            if (!company.company_name || !company.risk_factors || !Array.isArray(company.risk_factors)) {
                return;
            }
            
            const companyDiv = document.createElement('div');
            companyDiv.className = 'company-risk-factors mb-4';
            
            const companyHeader = document.createElement('h6');
            companyHeader.className = 'company-name text-dark mb-3';
            companyHeader.textContent = company.company_name;
            companyDiv.appendChild(companyHeader);
            
            company.risk_factors.forEach(risk => {
                const severityClass = risk.severity === 'Critical' ? 'danger' : 
                                     risk.severity === 'High' ? 'danger' : 
                                     risk.severity === 'Medium' ? 'secondary' : 'secondary';
                
                const riskDiv = document.createElement('div');
                riskDiv.className = 'risk-factor-item mb-3 p-3 border rounded';
                
                const headerDiv = document.createElement('div');
                headerDiv.className = 'd-flex justify-content-between align-items-start mb-2';
                
                const typeHeader = document.createElement('h6');
                typeHeader.className = 'risk-type mb-1';
                typeHeader.textContent = risk.type;
                
                const severityBadge = document.createElement('span');
                severityBadge.className = `badge bg-${severityClass}`;
                severityBadge.textContent = risk.severity;
                
                headerDiv.appendChild(typeHeader);
                headerDiv.appendChild(severityBadge);
                riskDiv.appendChild(headerDiv);
                
                const descriptionP = document.createElement('p');
                descriptionP.className = 'risk-description text-muted mb-2';
                descriptionP.textContent = risk.description;
                riskDiv.appendChild(descriptionP);
                
                const actionSmall = document.createElement('small');
                actionSmall.className = 'risk-action text-primary';
                const actionStrong = document.createElement('strong');
                actionStrong.textContent = 'Recommended Action: ';
                actionSmall.appendChild(actionStrong);
                actionSmall.appendChild(document.createTextNode(risk.action));
                riskDiv.appendChild(actionSmall);
                
                if (risk.count > 1) {
                    const countDiv = document.createElement('div');
                    countDiv.className = 'text-end';
                    const countSmall = document.createElement('small');
                    countSmall.className = 'text-muted';
                    countSmall.textContent = `${risk.count} occurrences`;
                    countDiv.appendChild(countSmall);
                    riskDiv.appendChild(countDiv);
                }
                
                companyDiv.appendChild(riskDiv);
            });
            
            container.appendChild(companyDiv);
        });
    }
    
    // Export public functions
    window.dashboardModules.accountIntelligence = {
        populateHighRiskAccounts,
        populateGrowthOpportunities,
        populateAccountIntelligence,
        loadAccountIntelligence,
        renderAccountIntelligence,
        searchAccountIntelligence,
        clearAccountIntelFilters,
        populateAccountRiskFactors
    };
    
    console.log('📦 Dashboard Account Intelligence module loaded');
    
})();
