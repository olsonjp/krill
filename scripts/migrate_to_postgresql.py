#!/usr/bin/env python3
"""
Script to migrate data from SQLite to PostgreSQL.

This script helps migrate your existing SQLite database to PostgreSQL.
Make sure to backup your data before running this script.

Usage:
    python scripts/migrate_to_postgresql.py
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Set Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'krill.settings_local')
django.setup()

from django.core.management import call_command
from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError


def check_database_connection():
    """Check if PostgreSQL connection is working."""
    try:
        # Temporarily switch to PostgreSQL
        os.environ['DATABASE_ENGINE'] = 'postgresql'
        
        # Reload Django settings
        django.setup()
        
        # Test connection
        db_conn = connections['default']
        db_conn.cursor()
        print("✓ PostgreSQL connection successful")
        return True
        
    except OperationalError as e:
        print(f"✗ PostgreSQL connection failed: {e}")
        print("Please check your PostgreSQL configuration and environment variables")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def backup_sqlite_data():
    """Create a backup of the SQLite database."""
    sqlite_path = project_root / 'krill' / 'db.sqlite3'
    backup_path = project_root / 'krill' / 'db.sqlite3.backup'
    
    if sqlite_path.exists():
        import shutil
        shutil.copy2(sqlite_path, backup_path)
        print(f"✓ SQLite database backed up to: {backup_path}")
        return True
    else:
        print("✗ SQLite database not found")
        return False


def migrate_to_postgresql():
    """Migrate the database schema to PostgreSQL."""
    try:
        print("Migrating database schema to PostgreSQL...")
        
        # Run migrations
        call_command('migrate', verbosity=2)
        print("✓ Database schema migrated successfully")
        
        # Load fixtures if they exist
        fixtures_dir = project_root / 'tests' / 'fixtures'
        if fixtures_dir.exists():
            for fixture_file in fixtures_dir.glob('*.json'):
                print(f"Loading fixture: {fixture_file.name}")
                call_command('loaddata', str(fixture_file), verbosity=1)
        
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False


def create_superuser():
    """Create a superuser account."""
    try:
        print("Creating superuser account...")
        call_command('createsuperuser', interactive=False)
        print("✓ Superuser created successfully")
        return True
    except Exception as e:
        print(f"✗ Superuser creation failed: {e}")
        return False


def main():
    """Main migration process."""
    print("=== SQLite to PostgreSQL Migration Script ===\n")
    
    # Check PostgreSQL connection
    if not check_database_connection():
        print("\nMigration cannot proceed. Please fix PostgreSQL connection issues.")
        return False
    
    # Backup SQLite data
    if not backup_sqlite_data():
        print("\nMigration cannot proceed. Please ensure SQLite database exists.")
        return False
    
    # Migrate schema
    if not migrate_to_postgresql():
        print("\nMigration failed. Please check the error messages above.")
        return False
    
    # Create superuser
    create_superuser()
    
    print("\n=== Migration Completed Successfully! ===")
    print("\nNext steps:")
    print("1. Test your application with PostgreSQL")
    print("2. Update your environment variables to use PostgreSQL permanently")
    print("3. Remove the SQLite backup when you're confident everything works")
    print("4. Consider setting up regular PostgreSQL backups")
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
