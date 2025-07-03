// Dashboard JavaScript functionality

let dashboardData = null;
let charts = {};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadDashboardData();
});

function loadDashboardData() {
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
    // Update key metrics
    document.getElementById('totalResponses').textContent = dashboardData.total_responses || 0;
    document.getElementById('npsScore').textContent = dashboardData.nps_score || 0;
    document.getElementById('recentResponses').textContent = dashboardData.recent_responses || 0;
    document.getElementById('highRiskCount').textContent = dashboardData.high_risk_accounts?.length || 0;
    
    // Create charts
    createNpsChart();
    createSentimentChart();
    createRatingsChart();
    createThemesChart();
    
    // Populate high risk accounts
    populateHighRiskAccounts();
    
    // Populate growth opportunities
    populateGrowthOpportunities();
    
    // Load survey responses table
    loadSurveyResponses();
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
    const colors = ['#dc3545', '#ffc107', '#28a745']; // Red, Yellow, Green
    
    charts.npsChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#1a1a1a'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#ffffff',
                        usePointStyle: true,
                        padding: 20
                    }
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
    const labels = sentimentData.map(item => item.sentiment);
    const data = sentimentData.map(item => item.count);
    const colors = ['#28a745', '#6c757d', '#dc3545']; // Green, Gray, Red
    
    charts.sentimentChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Responses',
                data: data,
                backgroundColor: colors,
                borderWidth: 1,
                borderColor: '#1a1a1a'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#ffffff'
                    },
                    grid: {
                        color: '#333333'
                    }
                },
                x: {
                    ticks: {
                        color: '#ffffff'
                    },
                    grid: {
                        color: '#333333'
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
    
    charts.ratingsChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Rating',
                data: data,
                borderColor: '#007bff',
                backgroundColor: 'rgba(0, 123, 255, 0.1)',
                borderWidth: 2,
                pointBackgroundColor: '#007bff',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#ffffff'
                    }
                }
            },
            scales: {
                r: {
                    beginAtZero: true,
                    max: 5,
                    ticks: {
                        color: '#ffffff',
                        stepSize: 1
                    },
                    grid: {
                        color: '#333333'
                    },
                    pointLabels: {
                        color: '#ffffff'
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
    
    const labels = themes.map(item => item.theme);
    const data = themes.map(item => item.count);
    
    charts.themesChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Mentions',
                data: data,
                backgroundColor: '#17a2b8',
                borderWidth: 1,
                borderColor: '#1a1a1a'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#ffffff'
                    },
                    grid: {
                        color: '#333333'
                    }
                },
                x: {
                    beginAtZero: true,
                    ticks: {
                        color: '#ffffff'
                    },
                    grid: {
                        color: '#333333'
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
                    <span class="badge bg-danger">${Math.round(account.risk_score * 100)}% Risk</span>
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

function populateGrowthOpportunities() {
    const container = document.getElementById('growthOpportunities');
    const opportunities = dashboardData.growth_opportunities || [];
    
    if (opportunities.length === 0) {
        container.innerHTML = '<p class="text-muted">No growth opportunities identified.</p>';
        return;
    }
    
    const html = opportunities.map(opp => `
        <div class="opportunity-card p-3 mb-3 rounded">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h6 class="mb-1">${opp.company_name}</h6>
                    <p class="mb-2">${opp.description}</p>
                    <small class="text-muted">${opp.action}</small>
                </div>
                <span class="badge bg-primary">${opp.type}</span>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

function loadSurveyResponses() {
    fetch('/api/survey_responses')
        .then(response => response.json())
        .then(responses => {
            const tbody = document.getElementById('responsesTable');
            
            if (responses.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No survey responses yet.</td></tr>';
                return;
            }
            
            const html = responses.slice(0, 10).map(response => {
                const riskClass = response.churn_risk_score > 0.6 ? 'risk-high' : 
                                 response.churn_risk_score > 0.3 ? 'risk-medium' : 'risk-low';
                
                const sentimentClass = response.sentiment_label === 'positive' ? 'theme-positive' :
                                      response.sentiment_label === 'negative' ? 'theme-negative' : 'theme-neutral';
                
                return `
                    <tr>
                        <td>${response.company_name}</td>
                        <td>
                            <span class="badge ${response.nps_score >= 9 ? 'bg-success' : 
                                                response.nps_score >= 7 ? 'bg-warning' : 'bg-danger'}">
                                ${response.nps_score}
                            </span>
                        </td>
                        <td>${response.nps_category}</td>
                        <td class="${sentimentClass}">${response.sentiment_label || 'N/A'}</td>
                        <td class="${riskClass}">
                            ${response.churn_risk_score ? Math.round(response.churn_risk_score * 100) + '%' : 'N/A'}
                        </td>
                        <td>${response.created_at ? new Date(response.created_at).toLocaleDateString() : 'N/A'}</td>
                    </tr>
                `;
            }).join('');
            
            tbody.innerHTML = html;
        })
        .catch(error => {
            console.error('Error loading survey responses:', error);
            document.getElementById('responsesTable').innerHTML = 
                '<tr><td colspan="6" class="text-center text-danger">Error loading responses.</td></tr>';
        });
}

function refreshData() {
    loadDashboardData();
}

function exportData() {
    fetch('/api/export_data')
        .then(response => response.json())
        .then(data => {
            const dataStr = JSON.stringify(data, null, 2);
            const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
            
            const exportFileDefaultName = `voc_survey_data_${new Date().toISOString().split('T')[0]}.json`;
            
            const linkElement = document.createElement('a');
            linkElement.setAttribute('href', dataUri);
            linkElement.setAttribute('download', exportFileDefaultName);
            linkElement.click();
        })
        .catch(error => {
            console.error('Error exporting data:', error);
            alert('Error exporting data. Please try again.');
        });
}

// Auto-refresh dashboard every 5 minutes
setInterval(refreshData, 5 * 60 * 1000);
