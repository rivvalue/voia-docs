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
    const colors = ['#E13A44', '#BDBDBD', '#8A8A8A']; // Red (Detractor), Medium Gray (Passive), Dark Gray (Promoter)
    
    charts.npsChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#FFFFFF'
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
    const colors = ['#8A8A8A', '#BDBDBD', '#E13A44']; // Dark Gray (Positive), Medium Gray (Neutral), Red (Negative)
    
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
                        color: '#000000'
                    },
                    grid: {
                        color: '#E9E8E4'
                    }
                },
                x: {
                    ticks: {
                        color: '#000000'
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
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#000000'
                    }
                }
            },
            scales: {
                r: {
                    beginAtZero: true,
                    max: 5,
                    ticks: {
                        color: '#000000',
                        stepSize: 1
                    },
                    grid: {
                        color: '#BDBDBD'
                    },
                    pointLabels: {
                        color: '#000000'
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
                backgroundColor: '#BDBDBD',
                borderWidth: 1,
                borderColor: '#E9E8E4'
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
                        color: '#000000'
                    },
                    grid: {
                        color: '#E9E8E4'
                    }
                },
                x: {
                    beginAtZero: true,
                    ticks: {
                        color: '#000000'
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
                    '#FFFFFF'
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
                        padding: 20
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
                        stepSize: 1
                    },
                    grid: {
                        color: '#E9E8E4'
                    }
                },
                x: {
                    ticks: {
                        color: '#000000'
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

function loadSurveyResponses() {
    fetch('/api/survey_responses?per_page=10')
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('responsesTable');
            const responses = data.responses || data; // Handle both old and new format
            
            if (responses.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No survey responses yet.</td></tr>';
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
        })
        .catch(error => {
            console.error('Error loading survey responses:', error);
            document.getElementById('responsesTable').innerHTML = 
                '<tr><td colspan="7" class="text-center text-danger">Error loading responses.</td></tr>';
        });
}

function refreshData() {
    loadDashboardData();
}

function exportData() {
    // Check if user has admin token
    const token = localStorage.getItem('authToken');
    if (!token) {
        alert('Admin authentication required. Please use the Admin Login button first.');
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
            localStorage.setItem('authToken', data.token);
            alert('Admin login successful! You can now export data.');
            // Update button text
            const adminBtn = document.getElementById('adminLoginBtn');
            adminBtn.innerHTML = '<i class="fas fa-check me-2"></i>Admin Logged In';
            adminBtn.classList.remove('btn-outline-secondary');
            adminBtn.classList.add('btn-success');
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
        const adminBtn = document.getElementById('adminLoginBtn');
        adminBtn.innerHTML = '<i class="fas fa-check me-2"></i>Admin Logged In';
        adminBtn.classList.remove('btn-outline-secondary');
        adminBtn.classList.add('btn-success');
    }
}

// Auto-refresh dashboard every 5 minutes
setInterval(refreshData, 5 * 60 * 1000);

// Check admin status on page load
document.addEventListener('DOMContentLoaded', checkAdminStatus);
