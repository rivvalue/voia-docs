"""
Cache Configuration for VOÏA Platform
Provides admin-configurable caching settings for dashboard performance optimization.
"""
import os
import logging

logger = logging.getLogger(__name__)


class CacheConfig:
    """Manages cache configuration with admin controls"""
    
    def __init__(self):
        # Cache enable/disable (admin configurable via environment variable)
        self.enabled = os.environ.get('ENABLE_CACHE', 'true').lower() == 'true'
        
        # Cache timeout in seconds (admin configurable)
        # Default: 7200 seconds (2 hours) - Phase 2 optimization
        self.timeout = int(os.environ.get('CACHE_TIMEOUT', '7200'))
        
        # Cache type (simple for in-memory, redis for production scaling)
        cache_type = os.environ.get('CACHE_TYPE', 'simple').lower()
        self.cache_type = 'SimpleCache' if cache_type == 'simple' else 'RedisCache'
        
        # Redis configuration (if using Redis)
        self.redis_url = os.environ.get('CACHE_REDIS_URL', 'redis://localhost:6379/0')
        
        # Phase 2: Enhanced caching metrics
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Log configuration on startup
        if self.enabled:
            logger.info(f"✅ Cache enabled - Type: {self.cache_type}, Timeout: {self.timeout}s ({self.timeout/3600:.1f}h)")
        else:
            logger.info("❌ Cache disabled by admin configuration")
    
    def get_cache_config(self):
        """Get Flask-Caching configuration dictionary"""
        if not self.enabled:
            # Null cache - caching disabled
            return {
                'CACHE_TYPE': 'NullCache',
                'CACHE_NO_NULL_WARNING': True
            }
        
        if self.cache_type == 'RedisCache':
            return {
                'CACHE_TYPE': 'RedisCache',
                'CACHE_REDIS_URL': self.redis_url,
                'CACHE_DEFAULT_TIMEOUT': self.timeout
            }
        else:
            # Simple in-memory cache (default)
            return {
                'CACHE_TYPE': 'SimpleCache',
                'CACHE_DEFAULT_TIMEOUT': self.timeout
            }
    
    def get_timeout(self):
        """Get current cache timeout"""
        return self.timeout if self.enabled else 0
    
    def is_enabled(self):
        """Check if caching is enabled"""
        return self.enabled
    
    def record_hit(self):
        """Record cache hit for metrics"""
        self._cache_hits += 1
    
    def record_miss(self):
        """Record cache miss for metrics"""
        self._cache_misses += 1
    
    def get_hit_rate(self):
        """Calculate cache hit rate percentage"""
        total = self._cache_hits + self._cache_misses
        if total == 0:
            return 0.0
        return (self._cache_hits / total) * 100
    
    def get_metrics(self):
        """Get cache performance metrics"""
        return {
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'hit_rate': round(self.get_hit_rate(), 1),
            'total_requests': self._cache_hits + self._cache_misses
        }
    
    def get_status_info(self):
        """Get cache configuration status for admin dashboard"""
        return {
            'enabled': self.enabled,
            'type': self.cache_type,
            'timeout_seconds': self.timeout,
            'timeout_minutes': round(self.timeout / 60, 1),
            'timeout_hours': round(self.timeout / 3600, 1),
            'redis_url': self.redis_url if self.cache_type == 'RedisCache' else None,
            'metrics': self.get_metrics()
        }


# Global cache configuration instance
cache_config = CacheConfig()
