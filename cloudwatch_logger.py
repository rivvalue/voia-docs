"""
CloudWatch Error Logger for VOÏA
Sends structured JSON log lines to AWS CloudWatch Logs as a parallel
error-reporting backend alongside the (disabled) Sentry integration.

Environment Variables:
- CLOUDWATCH_LOGGING_ENABLED: Enable/disable CloudWatch logging (default: false)
- AWS_ACCESS_KEY_ID: AWS access key
- AWS_SECRET_ACCESS_KEY: AWS secret access key
- AWS_REGION: AWS region (e.g. us-east-1)
- CLOUDWATCH_LOG_GROUP: CloudWatch log group name
"""

import os
import json
import logging
import traceback
import datetime
from flask import request, session, has_request_context

logger = logging.getLogger(__name__)


class CloudWatchLogger:
    """CloudWatch logging backend mirroring the ErrorMonitor interface."""

    def __init__(self, app=None):
        self.app = app
        self.enabled = os.environ.get('CLOUDWATCH_LOGGING_ENABLED', 'false').lower() == 'true'
        self.initialized = False
        self._cw_handler = None
        self._cw_logger = None

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize CloudWatch logging for a Flask app."""
        self.app = app

        if not self.enabled:
            logger.info("CloudWatch logging is DISABLED")
            logger.info("   Set CLOUDWATCH_LOGGING_ENABLED=true to enable")
            return

        self._init_cloudwatch()

        if self.initialized:
            log_group = os.environ.get('CLOUDWATCH_LOG_GROUP', '')
            region = os.environ.get('AWS_REGION', '')
            logger.info(f"CloudWatch logging initialized: group={log_group}, region={region}")
        else:
            logger.warning("CLOUDWATCH_LOGGING_ENABLED=true but CloudWatch could not be initialized")

    def _init_cloudwatch(self):
        """Set up the watchtower CloudWatch log handler."""
        aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        aws_region = os.environ.get('AWS_REGION')
        log_group = os.environ.get('CLOUDWATCH_LOG_GROUP')

        if not all([aws_access_key_id, aws_secret_access_key, aws_region, log_group]):
            missing = [
                k for k, v in {
                    'AWS_ACCESS_KEY_ID': aws_access_key_id,
                    'AWS_SECRET_ACCESS_KEY': aws_secret_access_key,
                    'AWS_REGION': aws_region,
                    'CLOUDWATCH_LOG_GROUP': log_group,
                }.items() if not v
            ]
            logger.error(f"CloudWatch: missing required environment variables: {missing}")
            return

        try:
            import boto3
            import watchtower

            boto_client = boto3.client(
                'logs',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region,
            )

            self._cw_handler = watchtower.CloudWatchLogHandler(
                boto3_client=boto_client,
                log_group_name=log_group,
                create_log_group=True,
            )

            self._cw_logger = logging.getLogger('voia.cloudwatch')
            self._cw_logger.setLevel(logging.DEBUG)
            self._cw_logger.addHandler(self._cw_handler)
            self._cw_logger.propagate = False

            self.initialized = True

        except ImportError:
            logger.error("watchtower or boto3 not installed. Install with: pip install watchtower")
        except Exception as e:
            logger.error(f"CloudWatch initialization failed: {e}")

    def _build_event(self, event_type, message, level='error', context=None, exc=None):
        """Build a structured JSON event dict with enriched request context."""
        event = {
            'event_type': event_type,
            'message': message,
            'level': level,
            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
            'context': context or {},
        }

        if exc is not None:
            tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
            event['exception'] = {
                'type': type(exc).__name__,
                'value': str(exc),
                'traceback': ''.join(tb_lines),
            }

        try:
            if has_request_context():
                self._enrich_request_context(event)
            else:
                event['execution_context'] = 'non-request'
                event['user_type'] = 'background'
        except Exception:
            event['enrichment_error'] = True

        return event

    def _enrich_request_context(self, event):
        """Add request-scoped metadata to an event. IDs only, no PII."""
        event['ui_version'] = session.get('ui_version', 'v1')
        event['sidebar_enabled'] = session.get('sidebar_enabled', False)

        event['request_url'] = request.url
        event['request_method'] = request.method
        event['endpoint'] = request.endpoint
        event['user_agent'] = request.user_agent.string if request.user_agent else None

        user_type = self._determine_user_type(session)
        event['user_type'] = user_type

        if user_type == 'business_user':
            event['business_account_id'] = session.get('business_account_id')
            event['business_user_id'] = session.get('business_user_id')
            event['user_role'] = session.get('user_role')

        elif user_type == 'participant':
            campaign_id = session.get('campaign_id')
            participant_id = session.get('participant_id')
            event['campaign_id'] = campaign_id
            event['participant_id'] = participant_id
            event['business_account_id'] = session.get('business_account_id')
            event['language'] = session.get('language')

            survey_type = self._detect_survey_type(request)
            if survey_type:
                event['survey_type'] = survey_type

        elif user_type == 'platform_admin':
            event['admin_id'] = session.get('user_id')

    def _determine_user_type(self, sess):
        """Determine the type of user from session data."""
        if sess.get('business_user_id'):
            return 'business_user'
        elif sess.get('participant_id'):
            return 'participant'
        elif sess.get('user_id') or sess.get('is_admin'):
            return 'platform_admin'
        return 'anonymous'

    def _detect_survey_type(self, req):
        """Detect survey type from the request endpoint/URL."""
        endpoint = req.endpoint or ''
        path = req.path or ''
        if 'classic' in endpoint or 'classic' in path:
            return 'classic'
        elif 'conversation' in endpoint or 'chat' in path or 'voia' in path.lower():
            return 'conversational'
        elif 'survey' in endpoint or 'survey' in path:
            return 'survey'
        return None

    def _emit(self, event, level='error'):
        """Serialize the event dict and emit it to CloudWatch."""
        if not self.initialized or self._cw_logger is None:
            return

        try:
            log_method = getattr(self._cw_logger, level, self._cw_logger.error)
            log_method(json.dumps(event, default=str))
        except Exception as e:
            logger.error(f"CloudWatch emit failed: {e}")

    def capture_exception(self, exception, context=None):
        """Capture an exception and send it to CloudWatch."""
        if not self.enabled:
            return

        try:
            event = self._build_event(
                event_type='exception',
                message=str(exception),
                level='error',
                context=context,
                exc=exception,
            )
            self._emit(event, level='error')
        except Exception as e:
            logger.error(f"CloudWatch capture_exception failed: {e}")

    def capture_message(self, message, level='info', context=None):
        """Capture a message/event and send it to CloudWatch."""
        if not self.enabled:
            return

        try:
            event = self._build_event(
                event_type='message',
                message=message,
                level=level,
                context=context,
            )
            self._emit(event, level=level if level in ('debug', 'info', 'warning', 'error', 'critical') else 'info')
        except Exception as e:
            logger.error(f"CloudWatch capture_message failed: {e}")

    def add_breadcrumb(self, message, category='custom', level='info', data=None):
        """Log a breadcrumb event to CloudWatch."""
        if not self.enabled:
            return

        try:
            event = self._build_event(
                event_type='breadcrumb',
                message=message,
                level=level,
                context={'category': category, 'data': data or {}},
            )
            self._emit(event, level=level if level in ('debug', 'info', 'warning', 'error', 'critical') else 'info')
        except Exception as e:
            logger.error(f"CloudWatch add_breadcrumb failed: {e}")


cloudwatch_logger = CloudWatchLogger()
