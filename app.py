import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect, generate_csrf
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from database_config import db_config

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
if not app.secret_key:
    raise RuntimeError("SESSION_SECRET environment variable is required")
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

# Configure database using DatabaseConfig
# Read environment setting and configure accordingly
db_config.set_environment(app_env)

app.config["SQLALCHEMY_DATABASE_URI"] = db_config.get_database_url()
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = db_config.get_engine_options()

# Initialize the app with the extension
db.init_app(app)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Make csrf_token and business auth state available in all templates
@app.context_processor
def inject_csrf():
    from flask import session
    
    context = dict(csrf_token=generate_csrf)
    
    # Check business authentication state
    context['is_business_authenticated'] = bool(session.get('business_user_id'))
    
    if context['is_business_authenticated']:
        context['business_user_name'] = session.get('business_account_name', 'User')
        context['business_account_name'] = session.get('business_account_name')
    
    return context

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
