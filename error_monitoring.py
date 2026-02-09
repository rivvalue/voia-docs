"""
Error Monitoring Configuration for VOÏA Phase 2b
Prepares for Sentry/LogRocket integration with feature flag support

Environment Variables:
- ERROR_MONITORING_ENABLED: Enable/disable error monitoring (default: false)
- SENTRY_DSN: Sentry project DSN (optional)
- SENTRY_ENVIRONMENT: Environment name (development/staging/production)
- SENTRY_TRACES_SAMPLE_RATE: Trace sampling rate (0.0-1.0)
- LOGROCKET_APP_ID: LogRocket application ID (optional)
- ERROR_MONITORING_DEBUG: Enable debug logging (default: false)
"""

import os
import logging
from functools import wraps
from flask import request, session

logger = logging.getLogger(__name__)

class ErrorMonitor:
    """Centralized error monitoring configuration"""
    
    def __init__(self, app=None):
        self.app = app
        self.enabled = os.environ.get('ERROR_MONITORING_ENABLED', 'false').lower() == 'true'
        self.debug = os.environ.get('ERROR_MONITORING_DEBUG', 'false').lower() == 'true'
        self.sentry_initialized = False
        self.logrocket_initialized = False
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize error monitoring for Flask app"""
        self.app = app
        
        if not self.enabled:
            logger.info("🔇 Error monitoring is DISABLED")
            logger.info("   Set ERROR_MONITORING_ENABLED=true to enable")
            return
        
        # Initialize Sentry if configured
        self._init_sentry()
        
        # Initialize LogRocket if configured
        self._init_logrocket()
        
        # Register error handlers
        self._register_error_handlers()
        
        # Log initialization status
        if self.sentry_initialized or self.logrocket_initialized:
            logger.info("✅ Error monitoring initialized")
            if self.sentry_initialized:
                logger.info("   - Sentry: Active")
            if self.logrocket_initialized:
                logger.info("   - LogRocket: Active")
        else:
            logger.warning("⚠️  Error monitoring enabled but no services configured")
            logger.info("   Set SENTRY_DSN or LOGROCKET_APP_ID to activate")
    
    def _init_sentry(self):
        """Initialize Sentry error tracking"""
        sentry_dsn = os.environ.get('SENTRY_DSN')
        
        if not sentry_dsn:
            if self.debug:
                logger.debug("Sentry: No DSN configured")
            return
        
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            
            environment = os.environ.get('SENTRY_ENVIRONMENT', 'development')
            traces_sample_rate = float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1'))
            
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[FlaskIntegration()],
                environment=environment,
                traces_sample_rate=traces_sample_rate,
                send_default_pii=False,  # Don't send user data by default
                before_send=self._sentry_before_send
            )
            
            self.sentry_initialized = True
            logger.info(f"Sentry initialized: env={environment}, sample_rate={traces_sample_rate}")
            
        except ImportError:
            logger.error("Sentry SDK not installed. Install with: pip install sentry-sdk")
        except Exception as e:
            logger.error(f"Sentry initialization failed: {e}")
    
    def _init_logrocket(self):
        """Prepare LogRocket session recording configuration"""
        logrocket_app_id = os.environ.get('LOGROCKET_APP_ID')
        
        if not logrocket_app_id:
            if self.debug:
                logger.debug("LogRocket: No App ID configured")
            return
        
        # LogRocket is client-side, just store config for template injection
        self.app.config['LOGROCKET_APP_ID'] = logrocket_app_id
        self.app.config['LOGROCKET_ENABLED'] = True
        
        # Make LogRocket config available to templates
        @self.app.context_processor
        def inject_logrocket():
            return {
                'logrocket_enabled': True,
                'logrocket_app_id': logrocket_app_id
            }
        
        self.logrocket_initialized = True
        logger.info(f"LogRocket configured: app_id={logrocket_app_id[:8]}...")
    
    def _register_error_handlers(self):
        """Register Flask error handlers with monitoring"""
        
        @self.app.errorhandler(500)
        def handle_500(error):
            self.capture_exception(error, context={'error_code': 500})
            return "Internal Server Error", 500
        
        @self.app.errorhandler(404)
        def handle_404(error):
            # Don't report 404s to Sentry (too noisy)
            return "Not Found", 404
    
    def _sentry_before_send(self, event, hint):
        """Filter/modify events before sending to Sentry.
        
        Enriches error events with metadata for triage (IDs, roles, survey type).
        No PII (names, emails) is included — only numeric IDs and categorical tags.
        Wrapped in try/except so enrichment failures never block error reporting.
        """
        from flask import has_request_context
        
        if 'contexts' not in event:
            event['contexts'] = {}
        if 'tags' not in event:
            event['tags'] = {}
        
        try:
            if has_request_context():
                self._enrich_request_context(event)
            else:
                event['contexts']['execution'] = {
                    'context_type': 'non-request',
                    'note': 'Captured outside HTTP request context (background task or CLI)'
                }
                event['tags']['user_type'] = 'background'
        except Exception:
            event['tags']['enrichment_error'] = 'true'
        
        try:
            if 'request' in event and 'headers' in event['request']:
                headers = event['request']['headers']
                sensitive_headers = ['Authorization', 'Cookie', 'X-Api-Key']
                for header in sensitive_headers:
                    if header in headers:
                        headers[header] = '[Filtered]'
        except Exception:
            pass
        
        return event
    
    def _enrich_request_context(self, event):
        """Add request-scoped metadata to a Sentry event. IDs only, no PII."""
        event['contexts']['ui'] = {
            'ui_version': session.get('ui_version', 'v1'),
            'feature_flags': {
                'sidebar_enabled': session.get('sidebar_enabled', False)
            }
        }
        
        event['contexts']['request_info'] = {
            'url': request.url,
            'method': request.method,
            'endpoint': request.endpoint,
            'user_agent': request.user_agent.string if request.user_agent else None
        }
        
        user_type = self._determine_user_type(session)
        event['tags']['user_type'] = user_type
        
        if user_type == 'business_user':
            event['contexts']['business'] = {
                'business_account_id': session.get('business_account_id'),
                'business_user_id': session.get('business_user_id'),
                'user_role': session.get('user_role'),
            }
            event['tags']['business_account_id'] = str(session.get('business_account_id', ''))
            event['tags']['user_role'] = session.get('user_role', '')
            
            try:
                import sentry_sdk
                sentry_sdk.set_user({
                    'id': str(session.get('business_user_id', '')),
                })
            except Exception:
                pass
        
        elif user_type == 'participant':
            campaign_id = session.get('campaign_id')
            participant_id = session.get('participant_id')
            
            event['contexts']['survey_session'] = {
                'campaign_id': campaign_id,
                'participant_id': participant_id,
                'business_account_id': session.get('business_account_id'),
                'language': session.get('language'),
            }
            event['tags']['campaign_id'] = str(campaign_id) if campaign_id else ''
            event['tags']['participant_id'] = str(participant_id) if participant_id else ''
            
            survey_type = self._detect_survey_type(request)
            if survey_type:
                event['tags']['survey_type'] = survey_type
                event['contexts']['survey_session']['survey_type'] = survey_type
            
            try:
                import sentry_sdk
                sentry_sdk.set_user({
                    'id': f"participant_{participant_id}" if participant_id else 'unknown',
                })
            except Exception:
                pass
        
        elif user_type == 'platform_admin':
            admin_id = session.get('user_id')
            event['tags']['admin_id'] = str(admin_id) if admin_id else ''
            event['contexts']['admin'] = {
                'admin_id': admin_id,
            }
            
            try:
                import sentry_sdk
                sentry_sdk.set_user({
                    'id': f"admin_{admin_id}" if admin_id else 'unknown',
                })
            except Exception:
                pass
    
    def _determine_user_type(self, sess):
        """Determine the type of user from session data"""
        if sess.get('business_user_id'):
            return 'business_user'
        elif sess.get('participant_id'):
            return 'participant'
        elif sess.get('user_id') or sess.get('is_admin'):
            return 'platform_admin'
        return 'anonymous'
    
    def _detect_survey_type(self, req):
        """Detect survey type from the request endpoint/URL"""
        endpoint = req.endpoint or ''
        path = req.path or ''
        if 'classic' in endpoint or 'classic' in path:
            return 'classic'
        elif 'conversation' in endpoint or 'chat' in path or 'voia' in path.lower():
            return 'conversational'
        elif 'survey' in endpoint or 'survey' in path:
            return 'survey'
        return None
    
    def capture_exception(self, exception, context=None):
        """Capture an exception with optional context"""
        if not self.enabled:
            return
        
        try:
            if self.sentry_initialized:
                import sentry_sdk
                
                if context:
                    with sentry_sdk.push_scope() as scope:
                        for key, value in context.items():
                            scope.set_context(key, value)
                        sentry_sdk.capture_exception(exception)
                else:
                    sentry_sdk.capture_exception(exception)
        except Exception as e:
            logger.error(f"Error capturing exception: {e}")
    
    def capture_message(self, message, level='info', context=None):
        """Capture a message/event"""
        if not self.enabled:
            return
        
        try:
            if self.sentry_initialized:
                import sentry_sdk
                
                if context:
                    with sentry_sdk.push_scope() as scope:
                        for key, value in context.items():
                            scope.set_context(key, value)
                        sentry_sdk.capture_message(message, level=level)
                else:
                    sentry_sdk.capture_message(message, level=level)
        except Exception as e:
            logger.error(f"Error capturing message: {e}")
    
    def set_user(self, user_id, email=None, username=None):
        """Set user context for error tracking"""
        if not self.enabled or not self.sentry_initialized:
            return
        
        try:
            import sentry_sdk
            sentry_sdk.set_user({
                "id": user_id,
                "email": email,
                "username": username
            })
        except Exception as e:
            logger.error(f"Error setting user context: {e}")
    
    def add_breadcrumb(self, message, category='custom', level='info', data=None):
        """Add breadcrumb for error context"""
        if not self.enabled or not self.sentry_initialized:
            return
        
        try:
            import sentry_sdk
            sentry_sdk.add_breadcrumb(
                message=message,
                category=category,
                level=level,
                data=data or {}
            )
        except Exception as e:
            logger.error(f"Error adding breadcrumb: {e}")


# Decorator for monitoring specific functions
def monitor_errors(context_name=None):
    """Decorator to monitor errors in specific functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Add context about the function
                from app import app
                if hasattr(app, 'error_monitor'):
                    app.error_monitor.capture_exception(e, context={
                        'function': func.__name__,
                        'context': context_name or func.__module__
                    })
                raise
        return wrapper
    return decorator


# Initialize global error monitor
error_monitor = ErrorMonitor()


# Template filter for LogRocket initialization script
def logrocket_init_script():
    """Generate LogRocket initialization script for templates"""
    app_id = os.environ.get('LOGROCKET_APP_ID')
    
    if not app_id or os.environ.get('ERROR_MONITORING_ENABLED', 'false').lower() != 'true':
        return ""
    
    return f"""
    <script src="https://cdn.lr-in-prod.com/LogRocket.min.js" crossorigin="anonymous"></script>
    <script>
        window.LogRocket && window.LogRocket.init('{app_id}');
        
        // Identify user (if logged in)
        var userId = document.body.dataset.userId;
        var userEmail = document.body.dataset.userEmail;
        if (userId) {{
            window.LogRocket.identify(userId, {{
                email: userEmail
            }});
        }}
        
        // Track UI version for Phase 2b
        var uiVersion = document.body.dataset.uiVersion || 'v1';
        window.LogRocket.track('UI Version', {{ version: uiVersion }});
    </script>
    """


if __name__ == "__main__":
    # Test configuration
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    print("VOÏA Error Monitoring Configuration Test\n")
    print("=" * 50)
    
    # Check environment
    enabled = os.environ.get('ERROR_MONITORING_ENABLED', 'false')
    sentry_dsn = os.environ.get('SENTRY_DSN', 'Not set')
    logrocket_id = os.environ.get('LOGROCKET_APP_ID', 'Not set')
    
    print(f"\nEnvironment Configuration:")
    print(f"  ERROR_MONITORING_ENABLED: {enabled}")
    print(f"  SENTRY_DSN: {sentry_dsn[:20] + '...' if sentry_dsn != 'Not set' else 'Not set'}")
    print(f"  LOGROCKET_APP_ID: {logrocket_id[:8] + '...' if logrocket_id != 'Not set' else 'Not set'}")
    
    print(f"\nStatus:")
    if enabled.lower() == 'true':
        if sentry_dsn != 'Not set' or logrocket_id != 'Not set':
            print("  ✅ Error monitoring is configured and ready")
        else:
            print("  ⚠️  Error monitoring enabled but no services configured")
            print("     Set SENTRY_DSN or LOGROCKET_APP_ID")
    else:
        print("  🔇 Error monitoring is disabled")
        print("     Set ERROR_MONITORING_ENABLED=true to enable")
    
    print("\n" + "=" * 50)
