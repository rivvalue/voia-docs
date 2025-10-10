import os
import logging
from flask import Flask
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect, generate_csrf
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from database_config import db_config

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
if not app.secret_key:
    raise RuntimeError("SESSION_SECRET environment variable is required")

# Log environment variable status for debugging
logger = logging.getLogger(__name__)
logger.debug(f"EMAIL_ENCRYPTION_KEY loaded: {bool(os.environ.get('EMAIL_ENCRYPTION_KEY'))}")
logger.debug(f"SESSION_SECRET loaded: {bool(os.environ.get('SESSION_SECRET'))}")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1, x_for=1, x_port=1)

# Enable CORS for deployment compatibility
# In development, we allow broader origins for Replit's architecture
# In production, this should be restricted to specific domains
app_env = os.environ.get('APP_ENV', 'demo')
allowed_origins = ['*'] if app_env == 'demo' else [os.environ.get('ALLOWED_ORIGIN', 'https://your-domain.com')]
CORS(app, 
     origins=allowed_origins,
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization', 'Accept'],
     supports_credentials=True)

# Disable template caching for development
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# Set maximum file upload size to 5MB for security
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

# Configure database using DatabaseConfig
# Read environment setting and configure accordingly
db_config.set_environment(app_env)

app.config["SQLALCHEMY_DATABASE_URI"] = db_config.get_database_url()
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = db_config.get_engine_options()

# Initialize the app with the extension
db.init_app(app)

# Initialize Flask-Caching with admin-configurable settings
from flask_caching import Cache
from cache_config import cache_config

app.config.from_mapping(cache_config.get_cache_config())
cache = Cache(app)

logger.info(f"Cache configuration: {cache_config.get_status_info()}")

# Stage 1 Optimization: Performance Monitoring and Compression
# Feature flag controlled optimizations
try:
    from performance_monitor import performance_monitor, get_performance_metrics
    
    # SECURITY: Protected diagnostic endpoints - require business admin authentication
    @app.route('/business/admin/performance-metrics')
    def performance_metrics():
        """Performance monitoring endpoint - ADMIN ONLY"""
        # Import here to avoid circular imports
        from business_auth_routes import require_business_auth
        
        @require_business_auth
        def _performance_metrics():
            return get_performance_metrics()
        
        return _performance_metrics()
    
    @app.route('/business/admin/optimization-status')  
    def optimization_status_endpoint():
        """Optimization status endpoint - ADMIN ONLY"""
        # Import here to avoid circular imports
        from business_auth_routes import require_business_auth
        
        @require_business_auth
        def _optimization_status():
            try:
                from optimization_status import optimization_status
                return optimization_status.get_comprehensive_status()
            except ImportError as e:
                return {
                    'error': 'Optimization status unavailable',
                    'message': str(e),
                    'timestamp': time.time()
                }
        
        return _optimization_status()
    
    # Add performance monitoring to requests
    @app.before_request
    def before_request():
        from flask import g
        import time
        g.start_time = time.time()
    
    @app.after_request
    def after_request(response):
        from flask import g, request
        import time
        
        if hasattr(g, 'start_time'):
            duration = (time.time() - g.start_time) * 1000  # Convert to ms
            
            # Log slow requests
            if duration > 1000:  # Log requests over 1 second
                app.logger.warning(f'Slow request: {request.path} took {duration:.2f}ms')
            
            # Add performance header for monitoring
            response.headers['X-Response-Time'] = f'{duration:.2f}ms'
        
        return response
    
    app.logger.info("Performance monitoring initialized")
    
except ImportError as e:
    app.logger.warning(f"Performance monitoring unavailable: {e}")

# Stage 1 Optimization: Response Compression (Feature Flag Controlled)
ENABLE_COMPRESSION = os.environ.get('ENABLE_COMPRESSION', 'false').lower() == 'true'
if ENABLE_COMPRESSION:
    try:
        from flask_compress import Compress
        Compress(app)
        app.logger.info("Response compression enabled")
    except ImportError:
        app.logger.warning("Flask-Compress not available, compression disabled")

# Initialize CSRF protection
csrf = CSRFProtect(app)

# CSRF error handler
@app.errorhandler(400)
def handle_csrf_error(e):
    """Handle CSRF validation errors with user-friendly messages"""
    from flask import request, jsonify, flash, redirect, url_for
    
    # Check if this is a CSRF error
    if 'CSRFError' in str(type(e)) or 'csrf' in str(e).lower():
        if request.is_json:
            return jsonify({
                'error': 'Security token validation failed. Please refresh the page and try again.',
                'csrf_error': True
            }), 400
        else:
            flash('Security token validation failed. Please try again.', 'error')
            # Redirect back to the referring page or admin panel
            return redirect(request.referrer or url_for('business_auth.admin_panel'))
    
    # For non-CSRF 400 errors, use default handling
    return str(e), 400

# Make csrf_token and business auth state available in all templates
@app.context_processor
def inject_csrf():
    from flask import session, request
    
    context = dict(csrf_token=generate_csrf)
    
    # Check business authentication state
    context['is_business_authenticated'] = bool(session.get('business_user_id'))
    
    if context['is_business_authenticated']:
        context['business_user_name'] = session.get('business_user_name', 'User')  # User's actual name
        context['business_account_name'] = session.get('business_account_name')
        
        # Get branding context for multi-tenant logo display
        business_account_id = session.get('business_account_id')
        if business_account_id:
            from routes import get_branding_context
            context['branding_context'] = get_branding_context(business_account_id)
    else:
        # For trial/demo mode (unauthenticated users), show Archelo demo branding ONLY on trial pages
        trial_pages = ['demo_intro', 'dashboard']
        if request.endpoint in trial_pages:
            from routes import get_branding_context
            context['branding_context'] = get_branding_context(business_account_id=1)
    
    return context

# Make UI version available in all templates (Phase 2b Feature Flags)
@app.context_processor
def inject_ui_version():
    from feature_flags import feature_flags
    from flask import session
    
    # Get current UI version
    user_id = session.get('business_user_id')
    ui_version = feature_flags.get_ui_version(user_id=user_id)
    
    return {
        'ui_version': ui_version,
        'can_toggle_ui': feature_flags.can_user_toggle(),
        'sidebar_enabled': feature_flags.is_feature_enabled('sidebar_navigation'),
        'business_user_id': user_id,
        'business_user_email': session.get('business_user_email', '')
    }

with app.app_context():
    # Import models FIRST to avoid circular imports
    import models  # noqa: F401
    import models_auth  # noqa: F401
    
    # Create database tables before importing routes
    db.create_all()
    
    from task_queue import start_task_queue
    from business_accounts import business_account_manager
    
    # Validate database setup and create demo content
    try:
        # Ensure Rivvalue demo account exists
        demo_setup = business_account_manager.ensure_demo_setup()
        app.logger.info(f"Database validation passed. Rivvalue account: {demo_setup['account_name']}")
        
        # Log environment info
        env_info = db_config.get_environment_info()
        app.logger.info(f"Database environment: {env_info['current_environment']} - URL configured: {bool(env_info['database_url'])}")
        
        # Validate business accounts functionality
        accounts = business_account_manager.list_business_accounts()
        app.logger.info(f"Business accounts count: {len(accounts)}")
        
    except Exception as e:
        app.logger.error(f"Database validation failed: {str(e)}")
        # Continue startup but log the issue
    
    # Start the background task queue for AI processing
    start_task_queue()
    
    # Import routes LAST to avoid circular imports
    import routes  # noqa: F401
    
    # Register business authentication blueprint (Phase 2)
    from business_auth_routes import business_auth_bp, init_rivvalue_admin_user
    app.register_blueprint(business_auth_bp)
    
    # Register participant management blueprint (Phase 3)
    from participant_routes import participant_bp
    app.register_blueprint(participant_bp)
    
    # Register campaign management blueprint (Phase 3 completion)
    from campaign_routes import campaign_bp
    app.register_blueprint(campaign_bp)
    
    # Initialize Rivvalue admin user (Phase 2)
    try:
        init_result = init_rivvalue_admin_user()
        app.logger.info(f"Rivvalue admin user initialization: {init_result}")
    except Exception as e:
        app.logger.error(f"Failed to initialize admin user: {e}")
    
    # Log all registered routes for debugging (after blueprint registration)
    app.logger.info("=== REGISTERED ROUTES ===")
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods - {'HEAD', 'OPTIONS'})
        app.logger.info(f"Route: {rule.rule} | Methods: {methods} | Endpoint: {rule.endpoint}")
    app.logger.info("=== END REGISTERED ROUTES ===")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
