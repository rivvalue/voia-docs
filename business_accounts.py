from app import db
from models import BusinessAccount, Campaign
from database_config import db_config
from datetime import datetime
from typing import Optional, List, Dict, Any

class BusinessAccountManager:
    """Manages business accounts for multi-tenant participant system"""
    
    def __init__(self):
        self.db_config = db_config
        
    def create_rivvalue_demo_account(self) -> BusinessAccount:
        """Create the default Rivvalue Inc business account for demo content"""
        existing = self.get_business_account_by_name("Rivvalue Inc")
        if existing:
            return existing
            
        rivvalue_account = BusinessAccount(
            name="Rivvalue Inc",
            account_type="demo",
            contact_email="7amdoulilah@rivvalue.com",
            contact_name="Rivvalue Team",
            status="active"
        )
        
        db.session.add(rivvalue_account)
        db.session.commit()
        
        return rivvalue_account
    
    def get_business_account_by_name(self, name: str) -> Optional[BusinessAccount]:
        """Get business account by name"""
        return BusinessAccount.query.filter_by(name=name).first()
    
    def get_business_account_by_id(self, account_id: int) -> Optional[BusinessAccount]:
        """Get business account by ID"""
        return BusinessAccount.query.get(account_id)
    
    def create_business_account(self, name: str, account_type: str = "customer", 
                              contact_email: str = None, contact_name: str = None) -> BusinessAccount:
        """Create a new business account"""
        account = BusinessAccount(
            name=name,
            account_type=account_type,
            contact_email=contact_email,
            contact_name=contact_name,
            status="active"
        )
        
        db.session.add(account)
        db.session.commit()
        
        return account
    
    def list_business_accounts(self, account_type: str = None) -> List[BusinessAccount]:
        """List all business accounts, optionally filtered by type"""
        query = BusinessAccount.query
        
        if account_type:
            query = query.filter_by(account_type=account_type)
            
        return query.order_by(BusinessAccount.created_at.desc()).all()
    
    def get_demo_environment_info(self) -> Dict[str, Any]:
        """Get information about demo environment setup"""
        rivvalue_account = self.get_business_account_by_name("Rivvalue Inc")
        
        # Count existing campaigns (will be linked to Rivvalue account in later phases)
        total_campaigns = Campaign.query.count()
        
        return {
            "rivvalue_account_exists": rivvalue_account is not None,
            "rivvalue_account_id": rivvalue_account.id if rivvalue_account else None,
            "demo_campaigns_count": total_campaigns,
            "database_environment": self.db_config.current_environment,
            "database_url": self.db_config.get_database_url(),
            "ready_for_phase_2": rivvalue_account is not None
        }
    
    def ensure_demo_setup(self) -> Dict[str, Any]:
        """Ensure demo environment is properly set up"""
        # Create Rivvalue account if it doesn't exist
        rivvalue_account = self.create_rivvalue_demo_account()
        
        return {
            "rivvalue_account_created": True,
            "account_id": rivvalue_account.id,
            "account_name": rivvalue_account.name,
            "account_type": rivvalue_account.account_type,
            "setup_complete": True
        }

# Global business account manager instance
business_account_manager = BusinessAccountManager()