"""
Database Checkpoint Manager for VOÏA Phase 2b
Provides checkpoint metadata tracking for use with Replit's rollback system

NOTE: This utility creates checkpoint metadata only.
For actual database backup/restore, use Replit's built-in rollback feature:
- Checkpoints are created automatically during development
- Access via Replit UI: Tools > Rollback
- Restores code, files, AND database together
"""

import os
import logging
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class CheckpointManager:
    """Manages checkpoint metadata for VOÏA Phase 2b development"""
    
    CHECKPOINT_DIR = Path("checkpoints")
    
    def __init__(self):
        self.CHECKPOINT_DIR.mkdir(exist_ok=True)
    
    def create_checkpoint(self, checkpoint_name, description=None, tags=None):
        """
        Create a checkpoint metadata record
        
        Args:
            checkpoint_name: Descriptive name for this checkpoint
            description: Detailed description of what this checkpoint represents
            tags: List of tags for categorization (e.g., ['phase2b', 'pre-migration'])
            
        Returns:
            dict: Checkpoint metadata
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Sanitize checkpoint name
        checkpoint_name = "".join(c if c.isalnum() or c in '_-' else '_' for c in checkpoint_name)
        
        metadata_file = self.CHECKPOINT_DIR / f"{checkpoint_name}_{timestamp}.json"
        
        metadata = {
            'checkpoint_name': checkpoint_name,
            'timestamp': timestamp,
            'datetime': datetime.now().isoformat(),
            'description': description or "Manual checkpoint",
            'tags': tags or [],
            'replit_rollback_instructions': (
                "To restore to this checkpoint:\n"
                "1. Open Replit UI\n"
                "2. Click Tools > Rollback\n"
                f"3. Find checkpoint near: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"4. Description should mention: {description or checkpoint_name}\n"
                "5. Click 'Rollback' to restore code, files, and database"
            )
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ Checkpoint metadata created: {checkpoint_name}")
        logger.info(f"   Description: {description}")
        logger.info(f"   Tags: {tags or 'none'}")
        logger.info(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"\n   💡 Use Replit Rollback feature to restore this checkpoint")
        
        return metadata
    
    def list_checkpoints(self, tag_filter=None):
        """
        List all checkpoint metadata records
        
        Args:
            tag_filter: Optional tag to filter by
            
        Returns:
            list: List of checkpoint metadata dicts
        """
        checkpoints = []
        
        for metadata_file in sorted(self.CHECKPOINT_DIR.glob("*.json"), reverse=True):
            with open(metadata_file, 'r') as f:
                checkpoint = json.load(f)
                
                # Apply tag filter if specified
                if tag_filter and tag_filter not in checkpoint.get('tags', []):
                    continue
                
                checkpoints.append(checkpoint)
        
        return checkpoints
    
    def get_checkpoint(self, checkpoint_name):
        """Get metadata for a specific checkpoint"""
        # Find most recent matching checkpoint
        matches = list(self.CHECKPOINT_DIR.glob(f"{checkpoint_name}_*.json"))
        
        if not matches:
            return None
        
        # Sort by timestamp (newest first)
        latest = sorted(matches, reverse=True)[0]
        
        with open(latest, 'r') as f:
            return json.load(f)


# CLI utility for checkpoint management
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    manager = CheckpointManager()
    
    if len(sys.argv) < 2:
        print("""
VOÏA Checkpoint Manager - Phase 2b Development

This utility creates checkpoint metadata for use with Replit's rollback system.

Usage:
  python backup_utils.py checkpoint <name> [description] [--tag TAG]
  python backup_utils.py list [--tag TAG]
  python backup_utils.py show <name>

Examples:
  # Create Phase 2b pre-migration checkpoint
  python backup_utils.py checkpoint "pre_sidebar_migration" "Before sidebar navigation work" --tag phase2b

  # List all Phase 2b checkpoints
  python backup_utils.py list --tag phase2b

  # Show specific checkpoint details
  python backup_utils.py show "pre_sidebar_migration"

Note: For actual rollback, use Replit UI: Tools > Rollback
""")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "checkpoint":
        if len(sys.argv) < 3:
            print("Error: checkpoint name required")
            sys.exit(1)
        
        name = sys.argv[2]
        description = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else None
        
        # Extract tags
        tags = []
        for i, arg in enumerate(sys.argv):
            if arg == '--tag' and i + 1 < len(sys.argv):
                tags.append(sys.argv[i + 1])
        
        metadata = manager.create_checkpoint(name, description, tags)
        
        print(f"\n📍 Checkpoint Created")
        print(f"   Name: {metadata['checkpoint_name']}")
        print(f"   Time: {metadata['datetime']}")
        print(f"   Tags: {', '.join(metadata['tags']) if metadata['tags'] else 'none'}")
        print(f"\n💡 To restore: Use Replit UI > Tools > Rollback")
        
    elif command == "list":
        # Extract tag filter
        tag_filter = None
        for i, arg in enumerate(sys.argv):
            if arg == '--tag' and i + 1 < len(sys.argv):
                tag_filter = sys.argv[i + 1]
        
        checkpoints = manager.list_checkpoints(tag_filter)
        
        if checkpoints:
            filter_msg = f" (filtered by tag: {tag_filter})" if tag_filter else ""
            print(f"\n📦 Checkpoints{filter_msg}:\n")
            for checkpoint in checkpoints:
                print(f"  • {checkpoint['checkpoint_name']}")
                print(f"    Time: {checkpoint['datetime']}")
                print(f"    Desc: {checkpoint.get('description', 'N/A')}")
                print(f"    Tags: {', '.join(checkpoint.get('tags', [])) if checkpoint.get('tags') else 'none'}")
                print()
        else:
            filter_msg = f" with tag '{tag_filter}'" if tag_filter else ""
            print(f"\nNo checkpoints found{filter_msg}")
    
    elif command == "show":
        if len(sys.argv) < 3:
            print("Error: checkpoint name required")
            sys.exit(1)
        
        name = sys.argv[2]
        checkpoint = manager.get_checkpoint(name)
        
        if checkpoint:
            print(f"\n📍 Checkpoint: {checkpoint['checkpoint_name']}")
            print(f"   Created: {checkpoint['datetime']}")
            print(f"   Description: {checkpoint.get('description', 'N/A')}")
            print(f"   Tags: {', '.join(checkpoint.get('tags', [])) if checkpoint.get('tags') else 'none'}")
            print(f"\n{checkpoint.get('replit_rollback_instructions', 'No rollback instructions')}")
        else:
            print(f"\n❌ Checkpoint not found: {name}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
