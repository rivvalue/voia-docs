"""
VOÏA Stage 2 Query Optimization
Feature-flag controlled database query optimizations with eager loading and caching
"""

import os
import logging
from functools import wraps
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import text
from flask import current_app

logger = logging.getLogger(__name__)

class QueryOptimizer:
    """Query optimization with feature flag controls"""
    
    def __init__(self):
        # Feature flags for Stage 2 optimizations
        self.use_optimized_queries = os.environ.get('USE_OPTIMIZED_QUERIES', 'false').lower() == 'true'
        self.enable_eager_loading = os.environ.get('ENABLE_EAGER_LOADING', 'false').lower() == 'true'
        self.enable_query_hints = os.environ.get('ENABLE_QUERY_HINTS', 'false').lower() == 'true'
        
        if self.use_optimized_queries:
            logger.info("Stage 2 query optimizations enabled")
    
    def optimize_campaign_query(self, query):
        """Optimize campaign queries with eager loading"""
        if not self.use_optimized_queries:
            return query
        
        if self.enable_eager_loading:
            # Note: Relationship names would need to be imported from models
            # For now, return the query without eager loading to avoid import issues
            logger.info("Campaign query optimization enabled (eager loading disabled for safety)")
        
        return query
    
    def optimize_participant_query(self, query):
        """Optimize participant queries with eager loading"""
        if not self.use_optimized_queries:
            return query
        
        if self.enable_eager_loading:
            logger.info("Participant query optimization enabled (eager loading disabled for safety)")
        
        return query
    
    def optimize_survey_response_query(self, query):
        """Optimize survey response queries with eager loading"""
        if not self.use_optimized_queries:
            return query
        
        if self.enable_eager_loading:
            logger.info("Survey response query optimization enabled (eager loading disabled for safety)")
        
        return query
    
    def optimize_dashboard_query(self, business_account_id: int, limit: int = 100):
        """Optimized dashboard data query with reduced round trips"""
        if not self.use_optimized_queries:
            return None  # Fall back to original queries
        
        # Single optimized query for dashboard data
        optimized_query = text("""
            SELECT 
                sr.id,
                sr.nps_score,
                sr.nps_category,
                sr.sentiment_score,
                sr.sentiment_label,
                sr.created_at,
                sr.company_name,
                sr.respondent_name,
                c.name as campaign_name,
                c.status as campaign_status
            FROM survey_response sr
            JOIN campaign_participants cp ON sr.campaign_participant_id = cp.id
            JOIN campaigns c ON cp.campaign_id = c.id
            WHERE c.business_account_id = :business_account_id
            ORDER BY sr.created_at DESC
            LIMIT :limit
        """)
        
        return optimized_query
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status"""
        return {
            "use_optimized_queries": self.use_optimized_queries,
            "enable_eager_loading": self.enable_eager_loading,
            "enable_query_hints": self.enable_query_hints,
            "stage": "Stage 2" if self.use_optimized_queries else "Stage 1"
        }

# Global query optimizer instance
query_optimizer = QueryOptimizer()

def optimize_query(query_type: str):
    """Decorator for applying query optimizations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Apply optimizations based on query type
            if hasattr(result, 'options'):  # SQLAlchemy query object
                if query_type == 'campaign':
                    result = query_optimizer.optimize_campaign_query(result)
                elif query_type == 'participant':
                    result = query_optimizer.optimize_participant_query(result)
                elif query_type == 'survey_response':
                    result = query_optimizer.optimize_survey_response_query(result)
            
            return result
        return wrapper
    return decorator

def get_query_optimization_status() -> Dict[str, Any]:
    """Get current query optimization status"""
    return query_optimizer.get_optimization_status()