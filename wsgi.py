"""
WSGI config for krill project.

This file is used for production deployment and correctly references
the Django application in the krill subdirectory.
"""

import os
import sys

# Add the krill subdirectory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'krill'))

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'krill.settings_production')

# Import Django and get the WSGI application
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
