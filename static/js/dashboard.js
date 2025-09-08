// Dashboard JavaScript functionality

let dashboardData = null;
let charts = {};

// Mobile detection and responsive configuration
function isMobile() {
    return window.innerWidth <= 768;
}

function getMobileChartConfig() {
    const isMob = isMobile();
    return {
        fontSize: isMob ? 10 : 14,
        legendFontSize: isMob ? 9 : 13,
        legendPosition: isMob ? 'bottom' : 'bottom',
        legendPadding: isMob ? 10 : 20,
        maintainAspectRatio: isMob ? true : false,
        chartHeight: isMob ? '250px' : '300px'
    };
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard JavaScript loaded and DOM ready');
    
    // Immediate fallback for company NPS data
    setTimeout(function() {
        console.log('Fallback: Loading company NPS data directly');
        loadCompanyNpsDataDirect();
    }, 1000);
    
    loadDashboardData();
});

// Direct company NPS data loading as fallback
function loadCompanyNpsDataDirect() {
    console.log('Direct loading of company NPS data...');
    fetch('/api/company_nps')
        .then(response => response.json())
        .then(data => {
            console.log('Direct API response:', data);
            if (data.success && data.data) {
                const tbody = document.getElementById('companyNpsTable');
                if (tbody) {
                    console.log('Found table, populating with', data.data.length, 'companies');
                    tbody.innerHTML = data.data.map(company => `
                        <tr>
                            <td><strong>${company.company_name}</strong></td>
                            <td>${company.total_responses}</td>
                            <td>${company.avg_nps}</td>
                            <td><span class="badge bg-primary">${company.company_nps}</span></td>
                            <td><small>${company.promoters}P / ${company.passives}Pa / ${company.detractors}D</small></td>
                            <td><span class="badge bg-warning">${company.risk_level}</span></td>
                            <td>${company.latest_response || 'N/A'}</td>
                            <td>${company.latest_churn_risk || 'N/A'}</td>
                        </tr>
                    `).join('');
                } else {
                    console.error('companyNpsTable element not found');
                }
            }
        })
        .catch(error => {
            console.error('Direct loading error:', error);
        });
}

function loadDashboardData() {
    console.log('loadDashboardData called');
    document.getElementById('loadingIndicator').classList.remove('d-none');
    document.getElementById('dashboardContent').classList.add('d-none');
    
    fetch('/api/dashboard_data')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            dashboardData = data;
            populateDashboard();
            
            document.getElementById('loadingIndicator').classList.add('d-none');
            document.getElementById('dashboardContent').classList.remove('d-none');
        })
        .catch(error => {
            console.error('Error loading dashboard data:', error);
            document.getElementById('loadingIndicator').innerHTML = 
                '<div class="alert alert-danger">Error loading dashboard data. Please try again.</div>';
        });
}

function populateDashboard() {
    console.log('populateDashboard called with data:', dashboardData);
    // Update key metrics
    document.getElementById('totalResponses').textContent = dashboardData.total_responses || 0;
    document.getElementById('npsScore').textContent = dashboardData.nps_score || 0;
    document.getElementById('recentResponses').textContent = dashboardData.recent_responses || 0;
    document.getElementById('highRiskCount').textContent = dashboardData.high_risk_accounts?.length || 0;
    
    // Growth potential as percentage
    const growthPotential = dashboardData.growth_factor_analysis?.total_growth_potential || 0;
    document.getElementById('growthPotential').textContent = Math.round(growthPotential * 100) + '%';
    
    // Create charts
    createNpsChart();
    createSentimentChart();
    createRatingsChart();
    createThemesChart();
    createTenureChart();
    createGrowthFactorChart();
    
    // Populate high risk accounts
    populateHighRiskAccounts();
    
    // Populate unified account intelligence
    populateAccountIntelligence();
    
    // Populate growth opportunities
    populateGrowthOpportunities();
    
    // Populate account risk factors
    populateAccountRiskFactors();
    
    // Load survey responses table
    loadSurveyResponses();
    
    // Load company NPS data
    console.log('About to call loadCompanyNpsData...');
    loadCompanyNpsData();
    
    // Load tenure NPS data
    console.log('About to call loadTenureNpsData...');
    loadTenureNpsData();
}

function createNpsChart() {
    const ctx = document.getElementById('npsChart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (charts.npsChart) {
        charts.npsChart.destroy();
    }
    
    const npsData = dashboardData.nps_distribution || [];
    const labels = npsData.map(item => item.category);
    const data = npsData.map(item => item.count);
    
    // Professional color palette matching the design
    const chartColors = ['#E13A44', '#BDBDBD', '#8A8A8A']; // Red (Detractor), Medium Gray (Passive), Dark Gray (Promoter)
    
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

function createSentimentChart() {
    const ctx = document.getElementById('sentimentChart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (charts.sentimentChart) {
        charts.sentimentChart.destroy();
    }
    
    const sentimentData = dashboardData.sentiment_distribution || [];
    const labels = sentimentData.map(item => item.sentiment.charAt(0).toUpperCase() + item.sentiment.slice(1));
    const data = sentimentData.map(item => item.count);
    const colors = ['#8A8A8A', '#BDBDBD', '#E13A44']; // Dark Gray (Positive), Medium Gray (Neutral), Red (Negative)
    
    // Get mobile-responsive configuration
    const config = getMobileChartConfig();
    
    charts.sentimentChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Responses',
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

function createRatingsChart() {
    const ctx = document.getElementById('ratingsChart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (charts.ratingsChart) {
        charts.ratingsChart.destroy();
    }
    
    const ratings = dashboardData.average_ratings || {};
    const labels = ['Satisfaction', 'Product Value', 'Service', 'Pricing'];
    const data = [
        ratings.satisfaction || 0,
        ratings.product_value || 0,
        ratings.service || 0,
        ratings.pricing || 0
    ];
    
    // Get mobile-responsive configuration
    const config = getMobileChartConfig();
    
    charts.ratingsChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Rating',
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

function createThemesChart() {
    const ctx = document.getElementById('themesChart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (charts.themesChart) {
        charts.themesChart.destroy();
    }
    
    const themes = dashboardData.key_themes || [];
    if (themes.length === 0) {
        // Display message when no themes are available
        const chartContainer = ctx.canvas.parentElement;
        chartContainer.innerHTML = '<div class="d-flex justify-content-center align-items-center" style="height: 300px;"><p class="text-muted">No themes identified yet</p></div>';
        return;
    }
    
    // Sort themes by count (descending) and take top 10
    const sortedThemes = themes.sort((a, b) => b.count - a.count).slice(0, 10);
    
    const labels = sortedThemes.map(item => item.theme.charAt(0).toUpperCase() + item.theme.slice(1));
    const data = sortedThemes.map(item => item.count);
    
    // Get mobile-responsive configuration
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

function createTenureChart() {
    const ctx = document.getElementById('tenureChart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (charts.tenure) {
        charts.tenure.destroy();
    }
    
    if (!dashboardData.tenure_distribution || dashboardData.tenure_distribution.length === 0) {
        ctx.canvas.parentNode.innerHTML = '<div class="alert alert-info">No tenure data available yet. This will populate as surveys are completed.</div>';
        return;
    }
    
    const labels = dashboardData.tenure_distribution.map(item => item.tenure);
    const data = dashboardData.tenure_distribution.map(item => item.count);
    
    charts.tenure = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                label: 'Customers',
                data: data,
                backgroundColor: [
                    '#E13A44',
                    '#BDBDBD', 
                    '#E9E8E4',
                    '#000000',
                    'rgba(225, 58, 68, 0.6)'
                ],
                borderColor: '#FFFFFF',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#000000',
                        padding: 20,
                        font: {
                            size: 14
                        }
                    }
                }
            }
        }
    });
}

function createGrowthFactorChart() {
    const ctx = document.getElementById('growthFactorChart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (charts.growthFactor) {
        charts.growthFactor.destroy();
    }
    
    if (!dashboardData.growth_factor_analysis || 
        !dashboardData.growth_factor_analysis.distribution || 
        dashboardData.growth_factor_analysis.distribution.length === 0) {
        ctx.canvas.parentNode.innerHTML = '<div class="alert alert-info">No growth factor data available yet. This will populate as surveys are completed.</div>';
        return;
    }
    
    const distribution = dashboardData.growth_factor_analysis.distribution;
    const labels = distribution.map(item => `${item.nps_range} (${item.growth_rate})`);
    const data = distribution.map(item => item.count);
    const colors = ['#E13A44', '#BDBDBD', '#E9E8E4', '#000000', '#FFFFFF'];
    
    charts.growthFactor = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Customers',
                data: data,
                backgroundColor: colors.slice(0, data.length),
                borderColor: '#FFFFFF',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
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
                            size: 14
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
                            size: 14
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

function populateHighRiskAccounts() {
    const container = document.getElementById('highRiskAccounts');
    const highRiskAccounts = dashboardData.high_risk_accounts || [];
    
    if (highRiskAccounts.length === 0) {
        container.innerHTML = '<p class="text-muted">No high-risk accounts identified.</p>';
        return;
    }
    
    const html = highRiskAccounts.map(account => `
        <div class="risk-card p-3 mb-3 rounded">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h6 class="mb-1">${account.company_name}</h6>
                    <small class="text-muted">NPS Score: ${account.nps_score}</small>
                </div>
                <div class="text-end">
                    <span class="badge bg-danger">${account.risk_level || 'High'} Risk</span>
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

function populateGrowthOpportunities() {
    const container = document.getElementById('growthOpportunities');
    const companiesWithOpportunities = dashboardData.growth_opportunities || [];
    
    if (companiesWithOpportunities.length === 0) {
        container.innerHTML = '<p class="text-muted">No growth opportunities identified.</p>';
        return;
    }
    
    const html = companiesWithOpportunities.map(company => {
        // Ensure company has a name and opportunities array
        const companyName = company.company_name || 'Unknown Company';
        const opportunities = company.opportunities || [];
        
        if (opportunities.length === 0) {
            return ''; // Skip companies with no opportunities
        }
        
        return `
            <div class="company-opportunities-card p-3 mb-4 rounded" style="border: 1px solid #BDBDBD;">
                <h6 class="mb-3" style="color: #E13A44; font-weight: bold;">${companyName}</h6>
                ${opportunities.map(opp => `
                    <div class="opportunity-card p-2 mb-2 rounded" style="background-color: #E9E8E4; border-left: 3px solid #E13A44;">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <p class="mb-1" style="color: #000000;">${opp.description || 'No description available'}</p>
                                <small class="text-muted">${opp.action || 'No action specified'}</small>
                            </div>
                            <span class="badge bg-primary">${opp.type || 'unknown'}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }).filter(html => html !== '').join(''); // Remove empty entries
    
    if (html === '') {
        container.innerHTML = '<p class="text-muted">No growth opportunities identified.</p>';
        return;
    }
    
    container.innerHTML = html;
}

// Visual mapping for risk factors and opportunities using established color palette
function getVisualIndicator(type, category) {
    const riskIcons = {
        'pricing_concerns': { icon: '💰', color: '#E13A44', label: 'Pricing' },
        'product_problems': { icon: '🔧', color: '#C52D36', label: 'Product' },
        'service_issues': { icon: '📞', color: '#E13A44', label: 'Service' },
        'churn_risk': { icon: '⚠️', color: '#8A8A8A', label: 'Churn Risk' },
        'low_satisfaction': { icon: '📉', color: '#C52D36', label: 'Low NPS' },
        'poor_ratings': { icon: '⭐', color: '#E13A44', label: 'Poor Ratings' },
        'contract_issues': { icon: '📋', color: '#BDBDBD', label: 'Contract' },
        'relationship_threat': { icon: '🔗', color: '#C52D36', label: 'Relationship' },
        'critical_satisfaction': { icon: '🚨', color: '#8A8A8A', label: 'Critical' }
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
        return riskIcons[type] || { icon: '⚠️', color: '#8A8A8A', label: 'Risk' };
    } else {
        return opportunityIcons[type] || { icon: '📈', color: '#8A8A8A', label: 'Opportunity' };
    }
}

function normalizeTypeForVisual(originalType) {
    const typeMap = {
        // Risk mappings
        'pricing concerns': 'pricing_concerns',
        'product problem': 'product_problems',
        'product problems': 'product_problems',
        'service issue': 'service_issues',
        'service issues': 'service_issues', 
        'churn risk': 'churn_risk',
        'low satisfaction': 'low_satisfaction',
        'poor ratings': 'poor_ratings',
        'contract risk': 'contract_issues',
        'critical satisfaction': 'critical_satisfaction',
        'relationship threat': 'relationship_threat',
        
        // Opportunity mappings
        'upsell potential': 'upsell',
        'cross-sell': 'cross_sell',
        'referral potential': 'referral',
        'advocacy': 'advocacy',
        'expansion ready': 'expansion',
        'high satisfaction': 'high_satisfaction',
        'engagement opportunity': 'engagement'
    };
    
    return typeMap[originalType.toLowerCase()] || originalType.toLowerCase().replace(/\s+/g, '_');
}

function populateAccountIntelligence() {
    const container = document.getElementById('accountIntelligence');
    const accountData = dashboardData.account_intelligence || [];
    
    if (accountData.length === 0) {
        container.innerHTML = '<p class="text-muted">No account intelligence data available.</p>';
        return;
    }
    
    // Create legend
    const legendHtml = `
        <div class="account-health-legend mb-4 p-3 rounded" style="background-color: #f8f9fa; border: 1px solid #dee2e6;">
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-success mb-2">🚀 Growth Opportunities</h6>
                    <div class="d-flex flex-wrap gap-2">
                        <span class="badge bg-light text-dark">📈 Upsell</span>
                        <span class="badge bg-light text-dark">🎯 Cross-sell</span>
                        <span class="badge bg-light text-dark">👥 Referral</span>
                        <span class="badge bg-light text-dark">📢 Advocacy</span>
                        <span class="badge bg-light text-dark">⭐ High NPS</span>
                    </div>
                </div>
                <div class="col-md-6">
                    <h6 class="text-danger mb-2">⚠️ Risk Factors</h6>
                    <div class="d-flex flex-wrap gap-2">
                        <span class="badge bg-light text-dark">💰 Pricing</span>
                        <span class="badge bg-light text-dark">🔧 Product</span>
                        <span class="badge bg-light text-dark">📞 Service</span>
                        <span class="badge bg-light text-dark">📉 Low NPS</span>
                        <span class="badge bg-light text-dark">🚨 Critical</span>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    const accountsHtml = accountData.map(account => {
        const balanceClass = account.balance === 'risk_heavy' ? 'border-danger' : 
                           account.balance === 'opportunity_heavy' ? 'border-success' : 'border-warning';
        
        const balanceIcon = account.balance === 'risk_heavy' ? '🔴' : 
                          account.balance === 'opportunity_heavy' ? '🟢' : '🟡';
        
        const balanceLabel = account.balance === 'risk_heavy' ? 'High Risk' : 
                           account.balance === 'opportunity_heavy' ? 'High Potential' : 'Balanced';
        
        // Consolidate opportunities by type to avoid duplicates
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
        
        // Create visual indicators for consolidated opportunities
        const opportunityIndicators = Array.from(opportunityMap.values()).map(opp => {
            const visual = getVisualIndicator(opp.normalizedType, 'opportunity');
            return `
                <span class="visual-indicator opportunity-indicator" 
                      style="background-color: ${visual.color}20; border: 2px solid ${visual.color}; padding: 4px 8px; margin: 2px; border-radius: 12px; display: inline-block;"
                      title="${opp.type}${opp.count > 1 ? ` (${opp.count} opportunities)` : ''}">
                    ${visual.icon} ${visual.label}${opp.count > 1 ? ` (${opp.count})` : ''}
                </span>
            `;
        }).join('');
        
        // Consolidate risks by type to avoid duplicates
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
        
        // Create visual indicators for consolidated risks  
        const riskIndicators = Array.from(riskMap.values()).map(risk => {
            const visual = getVisualIndicator(risk.normalizedType, 'risk');
            const intensityMap = { 'Critical': '●●●', 'High': '●●', 'Medium': '●', 'Low': '○' };
            const intensity = intensityMap[risk.severity] || '●';
            
            return `
                <span class="visual-indicator risk-indicator" 
                      style="background-color: ${visual.color}20; border: 2px solid ${visual.color}; padding: 4px 8px; margin: 2px; border-radius: 12px; display: inline-block;"
                      title="${risk.type} - ${risk.severity}${risk.count > 1 ? ` (${risk.count} instances)` : ''}">
                    ${visual.icon} ${visual.label} ${intensity}${risk.count > 1 ? ` (${risk.count})` : ''}
                </span>
            `;
        }).join('');
        
        return `
            <div class="account-visual-card card mb-3 ${balanceClass}" style="border-width: 2px;">
                <div class="card-body p-3">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5 class="mb-0">${account.company_name}</h5>
                        <div class="d-flex align-items-center">
                            <span style="font-size: 1.2em; margin-right: 5px;">${balanceIcon}</span>
                            <span class="badge bg-light text-dark">${balanceLabel}</span>
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
}

function populateAccountRiskFactors() {
    const container = document.getElementById('accountRiskFactors');
    const companiesWithRiskFactors = dashboardData.account_risk_factors || [];
    
    if (companiesWithRiskFactors.length === 0) {
        container.innerHTML = '<p class="text-muted">No account risk factors identified.</p>';
        return;
    }
    
    const html = companiesWithRiskFactors.map(company => {
        // Ensure company has a name and risk factors array
        if (!company.company_name || !company.risk_factors || !Array.isArray(company.risk_factors)) {
            return '';
        }
        
        const riskFactorsHtml = company.risk_factors.map(risk => {
            const severityClass = risk.severity === 'Critical' ? 'danger' : 
                                 risk.severity === 'High' ? 'warning' : 
                                 risk.severity === 'Medium' ? 'info' : 'secondary';
            
            return `
                <div class="risk-factor-item mb-3 p-3 border rounded">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h6 class="risk-type mb-1">${risk.type}</h6>
                        <span class="badge bg-${severityClass}">${risk.severity}</span>
                    </div>
                    <p class="risk-description text-muted mb-2">${risk.description}</p>
                    <small class="risk-action text-primary"><strong>Recommended Action:</strong> ${risk.action}</small>
                    ${risk.count > 1 ? `<div class="text-end"><small class="text-muted">${risk.count} occurrences</small></div>` : ''}
                </div>
            `;
        }).join('');
        
        return `
            <div class="company-risk-factors mb-4">
                <h6 class="company-name text-dark mb-3">
                    <i class="fas fa-exclamation-triangle text-warning me-2"></i>
                    ${company.company_name}
                </h6>
                ${riskFactorsHtml}
            </div>
        `;
    }).join('');
    
    if (html === '') {
        container.innerHTML = '<p class="text-muted">No account risk factors identified.</p>';
        return;
    }
    
    container.innerHTML = html;
}

// Pagination state for all tables
let currentResponsesPage = 1;
let currentCompanyPage = 1;
let currentTenurePage = 1;
const responsesPerPage = 10;
const companiesPerPage = 10;
const tenureGroupsPerPage = 10;

function loadSurveyResponses(page = 1) {
    currentResponsesPage = page;
    fetch(`/api/survey_responses?page=${page}&per_page=${responsesPerPage}`)
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('responsesTable');
            const responses = data.responses || data; // Handle both old and new format
            const pagination = data.pagination;
            
            if (responses.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No survey responses yet.</td></tr>';
                updatePaginationInfo(0, 0, 0);
                updatePaginationControls(null);
                return;
            }
            
            const html = responses.map(response => {
                const riskLevel = response.churn_risk_level || 'Minimal';
                const riskClass = riskLevel === 'High' ? 'risk-high' : 
                                 riskLevel === 'Medium' ? 'risk-medium' : 
                                 riskLevel === 'Low' ? 'risk-low' : 'risk-minimal';
                
                const sentimentClass = response.sentiment_label === 'positive' ? 'theme-positive' :
                                      response.sentiment_label === 'negative' ? 'theme-negative' : 'theme-neutral';
                
                return `
                    <tr>
                        <td>${response.company_name}</td>
                        <td>${response.tenure_with_fc || 'N/A'}</td>
                        <td>
                            <span class="badge ${response.nps_score >= 9 ? 'bg-success' : 
                                                response.nps_score >= 7 ? 'bg-warning' : 'bg-danger'}">
                                ${response.nps_score}
                            </span>
                        </td>
                        <td>${response.nps_category}</td>
                        <td class="${sentimentClass}">${response.sentiment_label || 'N/A'}</td>
                        <td class="${riskClass}">
                            ${riskLevel}
                        </td>
                        <td>${response.created_at ? new Date(response.created_at).toLocaleDateString() : 'N/A'}</td>
                    </tr>
                `;
            }).join('');
            
            tbody.innerHTML = html;
            
            // Update pagination info and controls
            if (pagination) {
                updateResponsesPaginationInfo(pagination.page, pagination.pages, pagination.total);
                updateResponsesPaginationControls(pagination);
            }
        })
        .catch(error => {
            console.error('Error loading survey responses:', error);
            document.getElementById('responsesTable').innerHTML = 
                '<tr><td colspan="7" class="text-center text-danger">Error loading responses.</td></tr>';
            updateResponsesPaginationInfo(0, 0, 0);
            updateResponsesPaginationControls(null);
        });
}

function updateResponsesPaginationInfo(currentPage, totalPages, totalItems) {
    const info = document.getElementById('paginationInfo');
    if (totalItems === 0) {
        info.textContent = 'No responses found';
    } else {
        const startItem = (currentPage - 1) * responsesPerPage + 1;
        const endItem = Math.min(currentPage * responsesPerPage, totalItems);
        info.textContent = `Showing ${startItem}-${endItem} of ${totalItems} responses`;
    }
}

function updateResponsesPaginationControls(pagination) {
    const controls = document.getElementById('paginationControls');
    
    if (!pagination || pagination.pages <= 1) {
        controls.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Previous button
    if (pagination.has_prev) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadSurveyResponses(${pagination.page - 1}); return false;">
                    <i class="fas fa-chevron-left"></i>
                </a>
            </li>
        `;
    } else {
        html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-left"></i></span></li>';
    }
    
    // Page numbers
    for (let i = 1; i <= pagination.pages; i++) {
        if (i === pagination.page) {
            html += `<li class="page-item active"><span class="page-link">${i}</span></li>`;
        } else {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="loadSurveyResponses(${i}); return false;">${i}</a></li>`;
        }
    }
    
    // Next button
    if (pagination.has_next) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadSurveyResponses(${pagination.page + 1}); return false;">
                    <i class="fas fa-chevron-right"></i>
                </a>
            </li>
        `;
    } else {
        html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-right"></i></span></li>';
    }
    
    controls.innerHTML = html;
}

// Company pagination functions
function updateCompanyPaginationInfo(currentPage, totalPages, totalItems) {
    const info = document.getElementById('companyPaginationInfo');
    if (totalItems === 0) {
        info.textContent = 'No companies found';
    } else {
        const startItem = (currentPage - 1) * companiesPerPage + 1;
        const endItem = Math.min(currentPage * companiesPerPage, totalItems);
        info.textContent = `Showing ${startItem}-${endItem} of ${totalItems} companies`;
    }
}

function updateCompanyPaginationControls(pagination) {
    const controls = document.getElementById('companyPaginationControls');
    
    if (!pagination || pagination.pages <= 1) {
        controls.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Previous button
    if (pagination.has_prev) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadCompanyNpsData(${pagination.page - 1}); return false;">
                    <i class="fas fa-chevron-left"></i>
                </a>
            </li>
        `;
    } else {
        html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-left"></i></span></li>';
    }
    
    // Page numbers
    for (let i = 1; i <= pagination.pages; i++) {
        if (i === pagination.page) {
            html += `<li class="page-item active"><span class="page-link">${i}</span></li>`;
        } else {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="loadCompanyNpsData(${i}); return false;">${i}</a></li>`;
        }
    }
    
    // Next button
    if (pagination.has_next) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadCompanyNpsData(${pagination.page + 1}); return false;">
                    <i class="fas fa-chevron-right"></i>
                </a>
            </li>
        `;
    } else {
        html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-right"></i></span></li>';
    }
    
    controls.innerHTML = html;
}

// Tenure pagination functions
function updateTenurePaginationInfo(currentPage, totalPages, totalItems) {
    const info = document.getElementById('tenurePaginationInfo');
    if (totalItems === 0) {
        info.textContent = 'No tenure data found';
    } else {
        const startItem = (currentPage - 1) * tenureGroupsPerPage + 1;
        const endItem = Math.min(currentPage * tenureGroupsPerPage, totalItems);
        info.textContent = `Showing ${startItem}-${endItem} of ${totalItems} tenure groups`;
    }
}

function updateTenurePaginationControls(pagination) {
    const controls = document.getElementById('tenurePaginationControls');
    
    if (!pagination || pagination.pages <= 1) {
        controls.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Previous button
    if (pagination.has_prev) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadTenureNpsData(${pagination.page - 1}); return false;">
                    <i class="fas fa-chevron-left"></i>
                </a>
            </li>
        `;
    } else {
        html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-left"></i></span></li>';
    }
    
    // Page numbers
    for (let i = 1; i <= pagination.pages; i++) {
        if (i === pagination.page) {
            html += `<li class="page-item active"><span class="page-link">${i}</span></li>`;
        } else {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="loadTenureNpsData(${i}); return false;">${i}</a></li>`;
        }
    }
    
    // Next button
    if (pagination.has_next) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadTenureNpsData(${pagination.page + 1}); return false;">
                    <i class="fas fa-chevron-right"></i>
                </a>
            </li>
        `;
    } else {
        html += '<li class="page-item disabled"><span class="page-link"><i class="fas fa-chevron-right"></i></span></li>';
    }
    
    controls.innerHTML = html;
}

function loadTenureNpsData(page = 1) {
    currentTenurePage = page;
    console.log('Loading tenure NPS data...');
    fetch(`/api/tenure_nps?page=${page}&per_page=${tenureGroupsPerPage}`)
        .then(response => response.json())
        .then(data => {
            console.log('Tenure NPS data received:', data);
            if (data.success) {
                console.log('Populating table with', data.data.length, 'tenure groups');
                populateTenureNpsTable(data.data);
                
                // Update pagination info and controls for tenure table
                if (data.pagination) {
                    updateTenurePaginationInfo(data.pagination.page, data.pagination.pages, data.pagination.total);
                    updateTenurePaginationControls(data.pagination);
                }
            } else {
                console.error('Error loading tenure NPS data:', data.error);
                document.getElementById('tenureNpsTable').innerHTML = 
                    '<tr><td colspan="8" class="text-center text-danger">Error: ' + (data.error || 'Unknown error') + '</td></tr>';
                updateTenurePaginationInfo(0, 0, 0);
                updateTenurePaginationControls(null);
            }
        })
        .catch(error => {
            console.error('Error fetching tenure NPS data:', error);
            document.getElementById('tenureNpsTable').innerHTML = 
                '<tr><td colspan="8" class="text-center text-danger">Network error loading tenure data</td></tr>';
            updateTenurePaginationInfo(0, 0, 0);
            updateTenurePaginationControls(null);
        });
}

function populateTenureNpsTable(tenureData) {
    console.log('populateTenureNpsTable called with:', tenureData);
    const tbody = document.getElementById('tenureNpsTable');
    
    if (!tbody) {
        console.error('tenureNpsTable element not found!');
        return;
    }
    
    if (!tenureData || tenureData.length === 0) {
        console.log('No tenure data to display');
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No tenure data available yet</td></tr>';
        return;
    }
    
    console.log('Rendering', tenureData.length, 'tenure groups to table');
    
    tbody.innerHTML = tenureData.map(tenure => {
        // Risk level badge styling
        let riskBadgeClass = 'bg-secondary';
        if (tenure.risk_level === 'Low') riskBadgeClass = 'bg-success';
        else if (tenure.risk_level === 'Medium') riskBadgeClass = 'bg-warning';
        else if (tenure.risk_level === 'High') riskBadgeClass = 'bg-danger';
        else if (tenure.risk_level === 'Critical') riskBadgeClass = 'bg-dark';
        else if (tenure.risk_level === 'Insufficient Data') riskBadgeClass = 'bg-secondary';
        
        // Tenure NPS badge styling
        let npsBadgeClass = 'bg-secondary';
        if (tenure.tenure_nps > 20) npsBadgeClass = 'bg-success';
        else if (tenure.tenure_nps >= -20) npsBadgeClass = 'bg-warning'; 
        else npsBadgeClass = 'bg-danger';
        
        // Distribution breakdown
        const distributionText = `${tenure.promoters}P / ${tenure.passives}Pa / ${tenure.detractors}D`;
        
        // Churn risk display
        const churnRiskDisplay = tenure.latest_churn_risk || 'N/A';
        
        return `
            <tr>
                <td><strong>${tenure.tenure_group}</strong></td>
                <td>${tenure.total_responses}</td>
                <td>${tenure.avg_nps}</td>
                <td><span class="badge ${npsBadgeClass}">${tenure.tenure_nps > 0 ? '+' : ''}${tenure.tenure_nps}</span></td>
                <td><small>${distributionText}</small></td>
                <td><span class="badge ${riskBadgeClass}">${tenure.risk_level}</span></td>
                <td>${tenure.latest_response || 'N/A'}</td>
                <td>${churnRiskDisplay}</td>
            </tr>
        `;
    }).join('');
}

function loadCompanyNpsData(page = 1) {
    currentCompanyPage = page;
    console.log('Loading company NPS data...');
    fetch(`/api/company_nps?page=${page}&per_page=${companiesPerPage}`)
        .then(response => response.json())
        .then(data => {
            console.log('Company NPS data received:', data);
            if (data.success) {
                console.log('Populating table with', data.data.length, 'companies');
                populateCompanyNpsTable(data.data);
                
                // Update pagination info and controls for company table
                if (data.pagination) {
                    updateCompanyPaginationInfo(data.pagination.page, data.pagination.pages, data.pagination.total);
                    updateCompanyPaginationControls(data.pagination);
                }
            } else {
                console.error('Error loading company NPS data:', data.error);
                document.getElementById('companyNpsTableServerSide').innerHTML = 
                    '<tr><td colspan="8" class="text-center text-danger">Error: ' + (data.error || 'Unknown error') + '</td></tr>';
                updateCompanyPaginationInfo(0, 0, 0);
                updateCompanyPaginationControls(null);
            }
        })
        .catch(error => {
            console.error('Error fetching company NPS data:', error);
            document.getElementById('companyNpsTableServerSide').innerHTML = 
                '<tr><td colspan="8" class="text-center text-danger">Network error loading company data</td></tr>';
            updateCompanyPaginationInfo(0, 0, 0);
            updateCompanyPaginationControls(null);
        });
}

function populateCompanyNpsTable(companyData) {
    console.log('populateCompanyNpsTable called with:', companyData);
    const tbody = document.getElementById('companyNpsTableServerSide');
    
    if (!tbody) {
        console.error('companyNpsTable element not found!');
        return;
    }
    
    if (!companyData || companyData.length === 0) {
        console.log('No company data to display');
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No company data available yet</td></tr>';
        return;
    }
    
    console.log('Rendering', companyData.length, 'companies to table');
    
    tbody.innerHTML = companyData.map(company => {
        // Risk level badge styling
        let riskBadgeClass = 'bg-secondary';
        if (company.risk_level === 'Low') riskBadgeClass = 'bg-success';
        else if (company.risk_level === 'Medium') riskBadgeClass = 'bg-warning';
        else if (company.risk_level === 'High') riskBadgeClass = 'bg-danger';
        else if (company.risk_level === 'Critical') riskBadgeClass = 'bg-dark';
        
        // Company NPS badge styling
        let npsBadgeClass = 'bg-secondary';
        if (company.company_nps > 20) npsBadgeClass = 'bg-success';
        else if (company.company_nps >= -20) npsBadgeClass = 'bg-warning'; 
        else npsBadgeClass = 'bg-danger';
        
        // Distribution breakdown
        const distributionText = `${company.promoters}P / ${company.passives}Pa / ${company.detractors}D`;
        
        // Churn risk display
        const churnRiskDisplay = company.latest_churn_risk || 'N/A';
        
        return `
            <tr>
                <td><strong>${company.company_name}</strong></td>
                <td>${company.total_responses}</td>
                <td>${company.avg_nps}</td>
                <td><span class="badge ${npsBadgeClass}">${company.company_nps > 0 ? '+' : ''}${company.company_nps}</span></td>
                <td><small>${distributionText}</small></td>
                <td><span class="badge ${riskBadgeClass}">${company.risk_level}</span></td>
                <td>${company.latest_response || 'N/A'}</td>
                <td>${churnRiskDisplay}</td>
            </tr>
        `;
    }).join('');
}

function refreshData() {
    loadDashboardData();
    loadCompanyNpsData();
}

function exportData() {
    // Check if user has admin token
    const token = localStorage.getItem('authToken');
    if (!token) {
        alert('Download is only available to admin users. Please log in as Admin first.');
        return;
    }
    
    fetch('/api/export_data', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (response.status === 403) {
            alert('Admin access required. This feature is only available to administrators.');
            // Clear invalid token
            localStorage.removeItem('authToken');
            // Reset admin button
            const adminBtn = document.getElementById('adminLoginBtn');
            adminBtn.innerHTML = '<i class="fas fa-key me-2"></i>Admin Login';
            adminBtn.classList.remove('btn-success');
            adminBtn.classList.add('btn-outline-secondary');
            return null;
        }
        if (response.status === 401) {
            alert('Authentication failed. Please log in with an admin account.');
            // Clear invalid token
            localStorage.removeItem('authToken');
            // Reset admin button
            const adminBtn = document.getElementById('adminLoginBtn');
            adminBtn.innerHTML = '<i class="fas fa-key me-2"></i>Admin Login';
            adminBtn.classList.remove('btn-success');
            adminBtn.classList.add('btn-outline-secondary');
            return null;
        }
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(result => {
        if (!result) return; // Authentication failed
        
        const data = result.data || result; // Handle both old and new format
        const dataStr = JSON.stringify(data, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
        
        const exportFileDefaultName = `voc_survey_data_${new Date().toISOString().split('T')[0]}.json`;
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
        
        // Show success message if we have export info
        if (result.export_info) {
            console.log(`Data exported successfully by ${result.export_info.exported_by}`);
        }
    })
    .catch(error => {
        console.error('Error exporting data:', error);
        alert('Error exporting data. Please try again or contact administrator.');
    });
}

// Export user-specific data (current user's responses only)
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

// Admin login function
function adminLogin() {
    const email = prompt('Enter admin email address:');
    if (!email) return;
    
    // Generate admin token
    fetch('/auth/request-token', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: email })
    })
    .then(response => response.json())
    .then(data => {
        if (data.token) {
            // Clear any existing token first
            localStorage.removeItem('authToken');
            
            // Verify this is actually an admin token before storing
            fetch('/auth/verify-token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ token: data.token })
            })
            .then(response => response.json())
            .then(verifyData => {
                if (verifyData.valid && verifyData.is_admin) {
                    localStorage.setItem('authToken', data.token);
                    alert(`Admin login successful for ${email}! You can now export data.`);
                    // Update button text
                    const adminBtn = document.getElementById('adminLoginBtn');
                    adminBtn.innerHTML = `<i class="fas fa-check me-2"></i>Admin: ${email}`;
                    adminBtn.classList.remove('btn-outline-secondary');
                    adminBtn.classList.add('btn-success');
                } else {
                    alert(`Access denied. ${email} is not an admin user.`);
                }
            })
            .catch(error => {
                alert('Token verification failed.');
            });
        } else {
            alert('Failed to generate admin token: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error generating admin token:', error);
        alert('Error generating admin token. Please try again.');
    });
}

// Check admin login status on page load
function checkAdminStatus() {
    const token = localStorage.getItem('authToken');
    if (token) {
        // Verify the token is still valid and is admin
        fetch('/auth/verify-token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ token: token })
        })
        .then(response => response.json())
        .then(data => {
            if (data.valid && data.is_admin) {
                const adminBtn = document.getElementById('adminLoginBtn');
                adminBtn.innerHTML = `<i class="fas fa-check me-2"></i>Admin: ${data.email}`;
                adminBtn.classList.remove('btn-outline-secondary');
                adminBtn.classList.add('btn-success');
                adminBtn.onclick = adminLogout; // Change to logout function
            } else {
                // Token is invalid or not admin, clear it
                localStorage.removeItem('authToken');
                resetAdminButton();
            }
        })
        .catch(error => {
            // Token verification failed, clear it
            localStorage.removeItem('authToken');
            resetAdminButton();
        });
    }
}

function adminLogout() {
    localStorage.removeItem('authToken');
    resetAdminButton();
    alert('Admin logged out successfully.');
}

function resetAdminButton() {
    const adminBtn = document.getElementById('adminLoginBtn');
    adminBtn.innerHTML = '<i class="fas fa-key me-2"></i>Admin Login';
    adminBtn.classList.remove('btn-success');
    adminBtn.classList.add('btn-outline-secondary');
    adminBtn.onclick = adminLogin;
}

// Auto-refresh dashboard every 5 minutes
setInterval(refreshData, 5 * 60 * 1000);

// Check admin status on page load
document.addEventListener('DOMContentLoaded', checkAdminStatus);
