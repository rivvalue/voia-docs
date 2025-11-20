"""
Database Migration: Add Inheritance Flags to Campaign Model

This migration adds three boolean fields to track whether campaigns inherit
survey settings from their business account or use campaign-specific overrides:
- use_business_topics
- use_business_controls  
- use_business_product_focus

All fields default to True (inherit mode).
"""

from app import app, db
from models import Campaign
from sqlalchemy import text

def migrate():
    """Add inheritance flag columns to campaigns table"""
    with app.app_context():
        print("Starting migration: Add inheritance flags to campaigns...")
        
        # Add the new columns with default values
        try:
            with db.engine.connect() as conn:
                # Add use_business_topics column
                conn.execute(text("""
                    ALTER TABLE campaigns 
                    ADD COLUMN IF NOT EXISTS use_business_topics BOOLEAN NOT NULL DEFAULT TRUE
                """))
                conn.commit()
                print("✓ Added use_business_topics column")
                
                # Add use_business_controls column
                conn.execute(text("""
                    ALTER TABLE campaigns 
                    ADD COLUMN IF NOT EXISTS use_business_controls BOOLEAN NOT NULL DEFAULT TRUE
                """))
                conn.commit()
                print("✓ Added use_business_controls column")
                
                # Add use_business_product_focus column
                conn.execute(text("""
                    ALTER TABLE campaigns 
                    ADD COLUMN IF NOT EXISTS use_business_product_focus BOOLEAN NOT NULL DEFAULT TRUE
                """))
                conn.commit()
                print("✓ Added use_business_product_focus column")
                
            print("Migration completed successfully!")
            print("All campaigns now default to inheriting survey settings from business account.")
            
        except Exception as e:
            print(f"Migration failed: {str(e)}")
            raise

if __name__ == "__main__":
    migrate()
