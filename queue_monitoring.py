"""
Queue monitoring and health check utilities for VOÏA platform.

Provides health check endpoints and metrics for both in-memory and PostgreSQL queues.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import text
from app import db

logger = logging.getLogger(__name__)


def get_queue_health():
    """
    Get comprehensive queue health metrics.
    
    Works with both in-memory and PostgreSQL queues.
    
    Returns:
        Dict with health metrics and status
    """
    try:
        from task_queue import get_queue_stats
        from queue_config import queue_config
        
        # Get basic queue stats
        stats = get_queue_stats()
        
        # Add queue type and configuration
        stats['queue_configuration'] = queue_config.get_config_summary()
        
        # If PostgreSQL queue, add detailed metrics
        if queue_config.is_postgres_enabled():
            pg_metrics = get_postgresql_queue_metrics()
            stats['postgresql_metrics'] = pg_metrics
        
        # Determine overall health status (check critical threshold first)
        queue_size = stats.get('queue_size', 0)
        if queue_size > 500:
            stats['health_status'] = 'critical'
            stats['health_message'] = f'Critical queue backlog: {queue_size} tasks pending'
        elif queue_size > 100:
            stats['health_status'] = 'warning'
            stats['health_message'] = f'Queue backlog: {queue_size} tasks pending'
        else:
            stats['health_status'] = 'healthy'
            stats['health_message'] = 'Queue operating normally'
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting queue health: {e}")
        return {
            'health_status': 'error',
            'health_message': f'Failed to retrieve queue health: {str(e)}',
            'error': str(e)
        }


def get_postgresql_queue_metrics():
    """
    Get detailed PostgreSQL queue metrics.
    
    Returns:
        Dict with PostgreSQL-specific metrics
    """
    try:
        # Task counts by status (last 24 hours)
        result = db.session.execute(
            text("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    AVG(EXTRACT(EPOCH FROM (COALESCE(completed_at, NOW()) - created_at))) as avg_duration_seconds
                FROM task_queue
                WHERE created_at > NOW() - INTERVAL '24 hours'
                GROUP BY status
            """)
        )
        
        status_metrics = {}
        for row in result.fetchall():
            status_metrics[row[0]] = {
                'count': row[1],
                'avg_duration_seconds': round(row[2], 2) if row[2] else None
            }
        
        # Task type breakdown (last 24 hours)
        result = db.session.execute(
            text("""
                SELECT 
                    task_type,
                    COUNT(*) as total,
                    SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
                    AVG(CASE WHEN status='completed' THEN EXTRACT(EPOCH FROM (completed_at - started_at)) END) as avg_processing_time
                FROM task_queue
                WHERE created_at > NOW() - INTERVAL '24 hours'
                GROUP BY task_type
            """)
        )
        
        task_type_metrics = {}
        for row in result.fetchall():
            task_type_metrics[row[0]] = {
                'total': row[1],
                'completed': row[2],
                'failed': row[3],
                'avg_processing_time_seconds': round(row[4], 2) if row[4] else None,
                'success_rate': round((row[2] / row[1]) * 100, 1) if row[1] > 0 else 0
            }
        
        # Stuck tasks (processing > 5 minutes)
        result = db.session.execute(
            text("""
                SELECT 
                    id,
                    task_type,
                    claimed_by,
                    EXTRACT(EPOCH FROM (NOW() - started_at)) as processing_seconds
                FROM task_queue
                WHERE status = 'processing'
                  AND started_at < NOW() - INTERVAL '5 minutes'
                ORDER BY started_at ASC
                LIMIT 10
            """)
        )
        
        stuck_tasks = []
        for row in result.fetchall():
            stuck_tasks.append({
                'id': row[0],
                'task_type': row[1],
                'claimed_by': row[2],
                'processing_seconds': round(row[3], 0)
            })
        
        # Queue age metrics
        result = db.session.execute(
            text("""
                SELECT 
                    MIN(created_at) as oldest_task,
                    MAX(created_at) as newest_task,
                    AVG(EXTRACT(EPOCH FROM (NOW() - created_at))) as avg_age_seconds
                FROM task_queue
                WHERE status = 'pending'
            """)
        ).fetchone()
        
        queue_age = {
            'oldest_task': result[0].isoformat() if result[0] else None,
            'newest_task': result[1].isoformat() if result[1] else None,
            'avg_age_seconds': round(result[2], 2) if result[2] else 0
        }
        
        return {
            'status_metrics': status_metrics,
            'task_type_metrics': task_type_metrics,
            'stuck_tasks': stuck_tasks,
            'stuck_tasks_count': len(stuck_tasks),
            'queue_age': queue_age
        }
        
    except Exception as e:
        logger.error(f"Error getting PostgreSQL queue metrics: {e}")
        return {
            'error': str(e)
        }


def get_queue_depth_by_business_account():
    """
    Get queue depth breakdown by business account (PostgreSQL only).
    
    Returns:
        List of business accounts with pending task counts
    """
    try:
        from queue_config import queue_config
        
        if not queue_config.is_postgres_enabled():
            return {'error': 'Only available with PostgreSQL queue'}
        
        result = db.session.execute(
            text("""
                SELECT 
                    ba.id,
                    ba.name,
                    COUNT(*) as pending_tasks
                FROM task_queue tq
                JOIN business_accounts ba ON tq.business_account_id = ba.id
                WHERE tq.status = 'pending'
                GROUP BY ba.id, ba.name
                ORDER BY pending_tasks DESC
            """)
        )
        
        accounts = []
        for row in result.fetchall():
            accounts.append({
                'business_account_id': row[0],
                'business_account_name': row[1],
                'pending_tasks': row[2]
            })
        
        return accounts
        
    except Exception as e:
        logger.error(f"Error getting queue depth by business account: {e}")
        return {'error': str(e)}


def cleanup_old_postgresql_tasks():
    """
    Clean up old completed and failed tasks from PostgreSQL queue.
    
    - Completed tasks: kept for 7 days
    - Failed tasks: kept for 30 days
    
    Returns:
        Dict with cleanup results
    """
    try:
        from queue_config import queue_config
        
        if not queue_config.is_postgres_enabled():
            return {'error': 'Only available with PostgreSQL queue'}
        
        # Import cleanup function
        from postgres_task_queue import cleanup_old_tasks
        result = cleanup_old_tasks()
        
        if result:
            return {
                'success': True,
                'completed_deleted': result['completed_deleted'],
                'failed_deleted': result['failed_deleted'],
                'total_deleted': result['completed_deleted'] + result['failed_deleted']
            }
        else:
            return {
                'success': False,
                'error': 'Cleanup failed'
            }
        
    except Exception as e:
        logger.error(f"Error cleaning up old tasks: {e}")
        return {
            'success': False,
            'error': str(e)
        }
