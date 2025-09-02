"""
Ultra-simple token system that bypasses all circular import issues
"""
import jwt
import os
from datetime import datetime, timedelta

def create_simple_token(email):
    """Generate a simple JWT token without database dependencies"""
    try:
        # Use a simple secret (same as Flask app)
        secret = os.environ.get("SESSION_SECRET", "dev-secret-key")
        
        # Create token payload
        payload = {
            'email': email.lower().strip(),
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow(),
            'iss': 'voxa-auth'
        }
        
        # Generate token
        token = jwt.encode(payload, secret, algorithm='HS256')
        
        return {
            'success': True,
            'email': email.lower().strip(),
            'token': token,
            'expires_in': 86400  # 24 hours
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def verify_simple_token(token):
    """Verify a simple JWT token"""
    try:
        secret = os.environ.get("SESSION_SECRET", "dev-secret-key")
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        return {
            'valid': True,
            'email': payload.get('email'),
            'exp': payload.get('exp')
        }
    except:
        return {'valid': False}

if __name__ == "__main__":
    # Test the system
    result = create_simple_token("test@example.com")
    print("Token generation test:", result['success'])
    if result['success']:
        verify_result = verify_simple_token(result['token'])
        print("Token verification test:", verify_result['valid'])
    else:
        print("Error:", result['error'])