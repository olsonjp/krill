# Production Deployment Guide

This guide covers deploying the Krill application to production environments like DigitalOcean App Platform, Heroku, AWS, or any cloud platform.

## Environment Variables for Production

### Required Environment Variables

These variables **MUST** be set in your production environment:

#### Database Configuration
```bash
# Database Engine (MUST be postgresql for production)
DATABASE_ENGINE=postgresql

# PostgreSQL Connection Details
DB_NAME=your_production_database_name
DB_USER=your_database_username
DB_PASSWORD=your_secure_database_password
DB_HOST=your_database_host
DB_PORT=5432
DB_SSLMODE=require
```

#### Django Security
```bash
# Django Secret Key (MUST be unique and secret)
DJANGO_SECRET_KEY=your-very-long-random-secret-key-here

# Debug Mode (MUST be False in production)
DJANGO_DEBUG=False

# Allowed Hosts (comma-separated list)
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,api.yourdomain.com
```

#### Application Settings
```bash
# Environment Type
ENVIRONMENT=production

# Django Settings Module
DJANGO_SETTINGS_MODULE=krill.settings_production
```

### Recommended Environment Variables

These variables are **HIGHLY RECOMMENDED** for production:

#### Email Configuration
```bash
# SMTP Settings
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Alternative: SendGrid
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
```

#### Security Settings
```bash
# SSL/HTTPS Settings
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# CORS Settings (if using external frontends)
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CORS_ALLOW_CREDENTIALS=True
```

### Optional Environment Variables

These variables provide additional functionality:

#### Monitoring and Logging
```bash
# Sentry Error Tracking
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Log Level
LOG_LEVEL=INFO

# Log File Path
LOG_FILE_PATH=/var/log/krill/django.log
```

#### File Storage
```bash
# AWS S3 (if using S3 for file storage)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1
AWS_S3_CUSTOM_DOMAIN=your-cdn-domain.com

# Alternative: DigitalOcean Spaces
DO_SPACES_KEY=your-spaces-key
DO_SPACES_SECRET=your-spaces-secret
DO_SPACES_BUCKET=your-bucket-name
DO_SPACES_ENDPOINT=nyc3.digitaloceanspaces.com
```

#### Backup Configuration
```bash
# Backup Database (optional)
BACKUP_DB_NAME=krill_backup
BACKUP_DB_USER=krill_backup_user
BACKUP_DB_PASSWORD=your-backup-password
BACKUP_DB_HOST=your-backup-db-host
BACKUP_DB_PORT=5432
```

## DigitalOcean App Platform Specific

### Required Environment Variables for DO App Platform

```bash
# Database Configuration
DATABASE_ENGINE=postgresql
DB_NAME=${db.DATABASE}
DB_USER=${db.USERNAME}
DB_PASSWORD=${db.PASSWORD}
DB_HOST=${db.HOST}
DB_PORT=${db.PORT}

# Django Settings
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=${APP_DOMAIN},${APP_URL}

# Environment
ENVIRONMENT=production
DJANGO_SETTINGS_MODULE=krill.settings_production
```

### DO App Platform Database Binding

When you bind a PostgreSQL database to your app in DO App Platform, these variables are automatically set:
- `db.DATABASE` → `DB_NAME`
- `db.USERNAME` → `DB_USER`
- `db.PASSWORD` → `DB_PASSWORD`
- `db.HOST` → `DB_HOST`
- `db.PORT` → `DB_PORT`

## Environment Variable Templates

### Complete Production Environment File

Create a `.env.production` file with all variables:

```bash
# ========================================
# PRODUCTION ENVIRONMENT CONFIGURATION
# ========================================

# Database Configuration
DATABASE_ENGINE=postgresql
DB_NAME=krill_production
DB_USER=krill_user
DB_PASSWORD=your_very_secure_password_here
DB_HOST=your-db-host.com
DB_PORT=5432
DB_SSLMODE=require

# Django Settings
DJANGO_SECRET_KEY=your-very-long-random-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,api.yourdomain.com
DJANGO_SETTINGS_MODULE=krill.settings_production

# Environment
ENVIRONMENT=production

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Security Settings
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Monitoring
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
LOG_LEVEL=INFO

# File Storage (optional)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1
```

### DigitalOcean App Platform Environment

For DO App Platform, use these environment variables:

```bash
# Database (auto-configured when binding database)
DATABASE_ENGINE=postgresql
DB_NAME=${db.DATABASE}
DB_USER=${db.USERNAME}
DB_PASSWORD=${db.PASSWORD}
DB_HOST=${db.HOST}
DB_PORT=${db.PORT}
DB_SSLMODE=require

# Django Settings
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=${APP_DOMAIN},${APP_URL}
DJANGO_SETTINGS_MODULE=krill.settings_production

# Environment
ENVIRONMENT=production

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## Setting Environment Variables

### DigitalOcean App Platform

1. **Via Web Interface:**
   - Go to your app in DO App Platform
   - Click "Settings" → "Environment Variables"
   - Add each variable with its value

2. **Via CLI:**
   ```bash
   doctl apps update your-app-id --set-env-vars DATABASE_ENGINE=postgresql,DB_SSLMODE=require
   ```

3. **Via YAML Configuration:**
   ```yaml
   envs:
   - key: DATABASE_ENGINE
     value: postgresql
   - key: DB_SSLMODE
     value: require
   - key: DJANGO_SECRET_KEY
     value: your-secret-key
   ```

### Other Platforms

#### Heroku
```bash
heroku config:set DATABASE_ENGINE=postgresql
heroku config:set DJANGO_SECRET_KEY=your-secret-key
```

#### AWS Elastic Beanstalk
```bash
eb setenv DATABASE_ENGINE=postgresql
eb setenv DJANGO_SECRET_KEY=your-secret-key
```

#### Docker
```bash
docker run -e DATABASE_ENGINE=postgresql -e DJANGO_SECRET_KEY=your-secret-key krill
```

## Security Best Practices

### 1. Secret Management
- **Never commit secrets to version control**
- Use platform-specific secret management (DO App Platform Secrets, Heroku Config Vars, etc.)
- Rotate secrets regularly
- Use different secrets for different environments

### 2. Database Security
```bash
# Always use SSL in production
DB_SSLMODE=require

# Use strong, unique passwords
DB_PASSWORD=your-very-long-random-password

# Limit database user permissions
# Only grant necessary privileges
```

### 3. Django Security
```bash
# Always disable debug in production
DJANGO_DEBUG=False

# Use HTTPS/SSL
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Set appropriate allowed hosts
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

## Validation and Testing

### Test Your Configuration

1. **Check Environment Variables:**
   ```bash
   python manage.py setup_db --check
   ```

2. **Validate Django Settings:**
   ```bash
   python manage.py check --deploy
   ```

3. **Test Database Connection:**
   ```bash
   python manage.py dbshell
   ```

4. **Run Migrations:**
   ```bash
   python manage.py migrate
   ```

### Common Issues and Solutions

#### Issue: Database Connection Failed
```bash
# Check these variables:
echo $DATABASE_ENGINE
echo $DB_HOST
echo $DB_PORT
echo $DB_NAME
echo $DB_USER
# Note: Don't echo passwords in production
```

#### Issue: Django Secret Key Error
```bash
# Generate a new secret key:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

#### Issue: Allowed Hosts Error
```bash
# Check your domain is in DJANGO_ALLOWED_HOSTS
echo $DJANGO_ALLOWED_HOSTS
```

## Monitoring and Maintenance

### Health Checks

Set up health check endpoints in your app:
```python
# In your Django app
from django.http import JsonResponse
from django.db import connections

def health_check(request):
    try:
        # Test database connection
        db_conn = connections['default']
        db_conn.cursor()
        return JsonResponse({'status': 'healthy', 'database': 'connected'})
    except Exception as e:
        return JsonResponse({'status': 'unhealthy', 'error': str(e)}, status=500)
```

### Logging

Monitor your application logs:
```bash
# View logs in DO App Platform
doctl apps logs your-app-id

# Or check your logging configuration
tail -f /var/log/krill/django.log
```

### Backup Strategy

1. **Database Backups:**
   ```bash
   # Automated PostgreSQL backups
   pg_dump -h $DB_HOST -U $DB_USER $DB_NAME > backup_$(date +%Y%m%d).sql
   ```

2. **Environment Variable Backups:**
   - Export your current environment variables
   - Store them securely (not in version control)
   - Document any manual configurations

## Troubleshooting

### Debug Mode in Production

If you need to debug an issue temporarily:
```bash
# Set debug mode (REMOVE AFTER DEBUGGING)
DJANGO_DEBUG=True

# Check logs for errors
# Fix the issue

# REMEMBER TO SET BACK TO FALSE
DJANGO_DEBUG=False
```

### Database Connection Issues

1. **Check Network Access:**
   - Verify firewall rules
   - Check security groups
   - Ensure database is accessible from your app

2. **Check Credentials:**
   - Verify username/password
   - Check database name
   - Ensure user has proper permissions

3. **Check SSL:**
   - Verify SSL mode settings
   - Check certificate validity
   - Test connection manually

## Support and Resources

### Platform-Specific Documentation
- [DigitalOcean App Platform](https://docs.digitalocean.com/products/app-platform/)
- [Heroku](https://devcenter.heroku.com/)
- [AWS Elastic Beanstalk](https://docs.aws.amazon.com/elasticbeanstalk/)

### Django Production Resources
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)
- [Django Database](https://docs.djangoproject.com/en/stable/topics/db/)

### Database Resources
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
Remember: **Never commit sensitive environment variables to version control**. Always use your platform's secure environment variable management system.
