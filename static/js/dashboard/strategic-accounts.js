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
        const severityPriority = { 'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1 };
        const intensityMap = { 'Critical': '●●●', 'High': '●●', 'Medium': '●', 'Low': '○' };

        const balanceClass = account.balance === 'risk_heavy' ? 'border-danger' : 'border-secondary';
        const balanceIconColor = account.balance === 'risk_heavy' ? '#E13A44' :
                                 account.balance === 'opportunity_heavy' ? '#8A8A8A' : '#BDBDBD';
        const balanceLabel = account.balance === 'risk_heavy' ? 'Risk-Heavy' :
                             account.balance === 'opportunity_heavy' ? 'High Potential' : 'Balanced';

        const tierIsStrategic = (account.customer_tier || '').toLowerCase().includes('strategic');
        const tierBadgeColor = tierIsStrategic ? '#2E5090' : '#6c757d';
        const tierLabel = escapeHtml(account.customer_tier || 'Unknown');

        const coverageWarning = !account.has_responses
            ? `<div class="alert alert-warning py-1 px-2 mb-2 d-flex align-items-center gap-2" style="font-size:0.82em;">
                   <i class="fas fa-exclamation-triangle me-1"></i>
                   <span>No responses in this campaign — schedule an executive check-in to capture sentiment before renewal</span>
               </div>`
            : '';

        // ── Influence badges ──────────────────────────────────────────────────────
        const decisionMakerRiskBadge = account.decision_maker_risk
            ? `<span class="badge ms-1" style="background-color:#7B1B1B; color:#fff; font-size:0.72em; cursor:help;"
                   title="A C-Level or VP/Director respondent is a Detractor — executive sponsorship is at risk.">
                   <i class="fas fa-user-tie me-1"></i>DM Risk
               </span>` : '';

        const execCoverageBadge = account.missing_executive_coverage
            ? `<span class="badge ms-1" style="background-color:#6C4A00; color:#fff; font-size:0.72em; cursor:help;"
                   title="No C-Level or VP/Director response captured — executive sentiment is unknown.">
                   <i class="fas fa-eye-slash me-1"></i>No Exec Coverage
               </span>` : '';

        const strategicAdvocateBadge = account.c_level_promoter_opps
            ? `<span class="badge ms-1" style="background-color:#1A5E20; color:#fff; font-size:0.72em; cursor:help;"
                   title="A C-Level or VP/Director gave a Promoter score (9–10) — a high-value reference candidate.">
                   <i class="fas fa-star me-1"></i>Strategic Advocate
               </span>` : '';

        const influenceBadges = [decisionMakerRiskBadge, execCoverageBadge, strategicAdvocateBadge].filter(Boolean).join('');

        // ── NPS display ───────────────────────────────────────────────────────────
        const npsDisplay = account.company_nps !== undefined && account.company_nps !== null
            ? (account.company_nps > 0 ? '+' : '') + account.company_nps
            : 'N/A';
        const npsColor = (account.company_nps >= 30) ? '#1A5E20' : (account.company_nps >= 0) ? '#856600' : '#7B1B1B';

        // ── NPS by Influence Tier ─────────────────────────────────────────────────
        const npsByTierHtml = account.nps_by_tier && Object.keys(account.nps_by_tier).length > 0 ? (() => {
            const tierOrder = ['C-Level', 'VP/Director', 'Manager', 'Team Lead', 'End User'];
            const rows = tierOrder
                .filter(t => account.nps_by_tier[t])
                .map(t => {
                    const td = account.nps_by_tier[t];
                    const nps = td.nps;
                    const color = nps >= 30 ? '#1A5E20' : nps >= 0 ? '#856600' : '#7B1B1B';
                    const isHighInfluence = t === 'C-Level' || t === 'VP/Director';
                    const warningNote = isHighInfluence && nps < 0
                        ? `<span style="font-size:0.75em; color:#7B1B1B;" title="Executive detractor — priority escalation needed"> ⚠</span>` : '';
                    return `<div class="d-flex align-items-center justify-content-between py-1" style="border-bottom:1px solid #E0E0E0;">
                        <span style="font-size:0.78em; color:#555;">${isHighInfluence ? '<i class="fas fa-user-tie me-1" style="color:#2E5090;"></i>' : ''}<span>${escapeHtml(t)}</span> <span class="text-muted">(${td.count})</span>${warningNote}</span>
                        <span class="badge" style="background-color:${color}20; color:${color}; border:1px solid ${color}; font-size:0.78em;">${nps > 0 ? '+' : ''}${nps}</span>
                    </div>`;
                }).join('');
            return rows ? `<div class="mb-3 p-2 rounded" style="background-color:#F4F3F0; border:1px solid #BDBDBD;">
                <div class="fw-bold mb-1" style="font-size:0.8em; color:#555;"><i class="fas fa-layer-group me-1"></i>NPS by Influence Tier</div>
                ${rows}
            </div>` : '';
        })() : '';

        // ── Priority Action callout ────────────────────────────────────────────────
        // Surface the single highest-severity risk action as an explicit callout
        const risks = (account.risk_factors || []).slice().sort((a, b) =>
            (severityPriority[b.severity] || 0) - (severityPriority[a.severity] || 0)
        );
        const topRisk = risks.find(r => r.action && r.action.trim());
        const priorityActionHtml = topRisk
            ? (() => {
                const sev = topRisk.severity || 'Medium';
                const borderColor = sev === 'Critical' || sev === 'High' ? '#E13A44' : '#856600';
                const bgColor = sev === 'Critical' || sev === 'High' ? '#FFF5F5' : '#FFFBF0';
                const sevLabel = escapeHtml(sev);
                const actionText = escapeHtml(topRisk.action);
                return `<div class="mb-3 p-2 rounded" style="background-color:${bgColor}; border-left:3px solid ${borderColor};">
                    <div class="fw-bold mb-1" style="font-size:0.8em; color:${borderColor};">
                        <i class="fas fa-bolt me-1"></i>Priority Action <span style="font-weight:normal; opacity:0.8;">(${sevLabel} Risk)</span>
                    </div>
                    <div style="font-size:0.82em; color:#333;">${actionText}</div>
                </div>`;
            })()
            : '';

        // ── Risk factor rows (with description + action) ──────────────────────────
        const riskRowsHtml = risks.length > 0
            ? risks.map(risk => {
                const visual = getVisualIndicator(normalizeTypeForVisual(risk.type), 'risk');
                const sev = risk.severity || 'Medium';
                const intensity = intensityMap[sev] || '●';
                const description = risk.description ? escapeHtml(risk.description) : '';
                const action = risk.action ? escapeHtml(risk.action) : '';
                const isTopRisk = risk === topRisk;
                return `<div class="mb-2 p-2 rounded" style="background-color:#FFF5F5; border:1px solid #F5C6CB;">
                    <div class="d-flex align-items-center justify-content-between mb-1">
                        <span style="font-size:0.82em; font-weight:600; color:#7B1B1B;">
                            <i class="fas fa-exclamation-circle me-1"></i>${escapeHtml(visual.label)} ${intensity}
                        </span>
                        <span class="badge" style="background-color:#E13A4420; color:#E13A44; border:1px solid #E13A44; font-size:0.72em;">${escapeHtml(sev)}</span>
                    </div>
                    ${description ? `<div style="font-size:0.8em; color:#555; margin-bottom:${action ? '4px' : '0'};">${description}</div>` : ''}
                    ${action && !isTopRisk ? `<div style="font-size:0.78em; color:#856600;"><i class="fas fa-arrow-right me-1"></i>${action}</div>` : ''}
                </div>`;
            }).join('')
            : '';

        // ── Opportunity rows (with description + action) ──────────────────────────
        const opps = (account.opportunities || []).slice().sort((a, b) => (b.count || 1) - (a.count || 1));
        const oppRowsHtml = opps.length > 0
            ? opps.map(opp => {
                const visual = getVisualIndicator(normalizeTypeForVisual(opp.type), 'opportunity');
                const description = opp.description ? escapeHtml(opp.description) : '';
                const action = opp.action ? escapeHtml(opp.action) : '';
                const advocateTag = opp.strategic_advocate
                    ? `<span class="badge ms-1" style="background:#1A5E20; color:#fff; font-size:0.7em;">Strategic Advocate</span>`
                    : '';
                return `<div class="mb-2 p-2 rounded" style="background-color:#F0FFF4; border:1px solid #B2DFDB;">
                    <div class="d-flex align-items-center justify-content-between mb-1">
                        <span style="font-size:0.82em; font-weight:600; color:#1A5E20;">
                            <i class="fas fa-arrow-trend-up me-1"></i>${escapeHtml(visual.label)}${opp.count > 1 ? ` (${opp.count})` : ''}
                        </span>
                        ${advocateTag}
                    </div>
                    ${description ? `<div style="font-size:0.8em; color:#555; margin-bottom:${action ? '4px' : '0'};">${description}</div>` : ''}
                    ${action ? `<div style="font-size:0.78em; color:#1A5E20;"><i class="fas fa-arrow-right me-1"></i>${action}</div>` : ''}
                </div>`;
            }).join('')
            : '';

        const noInsights = risks.length === 0 && opps.length === 0
            ? '<div class="text-muted text-center py-2" style="font-size:0.9em;">No specific indicators identified for this campaign</div>'
            : '';

        const companyNameEscaped = escapeHtml(account.company_name);
        const campaignNameEscaped = escapeHtml(campaignName);

        return `
            <div class="account-visual-card card mb-3 ${balanceClass}" style="border-width:2px;">
                <div class="card-body p-3">
                    ${coverageWarning}

                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                            <h5 class="mb-1">
                                <a href="#" onclick="openCompanyResponsesModal('${companyNameEscaped.replace(/'/g, "\\'")}', '${campaignId || ''}', '${campaignNameEscaped.replace(/'/g, "\\'")}'); return false;"
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
                                <small class="text-muted">NPS</small>
                                <div class="fw-bold" style="color:${npsDisplay === 'N/A' ? '#8A8A8A' : npsColor};">${npsDisplay}</div>
                            </div>
                            <div class="col-4">
                                <small class="text-muted">Max Tenure</small>
                                <div class="fw-bold" style="color:#8A8A8A;">${account.max_tenure ? account.max_tenure + ' yrs' : 'N/A'}</div>
                            </div>
                            <div class="col-4">
                                <small class="text-muted">Responses</small>
                                <div class="fw-bold" style="color:#8A8A8A;">${account.response_count !== undefined ? account.response_count : 'N/A'}</div>
                            </div>
                        </div>
                    </div>

                    ${npsByTierHtml}

                    ${priorityActionHtml}

                    ${riskRowsHtml ? `
                        <div class="mb-3">
                            <div class="fw-bold mb-2" style="font-size:0.85em; color:#E13A44;">
                                <i class="fas fa-triangle-exclamation me-1"></i>Risk Factors
                            </div>
                            ${riskRowsHtml}
                        </div>` : ''}

                    ${oppRowsHtml ? `
                        <div class="mb-2">
                            <div class="fw-bold mb-2" style="font-size:0.85em; color:#1A5E20;">
                                <i class="fas fa-seedling me-1"></i>Growth Opportunities
                            </div>
                            ${oppRowsHtml}
                        </div>` : ''}

                    ${noInsights}
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
        const numericCampaignId = campaignSelect && campaignSelect.selectedOptions[0]
            ? campaignSelect.selectedOptions[0].getAttribute('data-id') : null;

        const params = new URLSearchParams();
        if (numericCampaignId) params.append('campaign_id', numericCampaignId);
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
