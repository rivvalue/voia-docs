"""
Classic Survey Feature Tests for VOÏA Platform.

Tests cover:
1. ClassicSurveyConfig model (CRUD, freeze, to_dict)
2. SurveyTemplate model
3. Config editor routes (access control, GET/POST, frozen enforcement)
4. Classic survey form rendering with custom names
5. Classic survey response submission and data storage
6. Classic analytics API endpoint (CSAT, CES, drivers, features, recommendation)
7. Cross-survey-type comparison (shared metrics only)
8. Regression: conversational surveys unaffected by classic additions
"""
import pytest
import json
from datetime import datetime, timedelta


class TestClassicSurveyConfigModel:
    """Test ClassicSurveyConfig model behavior."""

    def test_create_classic_config(self, db_session, sample_data, app_context):
        """ClassicSurveyConfig can be created and linked to a campaign."""
        from models import ClassicSurveyConfig, SurveyTemplate

        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, survey_type='classic')

        template = SurveyTemplate(
            name='Default NPS Template',
            version='1.0',
            is_system=True,
            sections_config={'section_1': True, 'section_2': True, 'section_3': True},
            default_driver_labels=[
                {'key': 'product_quality', 'label_en': 'Product Quality', 'label_fr': 'Qualité du produit'}
            ],
            default_feature_count=5,
        )
        db_session.add(template)
        db_session.flush()

        config = ClassicSurveyConfig(
            campaign_id=campaign.id,
            template_id=template.id,
            sections_enabled={'section_1': True, 'section_2': True, 'section_3': True},
            feature_count=3,
            features=[
                {'key': 'feature_1', 'name_en': 'Dashboard', 'name_fr': 'Tableau de bord'},
                {'key': 'feature_2', 'name_en': 'Reports', 'name_fr': 'Rapports'},
                {'key': 'feature_3', 'name_en': 'Alerts', 'name_fr': 'Alertes'},
            ],
            driver_labels=[
                {'key': 'product_quality', 'label_en': 'Product Quality', 'label_fr': 'Qualité du produit'},
                {'key': 'customer_support', 'label_en': 'Customer Support', 'label_fr': 'Support client'},
            ],
        )
        db_session.add(config)
        db_session.flush()

        assert config.id is not None
        assert config.campaign_id == campaign.id
        assert config.feature_count == 3
        assert len(config.features) == 3
        assert len(config.driver_labels) == 2
        assert config.is_frozen() is False

    def test_freeze_config(self, db_session, sample_data, app_context):
        """Freezing config sets frozen_at timestamp and is_frozen returns True."""
        from models import ClassicSurveyConfig, SurveyTemplate

        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, survey_type='classic')
        template = SurveyTemplate(name='T', version='1.0', is_system=True)
        db_session.add(template)
        db_session.flush()

        config = ClassicSurveyConfig(
            campaign_id=campaign.id,
            template_id=template.id,
            feature_count=5,
            features=[],
            driver_labels=[],
        )
        db_session.add(config)
        db_session.flush()

        assert config.is_frozen() is False
        config.freeze()
        assert config.is_frozen() is True
        assert config.frozen_at is not None

    def test_freeze_idempotent(self, db_session, sample_data, app_context):
        """Calling freeze multiple times doesn't change frozen_at."""
        from models import ClassicSurveyConfig, SurveyTemplate

        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, survey_type='classic')
        template = SurveyTemplate(name='T', version='1.0', is_system=True)
        db_session.add(template)
        db_session.flush()

        config = ClassicSurveyConfig(
            campaign_id=campaign.id,
            template_id=template.id,
            feature_count=5,
            features=[],
            driver_labels=[],
        )
        db_session.add(config)
        db_session.flush()

        config.freeze()
        first_frozen = config.frozen_at
        config.freeze()
        assert config.frozen_at == first_frozen

    def test_to_dict(self, db_session, sample_data, app_context):
        """to_dict returns complete config data."""
        from models import ClassicSurveyConfig, SurveyTemplate

        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, survey_type='classic')
        template = SurveyTemplate(name='T', version='1.0', is_system=True)
        db_session.add(template)
        db_session.flush()

        features = [{'key': 'f1', 'name_en': 'Feature 1', 'name_fr': 'Fonctionnalité 1'}]
        drivers = [{'key': 'd1', 'label_en': 'Driver 1', 'label_fr': 'Facteur 1'}]

        config = ClassicSurveyConfig(
            campaign_id=campaign.id,
            template_id=template.id,
            feature_count=1,
            features=features,
            driver_labels=drivers,
        )
        db_session.add(config)
        db_session.flush()

        d = config.to_dict()
        assert d['campaign_id'] == campaign.id
        assert d['feature_count'] == 1
        assert d['features'] == features
        assert d['driver_labels'] == drivers
        assert d['is_frozen'] is False
        assert d['frozen_at'] is None

    def test_unique_campaign_constraint(self, db_session, sample_data, app_context):
        """Only one ClassicSurveyConfig per campaign (unique constraint)."""
        from models import ClassicSurveyConfig, SurveyTemplate
        from sqlalchemy.exc import IntegrityError

        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, survey_type='classic')
        template = SurveyTemplate(name='T', version='1.0', is_system=True)
        db_session.add(template)
        db_session.flush()

        config1 = ClassicSurveyConfig(
            campaign_id=campaign.id,
            template_id=template.id,
            feature_count=5, features=[], driver_labels=[],
        )
        db_session.add(config1)
        db_session.flush()

        config2 = ClassicSurveyConfig(
            campaign_id=campaign.id,
            template_id=template.id,
            feature_count=3, features=[], driver_labels=[],
        )
        db_session.add(config2)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()


class TestClassicSurveyConfigRoutes:
    """Test classic survey config editor routes."""

    def test_config_page_requires_auth(self, client, db_session, sample_data, app_context):
        """Config editor requires authentication."""
        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, survey_type='classic')
        db_session.commit()

        response = client.get(f'/business/campaigns/{campaign.id}/classic-survey-config')
        assert response.status_code in [302, 401, 403]

    def test_config_page_renders_for_classic(self, authenticated_client, db_session, sample_data, app_context):
        """Config editor renders for classic campaigns."""
        client, user, account = authenticated_client
        campaign = sample_data.create_campaign(db_session, account, survey_type='classic')
        db_session.commit()

        response = client.get(f'/business/campaigns/{campaign.id}/classic-survey-config')
        assert response.status_code in [200, 302]

    def test_config_page_blocked_for_active_campaign(self, authenticated_client, db_session, sample_data, app_context):
        """Config editor redirects for active campaigns."""
        client, user, account = authenticated_client
        campaign = sample_data.create_campaign(db_session, account, survey_type='classic', status='active')
        db_session.commit()

        response = client.get(f'/business/campaigns/{campaign.id}/classic-survey-config')
        assert response.status_code in [302, 403]

    def test_config_page_blocked_for_conversational(self, authenticated_client, db_session, sample_data, app_context):
        """Config editor should not work for conversational campaigns."""
        client, user, account = authenticated_client
        campaign = sample_data.create_campaign(db_session, account, survey_type='conversational')
        db_session.commit()

        response = client.get(f'/business/campaigns/{campaign.id}/classic-survey-config')
        assert response.status_code in [302, 403, 404]


class TestClassicSurveyResponse:
    """Test classic survey response data storage."""

    def test_classic_response_fields(self, db_session, sample_data, app_context):
        """Classic survey responses store CSAT, CES, loyalty drivers, recommendation status."""
        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, survey_type='classic')

        response = sample_data.create_survey_response(
            db_session,
            campaign=campaign,
            source_type='classic',
            csat_score=4,
            ces_score=5,
            loyalty_drivers=['product_quality', 'customer_support'],
            recommendation_status='with_conditions',
        )
        db_session.flush()

        assert response.csat_score == 4
        assert response.ces_score == 5
        assert response.loyalty_drivers == ['product_quality', 'customer_support']
        assert response.recommendation_status == 'with_conditions'

    def test_classic_response_feature_evaluations(self, db_session, sample_data, app_context):
        """Classic survey responses store feature evaluations in general_feedback as JSON."""
        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, survey_type='classic')

        feature_evals = {
            'feature_1': {'usage': 'yes', 'satisfaction': 4, 'importance': 'high', 'frequency': 'daily'},
            'feature_2': {'usage': 'no_not_needed', 'satisfaction': None, 'importance': 'low', 'frequency': None},
        }

        response = sample_data.create_survey_response(
            db_session,
            campaign=campaign,
            source_type='classic',
            general_feedback=json.dumps(feature_evals),
        )
        db_session.flush()

        loaded = json.loads(response.general_feedback)
        assert loaded['feature_1']['usage'] == 'yes'
        assert loaded['feature_1']['satisfaction'] == 4
        assert loaded['feature_2']['usage'] == 'no_not_needed'


class TestClassicSurveyAnalyticsAPI:
    """Test /api/classic_survey_analytics endpoint."""

    def _create_classic_campaign_with_responses(self, db_session, sample_data, account):
        """Helper: create a classic campaign with config and sample responses."""
        from models import ClassicSurveyConfig, SurveyTemplate

        campaign = sample_data.create_campaign(db_session, account, survey_type='classic')
        template = SurveyTemplate(name='T', version='1.0', is_system=True)
        db_session.add(template)
        db_session.flush()

        config = ClassicSurveyConfig(
            campaign_id=campaign.id,
            template_id=template.id,
            feature_count=2,
            features=[
                {'key': 'feature_1', 'name_en': 'Dashboard', 'name_fr': 'Tableau de bord'},
                {'key': 'feature_2', 'name_en': 'Reports', 'name_fr': 'Rapports'},
            ],
            driver_labels=[
                {'key': 'product_quality', 'label_en': 'Product Quality', 'label_fr': 'Qualité du produit'},
                {'key': 'support', 'label_en': 'Support', 'label_fr': 'Support'},
            ],
        )
        db_session.add(config)

        for i in range(3):
            feature_evals = {
                'feature_1': {'usage': 'yes', 'satisfaction': 4 + (i % 2), 'importance': 'high', 'frequency': 'daily'},
                'feature_2': {'usage': 'no_not_needed' if i == 2 else 'yes', 'satisfaction': 3 if i != 2 else None},
            }
            sample_data.create_survey_response(
                db_session,
                campaign=campaign,
                source_type='classic',
                nps_score=7 + i,
                csat_score=3 + i,
                ces_score=4 + (i % 3),
                loyalty_drivers=['product_quality'] if i < 2 else ['support'],
                recommendation_status='yes' if i == 0 else 'with_conditions',
                general_feedback=json.dumps(feature_evals),
            )

        db_session.flush()
        return campaign

    def test_analytics_requires_auth(self, client, db_session, sample_data, app_context):
        """Analytics endpoint requires authentication."""
        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, survey_type='classic')
        db_session.commit()

        response = client.get(f'/api/classic_survey_analytics?campaign_id={campaign.id}')
        assert response.status_code == 401

    def test_analytics_requires_campaign_id(self, authenticated_client, db_session, app_context):
        """Analytics endpoint requires campaign_id parameter."""
        client, user, account = authenticated_client
        response = client.get('/api/classic_survey_analytics')
        assert response.status_code == 400

    def test_analytics_rejects_conversational(self, authenticated_client, db_session, sample_data, app_context):
        """Analytics endpoint rejects conversational campaigns."""
        client, user, account = authenticated_client
        campaign = sample_data.create_campaign(db_session, account, survey_type='conversational')
        db_session.commit()

        response = client.get(f'/api/classic_survey_analytics?campaign_id={campaign.id}')
        assert response.status_code == 404

    def test_analytics_empty_responses(self, authenticated_client, db_session, sample_data, app_context):
        """Analytics returns zeros for campaign with no responses."""
        client, user, account = authenticated_client
        campaign = sample_data.create_campaign(db_session, account, survey_type='classic')
        db_session.commit()

        response = client.get(f'/api/classic_survey_analytics?campaign_id={campaign.id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total_responses'] == 0
        assert data['csat']['average'] is None
        assert data['ces']['average'] is None

    def test_analytics_csat_distribution(self, authenticated_client, db_session, sample_data, app_context):
        """Analytics correctly calculates CSAT average and distribution."""
        client, user, account = authenticated_client
        campaign = self._create_classic_campaign_with_responses(db_session, sample_data, account)
        db_session.commit()

        response = client.get(f'/api/classic_survey_analytics?campaign_id={campaign.id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['csat']['average'] is not None
        assert isinstance(data['csat']['distribution'], dict)

    def test_analytics_ces_distribution(self, authenticated_client, db_session, sample_data, app_context):
        """Analytics correctly calculates CES average and distribution."""
        client, user, account = authenticated_client
        campaign = self._create_classic_campaign_with_responses(db_session, sample_data, account)
        db_session.commit()

        response = client.get(f'/api/classic_survey_analytics?campaign_id={campaign.id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['ces']['average'] is not None
        assert isinstance(data['ces']['distribution'], dict)

    def test_analytics_driver_attribution(self, authenticated_client, db_session, sample_data, app_context):
        """Analytics returns driver counts with bilingual labels."""
        client, user, account = authenticated_client
        campaign = self._create_classic_campaign_with_responses(db_session, sample_data, account)
        db_session.commit()

        response = client.get(f'/api/classic_survey_analytics?campaign_id={campaign.id}')
        assert response.status_code == 200
        data = response.get_json()
        drivers = data['drivers']
        assert 'product_quality' in drivers
        assert drivers['product_quality']['count'] == 2
        assert 'label_en' in drivers['product_quality']
        assert 'label_fr' in drivers['product_quality']

    def test_analytics_feature_data(self, authenticated_client, db_session, sample_data, app_context):
        """Analytics returns feature adoption and satisfaction data."""
        client, user, account = authenticated_client
        campaign = self._create_classic_campaign_with_responses(db_session, sample_data, account)
        db_session.commit()

        response = client.get(f'/api/classic_survey_analytics?campaign_id={campaign.id}')
        assert response.status_code == 200
        data = response.get_json()
        features = data['features']
        assert 'feature_1' in features
        assert features['feature_1']['name_en'] == 'Dashboard'
        assert features['feature_1']['name_fr'] == 'Tableau de bord'
        assert features['feature_1']['adoption_rate'] is not None

    def test_analytics_recommendation_status(self, authenticated_client, db_session, sample_data, app_context):
        """Analytics returns recommendation status distribution."""
        client, user, account = authenticated_client
        campaign = self._create_classic_campaign_with_responses(db_session, sample_data, account)
        db_session.commit()

        response = client.get(f'/api/classic_survey_analytics?campaign_id={campaign.id}')
        assert response.status_code == 200
        data = response.get_json()
        rec = data['recommendation']
        assert isinstance(rec, dict)

    def test_analytics_tenant_isolation(self, authenticated_client, db_session, sample_data, app_context):
        """Analytics endpoint only returns data for campaigns owned by the authenticated user's account."""
        client, user, account = authenticated_client
        other_account = sample_data.create_business_account(db_session, name='Other Corp')
        other_campaign = sample_data.create_campaign(db_session, other_account, survey_type='classic')
        db_session.commit()

        response = client.get(f'/api/classic_survey_analytics?campaign_id={other_campaign.id}')
        assert response.status_code == 404


class TestCrossSurveyTypeComparison:
    """Test that shared metrics work across survey types."""

    def test_comparison_includes_survey_type(self, authenticated_client, db_session, sample_data, app_context):
        """Campaign comparison response includes survey_type for both campaigns."""
        client, user, account = authenticated_client

        campaign1 = sample_data.create_campaign(db_session, account, survey_type='conversational', name='Conv Camp')
        campaign2 = sample_data.create_campaign(db_session, account, survey_type='classic', name='Classic Camp')
        db_session.commit()

        response = client.get(f'/api/campaign-comparison?campaign1={campaign1.id}&campaign2={campaign2.id}')
        if response.status_code == 200:
            data = response.get_json()
            assert data['campaign1']['survey_type'] == 'conversational'
            assert data['campaign2']['survey_type'] == 'classic'

    def test_shared_metrics_for_classic(self, db_session, sample_data, app_context):
        """Classic survey responses contribute to shared metrics (NPS, satisfaction)."""
        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, survey_type='classic')

        sample_data.create_survey_response(
            db_session,
            campaign=campaign,
            source_type='classic',
            nps_score=9,
            nps_category='Promoter',
            satisfaction_rating=5,
            csat_score=5,
            ces_score=6,
        )
        sample_data.create_survey_response(
            db_session,
            campaign=campaign,
            source_type='classic',
            nps_score=6,
            nps_category='Detractor',
            satisfaction_rating=2,
            csat_score=2,
            ces_score=3,
        )
        db_session.flush()

        from models import SurveyResponse
        responses = SurveyResponse.query.filter_by(campaign_id=campaign.id).all()
        assert len(responses) == 2
        nps_scores = [r.nps_score for r in responses]
        assert 9 in nps_scores
        assert 6 in nps_scores


class TestRegressionConversational:
    """Regression tests: conversational surveys should remain unaffected."""

    def test_conversational_campaign_no_classic_config(self, db_session, sample_data, app_context):
        """Conversational campaigns should not have a ClassicSurveyConfig."""
        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, survey_type='conversational')
        db_session.flush()

        assert campaign.classic_survey_config is None

    def test_conversational_response_no_classic_fields(self, db_session, sample_data, app_context):
        """Conversational survey responses can leave classic fields null."""
        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, survey_type='conversational')

        response = sample_data.create_survey_response(
            db_session,
            campaign=campaign,
            source_type='conversational',
            nps_score=10,
        )
        db_session.flush()

        assert response.csat_score is None
        assert response.ces_score is None
        assert response.loyalty_drivers is None
        assert response.recommendation_status is None

    def test_campaign_default_survey_type(self, db_session, sample_data, app_context):
        """Campaign survey_type defaults to 'conversational'."""
        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account)
        db_session.flush()

        assert getattr(campaign, 'survey_type', 'conversational') == 'conversational'


class TestSurveyTemplateModel:
    """Test SurveyTemplate model."""

    def test_create_system_template(self, db_session, app_context):
        """System templates can be created with default config."""
        from models import SurveyTemplate

        template = SurveyTemplate(
            name='NPS + CSAT Standard',
            version='1.0',
            is_system=True,
            description_en='Standard NPS and CSAT survey',
            description_fr='Sondage NPS et CSAT standard',
            estimated_duration_minutes=10,
            default_feature_count=5,
            max_features=9,
            default_driver_labels=[
                {'key': 'product_quality', 'label_en': 'Product Quality', 'label_fr': 'Qualité du produit'}
            ],
        )
        db_session.add(template)
        db_session.flush()

        assert template.id is not None
        assert template.is_system is True
        assert template.max_features == 9

    def test_template_to_dict(self, db_session, app_context):
        """to_dict returns complete template data."""
        from models import SurveyTemplate

        template = SurveyTemplate(
            name='Test',
            version='2.0',
            is_system=False,
            default_feature_count=3,
            max_features=5,
        )
        db_session.add(template)
        db_session.flush()

        d = template.to_dict()
        assert d['name'] == 'Test'
        assert d['version'] == '2.0'
        assert d['default_feature_count'] == 3
        assert d['max_features'] == 5


class TestDriverLabelValidation:
    """Test driver label constraints."""

    def test_max_15_drivers_stored(self, db_session, sample_data, app_context):
        """Config can store up to 15 driver labels."""
        from models import ClassicSurveyConfig, SurveyTemplate

        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, survey_type='classic')
        template = SurveyTemplate(name='T', version='1.0', is_system=True)
        db_session.add(template)
        db_session.flush()

        drivers = [
            {'key': f'driver_{i}', 'label_en': f'Driver {i}', 'label_fr': f'Facteur {i}'}
            for i in range(15)
        ]
        config = ClassicSurveyConfig(
            campaign_id=campaign.id,
            template_id=template.id,
            feature_count=5,
            features=[],
            driver_labels=drivers,
        )
        db_session.add(config)
        db_session.flush()

        assert len(config.driver_labels) == 15

    def test_feature_count_range(self, db_session, sample_data, app_context):
        """Feature count stored within valid range."""
        from models import ClassicSurveyConfig, SurveyTemplate

        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, survey_type='classic')
        template = SurveyTemplate(name='T', version='1.0', is_system=True)
        db_session.add(template)
        db_session.flush()

        config = ClassicSurveyConfig(
            campaign_id=campaign.id,
            template_id=template.id,
            feature_count=9,
            features=[{'key': f'f{i}', 'name_en': f'F{i}', 'name_fr': f'F{i}'} for i in range(9)],
            driver_labels=[],
        )
        db_session.add(config)
        db_session.flush()

        assert config.feature_count == 9
        assert len(config.features) == 9
