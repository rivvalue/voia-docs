import os
from typing import Dict, Any, Optional

class DatabaseConfig:
    """Database configuration for multi-environment support (demo/production)"""
    
    def __init__(self):
        self.demo_database_url = os.environ.get("DATABASE_URL", "sqlite:///voc_agent.db")
        self.prod_database_url = os.environ.get("PROD_DATABASE_URL", self.demo_database_url)
        
        # Default to demo environment for Phase 1 safety
        self.current_environment = "demo"
        
    def get_database_url(self, environment: Optional[str] = None) -> str:
        """Get database URL for specified environment"""
        env = environment if environment is not None else self.current_environment
            
        if env == "production":
            return self.prod_database_url
        else:
            return self.demo_database_url
    
    def get_engine_options(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """Get SQLAlchemy engine options optimized for environment"""
        env = environment if environment is not None else self.current_environment
            
        if env == "production":
            return {
                "pool_recycle": 300,
                "pool_pre_ping": True,
                "pool_size": 30,  # Higher pool size for production
                "max_overflow": 70,
                "pool_timeout": 30,
            }
        else:
            return {
                "pool_recycle": 300,
                "pool_pre_ping": True,
                "pool_size": 20,
                "max_overflow": 50,
                "pool_timeout": 30,
            }
    
    def set_environment(self, environment: str):
        """Set current environment (demo/production)"""
        if environment in ["demo", "production"]:
            self.current_environment = environment
        else:
            raise ValueError(f"Invalid environment: {environment}. Must be 'demo' or 'production'")
    
    def is_production_environment(self) -> bool:
        """Check if currently in production environment"""
        return self.current_environment == "production"
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get current environment information"""
        return {
            "current_environment": self.current_environment,
            "demo_database_configured": bool(self.demo_database_url),
            "prod_database_configured": bool(self.prod_database_url and 
                                           self.prod_database_url != self.demo_database_url),
            "database_url": self.get_database_url(),
        }

# Global database configuration instance
db_config = DatabaseConfig()