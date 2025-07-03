from app import db
from datetime import datetime
import json

class AuthToken(db.Model):
    """Store authentication tokens for audit and revocation"""
    __tablename__ = 'auth_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), nullable=False, index=True)
    token_id = db.Column(db.String(32), nullable=False, unique=True, index=True)  # JWT ID
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    
    def is_valid(self):
        """Check if token is still valid"""
        if self.revoked_at:
            return False
        return datetime.utcnow() < self.expires_at
    
    def revoke(self):
        """Revoke the token"""
        self.revoked_at = datetime.utcnow()
    
    def update_usage(self, ip_address=None, user_agent=None):
        """Update last used timestamp and metadata"""
        self.last_used_at = datetime.utcnow()
        if ip_address:
            self.ip_address = ip_address
        if user_agent:
            self.user_agent = user_agent
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'token_id': self.token_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'is_valid': self.is_valid()
        }