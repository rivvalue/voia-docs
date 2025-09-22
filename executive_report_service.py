"""
Executive Report Generation Service
Generates comprehensive PDF reports for completed campaigns with KPI deltas and business branding
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import base64
from jinja2 import Template
import weasyprint
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, desc

# Configure matplotlib for non-interactive use
plt.switch_backend('Agg')
plt.style.use('default')

logger = logging.getLogger(__name__)

class ExecutiveReportGenerator:
    """Generates executive reports for completed campaigns"""
    
    def __init__(self):
        self.report_dir = "/tmp/executive_reports"
        os.makedirs(self.report_dir, exist_ok=True)
    
    def generate_campaign_report(self, campaign_id: int, business_account_id: int) -> Optional[str]:
        """
        Generate executive report for a completed campaign
        Returns file path of generated PDF or None if failed
        """
        try:
            from models import Campaign, SurveyResponse, BusinessAccount
            from app import db
            
            # Get campaign data
            campaign = Campaign.query.filter_by(
                id=campaign_id,
                business_account_id=business_account_id
            ).first()
            
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found for business {business_account_id}")
                return None
            
            # Get business account for branding
            business_account = BusinessAccount.query.get(business_account_id)
            if not business_account:
                logger.error(f"Business account {business_account_id} not found")
                return None
            
            # Generate report data
            report_data = self._collect_report_data(campaign, business_account)
            
            # Generate PDF
            pdf_path = self._generate_pdf_report(report_data, campaign, business_account)
            
            logger.info(f"Executive report generated: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            logger.error(f"Error generating executive report: {e}")
            return None
    
    def _collect_report_data(self, campaign, business_account) -> Dict:
        """Collect all data needed for the executive report"""
        from models import SurveyResponse, Campaign
        from app import db
        # Note: NPS calculation handled directly in this function
        
        # Get campaign responses via CampaignParticipant
        from models import CampaignParticipant
        responses = SurveyResponse.query.join(
            CampaignParticipant, SurveyResponse.campaign_participant_id == CampaignParticipant.id
        ).filter(
            CampaignParticipant.campaign_id == campaign.id
        ).options(
            joinedload(SurveyResponse.campaign_participant)
        ).all()
        
        # Calculate current campaign KPIs
        current_kpis = self._calculate_campaign_kpis(responses)
        
        # Get previous campaigns for delta calculations
        previous_campaigns = self._get_previous_campaigns(campaign, business_account.id)
        delta_kpis = self._calculate_kpi_deltas(current_kpis, previous_campaigns)
        
        # Generate visualizations
        charts = self._generate_charts(responses, current_kpis)
        
        # Get AI insights
        ai_insights = self._extract_ai_insights(responses)
        
        return {
            'campaign': campaign,
            'business_account': business_account,
            'responses': responses,
            'current_kpis': current_kpis,
            'delta_kpis': delta_kpis,
            'previous_campaigns': previous_campaigns,
            'charts': charts,
            'ai_insights': ai_insights,
            'generated_at': datetime.utcnow()
        }
    
    def _calculate_campaign_kpis(self, responses: List) -> Dict:
        """Calculate KPIs for current campaign"""
        if not responses:
            return {
                'total_responses': 0,
                'nps_score': 0,
                'response_rate': 0,
                'sentiment_breakdown': {'positive': 0, 'neutral': 0, 'negative': 0},
                'avg_churn_risk': 0,
                'avg_growth_score': 0
            }
        
        # Basic metrics
        total_responses = len(responses)
        nps_scores = [r.nps_score for r in responses if r.nps_score is not None]
        nps_score = sum(nps_scores) / len(nps_scores) if nps_scores else 0
        
        # Sentiment analysis
        sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
        churn_risks = []
        growth_scores = []
        
        for response in responses:
            if response.ai_analysis:
                try:
                    analysis = json.loads(response.ai_analysis)
                    
                    # Sentiment
                    sentiment = analysis.get('sentiment', 'neutral').lower()
                    if sentiment in sentiment_counts:
                        sentiment_counts[sentiment] += 1
                    
                    # Churn risk and growth scores
                    if 'churn_risk_score' in analysis:
                        churn_risks.append(analysis['churn_risk_score'])
                    if 'growth_opportunity_score' in analysis:
                        growth_scores.append(analysis['growth_opportunity_score'])
                        
                except (json.JSONDecodeError, KeyError):
                    continue
        
        # Calculate percentages for sentiment
        sentiment_breakdown = {}
        for sentiment, count in sentiment_counts.items():
            sentiment_breakdown[sentiment] = (count / total_responses * 100) if total_responses > 0 else 0
        
        return {
            'total_responses': total_responses,
            'nps_score': round(nps_score, 1),
            'response_rate': 85.0,  # TODO: Calculate actual response rate from participants
            'sentiment_breakdown': sentiment_breakdown,
            'avg_churn_risk': round(sum(churn_risks) / len(churn_risks), 1) if churn_risks else 0,
            'avg_growth_score': round(sum(growth_scores) / len(growth_scores), 1) if growth_scores else 0
        }
    
    def _get_previous_campaigns(self, current_campaign, business_account_id: int) -> List:
        """Get previous campaigns within the same license period for comparison"""
        from models import Campaign
        try:
            from license_service import LicenseService
        except ImportError:
            # Fallback if license_service not available
            return []
        
        # Get current license period
        start_date, end_date = LicenseService.get_license_period(business_account_id, current_campaign.created_at.date())
        if not start_date or not end_date:
            return []
        
        # Get previous campaigns in same license period
        previous_campaigns = Campaign.query.filter(
            Campaign.business_account_id == business_account_id,
            Campaign.id != current_campaign.id,
            Campaign.status == 'completed',
            Campaign.created_at >= start_date,
            Campaign.created_at <= end_date,
            Campaign.created_at < current_campaign.created_at
        ).order_by(desc(Campaign.created_at)).all()
        
        return previous_campaigns
    
    def _calculate_kpi_deltas(self, current_kpis: Dict, previous_campaigns: List) -> Dict:
        """Calculate KPI changes from previous campaigns"""
        if not previous_campaigns:
            return {
                'nps_delta': None,
                'response_rate_delta': None,
                'sentiment_delta': None,
                'churn_risk_delta': None,
                'growth_score_delta': None,
                'trend_direction': 'baseline',
                'comparison_count': 0
            }
        
        # Get most recent previous campaign for comparison
        prev_campaign = previous_campaigns[0]
        prev_responses = prev_campaign.responses.all() if prev_campaign.responses else []
        prev_kpis = self._calculate_campaign_kpis(prev_responses)
        
        # Calculate deltas
        nps_delta = current_kpis['nps_score'] - prev_kpis['nps_score']
        response_rate_delta = current_kpis['response_rate'] - prev_kpis['response_rate']
        churn_risk_delta = current_kpis['avg_churn_risk'] - prev_kpis['avg_churn_risk']
        growth_score_delta = current_kpis['avg_growth_score'] - prev_kpis['avg_growth_score']
        
        # Determine overall trend
        positive_indicators = sum([
            nps_delta > 0,
            response_rate_delta > 0,
            churn_risk_delta < 0,  # Lower churn risk is better
            growth_score_delta > 0
        ])
        
        if positive_indicators >= 3:
            trend_direction = 'improving'
        elif positive_indicators <= 1:
            trend_direction = 'declining'
        else:
            trend_direction = 'stable'
        
        return {
            'nps_delta': round(nps_delta, 1),
            'response_rate_delta': round(response_rate_delta, 1),
            'churn_risk_delta': round(churn_risk_delta, 1),
            'growth_score_delta': round(growth_score_delta, 1),
            'trend_direction': trend_direction,
            'previous_campaign_name': prev_campaign.name,
            'comparison_count': len(previous_campaigns)
        }
    
    def _generate_charts(self, responses: List, kpis: Dict) -> Dict:
        """Generate chart images for the report"""
        charts = {}
        
        try:
            # NPS Distribution Chart
            charts['nps_distribution'] = self._create_nps_distribution_chart(responses)
            
            # Sentiment Breakdown Chart
            charts['sentiment_breakdown'] = self._create_sentiment_chart(kpis['sentiment_breakdown'])
            
            # Response Timeline Chart
            charts['response_timeline'] = self._create_response_timeline_chart(responses)
            
        except Exception as e:
            logger.error(f"Error generating charts: {e}")
        
        return charts
    
    def _create_nps_distribution_chart(self, responses: List) -> str:
        """Create NPS distribution chart"""
        fig, ax = plt.subplots(figsize=(8, 4))
        
        nps_scores = [r.nps_score for r in responses if r.nps_score is not None]
        if not nps_scores:
            ax.text(0.5, 0.5, 'No NPS data available', ha='center', va='center', transform=ax.transAxes)
            ax.set_xlim(0, 10)
            ax.set_ylim(0, 1)
        else:
            # Create bins for NPS categories
            detractors = len([s for s in nps_scores if s <= 6])
            passives = len([s for s in nps_scores if 7 <= s <= 8])
            promoters = len([s for s in nps_scores if s >= 9])
            
            categories = ['Detractors\n(0-6)', 'Passives\n(7-8)', 'Promoters\n(9-10)']
            values = [detractors, passives, promoters]
            colors = ['#ff6b6b', '#ffd93d', '#6bcf7f']
            
            bars = ax.bar(categories, values, color=colors, alpha=0.8)
            ax.set_ylabel('Number of Responses')
            ax.set_title('NPS Distribution')
            
            # Add value labels on bars
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                       f'{value}', ha='center', va='bottom')
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _create_sentiment_chart(self, sentiment_breakdown: Dict) -> str:
        """Create sentiment breakdown pie chart"""
        fig, ax = plt.subplots(figsize=(6, 6))
        
        sentiments = list(sentiment_breakdown.keys())
        values = list(sentiment_breakdown.values())
        
        if sum(values) == 0:
            ax.text(0.5, 0.5, 'No sentiment data available', ha='center', va='center', transform=ax.transAxes)
        else:
            colors = ['#6bcf7f', '#ffd93d', '#ff6b6b']
            pie_result = ax.pie(values, labels=sentiments, colors=colors, autopct='%1.1f%%', startangle=90)
            # Handle both 2-tuple and 3-tuple returns from matplotlib
            if len(pie_result) == 3:
                wedges, texts, autotexts = pie_result
            else:
                wedges, texts = pie_result
            ax.set_title('Sentiment Distribution')
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _create_response_timeline_chart(self, responses: List) -> str:
        """Create response timeline chart"""
        fig, ax = plt.subplots(figsize=(10, 4))
        
        if not responses:
            ax.text(0.5, 0.5, 'No response data available', ha='center', va='center', transform=ax.transAxes)
        else:
            # Group responses by date
            dates = [r.created_at.date() for r in responses]
            date_counts = {}
            for date in dates:
                date_counts[date] = date_counts.get(date, 0) + 1
            
            sorted_dates = sorted(date_counts.keys())
            counts = [date_counts[date] for date in sorted_dates]
            
            ax.plot(sorted_dates, counts, marker='o', linewidth=2, markersize=6, color='#4a90e2')
            ax.set_xlabel('Date')
            ax.set_ylabel('Responses')
            ax.set_title('Response Timeline')
            ax.grid(True, alpha=0.3)
            
            # Format x-axis dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(sorted_dates) // 10)))
            plt.xticks(rotation=45)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _fig_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string"""
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close(fig)
        return f"data:image/png;base64,{image_base64}"
    
    def _extract_ai_insights(self, responses: List) -> Dict:
        """Extract and summarize AI insights from responses"""
        themes = {}
        recommendations = []
        critical_issues = []
        
        for response in responses:
            if response.ai_analysis:
                try:
                    analysis = json.loads(response.ai_analysis)
                    
                    # Extract themes
                    if 'themes' in analysis:
                        for theme in analysis['themes']:
                            theme_name = theme.get('theme', 'Unknown')
                            if theme_name not in themes:
                                themes[theme_name] = {'count': 0, 'impact': []}
                            themes[theme_name]['count'] += 1
                            if 'impact' in theme:
                                themes[theme_name]['impact'].append(theme['impact'])
                    
                    # Extract high-impact items
                    if analysis.get('churn_risk_score', 0) >= 8:
                        critical_issues.append({
                            'respondent': response.respondent_name,
                            'issue': analysis.get('key_issues', ['High churn risk'])[0] if analysis.get('key_issues') else 'High churn risk',
                            'score': analysis.get('churn_risk_score')
                        })
                    
                except (json.JSONDecodeError, KeyError):
                    continue
        
        # Sort themes by frequency and impact
        sorted_themes = sorted(themes.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
        
        return {
            'top_themes': sorted_themes,
            'critical_issues': critical_issues[:3],  # Top 3 critical issues
            'total_themes': len(themes),
            'insights_available': len([r for r in responses if r.ai_analysis])
        }
    
    def _generate_pdf_report(self, report_data: Dict, campaign, business_account) -> str:
        """Generate the final PDF report"""
        # Create HTML content from template
        html_content = self._render_html_template(report_data)
        
        # Generate PDF
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"executive_report_{campaign.id}_{timestamp}.pdf"
        pdf_path = os.path.join(self.report_dir, filename)
        
        # Convert HTML to PDF
        weasyprint.HTML(string=html_content).write_pdf(pdf_path)
        
        return pdf_path
    
    def _render_html_template(self, report_data: Dict) -> str:
        """Render HTML template with report data"""
        template_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Executive Report - {{ campaign.name }}</title>
            <style>
                @page {
                    size: A4;
                    margin: 1in;
                    @top-center {
                        content: "{{ business_account.name }} - Executive Report";
                        font-size: 10px;
                        color: #666;
                    }
                    @bottom-center {
                        content: "Page " counter(page) " of " counter(pages);
                        font-size: 10px;
                        color: #666;
                    }
                }
                
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                }
                
                .header {
                    text-align: center;
                    border-bottom: 3px solid #4a90e2;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }
                
                .logo {
                    max-height: 60px;
                    margin-bottom: 10px;
                }
                
                .company-name {
                    font-size: 24px;
                    font-weight: bold;
                    color: #4a90e2;
                    margin-bottom: 5px;
                }
                
                .report-title {
                    font-size: 28px;
                    font-weight: bold;
                    margin-bottom: 5px;
                }
                
                .campaign-name {
                    font-size: 18px;
                    color: #666;
                    margin-bottom: 10px;
                }
                
                .report-date {
                    font-size: 12px;
                    color: #888;
                }
                
                .section {
                    margin-bottom: 30px;
                    page-break-inside: avoid;
                }
                
                .section-title {
                    font-size: 20px;
                    font-weight: bold;
                    color: #4a90e2;
                    border-bottom: 2px solid #e0e0e0;
                    padding-bottom: 5px;
                    margin-bottom: 15px;
                }
                
                .kpi-grid {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 20px;
                    margin-bottom: 20px;
                }
                
                .kpi-card {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #4a90e2;
                }
                
                .kpi-value {
                    font-size: 24px;
                    font-weight: bold;
                    color: #4a90e2;
                }
                
                .kpi-label {
                    font-size: 14px;
                    color: #666;
                    margin-top: 5px;
                }
                
                .kpi-delta {
                    font-size: 12px;
                    margin-top: 5px;
                }
                
                .delta-positive { color: #28a745; }
                .delta-negative { color: #dc3545; }
                .delta-neutral { color: #6c757d; }
                
                .chart-container {
                    text-align: center;
                    margin: 20px 0;
                }
                
                .chart-image {
                    max-width: 100%;
                    height: auto;
                }
                
                .insights-list {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 15px;
                }
                
                .insight-item {
                    margin-bottom: 10px;
                    padding-bottom: 10px;
                    border-bottom: 1px solid #e0e0e0;
                }
                
                .insight-item:last-child {
                    border-bottom: none;
                    margin-bottom: 0;
                    padding-bottom: 0;
                }
                
                .recommendation {
                    background: #e7f3ff;
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #007bff;
                    margin-bottom: 10px;
                }
                
                .page-break {
                    page-break-before: always;
                }
                
                .summary-box {
                    background: #f0f8ff;
                    padding: 20px;
                    border-radius: 8px;
                    border: 1px solid #b3d9ff;
                    margin-bottom: 20px;
                }
            </style>
        </head>
        <body>
            <!-- Header -->
            <div class="header">
                {% if business_account.logo_url %}
                <img src="{{ business_account.logo_url }}" alt="{{ business_account.name }}" class="logo">
                {% endif %}
                <div class="company-name">{{ business_account.name }}</div>
                <div class="report-title">Executive Report</div>
                <div class="campaign-name">{{ campaign.name }}</div>
                <div class="report-date">Generated on {{ generated_at.strftime('%B %d, %Y at %I:%M %p UTC') }}</div>
            </div>

            <!-- Executive Summary -->
            <div class="section">
                <h2 class="section-title">📊 Executive Summary</h2>
                <div class="summary-box">
                    <p><strong>Campaign Performance:</strong> {{ campaign.name }} completed with {{ current_kpis.total_responses }} responses and an NPS score of {{ current_kpis.nps_score }}.</p>
                    
                    {% if delta_kpis.nps_delta is not none %}
                    <p><strong>Trend:</strong> 
                        {% if delta_kpis.trend_direction == 'improving' %}
                        📈 Performance is <strong>improving</strong> compared to {{ delta_kpis.previous_campaign_name }}.
                        {% elif delta_kpis.trend_direction == 'declining' %}
                        📉 Performance shows <strong>decline</strong> compared to {{ delta_kpis.previous_campaign_name }}.
                        {% else %}
                        📊 Performance remains <strong>stable</strong> compared to {{ delta_kpis.previous_campaign_name }}.
                        {% endif %}
                    </p>
                    {% endif %}
                    
                    <p><strong>Key Insights:</strong> {{ ai_insights.insights_available }} responses analyzed with {{ ai_insights.total_themes }} distinct themes identified.</p>
                    
                    {% if ai_insights.critical_issues %}
                    <p><strong>Immediate Attention Required:</strong> {{ ai_insights.critical_issues|length }} high-risk respondents identified.</p>
                    {% endif %}
                </div>
            </div>

            <!-- Campaign Overview -->
            <div class="section">
                <h2 class="section-title">📈 Campaign Overview</h2>
                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-value">{{ current_kpis.total_responses }}</div>
                        <div class="kpi-label">Total Responses</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-value">{{ current_kpis.response_rate }}%</div>
                        <div class="kpi-label">Response Rate</div>
                        {% if delta_kpis.response_rate_delta is not none %}
                        <div class="kpi-delta {{ 'delta-positive' if delta_kpis.response_rate_delta > 0 else 'delta-negative' if delta_kpis.response_rate_delta < 0 else 'delta-neutral' }}">
                            {{ '+' if delta_kpis.response_rate_delta > 0 else '' }}{{ delta_kpis.response_rate_delta }}% from previous
                        </div>
                        {% endif %}
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-value">{{ current_kpis.nps_score }}</div>
                        <div class="kpi-label">NPS Score</div>
                        {% if delta_kpis.nps_delta is not none %}
                        <div class="kpi-delta {{ 'delta-positive' if delta_kpis.nps_delta > 0 else 'delta-negative' if delta_kpis.nps_delta < 0 else 'delta-neutral' }}">
                            {{ '+' if delta_kpis.nps_delta > 0 else '' }}{{ delta_kpis.nps_delta }} from previous
                        </div>
                        {% endif %}
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-value">{{ current_kpis.avg_churn_risk }}/10</div>
                        <div class="kpi-label">Avg Churn Risk</div>
                        {% if delta_kpis.churn_risk_delta is not none %}
                        <div class="kpi-delta {{ 'delta-negative' if delta_kpis.churn_risk_delta > 0 else 'delta-positive' if delta_kpis.churn_risk_delta < 0 else 'delta-neutral' }}">
                            {{ '+' if delta_kpis.churn_risk_delta > 0 else '' }}{{ delta_kpis.churn_risk_delta }} from previous
                        </div>
                        {% endif %}
                    </div>
                </div>
                
                <p><strong>Campaign Duration:</strong> {{ campaign.start_date.strftime('%B %d, %Y') }} - {{ campaign.end_date.strftime('%B %d, %Y') }}</p>
                <p><strong>Status:</strong> {{ campaign.status.title() }}</p>
            </div>

            <!-- Key Performance Indicators -->
            <div class="section page-break">
                <h2 class="section-title">🎯 Key Performance Indicators</h2>
                
                {% if charts.nps_distribution %}
                <div class="chart-container">
                    <h3>NPS Distribution</h3>
                    <img src="{{ charts.nps_distribution }}" alt="NPS Distribution" class="chart-image">
                </div>
                {% endif %}
                
                {% if charts.sentiment_breakdown %}
                <div class="chart-container">
                    <h3>Sentiment Analysis</h3>
                    <img src="{{ charts.sentiment_breakdown }}" alt="Sentiment Breakdown" class="chart-image">
                </div>
                {% endif %}
            </div>

            <!-- Strategic Insights -->
            <div class="section page-break">
                <h2 class="section-title">💡 Strategic Insights</h2>
                
                {% if ai_insights.top_themes %}
                <h3>Top Themes Identified</h3>
                <div class="insights-list">
                    {% for theme_name, theme_data in ai_insights.top_themes %}
                    <div class="insight-item">
                        <strong>{{ theme_name }}</strong> - Mentioned by {{ theme_data.count }} respondent{{ 's' if theme_data.count != 1 else '' }}
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
                
                {% if ai_insights.critical_issues %}
                <h3>Critical Issues Requiring Attention</h3>
                <div class="insights-list">
                    {% for issue in ai_insights.critical_issues %}
                    <div class="insight-item">
                        <strong>{{ issue.respondent }}:</strong> {{ issue.issue }} (Risk Score: {{ issue.score }}/10)
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
                
                {% if charts.response_timeline %}
                <div class="chart-container">
                    <h3>Response Timeline</h3>
                    <img src="{{ charts.response_timeline }}" alt="Response Timeline" class="chart-image">
                </div>
                {% endif %}
            </div>

            <!-- Recommendations -->
            <div class="section page-break">
                <h2 class="section-title">🚀 Recommendations & Action Plan</h2>
                
                <div class="recommendation">
                    <strong>Immediate Actions (Next 30 days):</strong>
                    <ul>
                        {% if current_kpis.avg_churn_risk > 6 %}
                        <li>Address high churn risk respondents identified in critical issues section</li>
                        {% endif %}
                        {% if current_kpis.nps_score < 50 %}
                        <li>Develop improvement plan to address primary detractor concerns</li>
                        {% endif %}
                        <li>Follow up with survey participants to validate AI-identified themes</li>
                    </ul>
                </div>
                
                <div class="recommendation">
                    <strong>Strategic Initiatives (Next 90 days):</strong>
                    <ul>
                        <li>Implement improvements based on top themes from AI analysis</li>
                        {% if delta_kpis.trend_direction == 'declining' %}
                        <li>Investigate root causes of performance decline since previous campaign</li>
                        {% endif %}
                        <li>Prepare next campaign with focus on identified improvement areas</li>
                    </ul>
                </div>
                
                <div class="recommendation">
                    <strong>Long-term Goals (Next 6-12 months):</strong>
                    <ul>
                        <li>Achieve NPS score improvement of 10+ points</li>
                        <li>Reduce average churn risk below 5.0</li>
                        <li>Increase response rate to 90%+</li>
                    </ul>
                </div>
            </div>

            <!-- Report Details -->
            <div class="section page-break">
                <h2 class="section-title">📋 Report Details</h2>
                <p><strong>Report Generated:</strong> {{ generated_at.strftime('%B %d, %Y at %I:%M %p UTC') }}</p>
                <p><strong>Business Account:</strong> {{ business_account.name }}</p>
                <p><strong>Campaign:</strong> {{ campaign.name }}</p>
                <p><strong>Data Period:</strong> {{ campaign.start_date.strftime('%B %d, %Y') }} - {{ campaign.end_date.strftime('%B %d, %Y') }}</p>
                <p><strong>Total Responses Analyzed:</strong> {{ current_kpis.total_responses }}</p>
                <p><strong>AI Insights Generated:</strong> {{ ai_insights.insights_available }} responses</p>
                
                {% if delta_kpis.comparison_count > 0 %}
                <p><strong>Historical Comparison:</strong> Compared against {{ delta_kpis.comparison_count }} previous campaign{{ 's' if delta_kpis.comparison_count != 1 else '' }} in current license period</p>
                {% endif %}
                
                <p><em>This report was automatically generated by VOÏA - Voice Of Client system.</em></p>
            </div>
        </body>
        </html>
        """
        
        template = Template(template_html)
        return template.render(**report_data)

# Global instance
report_generator = ExecutiveReportGenerator()

def generate_executive_report(campaign_id: int, business_account_id: int) -> Optional[str]:
    """Generate executive report for a campaign - main entry point"""
    return report_generator.generate_campaign_report(campaign_id, business_account_id)