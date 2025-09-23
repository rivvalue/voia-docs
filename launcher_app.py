#!/usr/bin/env python3
"""
VOÏA Application Module for Optimized Launcher
Simple app import for Gunicorn when launched via the supervisor
"""

# Import the Flask application
from app import app

# Export for Gunicorn
__all__ = ['app']