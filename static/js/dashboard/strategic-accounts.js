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
        if (!originalType) return 'unknown';
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

    function renderKpiStrip(kpi, accounts) {
        const atRiskEl = document.getElementById('strategicAtRiskCount');
        const growthEl = document.getElementById('strategicGrowthCount');
        const coverageEl = document.getElementById('strategicCoverageRate');
        const noResponseEl = document.getElementById('strategicNoResponseCount');
        const tier1El = document.getElementById('strategicTier1Count');
        const tier2El = document.getElementById('strategicTier2Count');

        if (atRiskEl) atRiskEl.textContent = kpi.at_risk_count !== undefined ? kpi.at_risk_count : '—';
        if (growthEl) growthEl.textContent = kpi.growth_count !== undefined ? kpi.growth_count : '—';
        if (coverageEl) coverageEl.textContent = kpi.coverage_rate !== undefined ? Math.round(kpi.coverage_rate * 100) + '%' : '—';
        if (noResponseEl) noResponseEl.textContent = kpi.no_response_count !== undefined ? kpi.no_response_count : '—';

        if (accounts) {
            const isTier1 = a => /^t1\b/i.test(a.customer_tier || '');
            const isTier2 = a => /^t2\b/i.test(a.customer_tier || '');
            const tier1Accounts = accounts.filter(isTier1);
            const tier2Accounts = accounts.filter(isTier2);
            if (tier1El) tier1El.textContent = tier1Accounts.length;
            if (tier2El) tier2El.textContent = tier2Accounts.length;

            const avgNps = accs => {
                const withNps = accs.filter(a => a.company_nps !== null && a.company_nps !== undefined);
                if (!withNps.length) return null;
                return Math.round(withNps.reduce((s, a) => s + a.company_nps, 0) / withNps.length);
            };

            const renderNpsEl = (el, accs) => {
                if (!el) return;
                const nps = avgNps(accs);
                if (nps !== null) {
                    const sign = nps > 0 ? '+' : '';
                    const color = nps >= 30 ? '#1A5E20' : nps >= 0 ? '#856600' : '#7B1B1B';
                    el.innerHTML = `NPS <strong style="color:${color};">${sign}${nps}</strong>`;
                } else {
                    el.textContent = 'NPS —';
                }
            };

            renderNpsEl(document.getElementById('strategicTier1Nps'), tier1Accounts);
            renderNpsEl(document.getElementById('strategicTier2Nps'), tier2Accounts);
        }
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

        const tierIsT1 = /^t1\b/i.test(account.customer_tier || '');
        const tierBadgeColor = tierIsT1 ? '#2E5090' : '#6c757d';
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

        // ── Risk factor rows (icon, label, severity badge, description only) ────────
        const risks = (account.risk_factors || []).slice().sort((a, b) =>
            (severityPriority[b.severity] || 0) - (severityPriority[a.severity] || 0)
        );
        const riskRowsHtml = risks.length > 0
            ? risks.map(risk => {
                const visual = getVisualIndicator(normalizeTypeForVisual(risk.type), 'risk');
                const sev = risk.severity || 'Medium';
                const intensity = intensityMap[sev] || '●';
                const description = risk.description ? escapeHtml(risk.description) : '';
                return `<div class="mb-2 p-2 rounded" style="background-color:#FFF5F5; border:1px solid #F5C6CB;">
                    <div class="d-flex align-items-center justify-content-between mb-1">
                        <span style="font-size:0.82em; font-weight:600; color:#7B1B1B;">
                            <i class="fas fa-exclamation-circle me-1"></i>${escapeHtml(visual.label)} ${intensity}
                        </span>
                        <span class="badge" style="background-color:#E13A4420; color:#E13A44; border:1px solid #E13A44; font-size:0.72em;">${escapeHtml(sev)}</span>
                    </div>
                    ${description ? `<div style="font-size:0.8em; color:#555;">${description}</div>` : ''}
                </div>`;
            }).join('')
            : '';

        // ── Opportunity rows (icon, label, description only) ──────────────────────
        const opps = (account.opportunities || []).slice().sort((a, b) => (b.count || 1) - (a.count || 1));
        const oppRowsHtml = opps.length > 0
            ? opps.map(opp => {
                const visual = getVisualIndicator(normalizeTypeForVisual(opp.type), 'opportunity');
                const description = opp.description ? escapeHtml(opp.description) : '';
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
                    ${description ? `<div style="font-size:0.8em; color:#555;">${description}</div>` : ''}
                </div>`;
            }).join('')
            : '';

        const noInsights = risks.length === 0 && opps.length === 0
            ? '<div class="text-muted text-center py-2" style="font-size:0.9em;">No specific indicators identified for this campaign</div>'
            : '';

        const companyNameEscaped = escapeHtml(account.company_name);
        const campaignNameEscaped = escapeHtml(campaignName);

        return `
            <div class="account-visual-card card h-100 ${balanceClass}" style="border-width:2px; background-color:#E9E8E4; box-shadow:0 2px 6px rgba(0,0,0,0.07); border-radius:0.75rem;">
                <div class="card-body p-3">
                    ${coverageWarning}

                    <div class="d-flex justify-content-between align-items-start mb-3">
                        <div>
                            <h5 class="mb-1" style="font-family:var(--font-family-headings); font-weight:700; font-size:1em; color:#2B2B2B;">
                                <a href="#" onclick="openCompanyResponsesModal('${companyNameEscaped.replace(/'/g, "\\'")}', '${campaignId || ''}', '${campaignNameEscaped.replace(/'/g, "\\'")}'); return false;"
                                   style="color:#2E5090; text-decoration:none; cursor:pointer; font-family:var(--font-family-headings); font-weight:700;"
                                   onmouseover="this.style.textDecoration='underline';"
                                   onmouseout="this.style.textDecoration='none';">
                                    ${companyNameEscaped}
                                    <i class="fas fa-external-link-alt ms-2" style="font-size:0.65em; color:#8A8A8A;"></i>
                                </a>
                            </h5>
                            <div class="d-flex flex-wrap gap-1 mt-1">
                                <span class="badge" style="background-color:${tierBadgeColor}; color:#fff; font-size:0.72em; font-family:var(--font-family-headings); letter-spacing:0.02em;">
                                    <i class="fas fa-crown me-1"></i>${tierLabel}
                                </span>
                                ${influenceBadges}
                            </div>
                        </div>
                        <div class="d-flex align-items-center ms-2">
                            <span class="badge" style="background-color:${balanceIconColor}20; color:${balanceIconColor}; border:1px solid ${balanceIconColor}; font-family:var(--font-family-headings); font-size:0.72em; font-weight:600; letter-spacing:0.02em;">${balanceLabel}</span>
                        </div>
                    </div>

                    <div class="account-details mb-3 p-2 rounded" style="background-color:#fff; border:1px solid #BDBDBD;">
                        <div class="row">
                            <div class="col-4 text-center">
                                <small style="font-family:var(--font-family-base); color:#8A8A8A; font-size:0.75em; text-transform:uppercase; letter-spacing:0.04em;">NPS</small>
                                <div class="fw-bold" style="font-family:var(--font-family-headings); color:${npsDisplay === 'N/A' ? '#8A8A8A' : npsColor}; font-size:1.1em;">${npsDisplay}</div>
                            </div>
                            <div class="col-4 text-center">
                                <small style="font-family:var(--font-family-base); color:#8A8A8A; font-size:0.75em; text-transform:uppercase; letter-spacing:0.04em;">Tenure</small>
                                <div class="fw-bold" style="font-family:var(--font-family-headings); color:#8A8A8A; font-size:1.1em;">${account.max_tenure ? account.max_tenure + ' yrs' : 'N/A'}</div>
                            </div>
                            <div class="col-4 text-center">
                                <small style="font-family:var(--font-family-base); color:#8A8A8A; font-size:0.75em; text-transform:uppercase; letter-spacing:0.04em;">Responses</small>
                                <div class="fw-bold" style="font-family:var(--font-family-headings); color:#8A8A8A; font-size:1.1em;">${account.response_count !== undefined ? account.response_count : 'N/A'}</div>
                            </div>
                        </div>
                    </div>

                    ${npsByTierHtml}

                    ${riskRowsHtml ? `
                        <div class="mb-3">
                            <div class="fw-bold mb-2" style="font-size:0.8em; font-family:var(--font-family-headings); color:#E13A44; text-transform:uppercase; letter-spacing:0.05em;">
                                <i class="fas fa-triangle-exclamation me-1"></i>Risk Factors
                            </div>
                            ${riskRowsHtml}
                        </div>` : ''}

                    ${oppRowsHtml ? `
                        <div class="mb-2">
                            <div class="fw-bold mb-2" style="font-size:0.8em; font-family:var(--font-family-headings); color:#1A5E20; text-transform:uppercase; letter-spacing:0.05em;">
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
    // ACCOUNT LIST RENDERER (tier grouping + balance filter)
    // ============================================================================

    let _allAccounts = [];
    let _campaignId = null;
    let _campaignName = null;

    function renderAccountList(listEl, accounts, campaignId, campaignName) {
        _allAccounts = accounts;
        _campaignId = campaignId;
        _campaignName = campaignName;

        const activeFilter = (listEl.dataset.balanceFilter) || 'all';
        _renderFilteredList(listEl, activeFilter);
    }

    function _renderFilteredList(listEl, balanceFilter) {
        listEl.dataset.balanceFilter = balanceFilter;

        const filtered = balanceFilter === 'all'
            ? _allAccounts
            : _allAccounts.filter(a => {
                const b = (a.balance || '').toLowerCase();
                if (balanceFilter === 'risk_heavy') return b === 'risk_heavy';
                if (balanceFilter === 'balanced') return b === 'balanced';
                if (balanceFilter === 'high_potential') return b === 'opportunity_heavy' || b === 'high_potential';
                return true;
            });

        const isTier1 = a => /^t1\b/i.test(a.customer_tier || '');
        const isTier2 = a => /^t2\b/i.test(a.customer_tier || '');
        const tier1 = filtered.filter(isTier1);
        const tier2 = filtered.filter(isTier2);
        const tierOther = filtered.filter(a => !isTier1(a) && !isTier2(a));

        const filterHtml = `
            <div class="d-flex align-items-center gap-2 mb-4 flex-wrap" id="balanceFilterBar">
                <span style="font-family:var(--font-family-headings); font-size:0.8em; font-weight:600; color:#8A8A8A; text-transform:uppercase; letter-spacing:0.05em;">Filter:</span>
                <div class="btn-group btn-group-sm" role="group" aria-label="Balance filter">
                    ${['all','risk_heavy','balanced','high_potential'].map(val => {
                        const labels = { all: 'All', risk_heavy: 'Risk-Heavy', balanced: 'Balanced', high_potential: 'High Potential' };
                        const active = balanceFilter === val;
                        return `<button type="button"
                            class="btn ${active ? 'btn-dark' : 'btn-outline-secondary'} strategic-balance-btn"
                            style="font-family:var(--font-family-headings); font-size:0.78em; font-weight:600; letter-spacing:0.03em; ${active ? 'background-color:#2B2B2B; border-color:#2B2B2B; color:#fff;' : 'color:#8A8A8A; border-color:#BDBDBD;'}"
                            data-filter="${val}">${labels[val]}</button>`;
                    }).join('')}
                </div>
                <span style="font-size:0.82em; color:#8A8A8A; font-family:var(--font-family-base);">${filtered.length} account${filtered.length !== 1 ? 's' : ''}</span>
            </div>`;

        let sectionsHtml = '';

        if (tier1.length > 0) {
            sectionsHtml += `
                <div class="strategic-tier-section mb-5">
                    <div class="d-flex align-items-center mb-3 pb-2" style="border-bottom:2px solid #2E5090;">
                        <i class="fas fa-crown me-2" style="color:#2E5090;"></i>
                        <span style="font-family:var(--font-family-headings); font-size:1em; font-weight:700; color:#2E5090; text-transform:uppercase; letter-spacing:0.04em;">Tier 1</span>
                        <span class="ms-2" style="font-family:var(--font-family-base); font-size:0.82em; color:#8A8A8A;">${tier1.length} account${tier1.length !== 1 ? 's' : ''}</span>
                    </div>
                    <div class="row g-3">
                        ${tier1.map(a => `<div class="col-12 col-md-6 col-xl-4">${renderAccountCard(a, _campaignId, _campaignName)}</div>`).join('')}
                    </div>
                </div>`;
        }

        if (tier2.length > 0) {
            sectionsHtml += `
                <div class="strategic-tier-section mb-5">
                    <div class="d-flex align-items-center mb-3 pb-2" style="border-bottom:2px solid #6c757d;">
                        <i class="fas fa-key me-2" style="color:#6c757d;"></i>
                        <span style="font-family:var(--font-family-headings); font-size:1em; font-weight:700; color:#6c757d; text-transform:uppercase; letter-spacing:0.04em;">Tier 2</span>
                        <span class="ms-2" style="font-family:var(--font-family-base); font-size:0.82em; color:#8A8A8A;">${tier2.length} account${tier2.length !== 1 ? 's' : ''}</span>
                    </div>
                    <div class="row g-3">
                        ${tier2.map(a => `<div class="col-12 col-md-6 col-xl-4">${renderAccountCard(a, _campaignId, _campaignName)}</div>`).join('')}
                    </div>
                </div>`;
        }

        if (tierOther.length > 0) {
            sectionsHtml += `
                <div class="strategic-tier-section mb-5">
                    <div class="d-flex align-items-center mb-3 pb-2" style="border-bottom:2px solid #BDBDBD;">
                        <i class="fas fa-building me-2" style="color:#8A8A8A;"></i>
                        <span style="font-family:var(--font-family-headings); font-size:1em; font-weight:700; color:#8A8A8A; text-transform:uppercase; letter-spacing:0.04em;">Other Strategic / Key</span>
                        <span class="ms-2" style="font-family:var(--font-family-base); font-size:0.82em; color:#8A8A8A;">${tierOther.length} account${tierOther.length !== 1 ? 's' : ''}</span>
                    </div>
                    <div class="row g-3">
                        ${tierOther.map(a => `<div class="col-12 col-md-6 col-xl-4">${renderAccountCard(a, _campaignId, _campaignName)}</div>`).join('')}
                    </div>
                </div>`;
        }

        if (filtered.length === 0) {
            sectionsHtml = `<div class="text-center py-4 text-muted" style="font-family:var(--font-family-base);">No accounts match this filter.</div>`;
        }

        listEl.innerHTML = filterHtml + sectionsHtml;

        listEl.querySelectorAll('.strategic-balance-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                _renderFilteredList(listEl, this.dataset.filter);
                if (typeof applyColorOverrides === 'function') applyColorOverrides(listEl, 100);
            });
        });

        if (typeof applyColorOverrides === 'function') {
            applyColorOverrides(listEl, 100);
        }
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
        // dashboard.js stores integer ID in data-id and UUID in option.value
        // API call needs the integer; company-responses link needs the UUID
        const selectedOption = campaignSelect && campaignSelect.selectedOptions[0];
        const campaignId = selectedOption
            ? (selectedOption.getAttribute('data-id') || null)
            : (window.dashboardState && window.dashboardState.selectedCampaignId
                ? String(window.dashboardState.selectedCampaignId) : null);
        const campaignUuid = selectedOption ? (selectedOption.value || null) : null;
        const campaignName = selectedOption && selectedOption.text
            ? selectedOption.text
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

                renderKpiStrip(kpi, accounts);
                renderNoResponseList(accounts);

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
                    renderAccountList(listEl, accounts, campaignUuid || campaignId, campaignName);
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
    // NO-RESPONSE LIST
    // ============================================================================

    function renderNoResponseList(accounts) {
        const section = document.getElementById('strategicNoResponseSection');
        const tbody   = document.getElementById('strategicNoResponseList');
        const badge   = document.getElementById('strategicNoResponseBadge');
        if (!section || !tbody) return;

        const noResponse = accounts.filter(a => !a.has_responses);

        if (noResponse.length === 0) {
            section.classList.add('d-none');
            return;
        }

        if (badge) badge.textContent = noResponse.length;

        const tierLabel = tier => {
            if (!tier) return '—';
            const t = tier.toLowerCase();
            if (t.includes('strategic')) return '<span class="badge" style="background:#1A3D5C;color:#fff;">Strategic</span>';
            if (t.includes('key'))       return '<span class="badge" style="background:#2E6DA4;color:#fff;">Key</span>';
            return `<span class="badge bg-secondary">${escapeHtml(tier)}</span>`;
        };

        tbody.innerHTML = noResponse.map(a => `
            <tr>
                <td class="ps-4 fw-semibold" style="vertical-align:middle;">
                    <i class="fas fa-building me-2 text-muted" style="font-size:0.85rem;"></i>
                    ${escapeHtml(a.company_name || '—')}
                </td>
                <td style="vertical-align:middle;">${tierLabel(a.customer_tier)}</td>
                <td style="vertical-align:middle;">
                    <span class="badge bg-warning text-dark">
                        <i class="fas fa-hourglass-half me-1"></i>No response yet
                    </span>
                </td>
            </tr>
        `).join('');

        section.classList.remove('d-none');
    }

    // ============================================================================
    // EXPORTS
    // ============================================================================

    window.dashboardModules.strategicAccounts = {
        loadStrategicAccounts,
        isLoaded: function() { return loaded; }
    };

    console.log('📦 Dashboard Strategic Accounts module loaded');

    if (window.moduleReadiness) {
        window.moduleReadiness.markReady('strategicAccounts');
    }

})();
