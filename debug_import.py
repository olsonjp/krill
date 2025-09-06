#!/usr/bin/env python3
"""
Debug script for data import functionality.
This script helps test the import process outside of the web interface.
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / 'krill'))

# Set Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'krill.settings_production')
django.setup()

from django.core.management import call_command
from django.conf import settings
import json
import tempfile
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_temp_directory():
    """Test if we can write to the temp directory"""
    temp_dir = getattr(settings, 'FILE_UPLOAD_TEMP_DIR', '/tmp')
    print(f"Testing temp directory: {temp_dir}")

    try:
        os.makedirs(temp_dir, exist_ok=True)
        test_file = os.path.join(temp_dir, 'test_write.tmp')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        print(f"✓ Temp directory {temp_dir} is writable")
        return True
    except Exception as e:
        print(f"✗ Temp directory {temp_dir} is not writable: {e}")
        return False

def test_loaddata_command():
    """Test if Django's loaddata command works"""
    print("\nTesting Django loaddata command...")

    # Create a simple test fixture
    test_fixture = [
        {
            "model": "sample.source",
            "pk": 9999,
            "fields": {
                "name": "Test Source",
                "description": "Test description"
            }
        }
    ]

    try:
        # Use Django's temp directory
        temp_dir = getattr(settings, 'FILE_UPLOAD_TEMP_DIR', '/tmp')
        os.makedirs(temp_dir, exist_ok=True)

        # Create temporary fixture file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', dir=temp_dir, delete=False) as f:
            json.dump(test_fixture, f, indent=2)
            fixture_path = f.name

        print(f"Created test fixture: {fixture_path}")

        # Test loaddata command
        try:
            call_command('loaddata', fixture_path, verbosity=2)
            print("✓ loaddata command executed successfully")

            # Clean up
            os.remove(fixture_path)
            return True

        except Exception as e:
            print(f"✗ loaddata command failed: {e}")
            # Clean up
            if os.path.exists(fixture_path):
                os.remove(fixture_path)
            return False

    except Exception as e:
        print(f"✗ Failed to create test fixture: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    print("\nTesting database connection...")

    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result[0] == 1:
                print("✓ Database connection successful")
                return True
            else:
                print("✗ Database connection returned unexpected result")
                return False
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def test_import_models():
    """Test if import models exist and are accessible"""
    print("\nTesting import models...")

    try:
        from sample.models import Source, Sample, Aliquot, AliquotType, AliquotDisposition
        from storage.models import Site, Device, Shelf, Rack, Box

        print("✓ All import models are accessible")
        return True
    except ImportError as e:
        print(f"✗ Failed to import models: {e}")
        return False

def main():
    """Run all tests"""
    print("=== Data Import Debug Script ===")
    print(f"Django settings: {settings.SETTINGS_MODULE}")
    print(f"Debug mode: {settings.DEBUG}")
    print(f"Database: {settings.DATABASES['default']['ENGINE']}")

    tests = [
        test_temp_directory,
        test_database_connection,
        test_import_models,
        test_loaddata_command,
    ]

    results = []
    for test in tests:
        results.append(test())

    print(f"\n=== Results ===")
    print(f"Passed: {sum(results)}/{len(results)}")

    if all(results):
        print("✓ All tests passed! Import should work.")
    else:
        print("✗ Some tests failed. Check the issues above.")

    return all(results)

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
