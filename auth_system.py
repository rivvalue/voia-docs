import os
import jwt
import secrets
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g
from app import db
from models import SurveyResponse

logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Custom exception for authentication errors"""
    pass

class AuthSystem:
    """Email-based token authentication system"""
    
    def __init__(self):
        self.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
        self.token_expiry_hours = 24  # Tokens valid for 24 hours
    
    def generate_token(self, email):
        """Generate a JWT token for an email address"""
        try:
            payload = {
                'email': email.lower().strip(),
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
                'jti': secrets.token_hex(16)  # Unique token ID
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm='HS256')
            logger.info(f"Generated token for email: {email}")
            return token
            
        except Exception as e:
            logger.error(f"Error generating token for {email}: {e}")
            raise AuthenticationError("Failed to generate authentication token")
    
    def verify_token(self, token):
        """Verify and decode a JWT token"""
        try:
            if not token:
                raise AuthenticationError("No token provided")
            
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            email = payload.get('email')
            
            if not email:
                raise AuthenticationError("Invalid token payload")
            
            logger.debug(f"Token verified for email: {email}")
            return email
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise AuthenticationError("Invalid token")
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise AuthenticationError("Token verification failed")
    
    def check_duplicate_response(self, email, allow_overwrite=False):
        """Check if user has already submitted a response"""
        try:
            existing_response = SurveyResponse.query.filter_by(
                respondent_email=email.lower().strip()
            ).first()
            
            if existing_response:
                if allow_overwrite:
                    logger.info(f"User {email} is overwriting previous response")
                    return existing_response  # Return existing to overwrite
                else:
                    logger.warning(f"Duplicate response attempt from {email}")
                    raise AuthenticationError("You have already submitted a response")
            
            return None
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error checking duplicate response for {email}: {e}")
            raise AuthenticationError("Failed to verify response status")

# Global auth system instance
auth_system = AuthSystem()

def require_auth(allow_overwrite=False):
    """Decorator to require authentication for endpoints"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            try:
                # Get token from header
                auth_header = request.headers.get('Authorization')
                if not auth_header:
                    return jsonify({
                        'error': 'Missing authorization header',
                        'code': 'MISSING_AUTH'
                    }), 401
                
                # Verify token and get email
                email = auth_system.verify_token(auth_header)
                
                # Check for duplicate responses if needed
                existing_response = None
                if hasattr(request, 'json') and request.json:
                    existing_response = auth_system.check_duplicate_response(
                        email, allow_overwrite
                    )
                
                # Add verified email and existing response to Flask's g object
                g.authenticated_email = email
                g.existing_response = existing_response
                
                return f(*args, **kwargs)
                
            except AuthenticationError as e:
                return jsonify({
                    'error': str(e),
                    'code': 'AUTH_ERROR'
                }), 401
            except Exception as e:
                logger.error(f"Authentication middleware error: {e}")
                return jsonify({
                    'error': 'Authentication failed',
                    'code': 'AUTH_FAILED'
                }), 500
        
        return wrapped
    return decorator

def generate_user_token(email):
    """Public function to generate token for email"""
    return auth_system.generate_token(email)

def verify_user_token(token):
    """Public function to verify token"""
    return auth_system.verify_token(token)