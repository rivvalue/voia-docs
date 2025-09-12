#!/usr/bin/env python3
"""
Data Migration Script: Decoupled Participant Management
=======================================================

This script transforms the existing tightly-coupled participant-campaign structure 
to the new decoupled architecture where:
- Participants exist independently of campaigns
- Campaign-participant associations are managed through CampaignParticipant table
- Each campaign-participant pair has its own token and status

BEFORE RUNNING:
- Backup your database
- Test on a development copy first
- Ensure application is stopped during migration

Usage: python migrate_participants.py
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path so we can import models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db, Participant, CampaignParticipant, Campaign, BusinessAccount
from app import app

def run_migration():
    """Execute the participant decoupling migration"""
    
    print("🔄 Starting Participant Decoupling Migration")
    print("=" * 50)
    
    with app.app_context():
        try:
            # Step 1: Create new tables if they don't exist
            print("\n📋 Step 1: Creating new database tables...")
            db.create_all()
            print("✅ Database tables created/verified")
            
            # Step 2: Analyze existing data
            print("\n📊 Step 2: Analyzing existing participant data...")
            existing_participants = Participant.query.all()
            print(f"Found {len(existing_participants)} existing participant records")
            
            # Group participants by (business_account_id, email) to identify duplicates
            participant_groups = {}
            for participant in existing_participants:
                key = (participant.business_account_id, participant.email)
                if key not in participant_groups:
                    participant_groups[key] = []
                participant_groups[key].append(participant)
            
            total_unique_participants = len(participant_groups)
            total_duplicates = len(existing_participants) - total_unique_participants
            print(f"Unique participants (by email): {total_unique_participants}")
            print(f"Duplicate records to merge: {total_duplicates}")
            
            # Step 3: Migrate participants to new structure
            print(f"\n🔄 Step 3: Migrating participant data...")
            
            migrated_count = 0
            associations_created = 0
            
            for (business_account_id, email), participants in participant_groups.items():
                # Find or create canonical participant record
                canonical_participant = None
                associations_to_create = []
                
                if len(participants) == 1:
                    # No duplicates - use existing participant
                    participant = participants[0]
                    if participant.campaign_id:
                        # Create association record
                        association_data = {
                            'participant_id': participant.id,
                            'campaign_id': participant.campaign_id,
                            'business_account_id': participant.business_account_id,
                            'token': participant.token,
                            'status': participant.status,
                            'created_at': participant.created_at,
                            'invited_at': participant.invited_at,
                            'started_at': participant.started_at,
                            'completed_at': participant.completed_at
                        }
                        associations_to_create.append(association_data)
                        
                        # Clear campaign relationship from participant
                        participant.campaign_id = None
                        participant.token = None  # Token moves to association
                        
                    canonical_participant = participant
                    
                else:
                    # Multiple participants with same email - need to merge
                    print(f"  🔀 Merging {len(participants)} records for {email}")
                    
                    # Use the oldest participant as canonical
                    canonical_participant = min(participants, key=lambda p: p.created_at)
                    duplicates = [p for p in participants if p.id != canonical_participant.id]
                    
                    # Create association records for all campaigns
                    for participant in participants:
                        if participant.campaign_id:
                            association_data = {
                                'participant_id': canonical_participant.id,
                                'campaign_id': participant.campaign_id,
                                'business_account_id': participant.business_account_id,
                                'token': participant.token,
                                'status': participant.status,
                                'created_at': participant.created_at,
                                'invited_at': participant.invited_at,
                                'started_at': participant.started_at,
                                'completed_at': participant.completed_at
                            }
                            associations_to_create.append(association_data)
                    
                    # Clear campaign relationship from canonical participant
                    canonical_participant.campaign_id = None
                    canonical_participant.token = None
                    
                    # Delete duplicate participant records
                    for duplicate in duplicates:
                        print(f"    🗑️  Removing duplicate participant ID {duplicate.id}")
                        db.session.delete(duplicate)
                
                # Create campaign-participant association records
                for assoc_data in associations_to_create:
                    # Check if association already exists
                    existing_assoc = CampaignParticipant.query.filter_by(
                        campaign_id=assoc_data['campaign_id'],
                        participant_id=assoc_data['participant_id']
                    ).first()
                    
                    if not existing_assoc:
                        campaign_participant = CampaignParticipant(**assoc_data)
                        db.session.add(campaign_participant)
                        associations_created += 1
                        print(f"    ✅ Created association: Participant {assoc_data['participant_id']} → Campaign {assoc_data['campaign_id']}")
                
                migrated_count += 1
                
                # Commit every 10 participants to avoid large transactions
                if migrated_count % 10 == 0:
                    db.session.commit()
                    print(f"  💾 Committed batch (processed {migrated_count}/{total_unique_participants})")
            
            # Final commit
            db.session.commit()
            print(f"\n✅ Migration completed successfully!")
            print(f"   📊 Migrated {migrated_count} unique participants")
            print(f"   🔗 Created {associations_created} campaign-participant associations")
            
            # Step 4: Validation
            print(f"\n🔍 Step 4: Validating migration results...")
            
            final_participants = Participant.query.count()
            final_associations = CampaignParticipant.query.count()
            
            print(f"   Participants after migration: {final_participants}")
            print(f"   Campaign associations created: {final_associations}")
            
            # Check for orphaned records
            participants_with_campaigns = Participant.query.filter(
                Participant.campaign_id.isnot(None)
            ).count()
            
            participants_with_tokens = Participant.query.filter(
                Participant.token.isnot(None)
            ).count()
            
            if participants_with_campaigns > 0:
                print(f"   ⚠️  WARNING: {participants_with_campaigns} participants still have campaign_id")
            else:
                print("   ✅ All participants properly decoupled from campaigns")
                
            if participants_with_tokens > 0:
                print(f"   ⚠️  WARNING: {participants_with_tokens} participants still have tokens")
            else:
                print("   ✅ All tokens moved to campaign associations")
            
            print(f"\n🎉 Migration Summary:")
            print(f"   • Transformed {len(existing_participants)} → {final_participants} participants")
            print(f"   • Created {final_associations} campaign-participant associations")
            print(f"   • Each participant can now be reused across multiple campaigns")
            print(f"   • Campaign-specific data (tokens, status) moved to associations")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            print("Rolling back changes...")
            db.session.rollback()
            raise e

def verify_migration():
    """Verify the migration was successful"""
    print("\n🔍 Verification Checks:")
    print("-" * 30)
    
    with app.app_context():
        # Check 1: No participants should have campaign_id or token
        participants_with_campaign = Participant.query.filter(
            Participant.campaign_id.isnot(None)
        ).count()
        
        participants_with_token = Participant.query.filter(
            Participant.token.isnot(None)
        ).count()
        
        if participants_with_campaign == 0 and participants_with_token == 0:
            print("✅ All participants properly decoupled")
        else:
            print(f"❌ Found {participants_with_campaign} participants with campaign_id")
            print(f"❌ Found {participants_with_token} participants with token")
        
        # Check 2: All associations should have tokens
        associations_without_token = CampaignParticipant.query.filter(
            CampaignParticipant.token.is_(None)
        ).count()
        
        if associations_without_token == 0:
            print("✅ All campaign associations have tokens")
        else:
            print(f"❌ Found {associations_without_token} associations without tokens")
        
        # Check 3: No duplicate associations
        total_associations = CampaignParticipant.query.count()
        unique_associations = CampaignParticipant.query.with_entities(
            CampaignParticipant.campaign_id, 
            CampaignParticipant.participant_id
        ).distinct().count()
        
        if total_associations == unique_associations:
            print("✅ No duplicate campaign-participant associations")
        else:
            print(f"❌ Found duplicate associations: {total_associations - unique_associations}")

if __name__ == "__main__":
    print("Participant Decoupling Migration")
    print("================================")
    print("This will transform your participant data structure.")
    print("Make sure you have backed up your database!\n")
    
    response = input("Continue with migration? (yes/no): ").lower().strip()
    if response in ['yes', 'y']:
        run_migration()
        verify_migration()
        print("\n✅ Migration completed! You can now restart your application.")
    else:
        print("Migration cancelled.")