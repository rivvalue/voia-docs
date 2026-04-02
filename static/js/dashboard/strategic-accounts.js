/**
 * Dashboard Strategic Accounts Module
 * Task #57: Strategic Accounts dedicated dashboard view
 *
 * Handles on-demand loading of Strategic and Key tier account data,
 * KPI strip rendering, account health card rendering, coverage warnings,
 * empty state, and error handling.
 *
 * Registered under window.dashboardModules.strategicAccounts.
 */

(function() {
    'use strict';

    const { escapeHtml, generatePaginationPages } = window.dashboardModules.bootstrap.utils;

    let loaded = false;

    // ============================================================================
    // VISUAL HELPERS (mirrors account-intelligence.js)
    // ============================================================================

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

    function normalizeTypeForVisual(originalType) {
        const typeMap = {
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
        if (normalized) return normalized;

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

        return originalType.toLowerCase().replace(/\s+/g, '_');
    }

    // ============================================================================
    // KPI STRIP
    // ============================================================================

    function renderKpiStrip(kpi) {
        const atRiskEl = document.getElementById('strategicAtRiskCount');
        const growthEl = document.getElementById('strategicGrowthCount');
        const coverageEl = document.getElementById('strategicCoverageRate');
        const noResponseEl = document.getElementById('strategicNoResponseCount');

        if (atRiskEl) atRiskEl.textContent = kpi.at_risk_count !== undefined ? kpi.at_risk_count : '—';
        if (growthEl) growthEl.textContent = kpi.growth_count !== undefined ? kpi.growth_count : '—';
        if (coverageEl) coverageEl.textContent = kpi.coverage_rate !== undefined ? Math.round(kpi.coverage_rate * 100) + '%' : '—';
        if (noResponseEl) noResponseEl.textContent = kpi.no_response_count !== undefined ? kpi.no_response_count : '—';
    }

    // ============================================================================
    // ACCOUNT CARD RENDERING
    // ============================================================================

    function renderAccountCard(account, campaignId, campaignName) {
        const balanceClass = account.balance === 'risk_heavy' ? 'border-danger' : 'border-secondary';
        const balanceIconColor = account.balance === 'risk_heavy' ? '#E13A44' :
                                 account.balance === 'opportunity_heavy' ? '#8A8A8A' : '#BDBDBD';
        const balanceLabel = account.balance === 'risk_heavy' ? 'Risk-Heavy' :
                             account.balance === 'opportunity_heavy' ? 'High Potential' : 'Balanced';

        const tierBadgeColor = (account.customer_tier || '').toLowerCase() === 'strategic' ? '#2E5090' : '#6c757d';
        const tierLabel = escapeHtml(account.customer_tier || 'Unknown');

        const coverageWarning = !account.has_responses
            ? `<div class="alert alert-warning py-1 px-2 mb-2 d-flex align-items-center gap-2" style="font-size:0.82em;">
                   <i class="fas fa-exclamation-triangle me-1"></i>
                   <span>No responses in this campaign — account coverage gap</span>
               </div>`
            : '';

        const opportunityMap = new Map();
        (account.opportunities || []).forEach(opp => {
            const normalizedType = normalizeTypeForVisual(opp.type);
            if (opportunityMap.has(normalizedType)) {
                opportunityMap.get(normalizedType).count += (opp.count || 1);
                if (opp.strategic_advocate) {
                    opportunityMap.get(normalizedType).strategic_advocate = true;
                }
            } else {
                opportunityMap.set(normalizedType, {
                    type: opp.type,
                    normalizedType,
                    count: opp.count || 1,
                    strategic_advocate: opp.strategic_advocate || false
                });
            }
        });

        const opportunityIndicators = Array.from(opportunityMap.values()).map(opp => {
            const visual = getVisualIndicator(opp.normalizedType, 'opportunity');
            const advocateLabel = opp.strategic_advocate
                ? ` <span style="background:#1A5E20; color:#fff; border-radius:6px; font-size:0.7em; padding:1px 5px; vertical-align:middle;">Strategic Advocate</span>`
                : '';
            return `<span class="visual-indicator opportunity-indicator"
                          style="background-color:${visual.color}20; border:2px solid ${visual.color}; padding:4px 8px; margin:2px; border-radius:12px; display:inline-block;"
                          title="${escapeHtml(opp.type)}${opp.count > 1 ? ` (${opp.count} opportunities)` : ''}">
                        ${escapeHtml(visual.label)}${opp.count > 1 ? ` (${opp.count})` : ''}${advocateLabel}
                    </span>`;
        }).join('');

        const riskMap = new Map();
        (account.risk_factors || []).forEach(risk => {
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
                    normalizedType,
                    severity: risk.severity,
                    count: risk.count || 1
                });
            }
        });

        const riskIndicators = Array.from(riskMap.values()).map(risk => {
            const visual = getVisualIndicator(risk.normalizedType, 'risk');
            const intensityMap = { 'Critical': '●●●', 'High': '●●', 'Medium': '●', 'Low': '○' };
            const intensity = intensityMap[risk.severity] || '●';
            return `<span class="visual-indicator risk-indicator"
                          style="background-color:${visual.color}20; border:2px solid ${visual.color}; padding:4px 8px; margin:2px; border-radius:12px; display:inline-block;"
                          title="${escapeHtml(risk.type)} - ${escapeHtml(risk.severity)}${risk.count > 1 ? ` (${risk.count} instances)` : ''}">
                        ${escapeHtml(visual.label)} ${intensity}${risk.count > 1 ? ` (${risk.count})` : ''}
                    </span>`;
        }).join('');

        const decisionMakerRiskBadge = account.decision_maker_risk
            ? `<span class="badge ms-1" style="background-color:#7B1B1B; color:#fff; font-size:0.72em; cursor:help;"
                   title="Churn risk driven by decision-makers.">
                   <i class="fas fa-user-tie me-1"></i>DM Risk
               </span>` : '';

        const coverageWarningBadge = account.missing_executive_coverage
            ? `<span class="badge ms-1" style="background-color:#6C4A00; color:#fff; font-size:0.72em; cursor:help;"
                   title="No C-Level or VP/Director response captured.">
                   <i class="fas fa-eye-slash me-1"></i>No Exec Coverage
               </span>` : '';

        const strategicAdvocateBadge = account.c_level_promoter_opps
            ? `<span class="badge ms-1" style="background-color:#1A5E20; color:#fff; font-size:0.72em; cursor:help;"
                   title="Strategic Advocate opportunity: a C-Level or VP/Director gave a Promoter score.">
                   <i class="fas fa-star me-1"></i>Strategic Advocate
               </span>` : '';

        const influenceBadges = [decisionMakerRiskBadge, coverageWarningBadge, strategicAdvocateBadge].filter(Boolean).join('');

        const npsDisplay = account.company_nps !== undefined && account.company_nps !== null ? account.company_nps : 'N/A';

        const npsByTierHtml = account.nps_by_tier && Object.keys(account.nps_by_tier).length > 0 ? (() => {
            const tierOrder = ['C-Level', 'VP/Director', 'Manager', 'Team Lead', 'End User'];
            const rows = tierOrder
                .filter(t => account.nps_by_tier[t])
                .map(t => {
                    const td = account.nps_by_tier[t];
                    const nps = td.nps;
                    const color = nps >= 30 ? '#1A5E20' : nps >= 0 ? '#856600' : '#7B1B1B';
                    const isHighInfluence = t === 'C-Level' || t === 'VP/Director';
                    return `<div class="d-flex align-items-center justify-content-between py-1" style="border-bottom:1px solid #E0E0E0;">
                        <span style="font-size:0.78em; color:#555;">${isHighInfluence ? '<i class="fas fa-user-tie me-1" style="color:#2E5090;"></i>' : ''}<span>${t}</span> <span class="text-muted">(${td.count})</span></span>
                        <span class="badge" style="background-color:${color}20; color:${color}; border:1px solid ${color}; font-size:0.78em;">${nps > 0 ? '+' : ''}${nps}</span>
                    </div>`;
                }).join('');
            return rows ? `<div class="mb-3 p-2 rounded" style="background-color:#F4F3F0; border:1px solid #BDBDBD;">
                <div class="fw-bold mb-1" style="font-size:0.8em; color:#555;">NPS by Influence Tier</div>
                ${rows}
            </div>` : '';
        })() : '';

        const companyNameEscaped = escapeHtml(account.company_name);
        const campaignNameEscaped = escapeHtml(campaignName);

        return `
            <div class="account-visual-card card mb-3 ${balanceClass}" style="border-width:2px;">
                <div class="card-body p-3">
                    ${coverageWarning}
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                            <h5 class="mb-1">
                                <a href="#" onclick="openCompanyResponsesModal('${companyNameEscaped.replace(/'/g, "\\'")}', ${campaignId || 'null'}, '${campaignNameEscaped.replace(/'/g, "\\'")}'); return false;"
                                   style="color:#2E5090; text-decoration:none; cursor:pointer;"
                                   onmouseover="this.style.textDecoration='underline';"
                                   onmouseout="this.style.textDecoration='none';">
                                    ${companyNameEscaped}
                                    <i class="fas fa-external-link-alt ms-2" style="font-size:0.7em; color:#8A8A8A;"></i>
                                </a>
                            </h5>
                            <div class="d-flex flex-wrap gap-1 mt-1">
                                <span class="badge" style="background-color:${tierBadgeColor}; color:#fff; font-size:0.72em;">
                                    <i class="fas fa-crown me-1"></i>${tierLabel}
                                </span>
                                ${influenceBadges}
                            </div>
                        </div>
                        <div class="d-flex align-items-center ms-2">
                            <span style="font-size:1.2em; margin-right:5px; color:${balanceIconColor};">●</span>
                            <span class="badge" style="background-color:${balanceIconColor}20; color:${balanceIconColor}; border:1px solid ${balanceIconColor};">${balanceLabel}</span>
                        </div>
                    </div>

                    <div class="account-details mb-3 p-2 rounded" style="background-color:#E9E8E4; border:1px solid #BDBDBD;">
                        <div class="row">
                            <div class="col-4">
                                <small class="text-muted">NPS:</small>
                                <div class="fw-bold" style="color:#8A8A8A;">${npsDisplay}</div>
                            </div>
                            <div class="col-4">
                                <small class="text-muted">Max Tenure:</small>
                                <div class="fw-bold" style="color:#8A8A8A;">${account.max_tenure ? account.max_tenure + ' years' : 'N/A'}</div>
                            </div>
                            <div class="col-4">
                                <small class="text-muted">Responses:</small>
                                <div class="fw-bold" style="color:#8A8A8A;">${account.response_count !== undefined ? account.response_count : 'N/A'}</div>
                            </div>
                        </div>
                    </div>

                    ${npsByTierHtml}

                    <div class="account-indicators">
                        ${opportunityIndicators ? `
                            <div class="mb-2">
                                <div class="fw-bold text-success mb-1" style="font-size:0.9em;">Growth Opportunities</div>
                                <div>${opportunityIndicators}</div>
                            </div>` : ''}
                        ${riskIndicators ? `
                            <div class="mb-2">
                                <div class="fw-bold text-danger mb-1" style="font-size:0.9em;">Risk Factors</div>
                                <div>${riskIndicators}</div>
                            </div>` : ''}
                        ${!opportunityIndicators && !riskIndicators
                            ? '<div class="text-muted text-center py-2" style="font-size:0.9em;">No specific indicators identified</div>'
                            : ''}
                    </div>
                </div>
            </div>
        `;
    }

    // ============================================================================
    // MAIN LOAD FUNCTION
    // ============================================================================

    function loadStrategicAccounts() {
        const loadingEl = document.getElementById('strategicAccountsLoading');
        const listEl = document.getElementById('strategicAccountsList');

        if (!loadingEl || !listEl) return;

        if (loadingEl) loadingEl.classList.remove('d-none');
        if (listEl) listEl.classList.add('d-none');

        const campaignSelect = document.getElementById('campaignFilter');
        const campaignId = campaignSelect && campaignSelect.value ? campaignSelect.value : null;
        const campaignName = campaignSelect && campaignId
            ? campaignSelect.options[campaignSelect.selectedIndex].text
            : 'Current Campaign';

        const params = new URLSearchParams();
        if (campaignId) params.append('campaign_id', campaignId);
        params.append('_t', Date.now());

        fetch(`/api/strategic_accounts?${params}`)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error ${response.status}`);
                return response.json();
            })
            .then(data => {
                if (!data.success) throw new Error('API returned success=false');

                const accounts = data.accounts || [];
                const kpi = data.kpi || {};

                renderKpiStrip(kpi);

                if (accounts.length === 0) {
                    listEl.innerHTML = `
                        <div class="text-center py-5">
                            <i class="fas fa-crown fa-3x mb-3" style="color:#BDBDBD;"></i>
                            <h5 class="text-muted">No Strategic or Key Accounts Found</h5>
                            <p class="text-muted">
                                No participants in this campaign are tagged as Strategic or Key tier.
                                ${!campaignId ? '<br><small>Try selecting a specific campaign above.</small>' : ''}
                            </p>
                        </div>`;
                } else {
                    const cardsHtml = accounts.map(account =>
                        renderAccountCard(account, campaignId, campaignName)
                    ).join('');
                    listEl.innerHTML = cardsHtml;

                    if (typeof applyColorOverrides === 'function') {
                        applyColorOverrides(listEl, 100);
                    }
                }

                if (loadingEl) loadingEl.classList.add('d-none');
                listEl.classList.remove('d-none');

                console.log(`✅ Strategic accounts loaded: ${accounts.length} accounts`);
                loaded = true;
            })
            .catch(error => {
                console.error('Error loading strategic accounts:', error);
                if (loadingEl) loadingEl.classList.add('d-none');
                listEl.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        Error loading strategic accounts: ${escapeHtml(error.message)}
                    </div>`;
                listEl.classList.remove('d-none');
            });
    }

    // ============================================================================
    // EXPORTS
    // ============================================================================

    window.dashboardModules.strategicAccounts = {
        loadStrategicAccounts
    };

    console.log('📦 Dashboard Strategic Accounts module loaded');

    if (window.moduleReadiness) {
        window.moduleReadiness.markReady('strategicAccounts');
    }

})();
