import urllib.parse
from flask import Blueprint, jsonify, request, session
from app import db
from models import SurveyResponse, Campaign, Participant, CampaignParticipant
from sqlalchemy import func

whiteboard_api_bp = Blueprint('whiteboard_api', __name__)


@whiteboard_api_bp.route('/api/whiteboard/filter-accounts')
def filter_accounts():
    business_account_id = session.get('business_account_id')
    if not business_account_id:
        return jsonify({'error': 'Unauthorized'}), 401

    campaign_id     = request.args.get('campaign_id',     type=int)
    tier            = request.args.get('tier')
    churn_risk      = request.args.get('churn_risk')
    balance         = request.args.get('balance')
    nps_category    = request.args.get('nps_category')
    nps_opportunity = request.args.get('nps_opportunity')
    recommendation  = request.args.get('recommendation')
    csat            = request.args.get('csat',            type=int)
    ces             = request.args.get('ces',             type=int)

    campaign_uuid = None
    campaign_name = None
    if campaign_id:
        camp = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=business_account_id,
        ).first()
        if camp:
            campaign_uuid = camp.uuid
            campaign_name = camp.name

    query = (
        db.session.query(
            SurveyResponse.company_name,
            func.round(func.avg(SurveyResponse.nps_score), 1).label('avg_nps_score'),
            func.count(SurveyResponse.id).label('response_count'),
        )
        .join(Campaign, SurveyResponse.campaign_id == Campaign.id)
        .filter(
            Campaign.business_account_id == business_account_id,
            SurveyResponse.company_name.isnot(None),
        )
    )

    if campaign_id:
        query = query.filter(SurveyResponse.campaign_id == campaign_id)

    if churn_risk:
        query = query.filter(
            func.lower(SurveyResponse.churn_risk_level) == churn_risk.lower()
        )

    if nps_category:
        query = query.filter(
            func.lower(SurveyResponse.nps_category) == nps_category.lower()
        )

    if csat is not None:
        query = query.filter(SurveyResponse.csat_score == csat)

    if ces is not None:
        query = query.filter(SurveyResponse.ces_score == ces)

    if nps_opportunity:
        parts = nps_opportunity.split('-')
        try:
            low  = int(parts[0])
            high = int(parts[1]) if len(parts) > 1 else 100
            query = query.filter(
                SurveyResponse.growth_factor >= low,
                SurveyResponse.growth_factor <= high,
            )
        except (ValueError, IndexError):
            pass

    if balance:
        if balance == 'risk_heavy':
            query = query.filter(
                SurveyResponse.churn_risk_level.in_(['High', 'Critical'])
            )
        elif balance == 'opportunity_heavy':
            query = query.filter(
                SurveyResponse.churn_risk_level.in_(['Minimal', 'Low'])
            )
        elif balance == 'balanced':
            query = query.filter(
                SurveyResponse.churn_risk_level.in_(['Medium'])
            )

    if recommendation:
        query = query.filter(
            func.lower(SurveyResponse.recommendation_status) == recommendation.lower()
        )

    query = query.group_by(
        func.upper(SurveyResponse.company_name),
        SurveyResponse.company_name,
    )

    rows = query.all()

    if tier:
        tier_list = [t.strip() for t in tier.split(',') if t.strip()]
        tier_q = (
            db.session.query(func.upper(Participant.company_name))
            .join(CampaignParticipant, Participant.id == CampaignParticipant.participant_id)
        )
        if campaign_id:
            tier_q = tier_q.filter(CampaignParticipant.campaign_id == campaign_id)
        else:
            tier_q = tier_q.join(Campaign, CampaignParticipant.campaign_id == Campaign.id).filter(
                Campaign.business_account_id == business_account_id
            )
        tier_q = tier_q.filter(Participant.customer_tier.in_(tier_list)).distinct()
        tier_companies = {row[0] for row in tier_q.all()}
        rows = [r for r in rows if r.company_name and r.company_name.upper() in tier_companies]

    def _detail_url(company):
        if campaign_uuid:
            safe = urllib.parse.quote(company, safe='')
            return '/dashboard/company-responses/' + safe + '?campaign=' + campaign_uuid
        return None

    accounts = sorted(
        [
            {
                'company_name': r.company_name,
                'avg_nps_score': float(r.avg_nps_score) if r.avg_nps_score is not None else None,
                'response_count': r.response_count,
                'detail_url': _detail_url(r.company_name),
            }
            for r in rows
        ],
        key=lambda x: (x['company_name'] or '').lower(),
    )

    return jsonify({
        'accounts': accounts,
        'campaign_id': campaign_id,
        'campaign_uuid': campaign_uuid,
        'campaign_name': campaign_name,
        'count': len(accounts),
    })
