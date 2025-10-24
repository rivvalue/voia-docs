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
    
    Args:
        lang: Language code ('en' or 'fr')
    
    Returns:
        Redirect to the referring page or home
    """
    # Validate language
    if lang not in ['en', 'fr']:
        lang = 'en'
    
    # Store in session
    session['language'] = lang
    session.permanent = True  # Make session persistent
    
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
