# Dockerfile Deployment Guide

## Overview

This guide explains how the Dockerfile handles the working directory configuration for deploying the Krill Django application. This approach is more reliable than trying to set working directories in platform-specific configuration files.

## Why Use Dockerfile for Working Directory?

### Problems with Platform-Specific Configuration
- **DigitalOcean Console Limitations**: Can't always override working directory settings
- **Container Compatibility**: Some containers don't have `cd` command available
- **Inconsistent Behavior**: Different platforms handle working directory differently

### Benefits of Dockerfile Approach
- **Consistent**: Works the same way across all platforms
- **Reliable**: No dependency on external configuration
- **Portable**: Can deploy to any platform that supports Docker
- **Version Controlled**: Working directory is part of your source code

## How It Works

### Base Stage
```dockerfile
# Base stage sets up common dependencies
FROM python:3.10-slim as base
WORKDIR /app  # Base working directory for installing dependencies
```

### Production Stage
```dockerfile
# Production stage sets the correct working directory
FROM base as production
# ... other setup steps ...

# Set working directory to krill subdirectory for production
WORKDIR /app/krill

# Production command - now relative to /app/krill
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "krill.wsgi:application"]
```

## Directory Structure in Container

```
/app/                    # Base container directory
├── requirements.txt     # Python dependencies
├── krill/              # Django project directory
│   ├── krill/          # Django project package
│   │   ├── wsgi.py     # WSGI application
│   │   ├── settings.py # Django settings
│   │   └── ...
│   ├── manage.py       # Django management
│   ├── person/         # Django apps
│   ├── sample/         # Django apps
│   └── ...
└── media/              # User uploads
    staticfiles/         # Collected static files
    logs/               # Application logs
```

## WSGI Path Resolution

### With `WORKDIR /app/krill`:
- **Command**: `gunicorn krill.wsgi:application`
- **Resolves to**: `/app/krill/krill/wsgi.py`
- **Result**: ✅ Correct WSGI module found

### Without `WORKDIR /app/krill`:
- **Command**: `gunicorn krill.wsgi:application`
- **Resolves to**: `/app/krill/wsgi.py` (doesn't exist)
- **Result**: ❌ "No module named krill.wsgi" error

## Deployment Configuration

### DigitalOcean App Platform
```yaml
name: krill-app
services:
- name: web
  source_dir: /
  github:
    repo: your-username/krill
    branch: main
  # No working_dir needed - Dockerfile handles it
  run_command: python manage.py migrate && gunicorn krill.wsgi:application --bind 0.0.0.0:8000
  environment_slug: python
  # ... rest of config
```

### Other Platforms
The same approach works for:
- **Heroku**: Uses the Dockerfile directly
- **AWS ECS**: Uses the Dockerfile directly
- **Google Cloud Run**: Uses the Dockerfile directly
- **Docker Compose**: Uses the Dockerfile directly

## Commands That Work

### From `/app/krill` (Production Working Directory)
```bash
# Django management commands
python manage.py migrate
python manage.py collectstatic
python manage.py createsuperuser

# Gunicorn with correct WSGI path
gunicorn krill.wsgi:application --bind 0.0.0.0:8000

# Alternative: Use root-level wsgi.py
gunicorn wsgi:application --bind 0.0.0.0:8000
```

### File Paths
```bash
# Static files
/app/media/staticfiles/

# Media files
/app/media/

# Logs
/app/logs/

# Django project
/app/krill/
```

## Troubleshooting

### Common Issues

#### Issue: "No module named krill.wsgi"
**Cause**: Working directory not set correctly
**Solution**: Ensure Dockerfile has `WORKDIR /app/krill` in production stage

#### Issue: "manage.py not found"
**Cause**: Commands running from wrong directory
**Solution**: Verify `WORKDIR /app/krill` is set in Dockerfile

#### Issue: Static files not found
**Cause**: Paths relative to wrong working directory
**Solution**: Check that static file collection happens in correct directory

### Debug Commands
```bash
# Check current working directory
pwd

# List files in current directory
ls -la

# Check Python path
python -c "import sys; print(sys.path)"

# Test WSGI import
python -c "import krill.wsgi; print('WSGI import successful')"
```

## Best Practices

### 1. Keep Working Directory in Dockerfile
- Don't rely on platform-specific working directory settings
- Use `WORKDIR` directive in Dockerfile
- Test locally with Docker before deploying

### 2. Use Absolute Paths for Critical Operations
```dockerfile
# Good: Absolute path for static collection
RUN DJANGO_SETTINGS_MODULE=krill.settings_production python krill/manage.py collectstatic --noinput

# Good: Absolute path for permissions
RUN chmod +x /app/krill/manage.py
```

### 3. Test Your Configuration
```bash
# Build and test locally
docker build --target production -t krill-prod .
docker run -it krill-prod bash

# Inside container, verify working directory
pwd  # Should show /app/krill
ls -la  # Should show manage.py, krill/ directory, etc.
```

### 4. Monitor Deployment Logs
```bash
# DigitalOcean App Platform
doctl apps logs your-app-id --follow

# Look for working directory related errors
# Check if commands are running from correct location
```

## Alternative Approaches

### Option 1: Root-Level WSGI File
If you prefer to use the root-level `wsgi.py`:
```dockerfile
# Keep WORKDIR /app/krill
WORKDIR /app/krill

# Use root-level wsgi
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "wsgi:application"]
```

### Option 2: Environment Variable Override
You can still override working directory in some platforms:
```yaml
# Some platforms support this
working_dir: /app/krill
```

But the Dockerfile approach is more reliable and portable.

## Summary

Using `WORKDIR /app/krill` in the Dockerfile production stage is the most reliable way to handle the working directory for your Django application. This approach:

1. **Eliminates platform-specific configuration issues**
2. **Provides consistent behavior across all deployment targets**
3. **Makes your application more portable**
4. **Reduces deployment errors and troubleshooting time**

The key is understanding that your Django project lives in the `krill/` subdirectory, so the working directory needs to be set to `/app/krill` for all Django commands to work correctly.
