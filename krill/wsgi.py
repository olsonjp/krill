"""
WSGI config for krill project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

# Initialize Sentry before Django to catch all errors
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_dsn = os.environ.get('SENTRY_DSN')
if sentry_dsn:
    environment = os.environ.get('SENTRY_ENVIRONMENT', 'development')
    # Set traces_sample_rate based on environment
    # In production, sample 10% of transactions to save on quota
    # In development, capture all transactions to see issues
    traces_sample_rate = 0.1 if environment == 'production' else 1.0

    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            DjangoIntegration(
                transaction_style='url',
                middleware_spans=True,
                signals_spans=True,
                cache_spans=True,
            ),
        ],
        traces_sample_rate=traces_sample_rate,
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
        # Set environment
        environment=environment,
    )

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'krill.settings')

application = get_wsgi_application()
