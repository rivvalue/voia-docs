"""
Executive Report Generation Service
Generates comprehensive PDF reports for completed campaigns with KPI deltas and business branding
"""

import os
import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from io import BytesIO
import base64
from jinja2 import Template
import weasyprint
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, desc
from survey_config_utils import normalize_driver_labels, normalize_features

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
            joinedload(SurveyResponse.campaign_participant).joinedload(CampaignParticipant.participant)
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
        
        seg_data = self._calculate_segmentation_data(responses)
        seg_charts = self._generate_segmentation_charts(seg_data, chart_colors)
        recommendations = self._generate_recommendations(seg_data, current_kpis, average_ratings)
        
        decision_maker_risk_accounts = self._calculate_decision_maker_risk_accounts(responses)
        
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
            'survey_type': survey_type,
            'segmentation_data': seg_data,
            'segmentation_charts': seg_charts,
            'recommendations': recommendations,
            'decision_maker_risk_accounts': decision_maker_risk_accounts,
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
            if classic_config:
                for dl in normalize_driver_labels(classic_config.driver_labels):
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
        if classic_config:
            for f in normalize_features(classic_config.features):
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
        
        promoter_themes = {}
        detractor_themes = {}
        for response in responses:
            nps = getattr(response, 'nps_score', None)
            if nps is None or not response.key_themes:
                continue
            try:
                theme_list = json.loads(response.key_themes) if isinstance(response.key_themes, str) else response.key_themes
                for theme in theme_list:
                    theme_name = theme if isinstance(theme, str) else theme.get('theme', 'Unknown')
                    if nps >= 9:
                        promoter_themes[theme_name] = promoter_themes.get(theme_name, 0) + 1
                    elif nps <= 6:
                        detractor_themes[theme_name] = detractor_themes.get(theme_name, 0) + 1
            except (json.JSONDecodeError, TypeError):
                continue
        
        growth_signals = []
        for theme_name, p_count in sorted(promoter_themes.items(), key=lambda x: x[1], reverse=True):
            if p_count >= 2:
                growth_signals.append({
                    'theme': theme_name,
                    'promoter_count': p_count,
                    'detractor_count': detractor_themes.get(theme_name, 0),
                })
        growth_signals = growth_signals[:5]
        
        return {
            'top_themes': sorted_themes,
            'critical_issues': critical_issues[:3],
            'total_themes': len(themes),
            'insights_available': len([r for r in responses if r.sentiment_label or r.key_themes or r.churn_risk_score is not None]),
            'growth_signals': growth_signals,
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

    def _get_influence_tier(self, role: Optional[str]) -> str:
        """Map a participant role string to an influence tier label."""
        if not role:
            return 'Unknown'
        role_lower = role.lower().strip()
        if any(kw in role_lower for kw in ('c-level', 'c level', 'clevel', 'ceo', 'cto', 'cfo',
                                            'coo', 'cmo', 'cso', 'president', 'chief')):
            return 'C-Level'
        if any(kw in role_lower for kw in ('vp', 'vice president', 'director', 'svp', 'evp')):
            return 'VP/Director'
        if 'manager' in role_lower or 'mgr' in role_lower:
            return 'Manager'
        if any(kw in role_lower for kw in ('team lead', 'lead', 'supervisor')):
            return 'Team Lead'
        return 'End User'

    def _calculate_decision_maker_risk_accounts(self, responses: List) -> List[Dict]:
        """
        Identify accounts where C-Level or VP/Director respondents are Detractors (NPS <= 6).
        Returns a list of dicts with company_name, detractor_count, min_nps, roles,
        and verbatim_risk_factors extracted from the respondents' account_risk_factors JSON.
        """
        import json as _json

        dm_risk_by_company = {}
        for response in responses:
            if not response.company_name:
                continue
            # Null-safe participant role access via loaded relationship
            role = None
            cp = response.campaign_participant
            if cp is not None and cp.participant is not None:
                role = cp.participant.role
            tier = self._get_influence_tier(role)
            if tier not in ('C-Level', 'VP/Director'):
                continue
            nps = response.nps_score
            if nps is None or nps > 6:
                continue
            company_key = response.company_name.upper()
            if company_key not in dm_risk_by_company:
                dm_risk_by_company[company_key] = {
                    'company_name': response.company_name,
                    'detractor_count': 0,
                    'nps_scores': [],
                    'roles': [],
                    'verbatim_risk_factors': [],
                }
            entry = dm_risk_by_company[company_key]
            entry['detractor_count'] += 1
            entry['nps_scores'].append(nps)
            if role and role not in entry['roles']:
                entry['roles'].append(role)
            # Extract verbatim risk factor descriptions from this respondent
            if response.account_risk_factors:
                try:
                    risk_factors = _json.loads(response.account_risk_factors) if isinstance(response.account_risk_factors, str) else response.account_risk_factors
                    if isinstance(risk_factors, list):
                        for rf in risk_factors:
                            if not isinstance(rf, dict):
                                continue
                            desc = rf.get('description') or rf.get('description_verbatim') or ''
                            if desc and desc not in entry['verbatim_risk_factors']:
                                entry['verbatim_risk_factors'].append(desc)
                except (ValueError, TypeError) as parse_err:
                    logger.warning(f"DM Risk: could not parse account_risk_factors for response {response.id}: {parse_err}")

        result = []
        for company_key, entry in dm_risk_by_company.items():
            result.append({
                'company_name': entry['company_name'],
                'detractor_count': entry['detractor_count'],
                'min_nps': min(entry['nps_scores']),
                'avg_nps': round(sum(entry['nps_scores']) / len(entry['nps_scores']), 1),
                'roles': entry['roles'],
                'verbatim_risk_factors': entry['verbatim_risk_factors'][:4],
            })
        result.sort(key=lambda x: (x['min_nps'], -x['detractor_count']))
        return result

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
    
    def _calculate_segmentation_data(self, responses: List) -> Dict:
        """Calculate segmentation analytics from participant data"""
        dimensions = {
            'role': {}, 'region': {}, 'customer_tier': {}, 'client_industry': {}
        }
        churn_risk_by_segment = {'tier': {}, 'role': {}, 'region': {}}
        tenure_cohorts = {}
        
        for response in responses:
            cp = getattr(response, 'campaign_participant', None)
            if cp is None:
                continue
            participant = getattr(cp, 'participant', None)
            if participant is None:
                continue
            
            role = getattr(participant, 'role', None) or 'Unknown'
            region = getattr(participant, 'region', None) or 'Unknown'
            tier = getattr(participant, 'customer_tier', None) or 'Unknown'
            industry = getattr(participant, 'client_industry', None) or 'Unknown'
            
            metrics = {
                'nps_score': getattr(response, 'nps_score', None),
                'satisfaction_rating': getattr(response, 'satisfaction_rating', None),
                'product_value_rating': getattr(response, 'product_value_rating', None),
                'service_rating': getattr(response, 'service_rating', None),
                'pricing_rating': getattr(response, 'pricing_rating', None),
                'support_rating': getattr(response, 'support_rating', None),
            }
            
            dim_values = {'role': role, 'region': region, 'customer_tier': tier, 'client_industry': industry}
            for dim_key, seg_val in dim_values.items():
                if seg_val not in dimensions[dim_key]:
                    dimensions[dim_key][seg_val] = []
                dimensions[dim_key][seg_val].append(metrics)
            
            churn_level = getattr(response, 'churn_risk_level', None) or 'Minimal'
            for seg_key, seg_val in [('tier', tier), ('role', role), ('region', region)]:
                if seg_val not in churn_risk_by_segment[seg_key]:
                    churn_risk_by_segment[seg_key][seg_val] = {'Minimal': 0, 'Low': 0, 'Medium': 0, 'High': 0}
                if churn_level in churn_risk_by_segment[seg_key][seg_val]:
                    churn_risk_by_segment[seg_key][seg_val][churn_level] += 1
            
            tenure_str = getattr(response, 'tenure_with_fc', None)
            if tenure_str:
                match = re.search(r'(\d+)', str(tenure_str))
                if match:
                    years = int(match.group(1))
                    if years <= 2:
                        band = '1-2 years'
                    elif years <= 5:
                        band = '3-5 years'
                    elif years <= 8:
                        band = '6-8 years'
                    else:
                        band = '9+ years'
                    if band not in tenure_cohorts:
                        tenure_cohorts[band] = []
                    tenure_cohorts[band].append(metrics)
        
        def calc_nps(scores_list):
            nps_scores = [m['nps_score'] for m in scores_list if m['nps_score'] is not None]
            if not nps_scores:
                return 0, 0
            promoters = sum(1 for s in nps_scores if s >= 9)
            detractors = sum(1 for s in nps_scores if s <= 6)
            return round((promoters - detractors) / len(nps_scores) * 100, 1), len(nps_scores)
        
        def calc_avg(scores_list, key):
            vals = [m[key] for m in scores_list if m.get(key) is not None]
            if not vals:
                return None
            return round(sum(vals) / len(vals), 2)
        
        def build_segment_dict(dim_data):
            result = {}
            for seg_name, metrics_list in dim_data.items():
                nps, n = calc_nps(metrics_list)
                result[seg_name] = {
                    'nps': nps, 'count': n,
                    'satisfaction': calc_avg(metrics_list, 'satisfaction_rating'),
                    'product_value': calc_avg(metrics_list, 'product_value_rating'),
                    'service': calc_avg(metrics_list, 'service_rating'),
                    'pricing': calc_avg(metrics_list, 'pricing_rating'),
                    'support': calc_avg(metrics_list, 'support_rating'),
                }
            return result
        
        nps_by_role = build_segment_dict(dimensions['role'])
        nps_by_region = build_segment_dict(dimensions['region'])
        nps_by_tier = build_segment_dict(dimensions['customer_tier'])
        nps_by_industry = build_segment_dict(dimensions['client_industry'])
        
        response_distribution = {
            'by_role': {k: v['count'] for k, v in nps_by_role.items()},
            'by_region': {k: v['count'] for k, v in nps_by_region.items()},
            'by_tier': {k: v['count'] for k, v in nps_by_tier.items()},
            'by_industry': {k: v['count'] for k, v in nps_by_industry.items()},
        }
        
        tenure_order = ['1-2 years', '3-5 years', '6-8 years', '9+ years']
        tenure_cohorts_result = {}
        for band in tenure_order:
            if band in tenure_cohorts:
                metrics_list = tenure_cohorts[band]
                nps, n = calc_nps(metrics_list)
                tenure_cohorts_result[band] = {
                    'nps': nps, 'count': n,
                    'total_responses': n,
                    'satisfaction': calc_avg(metrics_list, 'satisfaction_rating'),
                    'avg_satisfaction': calc_avg(metrics_list, 'satisfaction_rating'),
                }
        
        sub_metrics_by_role = {k: {sk: v[sk] for sk in ['product_value', 'service', 'pricing', 'support']} for k, v in nps_by_role.items()}
        sub_metrics_by_tier = {k: {sk: v[sk] for sk in ['product_value', 'service', 'pricing', 'support']} for k, v in nps_by_tier.items()}
        sub_metrics_by_region = {k: {sk: v[sk] for sk in ['product_value', 'service', 'pricing', 'support']} for k, v in nps_by_region.items()}
        sub_metrics_by_industry = {k: {sk: v[sk] for sk in ['product_value', 'service', 'pricing', 'support']} for k, v in nps_by_industry.items()}
        
        all_metrics_flat = dimensions.get('role', {})
        total_resp = sum(len(v) for v in all_metrics_flat.values())
        sub_metric_counts = {}
        for key in ['product_value_rating', 'service_rating', 'pricing_rating', 'support_rating']:
            count = 0
            for seg_metrics in dimensions.get('role', {}).values():
                count += sum(1 for m in seg_metrics if m.get(key) is not None)
            sub_metric_counts[key.replace('_rating', '')] = count
        sub_metric_counts['_total'] = total_resp
        
        return {
            'nps_by_role': nps_by_role,
            'nps_by_region': nps_by_region,
            'nps_by_tier': nps_by_tier,
            'nps_by_industry': nps_by_industry,
            'satisfaction_by_role': {k: v.get('satisfaction') for k, v in nps_by_role.items()},
            'satisfaction_by_region': {k: v.get('satisfaction') for k, v in nps_by_region.items()},
            'satisfaction_by_tier': {k: v.get('satisfaction') for k, v in nps_by_tier.items()},
            'satisfaction_by_industry': {k: v.get('satisfaction') for k, v in nps_by_industry.items()},
            'response_distribution': response_distribution,
            'churn_risk_by_segment': churn_risk_by_segment,
            'sub_metrics_by_role': sub_metrics_by_role,
            'sub_metrics_by_tier': sub_metrics_by_tier,
            'sub_metrics_by_region': sub_metrics_by_region,
            'sub_metrics_by_industry': sub_metrics_by_industry,
            'tenure_cohorts': tenure_cohorts_result,
            'sub_metric_response_counts': sub_metric_counts,
        }
    
    def _generate_segmentation_charts(self, seg_data: Dict, chart_colors: List) -> Dict:
        """Generate segmentation analytics charts"""
        charts = {}
        
        try:
            charts['nps_by_segment'] = self._create_nps_by_segment_chart(seg_data, chart_colors)
        except Exception as e:
            logger.error(f"Error generating NPS by segment chart: {e}")
        
        try:
            charts['churn_heatmap'] = self._create_churn_heatmap_chart(seg_data, chart_colors)
        except Exception as e:
            logger.error(f"Error generating churn heatmap chart: {e}")
        
        try:
            charts['tenure_cohort'] = self._create_tenure_cohort_chart(seg_data, chart_colors)
        except Exception as e:
            logger.error(f"Error generating tenure cohort chart: {e}")
        
        return charts
    
    def _create_nps_by_segment_chart(self, seg_data: Dict, chart_colors: List) -> str:
        """Create side-by-side subplot chart showing NPS by role and tier"""
        role_data = seg_data.get('nps_by_role', {})
        tier_data = seg_data.get('nps_by_tier', {})
        
        role_data = {k: v for k, v in role_data.items() if k != 'Unknown' and v.get('count', 0) > 0}
        tier_data = {k: v for k, v in tier_data.items() if k != 'Unknown' and v.get('count', 0) > 0}
        
        if not role_data and not tier_data:
            fig, ax = plt.subplots(figsize=(9, 4))
            ax.text(0.5, 0.5, 'No segmentation data available', ha='center', va='center', transform=ax.transAxes)
            plt.tight_layout()
            return self._fig_to_base64(fig)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, max(4, max(len(role_data), len(tier_data)) * 0.6 + 1)))
        
        role_color = chart_colors[0] if len(chart_colors) > 0 else '#4a90e2'
        tier_color = chart_colors[1] if len(chart_colors) > 1 else '#28a745'
        
        if role_data:
            sorted_roles = sorted(role_data.items(), key=lambda x: x[1].get('nps', 0))
            labels = [k for k, v in sorted_roles]
            values = [v.get('nps', 0) for k, v in sorted_roles]
            counts = [v.get('count', 0) for k, v in sorted_roles]
            y_pos = range(len(labels))
            bars = ax1.barh(y_pos, values, color=role_color, alpha=0.85, edgecolor='white', linewidth=0.5)
            ax1.set_yticks(y_pos)
            ax1.set_yticklabels(labels, fontsize=9)
            ax1.set_xlabel('NPS Score', fontsize=10)
            ax1.set_title('NPS by Role', fontsize=11, fontweight='bold')
            ax1.axvline(x=0, color='#333', linewidth=0.8, linestyle='--')
            ax1.grid(axis='x', alpha=0.3)
            for bar, val, n in zip(bars, values, counts):
                x_pos = bar.get_width() + 1 if val >= 0 else bar.get_width() - 8
                ax1.text(x_pos, bar.get_y() + bar.get_height()/2, f'{val:.0f} (n={n})',
                        va='center', fontsize=8, fontweight='bold')
        else:
            ax1.text(0.5, 0.5, 'No role data', ha='center', va='center', transform=ax1.transAxes)
            ax1.set_title('NPS by Role', fontsize=11, fontweight='bold')
        
        if tier_data:
            sorted_tiers = sorted(tier_data.items(), key=lambda x: x[1].get('nps', 0))
            labels = [k for k, v in sorted_tiers]
            values = [v.get('nps', 0) for k, v in sorted_tiers]
            counts = [v.get('count', 0) for k, v in sorted_tiers]
            y_pos = range(len(labels))
            bars = ax2.barh(y_pos, values, color=tier_color, alpha=0.85, edgecolor='white', linewidth=0.5)
            ax2.set_yticks(y_pos)
            ax2.set_yticklabels(labels, fontsize=9)
            ax2.set_xlabel('NPS Score', fontsize=10)
            ax2.set_title('NPS by Tier', fontsize=11, fontweight='bold')
            ax2.axvline(x=0, color='#333', linewidth=0.8, linestyle='--')
            ax2.grid(axis='x', alpha=0.3)
            for bar, val, n in zip(bars, values, counts):
                x_pos = bar.get_width() + 1 if val >= 0 else bar.get_width() - 8
                ax2.text(x_pos, bar.get_y() + bar.get_height()/2, f'{val:.0f} (n={n})',
                        va='center', fontsize=8, fontweight='bold')
        else:
            ax2.text(0.5, 0.5, 'No tier data', ha='center', va='center', transform=ax2.transAxes)
            ax2.set_title('NPS by Tier', fontsize=11, fontweight='bold')
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _create_churn_heatmap_chart(self, seg_data: Dict, chart_colors: List) -> str:
        """Create stacked horizontal bar chart for churn risk by tier"""
        fig, ax = plt.subplots(figsize=(8, 4))
        
        churn_data = seg_data.get('churn_risk_by_segment', {}).get('tier', {})
        churn_data = {k: v for k, v in churn_data.items() if k != 'Unknown'}
        
        if not churn_data:
            ax.text(0.5, 0.5, 'No churn risk data available', ha='center', va='center', transform=ax.transAxes)
            plt.tight_layout()
            return self._fig_to_base64(fig)
        
        labels = list(churn_data.keys())
        minimal = [churn_data[l].get('Minimal', 0) for l in labels]
        low = [churn_data[l].get('Low', 0) for l in labels]
        medium = [churn_data[l].get('Medium', 0) for l in labels]
        high = [churn_data[l].get('High', 0) for l in labels]
        
        y_pos = range(len(labels))
        
        ax.barh(y_pos, minimal, color='#28a745', alpha=0.85, label='Minimal', edgecolor='white', linewidth=0.5)
        ax.barh(y_pos, low, left=minimal, color='#17a2b8', alpha=0.85, label='Low', edgecolor='white', linewidth=0.5)
        left2 = [m + l for m, l in zip(minimal, low)]
        ax.barh(y_pos, medium, left=left2, color='#ffc107', alpha=0.85, label='Medium', edgecolor='white', linewidth=0.5)
        left3 = [l2 + md for l2, md in zip(left2, medium)]
        ax.barh(y_pos, high, left=left3, color='#dc3545', alpha=0.85, label='High', edgecolor='white', linewidth=0.5)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel('Number of Responses', fontsize=10)
        ax.set_title('Churn Risk Distribution by Tier', fontsize=12, fontweight='bold')
        ax.legend(loc='lower right', fontsize=8)
        ax.grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _create_tenure_cohort_chart(self, seg_data: Dict, chart_colors: List) -> str:
        """Create grouped bar chart with NPS and satisfaction by tenure band"""
        fig, ax1 = plt.subplots(figsize=(8, 4))
        
        tenure_data = seg_data.get('tenure_cohorts', {})
        band_order = ['1-2 years', '3-5 years', '6-8 years', '9+ years']
        ordered_bands = [b for b in band_order if b in tenure_data]
        
        if not ordered_bands:
            ax1.text(0.5, 0.5, 'No tenure data available', ha='center', va='center', transform=ax1.transAxes)
            plt.tight_layout()
            return self._fig_to_base64(fig)
        
        x = np.arange(len(ordered_bands))
        width = 0.35
        
        nps_vals = [tenure_data[b].get('nps', 0) for b in ordered_bands]
        sat_vals = [tenure_data[b].get('satisfaction', 0) or 0 for b in ordered_bands]
        
        bars1 = ax1.bar(x - width/2, nps_vals, width, label='NPS', color=chart_colors[0] if chart_colors else '#dc3545', alpha=0.85)
        ax1.set_xlabel('Tenure Cohort', fontsize=10)
        ax1.set_ylabel('NPS Score', fontsize=10, color=chart_colors[0] if chart_colors else '#dc3545')
        ax1.set_xticks(x)
        ax1.set_xticklabels(ordered_bands, fontsize=9)
        ax1.axhline(y=0, color='#333', linewidth=0.5, linestyle='--')
        
        ax2 = ax1.twinx()
        bars2 = ax2.bar(x + width/2, sat_vals, width, label='Satisfaction', color=chart_colors[1] if len(chart_colors) > 1 else '#28a745', alpha=0.85)
        ax2.set_ylabel('Satisfaction (1-5)', fontsize=10, color=chart_colors[1] if len(chart_colors) > 1 else '#28a745')
        ax2.set_ylim(0, 5.5)
        
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=8)
        
        ax1.set_title('Tenure Cohort Analysis: NPS & Satisfaction', fontsize=12, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _generate_recommendations(self, seg_data: Dict, current_kpis: Dict, average_ratings: Dict) -> List[Dict]:
        """Generate confidence-scored recommendations from segmentation data"""
        recommendations = []
        
        if not seg_data:
            return recommendations
        
        campaign_nps = current_kpis.get('nps_score', 0)
        total_responses = current_kpis.get('total_responses', 0)
        
        for dim_key, dim_label in [('nps_by_role', 'Role'), ('nps_by_tier', 'Tier'), ('nps_by_region', 'Region'), ('nps_by_industry', 'Industry')]:
            dim_data = seg_data.get(dim_key, {})
            for seg_name, seg_info in dim_data.items():
                if seg_name == 'Unknown':
                    continue
                seg_nps = seg_info.get('nps', 0)
                n = seg_info.get('count', 0)
                gap = campaign_nps - seg_nps
                if gap >= 5 and n >= 3:
                    if n >= 20 and gap >= 15:
                        confidence = 'High'
                    elif n >= 10 and gap >= 10:
                        confidence = 'Medium'
                    elif n >= 10 or gap >= 10:
                        confidence = 'Medium'
                    else:
                        confidence = 'Low'
                    completeness = round(n / total_responses * 100, 0) if total_responses > 0 else 0
                    recommendations.append({
                        'title': f'NPS Gap in {dim_label}: {seg_name}',
                        'description': f'{seg_name} ({dim_label.lower()}) shows an NPS of {seg_nps:.0f}, which is {gap:.0f} points below the campaign average of {campaign_nps:.0f}. This segment has {n} responses and may require targeted engagement.',
                        'confidence': confidence,
                        'sample_size': n,
                        'gap_magnitude': round(gap, 1),
                        'data_completeness_pct': completeness,
                    })
        
        sub_metrics = {}
        sub_counts = seg_data.get('sub_metric_response_counts', {})
        total_for_completeness = sub_counts.get('_total', total_responses) or total_responses
        for key, label in [('product_value', 'Product Value'), ('service', 'Service Quality'), ('pricing', 'Pricing'), ('support', 'Support')]:
            val = average_ratings.get(key, 0)
            if key == 'support' and val == 0:
                support_vals = []
                for r in seg_data.get('nps_by_role', {}).values():
                    sv = r.get('support')
                    if sv is not None:
                        support_vals.append(sv)
                val = round(sum(support_vals) / len(support_vals), 2) if support_vals else 0
            resp_with_metric = sub_counts.get(key, 0)
            pct = round(resp_with_metric / total_for_completeness * 100, 0) if total_for_completeness > 0 else 0
            sub_metrics[key] = {'value': val, 'label': label, 'completeness': pct, 'response_count': resp_with_metric}
        
        sorted_subs = sorted(sub_metrics.items(), key=lambda x: x[1]['value'])
        if len(sorted_subs) >= 2:
            lowest_key, lowest_info = sorted_subs[0]
            next_key, next_info = sorted_subs[1]
            gap = next_info['value'] - lowest_info['value']
            if gap >= 0.2 and lowest_info['value'] > 0:
                completeness = lowest_info['completeness']
                
                if completeness >= 80 and gap >= 0.5:
                    confidence = 'High'
                elif completeness >= 60 and gap >= 0.3:
                    confidence = 'Medium'
                else:
                    confidence = 'Low'
                
                recommendations.append({
                    'title': f'Lowest Sub-Metric: {lowest_info["label"]}',
                    'description': f'{lowest_info["label"]} has the lowest rating at {lowest_info["value"]:.1f}/5.0, which is {gap:.1f} points below the next lowest metric ({next_info["label"]} at {next_info["value"]:.1f}/5.0). Consider prioritizing improvements in this area.',
                    'confidence': confidence,
                    'sample_size': total_responses,
                    'gap_magnitude': round(gap, 1),
                    'data_completeness_pct': completeness,
                })
        
        for seg_key in ['tier', 'role', 'region']:
            churn_data = seg_data.get('churn_risk_by_segment', {}).get(seg_key, {})
            for seg_name, levels in churn_data.items():
                if seg_name == 'Unknown':
                    continue
                total = sum(levels.values())
                high_count = levels.get('High', 0)
                if total >= 5 and high_count > 0:
                    high_pct = high_count / total * 100
                    if high_pct > 15:
                        if total >= 15 and high_pct > 40:
                            confidence = 'High'
                        elif total >= 8 and high_pct > 30:
                            confidence = 'Medium'
                        else:
                            confidence = 'Low'
                        recommendations.append({
                            'title': f'Churn Concentration: {seg_name} ({seg_key.title()})',
                            'description': f'{high_pct:.0f}% of responses from {seg_name} ({seg_key}) show High churn risk ({high_count} of {total} responses). This concentration suggests systemic issues affecting this segment.',
                            'confidence': confidence,
                            'sample_size': total,
                            'gap_magnitude': round(high_pct, 1),
                            'data_completeness_pct': 100,
                        })
        
        tenure = seg_data.get('tenure_cohorts', {})
        mid_nps = tenure.get('3-5 years', {}).get('nps')
        for long_band in ['6-8 years', '9+ years']:
            long_data = tenure.get(long_band, {})
            long_nps = long_data.get('nps')
            if mid_nps is not None and long_nps is not None:
                gap = mid_nps - long_nps
                if gap >= 5:
                    mid_n = tenure.get('3-5 years', {}).get('count', 0)
                    long_n = long_data.get('count', 0)
                    min_n = min(mid_n, long_n)
                    if min_n >= 20 and gap >= 10:
                        confidence = 'High'
                    elif min_n >= 10 and gap >= 7:
                        confidence = 'Medium'
                    elif min_n >= 10 or gap >= 10:
                        confidence = 'Medium'
                    else:
                        confidence = 'Low'
                    recommendations.append({
                        'title': f'Tenure Fatigue: {long_band} Cohort',
                        'description': f'Long-tenure clients ({long_band}) show NPS of {long_nps:.0f}, which is {gap:.0f} points below mid-tenure (3-5 years) clients at {mid_nps:.0f}. This may indicate declining satisfaction among established accounts.',
                        'confidence': confidence,
                        'sample_size': long_n,
                        'gap_magnitude': round(gap, 1),
                        'data_completeness_pct': round(min_n / max(mid_n, 1) * 100, 0) if mid_n > 0 else 0,
                    })
        
        if not recommendations and total_responses >= 5:
            overall_satisfaction = average_ratings.get('satisfaction', 0)
            lowest_sub = sorted_subs[0] if sorted_subs else None
            if lowest_sub:
                lowest_key, lowest_info = lowest_sub
                recommendations.append({
                    'title': 'Monitor Lowest-Rated Dimension',
                    'description': f'{lowest_info["label"]} is the lowest-rated sub-metric at {lowest_info["value"]:.1f}/5.0. While no statistically significant gaps were detected across segments, this area may benefit from proactive attention.',
                    'confidence': 'Low',
                    'sample_size': total_responses,
                    'gap_magnitude': round(sorted_subs[1][1]['value'] - lowest_info['value'], 1) if len(sorted_subs) >= 2 else 0,
                    'data_completeness_pct': lowest_info.get('completeness', 0),
                })
            
            recommendations.append({
                'title': 'Maintain Current Trajectory',
                'description': f'No significant risk patterns were detected across {total_responses} responses. Segment-level NPS variation is within normal range and churn risk indicators are stable. Continue monitoring key metrics for emerging trends.',
                'confidence': 'Low',
                'sample_size': total_responses,
                'gap_magnitude': 0,
                'data_completeness_pct': 100,
            })
        
        confidence_order = {'High': 0, 'Medium': 1, 'Low': 2}
        recommendations.sort(key=lambda x: (confidence_order.get(x['confidence'], 3), -x['gap_magnitude']))
        
        return recommendations[:5]
    
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
            
            logo_data_uri = branding_config.get_logo_base64_data_uri()
            if logo_data_uri:
                branding_data['company_logo_base64'] = logo_data_uri
        
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
                {% if current_kpis.transcripts_count > 0 %}<p style="color: #888; font-size: 0.85em;"><em>Includes {{ current_kpis.transcripts_count }} transcript-sourced responses.</em></p>{% endif %}
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
                
                {% if ai_insights.critical_issues %}
                <h3>Critical Issues Requiring Attention</h3>
                <p style="color: #666; margin-bottom: 10px;">{{ ai_insights.critical_issues|length }} respondent{{ 's' if ai_insights.critical_issues|length != 1 else '' }} flagged with churn risk score ≥ 7.0/10, indicating elevated likelihood of disengagement.</p>
                <div class="insights-list">
                    {% for issue in ai_insights.critical_issues %}
                    <div class="insight-item" style="border-left: 4px solid #dc3545; padding-left: 12px; margin-bottom: 10px;">
                        <strong>{{ issue.respondent }}:</strong> {{ issue.issue }} (Risk Score: {{ issue.score }}/10)
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <div style="padding: 12px 15px; background: #d4edda; border-radius: 8px; border-left: 4px solid #28a745; margin-bottom: 15px;">
                    <strong style="color: #155724;">No High-Risk Respondents Identified</strong>
                    <p style="color: #155724; margin: 5px 0 0 0; font-size: 0.9em;">None of the {{ current_kpis.total_responses }} responses in this campaign exceeded the churn risk threshold (≥ 7.0/10). Overall relationship health appears stable across the respondent base.</p>
                </div>
                {% endif %}
                
                {% if ai_insights.top_themes %}
                <h3 style="margin-top: 20px;">Top Themes at a Glance</h3>
                <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px;">
                    {% for theme_name, theme_data in ai_insights.top_themes %}
                    <span style="background: #e9ecef; padding: 6px 12px; border-radius: 20px; font-size: 0.85em;">
                        {{ theme_name }} <strong style="color: var(--primary-color, #dc3545);">({{ theme_data.count }})</strong>
                    </span>
                    {% endfor %}
                </div>
                {% endif %}
                
                {% if ai_insights.growth_signals %}
                <h3 style="margin-top: 20px;">Growth Signals</h3>
                <p style="color: #666; font-size: 0.9em; margin-bottom: 10px;">Patterns detected from promoter feedback (NPS 9-10) that suggest organic growth opportunities.</p>
                <div class="insights-list">
                    {% for signal in ai_insights.growth_signals %}
                    <div class="insight-item" style="border-left: 4px solid #28a745; padding-left: 12px; margin-bottom: 8px;">
                        <strong>{{ signal.theme }}</strong> — mentioned by {{ signal.promoter_count }} promoter{{ 's' if signal.promoter_count != 1 else '' }}
                        {% if signal.detractor_count > 0 %}<span style="color: #888; font-size: 0.85em;">(also {{ signal.detractor_count }} detractor{{ 's' if signal.detractor_count != 1 else '' }})</span>{% endif %}
                    </div>
                    {% endfor %}
                </div>
                {% elif current_kpis.promoters is defined and current_kpis.promoters > 0 %}
                <h3 style="margin-top: 20px;">Growth Signals</h3>
                <div style="padding: 12px 15px; background: #f8f9fa; border-radius: 8px; margin-bottom: 15px;">
                    <p style="color: #666; font-size: 0.9em; margin: 0;">{{ current_kpis.promoters }} promoter{{ 's' if current_kpis.promoters != 1 else '' }} identified (NPS 9-10). Qualitative theme analysis did not isolate promoter-specific patterns distinct from the overall feedback.</p>
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

            <!-- Decision-Maker Risk -->
            {% if decision_maker_risk_accounts %}
            <div class="section page-break">
                <h2 class="section-title">👔 Decision-Maker Risk</h2>
                <p style="color: #666; margin-bottom: 15px;">
                    The following accounts have C-Level or VP/Director respondents who scored as Detractors (NPS ≤ 6).
                    Executive-level dissatisfaction represents elevated churn risk that cannot be attributed solely to end-user sentiment.
                </p>
                <div class="insights-list">
                    {% for account in decision_maker_risk_accounts[:8] %}
                    <div class="insight-item" style="border-left: 4px solid #7B1B1B; padding-left: 15px; margin-bottom: 18px;">
                        <strong>{{ account.company_name }}</strong>
                        <div style="color: #666; font-size: 0.9em; margin-top: 5px;">
                            Decision-Maker Detractors: <span style="color: #7B1B1B; font-weight: bold;">{{ account.detractor_count }}</span>
                            | Lowest NPS: <span style="color: #7B1B1B; font-weight: bold;">{{ account.min_nps }}</span>
                            | Avg NPS: {{ account.avg_nps }}
                            {% if account.roles %} | Roles: {{ account.roles | join(', ') }}{% endif %}
                        </div>
                        {% if account.verbatim_risk_factors %}
                        <div style="margin-top: 8px;">
                            <span style="font-size: 0.82em; color: #888; font-style: italic;">Captured risk factors:</span>
                            <ul style="margin: 4px 0 0 16px; padding: 0; font-size: 0.85em; color: #555;">
                                {% for rf in account.verbatim_risk_factors %}
                                <li style="margin-bottom: 2px;">{{ rf }}</li>
                                {% endfor %}
                            </ul>
                        </div>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
                <p style="font-size: 0.85em; color: #888; margin-top: 10px;">
                    Prioritize executive outreach for these accounts — sponsor-level intervention may be necessary to prevent churn.
                </p>
            </div>
            {% endif %}

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

            {% if segmentation_charts and segmentation_charts.nps_by_segment %}
            <!-- Segmentation Analytics -->
            <div class="section page-break">
                <h2 class="section-title">📊 Segmentation Analytics</h2>
                <p style="color: #666; margin-bottom: 15px;">NPS performance broken down by participant role and customer tier, revealing which segments are driving or dragging overall scores.</p>
                
                <div class="chart-container">
                    <img src="{{ segmentation_charts.nps_by_segment }}" alt="NPS by Segment" class="chart-image">
                </div>
            </div>
            {% endif %}

            {% if segmentation_charts and segmentation_charts.churn_heatmap %}
            <!-- Churn Risk Distribution -->
            <div class="section page-break">
                <h2 class="section-title">⚠️ Churn Risk Distribution</h2>
                <p style="color: #666; margin-bottom: 15px;">Distribution of churn risk levels across customer tiers, highlighting segments with concentrated retention risk.</p>
                
                <div class="chart-container">
                    <img src="{{ segmentation_charts.churn_heatmap }}" alt="Churn Risk Heatmap" class="chart-image">
                </div>
            </div>
            {% endif %}

            {% if segmentation_charts and segmentation_charts.tenure_cohort %}
            <!-- Tenure Cohort Analysis -->
            <div class="section page-break">
                <h2 class="section-title">📅 Tenure Cohort Analysis</h2>
                <p style="color: #666; margin-bottom: 15px;">How NPS and satisfaction evolve across client tenure bands, identifying potential loyalty fatigue patterns.</p>
                
                <div class="chart-container">
                    <img src="{{ segmentation_charts.tenure_cohort }}" alt="Tenure Cohort Analysis" class="chart-image">
                </div>
            </div>
            {% endif %}

            {% if recommendations %}
            <!-- Recommended Actions -->
            <div class="section page-break">
                <h2 class="section-title">🎯 Recommended Actions</h2>
                <p style="color: #666; margin-bottom: 15px;">Data-driven recommendations based on pattern analysis across segmentation data.</p>
                
                {% for rec in recommendations %}
                <div style="border-left: 4px solid {% if rec.confidence == 'High' %}#28a745{% elif rec.confidence == 'Medium' %}#ffc107{% else %}#dc3545{% endif %}; padding: 12px 15px; margin-bottom: 15px; background: #f8f9fa; border-radius: 0 8px 8px 0;">
                    <div style="font-weight: bold; font-size: 1em; margin-bottom: 6px;">{{ rec.title }}</div>
                    <div style="color: #444; font-size: 0.9em; margin-bottom: 8px;">{{ rec.description }}</div>
                    <div style="color: #888; font-size: 0.8em;">
                        Confidence: <strong style="color: {% if rec.confidence == 'High' %}#28a745{% elif rec.confidence == 'Medium' %}#ffc107{% else %}#dc3545{% endif %};">{{ rec.confidence }}</strong>
                        (n={{ rec.sample_size }}, {{ rec.gap_magnitude }}-pt gap, {{ rec.data_completeness_pct|int }}% data completeness)
                    </div>
                </div>
                {% endfor %}
                
                <div style="margin-top: 20px; padding: 12px; background: #f0f0f0; border-radius: 6px; font-size: 0.8em; color: #666;">
                    <strong>Methodology:</strong> Confidence levels are determined by three factors: sample size, gap magnitude, and data completeness.<br>
                    &bull; <strong>High:</strong> 20+ responses with large gap (15+ NPS points or 0.5+ rating points) and 80%+ data completeness<br>
                    &bull; <strong>Medium:</strong> 10+ responses with moderate gap (10+ NPS points or 0.3+ rating points) and 60%+ completeness<br>
                    &bull; <strong>Low:</strong> Smaller samples, narrower gaps, or lower completeness — pattern noted but warrants further investigation<br><br>
                    <em>Recommendations are generated from rule-based pattern detection across segment data. They reflect observed patterns in survey responses, not predictive models.</em>
                </div>
            </div>
            {% endif %}

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

            <!-- Report Footer -->
            <div style="margin-top: 30px; padding: 15px 20px; background: #f5f5f5; border-top: 2px solid #ddd; border-radius: 4px; font-size: 0.85em; color: #666;">
                <strong>Survey Type:</strong> {{ survey_type|title }} &nbsp;|&nbsp;
                <strong>Data Period:</strong> {{ campaign.start_date.strftime('%b %d, %Y') }} – {{ campaign.end_date.strftime('%b %d, %Y') }} &nbsp;|&nbsp;
                <strong>Responses Analyzed:</strong> {{ current_kpis.total_responses }}
                {% if delta_kpis.comparison_count > 0 %}
                <br><strong>Historical Comparison:</strong> Compared against {{ delta_kpis.comparison_count }} previous campaign{{ 's' if delta_kpis.comparison_count != 1 else '' }} in current license period.
                {% endif %}
                <br><em>This report was automatically generated by VOÏA – Voice Of Client system.</em>
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