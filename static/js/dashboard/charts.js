/**
 * Dashboard Charts Module
 * Phase 3: Frontend Refactoring - Complete Chart.js visualization logic
 * 
 * This module handles all Chart.js rendering logic.
 * It reads data from window.dashboardState and creates/updates visualizations.
 * Migrated from dashboard.js lines 1468-2057
 */

(function() {
    'use strict';
    
    // Import utilities from bootstrap module
    const { escapeHtml, getMobileChartConfig } = window.dashboardModules.bootstrap.utils;

    // ─── Brand Palette Helper ─────────────────────────────────────────────────
    // Reads window.brandColors (emitted by the template) and returns a palette
    // object. `configured` is true only when the brand palette was actually set
    // by the template. Chart functions use this flag to decide whether to apply
    // brand colors or fall back to their original hardcoded defaults, ensuring
    // zero visual regression for accounts without configured branding.
    function getBrandPalette() {
        const bc = window.brandColors || {};
        const primary   = (bc.primary   && bc.primary   !== '') ? bc.primary   : null;
        const secondary = (bc.secondary && bc.secondary !== '') ? bc.secondary : null;
        const accent    = (bc.accent    && bc.accent    !== '') ? bc.accent    : null;
        const configured = !!(primary || secondary || accent);

        function hexToRgb(hex) {
            const h = hex.replace('#', '');
            return [
                parseInt(h.substring(0, 2), 16),
                parseInt(h.substring(2, 4), 16),
                parseInt(h.substring(4, 6), 16)
            ];
        }

        function tintHex(hex, amount) {
            const [r, g, b] = hexToRgb(hex);
            const tr = Math.round(r + (255 - r) * amount);
            const tg = Math.round(g + (255 - g) * amount);
            const tb = Math.round(b + (255 - b) * amount);
            return '#' + [tr, tg, tb].map(v => v.toString(16).padStart(2, '0')).join('');
        }

        function tintSequence(baseHex, n) {
            const result = [];
            for (let i = 0; i < n; i++) {
                result.push(tintHex(baseHex, i * (0.55 / Math.max(n - 1, 1))));
            }
            return result;
        }

        return { primary, secondary, accent, configured, tintSequence };
    }
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Create NPS Distribution Chart (Doughnut)
     */
    function createNpsChart() {
        const { dashboardData, charts } = window.dashboardState;
        const translations = window.translations;
        
        const chartElement = document.getElementById('npsChart');
        if (!chartElement) {
            console.warn('NPS chart element not found');
            return;
        }
        
        const ctx = chartElement.getContext('2d');
        
        // Destroy existing chart if it exists
        if (charts.npsChart) {
            charts.npsChart.destroy();
        }
        
        if (!dashboardData || !dashboardData.nps_distribution) {
            console.warn('No dashboard data available for NPS chart');
            return;
        }
        
        const npsData = dashboardData.nps_distribution || [];
        const labels = npsData.map(item => item.category);
        const data = npsData.map(item => item.count);
        
        // Professional color palette matching the design
        const chartColors = ['#E13A44', '#BDBDBD', '#8A8A8A'];
        
        // Get mobile-responsive configuration
        const config = getMobileChartConfig();
        
        charts.npsChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: chartColors,
                    borderWidth: 3,
                    borderColor: '#FFFFFF',
                    hoverBorderWidth: 4,
                    hoverBorderColor: '#E13A44'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: config.maintainAspectRatio,
                cutout: '60%',
                plugins: {
                    legend: {
                        position: config.legendPosition,
                        labels: {
                            color: '#000000',
                            usePointStyle: true,
                            padding: config.legendPadding,
                            font: {
                                family: 'Karla',
                                size: config.legendFontSize,
                                weight: '500'
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: '#000000',
                        titleColor: '#FFFFFF',
                        bodyColor: '#FFFFFF',
                        borderColor: '#E13A44',
                        borderWidth: 1,
                        cornerRadius: 8,
                        titleFont: {
                            family: 'Montserrat',
                            size: config.fontSize,
                            weight: '600'
                        },
                        bodyFont: {
                            family: 'Karla',
                            size: config.fontSize - 1,
                            weight: '500'
                        }
                    }
                },
                elements: {
                    arc: {
                        borderRadius: 4
                    }
                }
            }
        });
    }
    
    /**
     * Create Sentiment Distribution Chart (Bar)
     */
    function createSentimentChart() {
        const { dashboardData, charts } = window.dashboardState;
        const translations = window.translations;
        
        const chartElement = document.getElementById('sentimentChart');
        if (!chartElement) {
            console.warn('Sentiment chart element not found');
            return;
        }
        
        const ctx = chartElement.getContext('2d');
        
        // Destroy existing chart if it exists
        if (charts.sentimentChart) {
            charts.sentimentChart.destroy();
        }
        
        if (!dashboardData) {
            console.warn('No dashboard data available for sentiment chart');
            return;
        }
        
        const sentimentData = dashboardData.sentiment_distribution || [];
        
        // Filter out items with missing sentiment data
        const validSentimentData = sentimentData.filter(item => item.sentiment && typeof item.sentiment === 'string');
        
        if (validSentimentData.length === 0) {
            console.warn('No valid sentiment data available for chart');
            charts.sentimentChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['No Data'],
                    datasets: [{
                        label: 'Responses',
                        data: [0],
                        backgroundColor: ['#E9E8E4'],
                        borderWidth: 1,
                        borderColor: '#E9E8E4'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: getMobileChartConfig().maintainAspectRatio,
                    plugins: {
                        legend: { display: false },
                        tooltip: { enabled: false }
                    },
                    scales: {
                        y: { beginAtZero: true, max: 1 },
                        x: { display: false }
                    }
                }
            });
            return;
        }
        
        const labels = validSentimentData.map(item => item.sentiment.charAt(0).toUpperCase() + item.sentiment.slice(1));
        const data = validSentimentData.map(item => item.count || 0);
        const colors = ['#8A8A8A', '#BDBDBD', '#E13A44'];
        
        const config = getMobileChartConfig();
        
        charts.sentimentChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: translations.responses,
                    data: data,
                    backgroundColor: colors,
                    borderWidth: 1,
                    borderColor: '#E9E8E4'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: config.maintainAspectRatio,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#000000',
                            font: {
                                size: config.fontSize
                            }
                        },
                        grid: {
                            color: '#E9E8E4'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#000000',
                            font: {
                                size: config.fontSize
                            }
                        },
                        grid: {
                            color: '#E9E8E4'
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Create Average Ratings Chart (Radar)
     */
    function createRatingsChart() {
        const { dashboardData, charts } = window.dashboardState;
        const translations = window.translations;
        
        const chartElement = document.getElementById('ratingsChart');
        if (!chartElement) {
            console.warn('Ratings chart element not found');
            return;
        }
        
        const ctx = chartElement.getContext('2d');
        
        // Destroy existing chart if it exists
        if (charts.ratingsChart) {
            charts.ratingsChart.destroy();
        }
        
        if (!dashboardData) {
            console.warn('No dashboard data available for ratings chart');
            return;
        }
        
        const ratings = dashboardData.average_ratings || {};
        
        const labels = [translations.satisfaction, translations.productValue, translations.service, translations.pricing];
        const data = [
            ratings.satisfaction || 0,
            ratings.product_value || 0,
            ratings.service || 0,
            ratings.pricing || 0
        ];
        
        const config = getMobileChartConfig();
        
        charts.ratingsChart = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: labels,
                datasets: [{
                    label: translations.averageRating,
                    data: data,
                    borderColor: '#E13A44',
                    backgroundColor: 'rgba(225, 58, 68, 0.1)',
                    borderWidth: 2,
                    pointBackgroundColor: '#E13A44',
                    pointBorderColor: '#FFFFFF',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: config.maintainAspectRatio,
                plugins: {
                    legend: {
                        position: config.legendPosition,
                        labels: {
                            color: '#000000',
                            padding: config.legendPadding,
                            font: {
                                size: config.legendFontSize
                            }
                        }
                    }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 5,
                        ticks: {
                            color: '#000000',
                            stepSize: 1,
                            font: {
                                size: config.fontSize
                            }
                        },
                        grid: {
                            color: '#BDBDBD'
                        },
                        pointLabels: {
                            color: '#000000',
                            font: {
                                size: config.fontSize
                            }
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Create Key Themes Chart (Horizontal Bar)
     */
    function createThemesChart() {
        const { dashboardData, charts } = window.dashboardState;
        
        const chartElement = document.getElementById('themesChart');
        if (!chartElement) {
            console.warn('Themes chart element not found');
            return;
        }
        
        const ctx = chartElement.getContext('2d');
        
        // Destroy existing chart if it exists
        if (charts.themesChart) {
            charts.themesChart.destroy();
        }
        
        if (!dashboardData) {
            console.warn('Dashboard data not loaded yet, skipping themes chart');
            return;
        }
        
        const themes = dashboardData.key_themes || [];
        
        if (themes.length === 0) {
            charts.themesChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['No Data'],
                    datasets: [{
                        label: 'Mentions',
                        data: [0],
                        backgroundColor: '#E9E8E4',
                        borderWidth: 1,
                        borderColor: '#E9E8E4'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: getMobileChartConfig().maintainAspectRatio,
                    indexAxis: 'y',
                    plugins: {
                        legend: { display: false },
                        tooltip: { enabled: false }
                    },
                    scales: {
                        y: { display: false },
                        x: { 
                            beginAtZero: true,
                            max: 1,
                            display: false
                        }
                    }
                }
            });
            return;
        }
        
        const sortedThemes = themes.sort((a, b) => b.count - a.count).slice(0, 10);
        const labels = sortedThemes.map(item => item.theme.charAt(0).toUpperCase() + item.theme.slice(1));
        const data = sortedThemes.map(item => item.count);
        
        const config = getMobileChartConfig();
        
        charts.themesChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Mentions',
                    data: data,
                    backgroundColor: '#BDBDBD',
                    borderWidth: 1,
                    borderColor: '#E9E8E4'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: config.maintainAspectRatio,
                indexAxis: 'y',
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        ticks: {
                            color: '#000000',
                            font: {
                                size: config.fontSize - 1
                            },
                            maxTicksLimit: false,
                            autoSkip: false,
                            maxRotation: 0,
                            minRotation: 0
                        },
                        grid: {
                            color: '#E9E8E4'
                        }
                    },
                    x: {
                        beginAtZero: true,
                        ticks: {
                            color: '#000000',
                            font: {
                                size: config.fontSize
                            }
                        },
                        grid: {
                            color: '#E9E8E4'
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Create Tenure Distribution Chart (Doughnut)
     */
    function createTenureChart() {
        const { dashboardData, charts } = window.dashboardState;
        
        let chartElement = document.getElementById('tenureChart');
        
        // If canvas was destroyed by previous "no data" message, recreate it
        if (!chartElement) {
            const chartContainers = document.querySelectorAll('.chart-container');
            for (const container of chartContainers) {
                if (container.querySelector('.alert-info') && container.textContent.includes('tenure data')) {
                    container.innerHTML = '<canvas id="tenureChart"></canvas>';
                    chartElement = document.getElementById('tenureChart');
                    break;
                }
            }
        }
        
        if (!chartElement) {
            console.warn('Tenure chart element not found');
            return;
        }
        
        const ctx = chartElement.getContext('2d');
        
        // Destroy existing chart if it exists
        if (charts.tenure) {
            charts.tenure.destroy();
        }
        
        if (!dashboardData || !dashboardData.tenure_distribution || dashboardData.tenure_distribution.length === 0) {
            ctx.canvas.parentNode.innerHTML = '<div class="alert alert-info">No tenure data available yet. This will populate as surveys are completed.</div>';
            return;
        }
        
        const labels = dashboardData.tenure_distribution.map(item => item.tenure);
        const data = dashboardData.tenure_distribution.map(item => item.count);
        
        const config = getMobileChartConfig();
        
        charts.tenure = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Customers',
                    data: data,
                    backgroundColor: (function(){
                        const bp = getBrandPalette();
                        if (bp.configured && bp.primary) return bp.tintSequence(bp.primary, 5);
                        return ['#E13A44', '#000000', '#8A8A8A', '#BDBDBD', '#E9E8E4'];
                    })(),
                    borderColor: '#FFFFFF',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: config.maintainAspectRatio,
                plugins: {
                    legend: {
                        position: config.legendPosition,
                        labels: {
                            color: '#000000',
                            padding: config.legendPadding,
                            font: {
                                size: config.legendFontSize
                            }
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Create Growth Factor Analysis Chart (Bar)
     */
    function createGrowthFactorChart() {
        const { dashboardData, charts } = window.dashboardState;
        
        let chartElement = document.getElementById('growthFactorChart');
        
        // If canvas was destroyed by previous "no data" message, recreate it
        if (!chartElement) {
            const chartContainers = document.querySelectorAll('.chart-container');
            for (const container of chartContainers) {
                if (container.querySelector('.alert-info') && container.textContent.includes('growth factor data')) {
                    container.innerHTML = '<canvas id="growthFactorChart"></canvas>';
                    chartElement = document.getElementById('growthFactorChart');
                    break;
                }
            }
        }
        
        if (!chartElement) {
            console.warn('Growth factor chart element not found');
            return;
        }
        
        const ctx = chartElement.getContext('2d');
        
        // Destroy existing chart if it exists
        if (charts.growthFactor) {
            charts.growthFactor.destroy();
        }
        
        if (!dashboardData || 
            !dashboardData.growth_factor_analysis || 
            !dashboardData.growth_factor_analysis.distribution || 
            dashboardData.growth_factor_analysis.distribution.length === 0) {
            ctx.canvas.parentNode.innerHTML = '<div class="alert alert-info">No growth factor data available yet. This will populate as surveys are completed.</div>';
            return;
        }
        
        const distribution = dashboardData.growth_factor_analysis.distribution;
        const labels = distribution.map(item => `${item.nps_range} (${item.growth_rate})`);
        const data = distribution.map(item => item.count);
        // When brand accent is configured: apply semantic NPS_COLOR_MAP with accent
        // for growth/champion ranges, preserving red/yellow for negative/passive ranges.
        // When no brand is configured: fall back to the original positional color array
        // (no visual regression for unbranded accounts).
        const _gfBp = getBrandPalette();
        const _gfGrowthColor   = (_gfBp.configured && _gfBp.accent)
            ? _gfBp.tintSequence(_gfBp.accent, 2)[0] : '#22C55E';
        const _gfChampionColor = (_gfBp.configured && _gfBp.accent)
            ? _gfBp.tintSequence(_gfBp.accent, 2)[1] : '#15803d';
        const NPS_COLOR_MAP = {
            '<0':     '#991b1b',
            '0-29':   '#E13A44',
            '30-49':  '#f59e0b',
            '50-69':  _gfGrowthColor,
            '70-100': _gfChampionColor
        };
        const colors = distribution.map(item => NPS_COLOR_MAP[item.nps_range] || '#BDBDBD');
        
        const config = getMobileChartConfig();
        
        charts.growthFactor = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Customers',
                    data: data,
                    backgroundColor: colors,
                    borderColor: '#FFFFFF',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: config.maintainAspectRatio,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(context) {
                                const item = distribution[context.dataIndex];
                                return [`Growth Factor: ${item.avg_factor}`, `Expected Growth: ${item.growth_rate}`];
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#000000',
                            stepSize: 1,
                            font: {
                                size: config.fontSize
                            }
                        },
                        grid: {
                            color: '#E9E8E4'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#000000',
                            font: {
                                size: config.fontSize
                            }
                        },
                        grid: {
                            color: '#E9E8E4'
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Destroy a specific chart instance
     */
    function destroyChart(chartKey) {
        const charts = window.dashboardState.charts;
        if (charts[chartKey]) {
            charts[chartKey].destroy();
            delete charts[chartKey];
        }
    }
    
    /**
     * Destroy all chart instances
     */
    function destroyAllCharts() {
        const charts = window.dashboardState.charts;
        Object.keys(charts).forEach(key => {
            if (charts[key] && typeof charts[key].destroy === 'function') {
                charts[key].destroy();
            }
        });
        window.dashboardState.charts = {};
    }
    
    // Export public API
    window.dashboardModules.charts = {
        createNpsChart,
        createSentimentChart,
        createRatingsChart,
        createThemesChart,
        createTenureChart,
        createGrowthFactorChart,
        destroyChart,
        destroyAllCharts
    };
    
    console.log('📦 Dashboard Charts module loaded (complete implementation)');
    
})();
