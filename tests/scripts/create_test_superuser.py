#!/usr/bin/env python3
"""
Script to create a test superuser for the Krill project.
This creates a superuser with username 'admin' and password 'admin'.
"""

import os
import sys
import django
from django.contrib.auth import get_user_model

# Add the project root to the Python path
project_root = os.path.join(os.path.dirname(__file__), '../../krill')
sys.path.insert(0, project_root)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'krill.settings')
django.setup()

def create_test_superuser():
    """Create a test superuser if it doesn't exist"""
    User = get_user_model()

    username = 'admin'
    password = 'admin'
    email = 'admin@test.com'

    # Check if superuser already exists
    if User.objects.filter(username=username).exists():
        print(f"Superuser '{username}' already exists. Updating password...")
        user = User.objects.get(username=username)
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.email = email
        user.save()
        print(f"✓ Updated superuser '{username}' with password '{password}'")
    else:
        print(f"Creating superuser '{username}' with password '{password}'...")
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        print(f"✓ Created superuser '{username}' with password '{password}'")

    print(f"\nTest superuser credentials:")
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    print(f"  Email: {email}")

if __name__ == "__main__":
    create_test_superuser()
