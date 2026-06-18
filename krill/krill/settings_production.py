"""
Production settings for krill project.

This file contains production-specific settings with enhanced security.
Copy this file and modify as needed for your production environment.
"""

import os
from pathlib import Path
from .settings import *

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# Generate a new secret key for production:
# python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'your-production-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Production hosts - read from environment variable
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r'^health/$']
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS Settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Session Security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

# CSRF Settings
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_AGE = 31449600  # 1 year
CSRF_TRUSTED_ORIGINS = [
    f'https://{host}' for host in ALLOWED_HOSTS if host not in ['localhost', '127.0.0.1']
]

# Database - Use PostgreSQL in production
# Statement timeout in milliseconds for all queries (default 30 seconds).
# Prevents long-running queries from hanging the app; override via DB_STATEMENT_TIMEOUT_MS.
_pg_timeout_ms = os.environ.get('DB_STATEMENT_TIMEOUT_MS', '30000')
_pg_options = {'options': f'-c statement_timeout={_pg_timeout_ms}'}

_database_url = os.environ.get('DATABASE_URL')
if _database_url:
    # Railway provides a single DATABASE_URL connection string.
    import dj_database_url
    DATABASES = {'default': dj_database_url.parse(_database_url, ssl_require=True)}
    DATABASES['default'].setdefault('OPTIONS', {}).update(_pg_options)
else:
    # DO App Platform (and other envs) supply individual DB_* vars.
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'krill_production'),
            'USER': os.environ.get('DB_USER', 'krill_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'OPTIONS': {'sslmode': 'require', **_pg_options},
        }
    }

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR.parent / 'staticfiles'

# Static files directories (for collectstatic)
STATICFILES_DIRS = [
    BASE_DIR / "static/krill",
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Configure Whitenoise for static file serving
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Logging configuration
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
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'krill': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@your-domain.com')

# Password validation - Enhanced for production
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'max_similarity': 0.7,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
]

# Rate limiting
RATELIMIT_ENABLE = True

# Security middleware additions
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add Whitenoise for static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Add rate limiting middleware if using django-ratelimit
    # 'django_ratelimit.middleware.RatelimitMiddleware',
]

# Custom security middleware
class SecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Additional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        return response

# Add custom security middleware
MIDDLEWARE.append('krill.settings_production.SecurityMiddleware')

# Admin site customization
ADMIN_SITE_HEADER = "Krill Administration"
ADMIN_SITE_TITLE = "Krill Admin Portal"
ADMIN_INDEX_TITLE = "Welcome to Krill Administration"

# Backup configuration
BACKUP_DIR = BASE_DIR / 'backups'
BACKUP_RETENTION_DAYS = 30

# Monitoring and health checks
HEALTH_CHECK = {
    'DISK_USAGE_MAX': 90,  # percentage
    'MEMORY_MIN': 100,     # MB
}

# API rate limiting
API_RATE_LIMITS = {
    'default': '100/hour',
    'auth': '5/minute',
    'admin': '1000/hour',
}

# Audit logging
AUDIT_LOG_ENABLED = True
AUDIT_LOG_RETENTION_DAYS = 365

# File upload security
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5 MB
FILE_UPLOAD_TEMP_DIR = BASE_DIR / 'temp'

# Allowed file types for uploads
ALLOWED_FILE_EXTENSIONS = [
    '.pdf', '.doc', '.docx', '.txt', '.csv', '.xlsx', '.xls',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'
]

# Maximum file size (in bytes)
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# Backup database configuration
BACKUP_DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('BACKUP_DB_NAME', 'krill_backup'),
        'USER': os.environ.get('BACKUP_DB_USER', 'krill_backup_user'),
        'PASSWORD': os.environ.get('BACKUP_DB_PASSWORD', ''),
        'HOST': os.environ.get('BACKUP_DB_HOST', 'localhost'),
        'PORT': os.environ.get('BACKUP_DB_PORT', '5432'),
    }
}

# Performance optimization
CONN_MAX_AGE = 60  # Database connection lifetime
OPTIMIZE_DB_QUERIES = True

# Security monitoring
SECURITY_MONITORING = {
    'LOG_FAILED_LOGINS': True,
    'LOG_PERMISSION_DENIED': True,
    'LOG_SUSPICIOUS_ACTIVITY': True,
    'ALERT_ON_MULTIPLE_FAILURES': True,
    'MAX_LOGIN_ATTEMPTS': 5,
    'LOCKOUT_DURATION': 300,  # 5 minutes
}

# Environment-specific settings
ENVIRONMENT = 'production'

# Sentry Configuration
SENTRY_DSN = os.environ.get('SENTRY_DSN')
SENTRY_ENVIRONMENT = os.environ.get('SENTRY_ENVIRONMENT', 'production')

# Note: Sentry is initialized in wsgi.py and asgi.py before Django loads
# This ensures we catch all errors, including those during Django startup

# Create necessary directories
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
os.makedirs(BASE_DIR / 'backups', exist_ok=True)
os.makedirs(BASE_DIR / 'temp', exist_ok=True)
os.makedirs(STATIC_ROOT, exist_ok=True)
os.makedirs(MEDIA_ROOT, exist_ok=True)
