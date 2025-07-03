import time
import logging
from collections import defaultdict, deque
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple in-memory rate limiter for handling high load"""
    
    def __init__(self):
        self.clients = defaultdict(deque)
        self.default_limit = 100  # requests per minute per IP
        self.window_size = 60  # 60 seconds
    
    def is_allowed(self, client_id, limit=None):
        """Check if client is allowed to make a request"""
        if limit is None:
            limit = self.default_limit
            
        now = time.time()
        client_requests = self.clients[client_id]
        
        # Remove old requests outside the window
        while client_requests and client_requests[0] <= now - self.window_size:
            client_requests.popleft()
        
        # Check if under limit
        if len(client_requests) < limit:
            client_requests.append(now)
            return True
        
        return False
    
    def get_remaining(self, client_id, limit=None):
        """Get remaining requests for client"""
        if limit is None:
            limit = self.default_limit
            
        now = time.time()
        client_requests = self.clients[client_id]
        
        # Remove old requests
        while client_requests and client_requests[0] <= now - self.window_size:
            client_requests.popleft()
        
        return max(0, limit - len(client_requests))
    
    def reset_time(self, client_id):
        """Get time until rate limit resets"""
        now = time.time()
        client_requests = self.clients[client_id]
        
        if not client_requests:
            return 0
        
        return max(0, self.window_size - (now - client_requests[0]))

# Global rate limiter instance
rate_limiter = RateLimiter()

def rate_limit(limit=None):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Get client IP
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', 
                                          request.environ.get('REMOTE_ADDR', 'unknown'))
            
            if not rate_limiter.is_allowed(client_ip, limit):
                # Rate limit exceeded
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': int(rate_limiter.reset_time(client_ip))
                }), 429
            
            return f(*args, **kwargs)
        return wrapped
    return decorator