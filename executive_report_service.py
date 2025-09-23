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
        self.report_dir = "static/reports"
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
        
        # Generate visualizations with business account branding
        branding_config = business_account.branding_config if hasattr(business_account, 'branding_config') else None
        chart_colors = branding_config.get_chart_colors() if branding_config else ['#dc3545', '#28a745', '#6c757d', '#17a2b8', '#ffc107', '#fd7e14', '#6610f2', '#e83e8c']
        charts = self._generate_charts(responses, current_kpis, chart_colors)
        
        # Get AI insights
        ai_insights = self._extract_ai_insights(responses)
        
        # Calculate additional dashboard metrics
        high_risk_accounts = self._calculate_high_risk_accounts(responses)
        key_themes = self._calculate_key_themes(responses)
        average_ratings = self._calculate_average_ratings(responses)
        
        return {
            'campaign': campaign,
            'business_account': business_account,
            'responses': responses,
            'current_kpis': current_kpis,
            'delta_kpis': delta_kpis,
            'previous_campaigns': previous_campaigns,
            'charts': charts,
            'ai_insights': ai_insights,
            'high_risk_accounts': high_risk_accounts,
            'key_themes': key_themes,
            'average_ratings': average_ratings,
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
            # Use individual AI analysis fields instead of single ai_analysis field
            if response.sentiment_label:
                sentiment = response.sentiment_label.lower()
                if sentiment in sentiment_counts:
                    sentiment_counts[sentiment] += 1
            
            # Churn risk and growth scores
            if response.churn_risk_score is not None:
                churn_risks.append(response.churn_risk_score)
            if response.growth_factor is not None:
                growth_scores.append(response.growth_factor)
        
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
    
    def _generate_charts(self, responses: List, kpis: Dict, chart_colors: List) -> Dict:
        """Generate chart images for the report with business account branding"""
        charts = {}
        
        # chart_colors is now guaranteed to be provided
        
        try:
            # NPS Distribution Chart
            charts['nps_distribution'] = self._create_nps_distribution_chart(responses, chart_colors)
            
            # Sentiment Breakdown Chart
            charts['sentiment_breakdown'] = self._create_sentiment_chart(kpis['sentiment_breakdown'], chart_colors)
            
            # Response Timeline Chart
            charts['response_timeline'] = self._create_response_timeline_chart(responses, chart_colors[0])
            
        except Exception as e:
            logger.error(f"Error generating charts: {e}")
        
        return charts
    
    def _create_nps_distribution_chart(self, responses: List, chart_colors: List) -> str:
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
            # Use brand colors if available, otherwise default colors
            if chart_colors and len(chart_colors) >= 3:
                colors = [chart_colors[2], chart_colors[3], chart_colors[1]]  # Red, secondary, green
            else:
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
    
    def _create_sentiment_chart(self, sentiment_breakdown: Dict, chart_colors: List) -> str:
        """Create sentiment breakdown pie chart"""
        fig, ax = plt.subplots(figsize=(6, 6))
        
        sentiments = list(sentiment_breakdown.keys())
        values = list(sentiment_breakdown.values())
        
        if sum(values) == 0:
            ax.text(0.5, 0.5, 'No sentiment data available', ha='center', va='center', transform=ax.transAxes)
        else:
            # Use brand colors if available, otherwise default colors
            if chart_colors and len(chart_colors) >= 3:
                colors = [chart_colors[1], chart_colors[3], chart_colors[0]]  # Green, secondary, primary
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
    
    def _create_response_timeline_chart(self, responses: List, primary_color: str = '#dc3545') -> str:
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
        critical_issues = []
        
        for response in responses:
            # Use individual AI analysis fields instead of single ai_analysis field
            if response.key_themes:
                try:
                    # Parse themes from JSON field
                    theme_list = json.loads(response.key_themes) if isinstance(response.key_themes, str) else response.key_themes
                    for theme in theme_list:
                        theme_name = theme if isinstance(theme, str) else theme.get('theme', 'Unknown')
                        if theme_name not in themes:
                            themes[theme_name] = {'count': 0, 'impact': []}
                        themes[theme_name]['count'] += 1
                except (json.JSONDecodeError, TypeError):
                    continue
            
            # Extract high-impact items based on churn risk
            if response.churn_risk_score is not None and response.churn_risk_score >= 7.0:
                # Extract critical issues from churn risk factors
                issue_text = "High churn risk"
                if response.churn_risk_factors:
                    try:
                        factors = json.loads(response.churn_risk_factors) if isinstance(response.churn_risk_factors, str) else response.churn_risk_factors
                        if factors and len(factors) > 0:
                            issue_text = factors[0] if isinstance(factors[0], str) else factors[0].get('factor', 'High churn risk')
                    except (json.JSONDecodeError, TypeError, KeyError):
                        pass
                
                critical_issues.append({
                    'respondent': response.respondent_name,
                    'issue': issue_text,
                    'score': response.churn_risk_score
                })
        
        # Sort themes by frequency and impact
        sorted_themes = sorted(themes.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
        
        return {
            'top_themes': sorted_themes,
            'critical_issues': critical_issues[:3],  # Top 3 critical issues
            'total_themes': len(themes),
            'insights_available': len([r for r in responses if r.sentiment_label or r.key_themes or r.churn_risk_score is not None])
        }
    
    def _calculate_high_risk_accounts(self, responses: List) -> List[Dict]:
        """Calculate high risk accounts similar to dashboard implementation"""
        import json
        
        high_risk_by_company = {}
        
        # Filter responses with high/critical churn risk
        high_risk_responses = [r for r in responses if r.churn_risk_level in ['High', 'Critical']]
        
        for response in high_risk_responses:
            if response.company_name:
                company_key = response.company_name.upper()  # Case-insensitive grouping
                
                if company_key not in high_risk_by_company:
                    high_risk_by_company[company_key] = {
                        'company_name': response.company_name,
                        'risk_levels': [],
                        'risk_scores': [],
                        'nps_scores': [],
                        'respondent_count': 0,
                        'latest_response': response.created_at
                    }
                else:
                    # Update display name and latest response
                    high_risk_by_company[company_key]['company_name'] = response.company_name
                    if response.created_at > high_risk_by_company[company_key]['latest_response']:
                        high_risk_by_company[company_key]['latest_response'] = response.created_at
                
                # Add response data
                company_data = high_risk_by_company[company_key]
                if response.churn_risk_level:
                    company_data['risk_levels'].append(response.churn_risk_level)
                if response.churn_risk_score is not None:
                    company_data['risk_scores'].append(response.churn_risk_score)
                if response.nps_score is not None:
                    company_data['nps_scores'].append(response.nps_score)
                company_data['respondent_count'] += 1
        
        # Convert to final format
        high_risk_accounts = []
        for company_key, company_data in high_risk_by_company.items():
            # Determine highest risk level
            risk_levels = company_data['risk_levels']
            if 'Critical' in risk_levels:
                max_risk_level = 'Critical'
            elif 'High' in risk_levels:
                max_risk_level = 'High'
            else:
                max_risk_level = 'Medium'
            
            # Calculate averages
            avg_risk_score = sum(company_data['risk_scores']) / len(company_data['risk_scores']) if company_data['risk_scores'] else 0
            avg_nps_score = sum(company_data['nps_scores']) / len(company_data['nps_scores']) if company_data['nps_scores'] else 0
            
            high_risk_accounts.append({
                'company_name': company_data['company_name'],
                'risk_level': max_risk_level,
                'risk_score': round(avg_risk_score, 2),
                'nps_score': round(avg_nps_score, 1),
                'respondent_count': company_data['respondent_count'],
                'latest_response': company_data['latest_response']
            })
        
        # Sort by highest risk first, then by lowest NPS
        high_risk_accounts.sort(key=lambda x: (
            0 if x['risk_level'] == 'Critical' else 1 if x['risk_level'] == 'High' else 2,
            x['nps_score']
        ))
        
        return high_risk_accounts[:10]  # Top 10 high risk accounts
    
    def _calculate_key_themes(self, responses: List) -> List[Dict]:
        """Calculate key themes from responses similar to dashboard implementation"""
        import json
        
        all_themes = {}
        
        for response in responses:
            if response.key_themes:
                try:
                    themes = json.loads(response.key_themes)
                    for theme in themes:
                        if not isinstance(theme, dict):
                            continue
                        
                        theme_name = theme.get('theme', 'unknown')
                        # Simple consolidation - normalize the theme name
                        normalized_theme = theme_name.lower().strip()
                        
                        if normalized_theme not in all_themes:
                            all_themes[normalized_theme] = {
                                'theme': theme_name,  # Keep original case for display
                                'count': 0,
                                'sentiments': []
                            }
                        
                        all_themes[normalized_theme]['count'] += 1
                        all_themes[normalized_theme]['sentiments'].append(theme.get('sentiment', 'neutral'))
                except json.JSONDecodeError:
                    continue
        
        # Sort by frequency and return top themes
        sorted_themes = sorted(all_themes.values(), key=lambda x: x['count'], reverse=True)
        return sorted_themes[:10]  # Top 10 themes
    
    def _calculate_average_ratings(self, responses: List) -> Dict:
        """Calculate average ratings similar to dashboard implementation"""
        
        # Collect all ratings
        satisfaction_ratings = [r.satisfaction_rating for r in responses if r.satisfaction_rating is not None]
        product_value_ratings = [r.product_value_rating for r in responses if r.product_value_rating is not None]
        service_ratings = [r.service_rating for r in responses if r.service_rating is not None]
        pricing_ratings = [r.pricing_rating for r in responses if r.pricing_rating is not None]
        
        # Calculate averages
        avg_satisfaction = sum(satisfaction_ratings) / len(satisfaction_ratings) if satisfaction_ratings else 0
        avg_product_value = sum(product_value_ratings) / len(product_value_ratings) if product_value_ratings else 0
        avg_service = sum(service_ratings) / len(service_ratings) if service_ratings else 0
        avg_pricing = sum(pricing_ratings) / len(pricing_ratings) if pricing_ratings else 0
        
        return {
            'satisfaction': round(float(avg_satisfaction), 1),
            'product_value': round(float(avg_product_value), 1),
            'service': round(float(avg_service), 1),
            'pricing': round(float(avg_pricing), 1)
        }
    
    def _generate_pdf_report(self, report_data: Dict, campaign, business_account) -> str:
        """Generate the final PDF report"""
        # Add branding data to report
        branding_data = self._get_branding_data(business_account)
        report_data.update(branding_data)
        
        # Create HTML content from template
        html_content = self._render_html_template(report_data)
        
        # Generate PDF
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"executive_report_{campaign.id}_{timestamp}.pdf"
        pdf_path = os.path.join(self.report_dir, filename)
        
        # Convert HTML to PDF
        weasyprint.HTML(string=html_content).write_pdf(pdf_path)
        
        return pdf_path
    
    def _get_branding_data(self, business_account) -> Dict:
        """Get branding data including logo and color palette"""
        branding_data = {
            'company_logo_base64': None,
            'company_display_name': business_account.name,
            'brand_colors': {
                'primary': '#dc3545',
                'secondary': '#6c757d', 
                'accent': '#28a745',
                'text': '#212529',
                'background': '#ffffff'
            }
        }
        
        # Get branding configuration if available
        if hasattr(business_account, 'branding_config') and business_account.branding_config:
            branding_config = business_account.branding_config
            
            # Get company display name
            branding_data['company_display_name'] = branding_config.get_company_display_name()
            
            # Get color palette
            branding_data['brand_colors'] = branding_config.get_color_palette()
            
            # Convert logo to base64 for embedding
            logo_path = branding_config.get_logo_path()
            if logo_path and os.path.exists(logo_path):
                try:
                    with open(logo_path, 'rb') as logo_file:
                        logo_data = logo_file.read()
                        # Determine MIME type
                        if logo_path.lower().endswith('.png'):
                            mime_type = 'image/png'
                        elif logo_path.lower().endswith('.jpg') or logo_path.lower().endswith('.jpeg'):
                            mime_type = 'image/jpeg'
                        elif logo_path.lower().endswith('.gif'):
                            mime_type = 'image/gif'
                        elif logo_path.lower().endswith('.svg'):
                            mime_type = 'image/svg+xml'
                        else:
                            mime_type = 'image/png'  # Default
                        
                        # Create base64 data URL
                        logo_base64 = base64.b64encode(logo_data).decode('utf-8')
                        branding_data['company_logo_base64'] = f"data:{mime_type};base64,{logo_base64}"
                        
                except Exception as e:
                    logger.warning(f"Failed to load logo file {logo_path}: {e}")
        
        return branding_data
    
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
                    color: {{ brand_colors.text }};
                    margin: 0;
                    padding: 0;
                    background-color: {{ brand_colors.background }};
                }
                
                .header {
                    text-align: center;
                    border-bottom: 3px solid {{ brand_colors.primary }};
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
                    color: {{ brand_colors.primary }};
                    border-bottom: 2px solid {{ brand_colors.secondary }}55;
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
                    background: {{ brand_colors.background }};
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid {{ brand_colors.primary }};
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
                {% if company_logo_base64 %}
                <img src="{{ company_logo_base64 }}" alt="{{ company_display_name }}" class="logo">
                {% endif %}
                <div class="company-name">{{ company_display_name }}</div>
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

            <!-- High Risk Accounts -->
            <div class="section page-break">
                <h2 class="section-title">🚨 High Risk Accounts</h2>
                
                {% if high_risk_accounts %}
                <p>{{ high_risk_accounts|length }} companies identified with elevated churn risk requiring immediate attention.</p>
                
                <div class="insights-list">
                    {% for account in high_risk_accounts[:5] %}
                    <div class="insight-item" style="border-left: 4px solid {% if account.risk_level == 'Critical' %}#dc3545{% else %}#fd7e14{% endif %}; padding-left: 15px; margin-bottom: 15px;">
                        <strong>{{ account.company_name }}</strong>
                        <div style="color: #666; font-size: 0.9em; margin-top: 5px;">
                            Risk Level: <span style="color: {% if account.risk_level == 'Critical' %}#dc3545{% else %}#fd7e14{% endif %}; font-weight: bold;">{{ account.risk_level }}</span> 
                            | Risk Score: {{ account.risk_score }}/10 
                            | NPS: {{ account.nps_score }}
                            {% if account.respondent_count > 1 %} | {{ account.respondent_count }} responses{% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <p>No high-risk accounts identified in this campaign period. All customer relationships appear stable based on current feedback.</p>
                {% endif %}
            </div>

            <!-- Key Themes Analysis -->
            <div class="section">
                <h2 class="section-title">🔍 Key Themes Analysis</h2>
                
                {% if key_themes %}
                <p>{{ key_themes|length }} distinct themes emerged from customer feedback analysis.</p>
                
                <div class="insights-list">
                    {% for theme in key_themes[:8] %}
                    <div class="insight-item" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <span><strong>{{ theme.theme }}</strong></span>
                        <span style="background: var(--primary-color, #dc3545); color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.8em;">{{ theme.count }} mention{{ 's' if theme.count != 1 else '' }}</span>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <p>No specific themes extracted from feedback in this campaign period.</p>
                {% endif %}
            </div>

            <!-- Average Ratings -->
            <div class="section">
                <h2 class="section-title">⭐ Average Ratings</h2>
                
                <div class="kpi-grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                    <div class="kpi-card">
                        <div class="kpi-label">Satisfaction</div>
                        <div class="kpi-value" style="color: {% if average_ratings.satisfaction >= 4 %}#28a745{% elif average_ratings.satisfaction >= 3 %}#ffc107{% else %}#dc3545{% endif %};">
                            {{ average_ratings.satisfaction }}/5.0
                        </div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Product Value</div>
                        <div class="kpi-value" style="color: {% if average_ratings.product_value >= 4 %}#28a745{% elif average_ratings.product_value >= 3 %}#ffc107{% else %}#dc3545{% endif %};">
                            {{ average_ratings.product_value }}/5.0
                        </div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Service Quality</div>
                        <div class="kpi-value" style="color: {% if average_ratings.service >= 4 %}#28a745{% elif average_ratings.service >= 3 %}#ffc107{% else %}#dc3545{% endif %};">
                            {{ average_ratings.service }}/5.0
                        </div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Pricing</div>
                        <div class="kpi-value" style="color: {% if average_ratings.pricing >= 4 %}#28a745{% elif average_ratings.pricing >= 3 %}#ffc107{% else %}#dc3545{% endif %};">
                            {{ average_ratings.pricing }}/5.0
                        </div>
                    </div>
                </div>
                
                {% if average_ratings.satisfaction > 0 or average_ratings.product_value > 0 or average_ratings.service > 0 or average_ratings.pricing > 0 %}
                <p style="margin-top: 20px; color: #666; font-size: 0.9em;">
                    <em>Ratings are on a 1-5 scale where 5 represents the highest satisfaction level.</em>
                </p>
                {% else %}
                <p>No rating data available for this campaign period.</p>
                {% endif %}
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