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
        
        survey_type = getattr(campaign, 'survey_type', 'conversational') or 'conversational'
        
        from models import CampaignParticipant
        responses = SurveyResponse.query.join(
            CampaignParticipant, SurveyResponse.campaign_participant_id == CampaignParticipant.id
        ).filter(
            CampaignParticipant.campaign_id == campaign.id
        ).options(
            joinedload(SurveyResponse.campaign_participant)
        ).all()
        
        current_kpis = self._calculate_campaign_kpis(responses, campaign)
        
        previous_campaigns = self._get_previous_campaigns(campaign, business_account.id)
        delta_kpis = self._calculate_kpi_deltas(current_kpis, previous_campaigns)
        
        branding_config = business_account.branding_config if hasattr(business_account, 'branding_config') else None
        chart_colors = branding_config.get_chart_colors() if branding_config else ['#dc3545', '#28a745', '#6c757d', '#17a2b8', '#ffc107', '#fd7e14', '#6610f2', '#e83e8c']
        charts = self._generate_charts(responses, current_kpis, chart_colors, survey_type=survey_type)
        
        ai_insights = self._extract_ai_insights(responses)
        
        high_risk_accounts = self._calculate_high_risk_accounts(responses)
        key_themes = self._calculate_key_themes(responses)
        average_ratings = self._calculate_average_ratings(responses)
        
        report_data = {
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
            'generated_at': datetime.utcnow(),
            'survey_type': survey_type
        }
        
        if survey_type == 'classic':
            classic_analytics = self._collect_classic_analytics(responses, campaign)
            report_data['classic_analytics'] = classic_analytics
            classic_charts = self._generate_classic_charts(classic_analytics, chart_colors)
            report_data['classic_charts'] = classic_charts
        
        return report_data
    
    def _collect_classic_analytics(self, responses: List, campaign) -> Dict:
        """Collect classic survey-specific analytics: CSAT, CES, drivers, features, recommendation, correlation"""
        import json as json_module
        
        total = len(responses)
        
        csat_scores = [r.csat_score for r in responses if r.csat_score is not None]
        csat_dist = {}
        for s in csat_scores:
            csat_dist[str(s)] = csat_dist.get(str(s), 0) + 1
        csat_avg = round(sum(csat_scores) / len(csat_scores), 2) if csat_scores else None
        
        ces_scores = [r.ces_score for r in responses if r.ces_score is not None]
        ces_dist = {}
        for s in ces_scores:
            ces_dist[str(s)] = ces_dist.get(str(s), 0) + 1
        ces_avg = round(sum(ces_scores) / len(ces_scores), 2) if ces_scores else None
        
        driver_data = {}
        for r in responses:
            if r.loyalty_drivers:
                drivers = r.loyalty_drivers if isinstance(r.loyalty_drivers, list) else []
                nps_cat = getattr(r, 'nps_category', None) or 'Unknown'
                for d in drivers:
                    if d not in driver_data:
                        driver_data[d] = {'count': 0, 'promoters': 0, 'passives': 0, 'detractors': 0}
                    driver_data[d]['count'] += 1
                    if nps_cat == 'Promoter':
                        driver_data[d]['promoters'] += 1
                    elif nps_cat == 'Passive':
                        driver_data[d]['passives'] += 1
                    elif nps_cat == 'Detractor':
                        driver_data[d]['detractors'] += 1
        
        driver_label_map = {}
        try:
            from models import ClassicSurveyConfig
            classic_config = ClassicSurveyConfig.query.filter_by(campaign_id=campaign.id).first()
            if classic_config and classic_config.driver_labels:
                for dl in classic_config.driver_labels:
                    driver_label_map[dl['key']] = dl.get('label_en', dl['key'])
        except Exception:
            classic_config = None
        
        drivers_with_impact = {}
        for key, dd in driver_data.items():
            label = driver_label_map.get(key, key.replace('_', ' ').title())
            net_impact = dd['promoters'] - dd['detractors']
            drivers_with_impact[key] = {
                'label': label,
                'count': dd['count'],
                'promoters': dd['promoters'],
                'passives': dd['passives'],
                'detractors': dd['detractors'],
                'net_impact': net_impact
            }
        
        correlation_points = []
        for r in responses:
            if r.csat_score is not None and r.ces_score is not None and r.nps_score is not None:
                nps_cat = getattr(r, 'nps_category', None) or 'Unknown'
                correlation_points.append({
                    'csat': r.csat_score,
                    'ces': r.ces_score,
                    'nps_score': r.nps_score,
                    'nps_category': nps_cat
                })
        
        avg_ces_by_nps = {}
        for cat in ['Promoter', 'Passive', 'Detractor']:
            cat_ces = [p['ces'] for p in correlation_points if p['nps_category'] == cat]
            avg_ces_by_nps[cat] = round(sum(cat_ces) / len(cat_ces), 2) if cat_ces else None
        
        high_nps = sum(1 for p in correlation_points if p['nps_score'] >= 9 and p['csat'] >= 4)
        total_high_nps = sum(1 for p in correlation_points if p['nps_score'] >= 9)
        nps_csat_alignment = round(high_nps / total_high_nps * 100, 1) if total_high_nps > 0 else None
        
        det_ces = avg_ces_by_nps.get('Detractor')
        pro_ces = avg_ces_by_nps.get('Promoter')
        if det_ces is not None and pro_ces is not None and pro_ces > 0:
            effort_ratio = round(det_ces / pro_ces, 1)
            insight_text = f"Detractors report {effort_ratio}x higher effort than Promoters"
        else:
            insight_text = None
        
        feature_data = {}
        feature_label_map = {}
        if classic_config and hasattr(classic_config, 'features') and classic_config.features:
            for f in classic_config.features:
                feature_label_map[f['key']] = f.get('name_en', f['key'])
        
        for r in responses:
            if r.general_feedback:
                try:
                    evals = json_module.loads(r.general_feedback) if isinstance(r.general_feedback, str) else r.general_feedback
                    if not isinstance(evals, dict):
                        continue
                    for fkey, fdata in evals.items():
                        if fkey not in feature_data:
                            feature_data[fkey] = {
                                'label': feature_label_map.get(fkey, fkey.replace('_', ' ').title()),
                                'usage_yes': 0, 'usage_no': 0,
                                'satisfaction_scores': []
                            }
                        fd = feature_data[fkey]
                        usage = fdata.get('usage', '')
                        if usage == 'yes':
                            fd['usage_yes'] += 1
                        elif usage and str(usage).startswith('no'):
                            fd['usage_no'] += 1
                        if fdata.get('satisfaction') is not None:
                            fd['satisfaction_scores'].append(fdata['satisfaction'])
                except (json_module.JSONDecodeError, AttributeError, TypeError):
                    pass
        
        features_summary = {}
        for fkey, fd in feature_data.items():
            total_usage = fd['usage_yes'] + fd['usage_no']
            features_summary[fkey] = {
                'label': fd['label'],
                'adoption_rate': round(fd['usage_yes'] / total_usage * 100, 1) if total_usage > 0 else 0,
                'avg_satisfaction': round(sum(fd['satisfaction_scores']) / len(fd['satisfaction_scores']), 2) if fd['satisfaction_scores'] else None
            }
        
        rec_counts = {}
        for r in responses:
            if r.recommendation_status:
                rec_counts[r.recommendation_status] = rec_counts.get(r.recommendation_status, 0) + 1
        
        return {
            'csat': {'average': csat_avg, 'distribution': csat_dist, 'count': len(csat_scores)},
            'ces': {'average': ces_avg, 'distribution': ces_dist, 'count': len(ces_scores)},
            'drivers': drivers_with_impact,
            'features': features_summary,
            'recommendation': rec_counts,
            'correlation': {
                'points': correlation_points,
                'summary': {
                    'avg_ces_by_nps_category': avg_ces_by_nps,
                    'nps_csat_alignment_pct': nps_csat_alignment,
                    'total_correlated_responses': len(correlation_points),
                    'insight_text': insight_text
                }
            }
        }
    
    def _calculate_campaign_kpis(self, responses: List, campaign) -> Dict:
        """Calculate KPIs for current campaign"""
        # Get participants invited count
        total_participants = campaign.participants_count if campaign else 0
        
        # Count transcript-sourced responses
        transcripts_count = sum(1 for r in responses if r.source_type == 'transcript') if responses else 0
        
        if not responses:
            return {
                'total_responses': 0,
                'participants_invited': total_participants,
                'transcripts_count': 0,
                'nps_score': 0,
                'response_rate': 0,
                'sentiment_breakdown': {'positive': 0, 'neutral': 0, 'negative': 0},
                'avg_churn_risk': 0,
                'avg_growth_score': 0
            }
        
        # Basic metrics
        total_responses = len(responses)
        nps_scores = [r.nps_score for r in responses if r.nps_score is not None]
        
        # Calculate NPS using standard formula: (promoters - detractors) / total * 100
        promoters = sum(1 for score in nps_scores if score >= 9)
        passives = sum(1 for score in nps_scores if 7 <= score <= 8)
        detractors = sum(1 for score in nps_scores if score <= 6)
        nps_score = ((promoters - detractors) / len(nps_scores) * 100) if nps_scores else 0
        
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
        
        # Calculate actual participation rate from campaign participants
        response_rate = (total_responses / total_participants * 100) if total_participants > 0 else 0
        
        return {
            'total_responses': total_responses,
            'participants_invited': total_participants,
            'transcripts_count': transcripts_count,
            'nps_score': round(nps_score, 1),
            'response_rate': round(response_rate, 1),
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
        prev_kpis = self._calculate_campaign_kpis(prev_responses, prev_campaign)
        
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
    
    def _generate_charts(self, responses: List, kpis: Dict, chart_colors: List, survey_type: str = 'conversational') -> Dict:
        """Generate chart images for the report with business account branding"""
        charts = {}
        
        try:
            charts['nps_distribution'] = self._create_nps_distribution_chart(responses, chart_colors)
            
            if survey_type != 'classic':
                charts['sentiment_breakdown'] = self._create_sentiment_chart(kpis['sentiment_breakdown'], chart_colors)
            
            charts['response_timeline'] = self._create_response_timeline_chart(responses, chart_colors[0])
            
        except Exception as e:
            logger.error(f"Error generating charts: {e}")
        
        return charts
    
    def _generate_classic_charts(self, classic_analytics: Dict, chart_colors: List) -> Dict:
        """Generate classic survey-specific charts (CSAT, CES, driver impact, correlation)"""
        charts = {}
        
        try:
            charts['csat_distribution'] = self._create_csat_distribution_chart(
                classic_analytics['csat']['distribution'], chart_colors)
            
            charts['ces_distribution'] = self._create_ces_distribution_chart(
                classic_analytics['ces']['distribution'], chart_colors)
            
            charts['driver_impact'] = self._create_driver_impact_chart(
                classic_analytics['drivers'], chart_colors)
            
            charts['correlation_scatter'] = self._create_correlation_scatter_chart(
                classic_analytics['correlation']['points'], chart_colors)
            
        except Exception as e:
            logger.error(f"Error generating classic charts: {e}")
        
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
    
    def _create_csat_distribution_chart(self, csat_distribution: Dict, chart_colors: List) -> str:
        """Create CSAT score distribution bar chart (1-5 scale)"""
        fig, ax = plt.subplots(figsize=(7, 4))
        
        if not csat_distribution:
            ax.text(0.5, 0.5, 'No CSAT data available', ha='center', va='center', transform=ax.transAxes)
        else:
            labels = [str(i) for i in range(1, 6)]
            values = [csat_distribution.get(str(i), 0) for i in range(1, 6)]
            color_map = ['#dc3545', '#fd7e14', '#ffc107', '#28a745', '#198754']
            
            bars = ax.bar(labels, values, color=color_map, alpha=0.85, edgecolor='white', linewidth=0.5)
            ax.set_xlabel('Satisfaction Score', fontsize=10)
            ax.set_ylabel('Number of Responses', fontsize=10)
            ax.set_title('Customer Satisfaction (CSAT) Distribution', fontsize=12, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)
            
            for bar, value in zip(bars, values):
                if value > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.1,
                           str(value), ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _create_ces_distribution_chart(self, ces_distribution: Dict, chart_colors: List) -> str:
        """Create CES score distribution bar chart (1-8 scale)"""
        fig, ax = plt.subplots(figsize=(8, 4))
        
        if not ces_distribution:
            ax.text(0.5, 0.5, 'No CES data available', ha='center', va='center', transform=ax.transAxes)
        else:
            labels = [str(i) for i in range(1, 9)]
            values = [ces_distribution.get(str(i), 0) for i in range(1, 9)]
            color_map = ['#198754', '#28a745', '#6bcf7f', '#ffc107', '#fd7e14', '#e05d44', '#dc3545', '#c82333']
            
            bars = ax.bar(labels, values, color=color_map, alpha=0.85, edgecolor='white', linewidth=0.5)
            ax.set_xlabel('Effort Score (1 = Low Effort, 8 = High Effort)', fontsize=10)
            ax.set_ylabel('Number of Responses', fontsize=10)
            ax.set_title('Customer Effort Score (CES) Distribution', fontsize=12, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)
            
            for bar, value in zip(bars, values):
                if value > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.1,
                           str(value), ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _create_driver_impact_chart(self, drivers: Dict, chart_colors: List) -> str:
        """Create diverging horizontal bar chart for driver impact analysis"""
        fig, ax = plt.subplots(figsize=(9, max(4, len(drivers) * 0.7 + 1)))
        
        if not drivers:
            ax.text(0.5, 0.5, 'No driver data available', ha='center', va='center', transform=ax.transAxes)
            plt.tight_layout()
            return self._fig_to_base64(fig)
        
        sorted_drivers = sorted(drivers.items(), key=lambda x: x[1].get('net_impact', 0), reverse=True)
        
        labels = [d[1].get('label', d[0].replace('_', ' ').title()) for d in sorted_drivers]
        promoters = [d[1].get('promoters', 0) for d in sorted_drivers]
        detractors = [-d[1].get('detractors', 0) for d in sorted_drivers]
        net_impacts = [d[1].get('net_impact', 0) for d in sorted_drivers]
        
        y_pos = range(len(labels))
        
        ax.barh(y_pos, promoters, color='#28a745', alpha=0.85, label='Promoters', edgecolor='white', linewidth=0.5)
        ax.barh(y_pos, detractors, color='#dc3545', alpha=0.85, label='Detractors', edgecolor='white', linewidth=0.5)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel('Number of Respondents', fontsize=10)
        ax.set_title('Driver Impact Analysis', fontsize=12, fontweight='bold')
        ax.axvline(x=0, color='#333', linewidth=0.8)
        ax.grid(axis='x', alpha=0.3)
        ax.legend(loc='lower right', fontsize=9)
        
        for i, ni in enumerate(net_impacts):
            x_pos = max(promoters[i], 0) + 0.3
            ax.text(x_pos, i, f'Net: {ni:+d}', va='center', fontsize=8, color='#333', fontweight='bold')
        
        ax.invert_yaxis()
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _create_correlation_scatter_chart(self, correlation_points: List, chart_colors: List) -> str:
        """Create NPS-CSAT-CES correlation scatter chart"""
        fig, ax = plt.subplots(figsize=(8, 6))
        
        if not correlation_points:
            ax.text(0.5, 0.5, 'No correlated data available\n(requires NPS + CSAT + CES)', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=11)
            plt.tight_layout()
            return self._fig_to_base64(fig)
        
        cat_colors = {'Promoter': '#28a745', 'Passive': '#ffc107', 'Detractor': '#dc3545', 'Unknown': '#6c757d'}
        
        for cat in ['Detractor', 'Passive', 'Promoter']:
            pts = [p for p in correlation_points if p['nps_category'] == cat]
            if pts:
                x = [p['csat'] for p in pts]
                y = [p['ces'] for p in pts]
                sizes = [max(30, p['nps_score'] * 8) for p in pts]
                ax.scatter(x, y, s=sizes, c=cat_colors.get(cat, '#6c757d'),
                          alpha=0.7, edgecolors='white', linewidth=0.5, label=f'{cat} ({len(pts)})')
        
        ax.set_xlabel('CSAT Score (1-5)', fontsize=10)
        ax.set_ylabel('CES Score (1-8, lower = less effort)', fontsize=10)
        ax.set_title('NPS-CSAT-CES Correlation', fontsize=12, fontweight='bold')
        ax.set_xlim(0.5, 5.5)
        ax.set_ylim(0.5, 8.5)
        ax.grid(True, alpha=0.2)
        ax.legend(loc='upper left', fontsize=9, title='NPS Category')
        
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
                    
                    {% if survey_type == 'classic' and classic_analytics %}
                    {% if classic_analytics.csat.average is not none %}
                    <p><strong>Customer Satisfaction:</strong> Average CSAT of {{ classic_analytics.csat.average }}/5 across {{ classic_analytics.csat.count }} responses.</p>
                    {% endif %}
                    {% if classic_analytics.ces.average is not none %}
                    <p><strong>Customer Effort:</strong> Average CES of {{ classic_analytics.ces.average }}/8 across {{ classic_analytics.ces.count }} responses.</p>
                    {% endif %}
                    {% endif %}
                    
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
                        <div class="kpi-value">{{ current_kpis.participants_invited }}</div>
                        <div class="kpi-label">Participants Invited</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-value">{{ current_kpis.total_responses }}</div>
                        <div class="kpi-label">Responses Completed</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-value">{{ current_kpis.transcripts_count }}</div>
                        <div class="kpi-label">Transcripts Analyzed</div>
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
                    {% if survey_type == 'classic' and classic_analytics %}
                    <div class="kpi-card">
                        <div class="kpi-value" style="color: {% if classic_analytics.csat.average and classic_analytics.csat.average >= 4 %}#28a745{% elif classic_analytics.csat.average and classic_analytics.csat.average >= 3 %}#ffc107{% else %}#dc3545{% endif %};">{{ classic_analytics.csat.average or 'N/A' }}/5</div>
                        <div class="kpi-label">Avg CSAT Score</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-value" style="color: {% if classic_analytics.ces.average and classic_analytics.ces.average <= 3 %}#28a745{% elif classic_analytics.ces.average and classic_analytics.ces.average <= 5 %}#ffc107{% else %}#dc3545{% endif %};">{{ classic_analytics.ces.average or 'N/A' }}/8</div>
                        <div class="kpi-label">Avg CES Score</div>
                    </div>
                    {% endif %}
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
                
                {% if survey_type != 'classic' and charts.sentiment_breakdown %}
                <div class="chart-container">
                    <h3>Sentiment Analysis</h3>
                    <img src="{{ charts.sentiment_breakdown }}" alt="Sentiment Breakdown" class="chart-image">
                </div>
                {% endif %}
            </div>
            
            {% if survey_type == 'classic' and classic_charts %}
            <!-- Classic Survey Analytics -->
            <div class="section page-break">
                <h2 class="section-title">📋 Classic Survey Analytics</h2>
                
                {% if classic_charts.csat_distribution %}
                <div class="chart-container">
                    <h3>Customer Satisfaction (CSAT) Distribution</h3>
                    <img src="{{ classic_charts.csat_distribution }}" alt="CSAT Distribution" class="chart-image">
                </div>
                {% endif %}
                
                {% if classic_charts.ces_distribution %}
                <div class="chart-container">
                    <h3>Customer Effort Score (CES) Distribution</h3>
                    <img src="{{ classic_charts.ces_distribution }}" alt="CES Distribution" class="chart-image">
                </div>
                {% endif %}
            </div>
            
            <!-- Driver Impact Analysis -->
            <div class="section page-break">
                <h2 class="section-title">📊 Driver Impact Analysis</h2>
                <p style="color: #666; margin-bottom: 15px;">Which factors positively or negatively influence customer loyalty. Green bars show Promoter mentions, red bars show Detractor mentions. Sorted by net impact (strongest drivers at top).</p>
                
                {% if classic_charts.driver_impact %}
                <div class="chart-container">
                    <img src="{{ classic_charts.driver_impact }}" alt="Driver Impact Analysis" class="chart-image">
                </div>
                {% endif %}
                
                {% if classic_analytics and classic_analytics.drivers %}
                <div class="insights-list" style="margin-top: 15px;">
                    <h4 style="margin-bottom: 10px;">Driver Breakdown</h4>
                    {% for key, driver in classic_analytics.drivers.items() %}
                    <div class="insight-item" style="display: flex; justify-content: space-between; align-items: center;">
                        <span><strong>{{ driver.label }}</strong> ({{ driver.count }} mentions)</span>
                        <span style="font-weight: bold; color: {% if driver.net_impact > 0 %}#28a745{% elif driver.net_impact < 0 %}#dc3545{% else %}#6c757d{% endif %};">
                            Net Impact: {{ '+' if driver.net_impact > 0 else '' }}{{ driver.net_impact }}
                        </span>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            
            <!-- NPS-CSAT-CES Correlation -->
            <div class="section page-break">
                <h2 class="section-title">🔗 NPS-CSAT-CES Correlation</h2>
                <p style="color: #666; margin-bottom: 15px;">How the three core metrics relate. Each dot represents a survey response, positioned by CSAT (x-axis) and CES (y-axis), colored by NPS category.</p>
                
                {% if classic_charts.correlation_scatter %}
                <div class="chart-container">
                    <img src="{{ classic_charts.correlation_scatter }}" alt="NPS-CSAT-CES Correlation" class="chart-image">
                </div>
                {% endif %}
                
                {% if classic_analytics and classic_analytics.correlation and classic_analytics.correlation.summary %}
                <div class="summary-box" style="margin-top: 15px;">
                    <h4 style="margin-bottom: 10px;">Correlation Summary</h4>
                    <div class="kpi-grid">
                        <div class="kpi-card">
                            <div class="kpi-value" style="color: #4a90e2;">{{ classic_analytics.correlation.summary.total_correlated_responses }}</div>
                            <div class="kpi-label">Responses with All 3 Metrics</div>
                        </div>
                        {% if classic_analytics.correlation.summary.nps_csat_alignment_pct is not none %}
                        <div class="kpi-card">
                            <div class="kpi-value" style="color: {% if classic_analytics.correlation.summary.nps_csat_alignment_pct >= 75 %}#28a745{% elif classic_analytics.correlation.summary.nps_csat_alignment_pct >= 50 %}#ffc107{% else %}#dc3545{% endif %};">{{ classic_analytics.correlation.summary.nps_csat_alignment_pct }}%</div>
                            <div class="kpi-label">NPS-CSAT Alignment</div>
                            <div style="font-size: 0.8em; color: #666; margin-top: 4px;">% of Promoters who also gave CSAT ≥ 4</div>
                        </div>
                        {% endif %}
                    </div>
                    
                    {% if classic_analytics.correlation.summary.avg_ces_by_nps_category %}
                    <div style="margin-top: 10px;">
                        <strong>Average CES by NPS Category:</strong>
                        <div style="display: flex; gap: 20px; margin-top: 8px; flex-wrap: wrap;">
                            {% for cat, val in classic_analytics.correlation.summary.avg_ces_by_nps_category.items() %}
                            {% if val is not none %}
                            <div style="background: #f8f9fa; padding: 8px 16px; border-radius: 6px; border-left: 3px solid {% if cat == 'Promoter' %}#28a745{% elif cat == 'Passive' %}#ffc107{% else %}#dc3545{% endif %};">
                                <span style="font-weight: bold;">{{ cat }}:</span> {{ val }}/8
                            </div>
                            {% endif %}
                            {% endfor %}
                        </div>
                    </div>
                    {% endif %}
                    
                    {% if classic_analytics.correlation.summary.insight_text %}
                    <p style="margin-top: 12px; font-style: italic; color: #555;">{{ classic_analytics.correlation.summary.insight_text }}</p>
                    {% endif %}
                </div>
                {% endif %}
            </div>
            
            {% if classic_analytics and classic_analytics.features %}
            <!-- Feature Analytics -->
            <div class="section page-break">
                <h2 class="section-title">⚙️ Feature Analytics</h2>
                <div class="insights-list">
                    {% for key, feat in classic_analytics.features.items() %}
                    <div class="insight-item" style="display: flex; justify-content: space-between; align-items: center;">
                        <span><strong>{{ feat.label }}</strong></span>
                        <span>
                            Adoption: <strong>{{ feat.adoption_rate }}%</strong>
                            {% if feat.avg_satisfaction is not none %}
                             | Satisfaction: <strong style="color: {% if feat.avg_satisfaction >= 4 %}#28a745{% elif feat.avg_satisfaction >= 3 %}#ffc107{% else %}#dc3545{% endif %};">{{ feat.avg_satisfaction }}/5</strong>
                            {% endif %}
                        </span>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
            
            {% if classic_analytics and classic_analytics.recommendation %}
            <!-- Recommendation Breakdown -->
            <div class="section">
                <h2 class="section-title">👍 Recommendation Breakdown</h2>
                <div class="kpi-grid" style="grid-template-columns: repeat(3, 1fr);">
                    {% for status, count in classic_analytics.recommendation.items() %}
                    <div class="kpi-card" style="text-align: center;">
                        <div class="kpi-value" style="color: {% if status == 'recommended' %}#28a745{% elif status == 'would_consider' %}#ffc107{% else %}#dc3545{% endif %};">{{ count }}</div>
                        <div class="kpi-label">{{ status.replace('_', ' ').title() }}</div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
            {% endif %}

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

            {% if survey_type != 'classic' %}
            <!-- Average Ratings (Conversational surveys only) -->
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
            {% endif %}

            <!-- Report Details -->
            <div class="section page-break">
                <h2 class="section-title">📋 Report Details</h2>
                <p><strong>Report Generated:</strong> {{ generated_at.strftime('%B %d, %Y at %I:%M %p UTC') }}</p>
                <p><strong>Business Account:</strong> {{ business_account.name }}</p>
                <p><strong>Campaign:</strong> {{ campaign.name }}</p>
                <p><strong>Survey Type:</strong> {{ survey_type|title }}</p>
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