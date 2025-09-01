# DigitalOcean App Platform - Quick Reference

## Essential Environment Variables

### 🔴 REQUIRED (Must Set)

```bash
# Database Engine
DATABASE_ENGINE=postgresql

# Django Security
DJANGO_SECRET_KEY=your-very-long-random-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=${APP_DOMAIN},${APP_URL}

# Django Settings
DJANGO_SETTINGS_MODULE=krill.settings_production
ENVIRONMENT=production

# Database SSL (Security)
DB_SSLMODE=require
```

### 🟡 AUTO-CONFIGURED (When Binding Database)

**These are automatically set when you bind a PostgreSQL database:**
- `DB_NAME=${db.DATABASE}`
- `DB_USER=${db.USERNAME}`
- `DB_PASSWORD=${db.PASSWORD}`
- `DB_HOST=${db.HOST}`
- `DB_PORT=${db.PORT}`

**These are automatically set when you bind a Redis database:**
- `REDIS_URL=${redis.REDIS_URL}`

### 🟢 RECOMMENDED (For Production)

```bash
# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Security Headers
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## Step-by-Step Setup

### 1. Create App
```bash
# Via CLI
doctl apps create --spec app.yaml

# Or via web interface
# Go to DO Console → Apps → Create App
```

### 2. Bind Database
```bash
# In DO Console:
# 1. Go to your app
# 2. Click "Settings" → "Resources"
# 3. Click "Link Resource" → "Database"
# 4. Select PostgreSQL
# 5. Choose plan and region
```

### 3. Set Environment Variables
```bash
# Via CLI
doctl apps update your-app-id --set-env-vars \
  DATABASE_ENGINE=postgresql \
  DJANGO_SECRET_KEY=your-secret-key \
  DJANGO_DEBUG=False \
  DJANGO_SETTINGS_MODULE=krill.settings_production \
  ENVIRONMENT=production \
  DB_SSLMODE=require

# Via Web Interface:
# 1. Go to your app
# 2. Click "Settings" → "Environment Variables"
# 3. Add each variable
```

### 4. Deploy
```bash
# Via CLI
doctl apps create-deployment your-app-id

# Or via web interface
# Click "Deploy" button
```

## Complete Environment Variables Example

```bash
# ========================================
# DIGITALOCEAN APP PLATFORM CONFIGURATION
# ========================================

# Database (Auto-configured when binding)
DATABASE_ENGINE=postgresql
DB_NAME=${db.DATABASE}
DB_USER=${db.USERNAME}
DB_PASSWORD=${db.PASSWORD}
DB_HOST=${db.HOST}
DB_PORT=${db.PORT}
DB_SSLMODE=require

# Django Settings
DJANGO_SECRET_KEY=your-very-long-random-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=${APP_DOMAIN},${APP_URL}
DJANGO_SETTINGS_MODULE=krill.settings_production

# Environment
ENVIRONMENT=production

# Cache (Auto-configured when binding Redis)
REDIS_URL=${redis.REDIS_URL}

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

## App Specification (app.yaml)

### Option 1: Using krill subdirectory (Recommended)

```yaml
name: krill-app
services:
- name: web
  source_dir: /
  github:
    repo: your-username/krill
    branch: main
  run_command: python manage.py migrate && gunicorn krill.wsgi:application --bind 0.0.0.0:8000
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: DATABASE_ENGINE
    value: postgresql
  - key: DJANGO_SECRET_KEY
    value: your-secret-key-here
  - key: DJANGO_DEBUG
    value: "False"
  - key: DJANGO_SETTINGS_MODULE
    value: krill.settings_production
  - key: ENVIRONMENT
    value: production
  - key: DB_SSLMODE
    value: require
```

### Option 2: Using root-level WSGI file

```yaml
name: krill-app
services:
- name: web
  source_dir: /
  github:
    repo: your-username/krill
    branch: main
  run_command: python manage.py migrate && gunicorn wsgi:application --bind 0.0.0.0:8000
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: DATABASE_ENGINE
    value: postgresql
  - key: DJANGO_SECRET_KEY
    value: your-secret-key-here
  - key: DJANGO_DEBUG
    value: "False"
  - key: DJANGO_SETTINGS_MODULE
    value: krill.settings_production
  - key: ENVIRONMENT
    value: production
  - key: DB_SSLMODE
    value: require
```

**Note**: The working directory is now set in the Dockerfile (`WORKDIR /app/krill`), so you don't need to specify it in the app.yaml.

## Common Commands

### Check App Status
```bash
doctl apps list
doctl apps get your-app-id
```

### View Logs
```bash
doctl apps logs your-app-id
doctl apps logs your-app-id --follow
```

### Update Environment Variables
```bash
doctl apps update your-app-id --set-env-vars KEY1=value1,KEY2=value2
```

### Redeploy
```bash
doctl apps create-deployment your-app-id
```

### Scale App
```bash
doctl apps update your-app-id --instance-count 2
```

## Troubleshooting

### Database Connection Issues
```bash
# Check if database is bound
doctl apps get your-app-id

# Verify environment variables
doctl apps get your-app-id --format YAML

# Check logs for errors
doctl apps logs your-app-id
```

### App Won't Start
```bash
# Check build logs
doctl apps logs your-app-id --type build

# Verify run command
# Ensure migrations run before starting the app
```

### WSGI Module Error
```bash
# Error: "no module named krill.wsgi"

# Solution: Working directory is set in Dockerfile
# The Dockerfile sets WORKDIR /app/krill, so commands run from the correct directory

# Your app.yaml should use:
run_command: python manage.py migrate && gunicorn krill.wsgi:application --bind 0.0.0.0:8000

# Or if using root-level wsgi.py:
run_command: python manage.py migrate && gunicorn wsgi:application --bind 0.0.0.0:8000

# Check your project structure:
# Your project has Django files in the krill/ subdirectory
# So the WSGI module is at krill/krill/wsgi.py
# The Dockerfile sets WORKDIR /app/krill to handle this automatically
```

### Environment Variable Issues
```bash
# List current env vars
doctl apps get your-app-id --format YAML

# Update specific variable
doctl apps update your-app-id --set-env-vars KEY=new-value
```

## Security Checklist

- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_SECRET_KEY` is set and unique
- [ ] `DB_SSLMODE=require`
- [ ] Database is bound and accessible
- [ ] HTTPS is enabled (automatic in DO App Platform)
- [ ] No sensitive data in logs
- [ ] Regular security updates

## Cost Optimization

- **Instance Size**: Start with `basic-xxs` for testing
- **Database**: Use `db-s-1vcpu-1gb` for development
- **Scaling**: Scale down to 0 instances when not in use
- **Monitoring**: Use DO's built-in monitoring tools

## Support

- **DO Documentation**: [App Platform Docs](https://docs.digitalocean.com/products/app-platform/)
- **DO Support**: Available in your account dashboard
- **Community**: [DO Community](https://www.digitalocean.com/community)
