"""
Local development settings for krill project.

This file contains development-specific settings that override production settings.
Use this for local development with SQLite database.
"""

from .settings import *

# Override for local development
DEBUG = True
SECRET_KEY = 'django-insecure-t9u1+2ux%d02^oc1fhy%rlyybh%)y28y=ee_8^%+rb^2i6i6cj'

# Local development hosts
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

# Force SQLite for local development
DATABASE_ENGINE = 'sqlite'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Disable security settings for local development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_HSTS_SECONDS = 0

# Enable debug toolbar for local development
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    
    # Debug toolbar configuration
    INTERNAL_IPS = [
        '127.0.0.1',
        'localhost',
    ]
    
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
    }

# Local logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'krill': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Local email backend (console output)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Local static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "static/krill",
]

# Local media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Environment indicator
ENVIRONMENT = 'local'

print(f"Loaded {ENVIRONMENT} settings")
