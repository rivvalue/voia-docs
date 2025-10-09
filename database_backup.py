"""
SQLAlchemy-based Database Backup for VOÏA Phase 2b
Exports/imports database tables as JSON for version-safe backup/restore

⚠️ IMPORTANT LIMITATIONS:
1. EXPERIMENTAL - Not recommended as primary backup for Phase 2b
2. Sequence reset requires manual intervention in some environments
3. FK constraint handling may require superuser privileges
4. Complex types (Decimal, UUID, Binary) use string conversion
5. Does NOT backup code or files (database only)

RECOMMENDED: Use Replit's built-in rollback for Phase 2b safety.
Use this tool only for database-only snapshots or data export.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy import inspect, MetaData, Table
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class DatabaseBackup:
    """SQLAlchemy-based database backup (version-safe)"""
    
    BACKUP_DIR = Path("backups")
    
    def __init__(self, db_engine):
        """
        Initialize with SQLAlchemy engine
        
        Args:
            db_engine: SQLAlchemy engine instance
        """
        self.engine = db_engine
        self.BACKUP_DIR.mkdir(exist_ok=True)
    
    def create_backup(self, backup_name=None, description=None, tables=None):
        """
        Export database tables to JSON
        
        Args:
            backup_name: Custom backup name (default: timestamp)
            description: Backup description
            tables: List of table names to backup (default: all tables)
            
        Returns:
            dict: Backup metadata
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = backup_name or f"voïa_backup_{timestamp}"
        backup_name = "".join(c if c.isalnum() or c in '_-' else '_' for c in backup_name)
        
        backup_file = self.BACKUP_DIR / f"{backup_name}.json"
        metadata_file = self.BACKUP_DIR / f"{backup_name}_meta.json"
        
        try:
            logger.info(f"Creating database backup: {backup_file}")
            
            # Reflect database schema
            metadata = MetaData()
            metadata.reflect(bind=self.engine)
            
            # Determine tables to backup
            if tables:
                table_names = tables
            else:
                table_names = metadata.tables.keys()
            
            backup_data = {
                'timestamp': timestamp,
                'datetime': datetime.now().isoformat(),
                'tables': {}
            }
            
            # Export each table
            with Session(self.engine) as session:
                for table_name in table_names:
                    if table_name not in metadata.tables:
                        logger.warning(f"Table {table_name} not found, skipping")
                        continue
                    
                    table = metadata.tables[table_name]
                    logger.info(f"  Exporting table: {table_name}")
                    
                    # Query all rows
                    rows = session.execute(table.select()).fetchall()
                    
                    # Convert rows to dicts
                    row_dicts = []
                    for row in rows:
                        row_dict = {}
                        for key in row._mapping.keys():
                            value = row._mapping[key]
                            # Handle datetime and other non-JSON types
                            if isinstance(value, datetime):
                                value = value.isoformat()
                            elif hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, type(None))):
                                value = str(value)
                            row_dict[key] = value
                        row_dicts.append(row_dict)
                    
                    backup_data['tables'][table_name] = {
                        'row_count': len(row_dicts),
                        'columns': [col.name for col in table.columns],
                        'data': row_dicts
                    }
                    
                    logger.info(f"    ✓ {len(row_dicts)} rows exported")
            
            # Write backup file
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            # Create metadata
            metadata_info = {
                'backup_name': backup_name,
                'timestamp': timestamp,
                'datetime': datetime.now().isoformat(),
                'description': description or "SQLAlchemy JSON backup",
                'file_path': str(backup_file),
                'file_size_bytes': backup_file.stat().st_size,
                'table_count': len(backup_data['tables']),
                'total_rows': sum(t['row_count'] for t in backup_data['tables'].values()),
                'tables': list(backup_data['tables'].keys())
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata_info, f, indent=2)
            
            logger.info(f"✅ Backup created: {backup_file}")
            logger.info(f"   Tables: {metadata_info['table_count']}, Rows: {metadata_info['total_rows']}")
            logger.info(f"   Size: {metadata_info['file_size_bytes'] / 1024 / 1024:.2f} MB")
            
            return metadata_info
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            # Cleanup partial files
            if backup_file.exists():
                backup_file.unlink()
            if metadata_file.exists():
                metadata_file.unlink()
            raise
    
    def restore_backup(self, backup_name, confirm=False, truncate=True):
        """
        ⚠️ DISABLED: Restore functionality has critical safety issues.
        Use Replit's built-in rollback for safe database restoration.
        
        This function is disabled to prevent data corruption. Issues include:
        - FK constraint handling requires superuser privileges
        - Sequence reset may fail
        - Type conversion issues with complex data types
        - Not exception-safe (can leave DB in corrupted state)
        
        For Phase 2b: Use Replit UI > Tools > Rollback
        """
        raise NotImplementedError(
            "⚠️ Database restore is DISABLED due to safety concerns.\n\n"
            "For Phase 2b rollback, use Replit's built-in rollback:\n"
            "1. Open Replit UI\n"
            "2. Click Tools > Rollback\n"
            "3. Select checkpoint to restore\n\n"
            "This ensures safe restoration of code, files, and database."
        )
        
        try:
            # Load backup data
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            # Load metadata for logging
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            
            logger.warning(f"⚠️  RESTORING DATABASE from: {backup_name}")
            logger.warning(f"    Created: {metadata.get('datetime', 'unknown')}")
            logger.warning(f"    Tables: {metadata.get('table_count', '?')}")
            logger.warning(f"    Total rows: {metadata.get('total_rows', '?')}")
            
            # Reflect current schema
            db_metadata = MetaData()
            db_metadata.reflect(bind=self.engine)
            
            stats = {'tables_restored': 0, 'rows_inserted': 0}
            
            with Session(self.engine) as session:
                # Disable foreign key checks temporarily (PostgreSQL)
                if 'postgresql' in str(self.engine.url):
                    session.execute("SET session_replication_role = 'replica';")
                    logger.info("  Disabled foreign key checks for restore")
                
                # Restore each table
                for table_name, table_data in backup_data['tables'].items():
                    if table_name not in db_metadata.tables:
                        logger.warning(f"Table {table_name} not in current schema, skipping")
                        continue
                    
                    table = db_metadata.tables[table_name]
                    logger.info(f"  Restoring table: {table_name}")
                    
                    # Truncate table if requested
                    if truncate:
                        session.execute(table.delete())
                        logger.info(f"    Truncated existing data")
                    
                    # Insert rows
                    if table_data['data']:
                        session.execute(table.insert(), table_data['data'])
                        logger.info(f"    ✓ Inserted {len(table_data['data'])} rows")
                        stats['rows_inserted'] += len(table_data['data'])
                        
                        # Reset auto-increment sequences for PostgreSQL
                        if 'postgresql' in str(self.engine.url):
                            # Find primary key column(s)
                            pk_cols = [col for col in table.columns if col.primary_key]
                            for pk_col in pk_cols:
                                # Check if column has a sequence
                                if pk_col.autoincrement:
                                    sequence_name = f"{table_name}_{pk_col.name}_seq"
                                    max_id_query = f"SELECT COALESCE(MAX({pk_col.name}), 0) FROM {table_name}"
                                    max_id = session.execute(max_id_query).scalar()
                                    reset_seq_query = f"SELECT setval('{sequence_name}', {max_id + 1}, false)"
                                    try:
                                        session.execute(reset_seq_query)
                                        logger.info(f"    ✓ Reset sequence {sequence_name} to {max_id + 1}")
                                    except Exception as e:
                                        logger.warning(f"    Sequence reset failed (may not exist): {e}")
                    
                    stats['tables_restored'] += 1
                
                # Re-enable foreign key checks
                if 'postgresql' in str(self.engine.url):
                    session.execute("SET session_replication_role = 'origin';")
                    logger.info("  Re-enabled foreign key checks")
                
                # Commit transaction
                session.commit()
            
            logger.info(f"✅ Restore complete: {stats['tables_restored']} tables, {stats['rows_inserted']} rows")
            return stats
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise
    
    def list_backups(self):
        """List all available backups"""
        backups = []
        
        for meta_file in sorted(self.BACKUP_DIR.glob("*_meta.json"), reverse=True):
            with open(meta_file, 'r') as f:
                backups.append(json.load(f))
        
        return backups
    
    def delete_backup(self, backup_name, confirm=False):
        """Delete a backup"""
        if not confirm:
            raise ValueError("Must set confirm=True to delete")
        
        backup_file = self.BACKUP_DIR / f"{backup_name}.json"
        metadata_file = self.BACKUP_DIR / f"{backup_name}_meta.json"
        
        deleted = []
        if backup_file.exists():
            backup_file.unlink()
            deleted.append(str(backup_file))
        if metadata_file.exists():
            metadata_file.unlink()
            deleted.append(str(metadata_file))
        
        if deleted:
            logger.info(f"Deleted: {', '.join(deleted)}")
            return True
        return False


# CLI utility
if __name__ == "__main__":
    import sys
    from app import app, db
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    # Create backup manager and run commands within application context
    with app.app_context():
        backup_mgr = DatabaseBackup(db.engine)
        
        if len(sys.argv) < 2:
            print("""
VOÏA Database Backup (Export Only - Restore DISABLED)

⚠️ For database restoration, use Replit UI > Tools > Rollback

Usage:
  python database_backup.py backup [name] [description]  - Export database to JSON
  python database_backup.py list                         - List available backups
  python database_backup.py delete <name> --confirm      - Delete a backup

Examples:
  python database_backup.py backup "pre_phase2b" "Before sidebar migration"
  python database_backup.py list

Note: Restore functionality is disabled due to safety concerns.
Use Replit's built-in rollback for safe database restoration.
""")
            sys.exit(1)
        
        command = sys.argv[1]
        
        if command == "backup":
            name = sys.argv[2] if len(sys.argv) > 2 else None
            desc = sys.argv[3] if len(sys.argv) > 3 else None
            result = backup_mgr.create_backup(backup_name=name, description=desc)
            print(f"\n✅ Backup: {result['file_path']}")
            print(f"   Tables: {result['table_count']}, Rows: {result['total_rows']}")
            print(f"\n💡 To restore: Use Replit UI > Tools > Rollback")
            
        elif command == "restore":
            print("\n⚠️  Database restore is DISABLED for safety.")
            print("\nFor Phase 2b rollback, use Replit's built-in rollback:")
            print("1. Open Replit UI")
            print("2. Click Tools > Rollback")
            print("3. Select checkpoint to restore")
            print("\nThis ensures safe restoration of code, files, and database.")
            sys.exit(1)
            
        elif command == "list":
            backups = backup_mgr.list_backups()
            if backups:
                print(f"\n📦 Backups ({len(backups)}):\n")
                for backup in backups:
                    size_mb = backup['file_size_bytes'] / (1024 * 1024)
                    print(f"  • {backup['backup_name']}")
                    print(f"    Date: {backup['datetime']}")
                    print(f"    Tables: {backup['table_count']}, Rows: {backup['total_rows']}")
                    print(f"    Size: {size_mb:.2f} MB")
                    print(f"    Desc: {backup.get('description', 'N/A')}")
                    print()
            else:
                print("\nNo backups found")
        
        elif command == "delete":
            if len(sys.argv) < 3:
                print("Error: backup name required")
                sys.exit(1)
            
            name = sys.argv[2]
            confirm = '--confirm' in sys.argv
            
            if not confirm:
                print("\n⚠️  WARNING: This will delete the backup!")
                print("Add --confirm to proceed")
                sys.exit(1)
            
            backup_mgr.delete_backup(name, confirm=True)
            print(f"\n✅ Deleted: {name}")
        
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
