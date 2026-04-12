/**
 * Hop Manager Module
 * Path 3 Navigation: hopTo() function for cross-tab and Whiteboard navigation
 * 
 * Exposes hopTo(destination, filters) globally via window.dashboardModules.hopManager
 * and syncs navigation state to the URL via the History API.
 */

(function () {
    'use strict';

    /**
     * Navigate to a destination with the given filters.
     *
     * @param {string} destination - Tab ID (e.g. 'intelligence', 'survey-insights')
     *                               or 'whiteboard' to navigate to the Whiteboard page.
     * @param {Object} filters     - Key/value pairs describing the query:
     *                               { campaign_id, company_name, nps_type, source_label, ... }
     */
    function hopTo(destination, filters) {
        filters = filters || {};

        if (destination === 'whiteboard') {
            _navigateToWhiteboard(filters);
        } else {
            _switchTab(destination, filters);
        }
    }

    /**
     * Navigate to the Whiteboard page, encoding filters as URL parameters.
     *
     * Whiteboard is a separate server-rendered page, so full navigation via
     * window.location.href is correct.  History API sync is completed on the
     * Whiteboard page: hop params are ingested, then stripped from the URL
     * via history.replaceState after the page loads.
     */
    function _navigateToWhiteboard(filters) {
        const params = new URLSearchParams();
        params.set('hop', '1');
        Object.entries(filters).forEach(([k, v]) => {
            if (v !== null && v !== undefined && v !== '') {
                params.set(k, v);
            }
        });

        const url = '/dashboard/whiteboard?' + params.toString();
        window.location.href = url;
    }

    /**
     * Switch to a Bootstrap tab on the current page and apply filter values.
     */
    function _switchTab(tabId, filters) {
        const tabEl = document.getElementById(tabId + '-tab');
        if (tabEl) {
            const bsTab = window.bootstrap && window.bootstrap.Tab
                ? new window.bootstrap.Tab(tabEl)
                : null;
            if (bsTab) {
                bsTab.show();
            } else {
                tabEl.click();
            }
        }

        _applyFilters(filters);

        const params = new URLSearchParams(window.location.search);
        params.set('active_tab', tabId);
        Object.entries(filters).forEach(([k, v]) => {
            if (v !== null && v !== undefined && v !== '') {
                params.set(k, v);
            }
        });
        history.replaceState(null, '', '?' + params.toString());
    }

    /**
     * Apply filter values to known filter elements on the current page.
     */
    function _applyFilters(filters) {
        if (!filters) return;

        if (filters.campaign_id) {
            const campaignSelect = document.getElementById('campaignFilter');
            if (campaignSelect) {
                campaignSelect.value = filters.campaign_id;
                campaignSelect.dispatchEvent(new Event('change'));
            }
        }

        if (filters.company_name) {
            const accountSearch = document.getElementById('accountIntelSearch');
            if (accountSearch) {
                accountSearch.value = filters.company_name;
                accountSearch.dispatchEvent(new Event('keyup'));
            }
        }

        if (filters.balance_filter) {
            const balSelect = document.getElementById('accountBalanceFilter');
            if (balSelect) {
                balSelect.value = filters.balance_filter;
                balSelect.dispatchEvent(new Event('change'));
            }
        }

        if (filters.nps_type) {
            const npsSelect = document.getElementById('npsTypeFilter');
            if (npsSelect) {
                npsSelect.value = filters.nps_type;
                npsSelect.dispatchEvent(new Event('change'));
            }
            const npsBtn = document.querySelector('[data-nps-filter="' + filters.nps_type + '"]');
            if (npsBtn) {
                npsBtn.click();
            }
        }
    }

    window.dashboardModules = window.dashboardModules || {};
    window.dashboardModules.hopManager = { hopTo };

    window.hopTo = hopTo;

    console.log('📦 Hop Manager module loaded');
})();
