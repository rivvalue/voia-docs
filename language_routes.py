"""
Language switching routes for VOÏA bilingual support
"""

from flask import Blueprint, session, redirect, request, url_for, jsonify
from flask_babel import refresh

language_bp = Blueprint('language', __name__, url_prefix='/language')

@language_bp.route('/set/<lang>')
def set_language(lang):
    """
    Set the user's language preference
    
    For authenticated users: Saves to both session and database (persistent across devices)
    For anonymous users: Saves to session only (current session only)
    
    Args:
        lang: Language code ('en' or 'fr')
    
    Returns:
        Redirect to the referring page or home
    """
    # Validate language
    if lang not in ['en', 'fr']:
        lang = 'en'
    
    # Store in session (for all users)
    session['language'] = lang
    session.permanent = True  # Make session persistent
    
    # For authenticated business users, also save to database (persistent across devices)
    business_user_id = session.get('business_user_id')
    if business_user_id:
        try:
            from models import BusinessAccountUser
            from app import db
            
            user = BusinessAccountUser.query.get(business_user_id)
            if user:
                user.set_language_preference(lang)
                db.session.commit()
        except Exception as e:
            # Log error but don't fail the language change - session language still works
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not save language preference to database for user {business_user_id}: {e}")
    
    # Refresh translations
    refresh()
    
    # Redirect back to where the user came from
    return redirect(request.referrer or url_for('index'))

@language_bp.route('/current')
def get_current_language():
    """API endpoint to get current language"""
    return jsonify({
        'language': session.get('language', 'en'),
        'available': ['en', 'fr']
    })
