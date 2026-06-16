# Database Setup Guide

This guide explains how to set up and switch between SQLite (local development) and PostgreSQL (production) databases in the Krill project.

## Overview

The project is configured to support both database engines:
- **SQLite**: Default for local development (easiest setup)
- **PostgreSQL**: Recommended for production deployments (better performance, features)

## Quick Start

### Local Development (SQLite)

1. **Clone and setup the project:**
   ```bash
   git clone <repository>
   cd krill
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Run with SQLite (default):**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```

### Production (PostgreSQL)

1. **Set environment variables:**
   ```bash
   export DATABASE_ENGINE=postgresql
   export DB_NAME=krill_production
   export DB_USER=krill_user
   export DB_PASSWORD=your_secure_password
   export DB_HOST=localhost
   export DB_PORT=5432
   ```

2. **Run with PostgreSQL:**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```

## Environment Configuration

### Environment Files

The project includes several environment file templates:

- `env.example` - Basic configuration for local development
- `env.production` - Production configuration with PostgreSQL
- `.env` - Your actual environment file (create this)

### Key Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_ENGINE` | Database engine (`sqlite` or `postgresql`) | `sqlite` | No |
| `DB_NAME` | Database name | `krill` | Yes (PostgreSQL) |
| `DB_USER` | Database user | `krill_user` | Yes (PostgreSQL) |
| `DB_PASSWORD` | Database password | - | Yes (PostgreSQL) |
| `DB_HOST` | Database host | `localhost` | Yes (PostgreSQL) |
| `DB_PORT` | Database port | `5432` | Yes (PostgreSQL) |
| `DB_SSLMODE` | SSL mode for PostgreSQL | `prefer` | No |

## Docker Setup (Recommended)

### Using Docker Compose

1. **Start PostgreSQL:**
   ```bash
   docker-compose up -d postgres
   ```

2. **Set environment variables:**
   ```bash
   export DATABASE_ENGINE=postgresql
   export DB_NAME=krill
   export DB_USER=krill_user
   export DB_PASSWORD=krill_password
   export DB_HOST=localhost
   export DB_PORT=5432
   ```

3. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

### Manual PostgreSQL Setup

1. **Install PostgreSQL:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   
   # macOS
   brew install postgresql
   
   # Windows
   # Download from https://www.postgresql.org/download/windows/
   ```

2. **Create database and user:**
   ```sql
   CREATE USER krill_user WITH PASSWORD 'your_password';
   CREATE DATABASE krill OWNER krill_user;
   GRANT ALL PRIVILEGES ON DATABASE krill TO krill_user;
   ```

## Management Commands

### Database Setup Command

The project includes a custom management command for database operations:

```bash
# Check current database configuration
python manage.py setup_db --check

# Switch to PostgreSQL
python manage.py setup_db --engine=postgresql

# Switch to SQLite
python manage.py setup_db --engine=sqlite

# Create PostgreSQL user (requires superuser privileges)
python manage.py setup_db --create-user
```

### Migration Commands

```bash
# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations

# Reset database (WARNING: destroys all data)
python manage.py flush
```

## Data Migration

### SQLite to PostgreSQL

1. **Backup your data:**
   ```bash
   cp krill/db.sqlite3 krill/db.sqlite3.backup
   ```

2. **Set PostgreSQL environment:**
   ```bash
   export DATABASE_ENGINE=postgresql
   # ... other DB variables
   ```

3. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Load fixtures (if available):**
   ```bash
   python manage.py loaddata tests/fixtures/sample_fixtures.json
   ```

### Using the Migration Script

A helper script is provided for easy migration:

```bash
python scripts/migrate_to_postgresql.py
```

## Settings Files

The project uses multiple settings files:

- `krill/settings.py` - Base settings with environment-based configuration
- `krill/settings_local.py` - Local development overrides
- `krill/settings_production.py` - Production settings

### Switching Settings

```bash
# Use local settings (SQLite)
export DJANGO_SETTINGS_MODULE=krill.settings_local

# Use production settings (PostgreSQL)
export DJANGO_SETTINGS_MODULE=krill.settings_production

# Use base settings (environment-based)
export DJANGO_SETTINGS_MODULE=krill.settings
```

## Troubleshooting

### Common Issues

1. **PostgreSQL Connection Failed:**
   - Check if PostgreSQL is running
   - Verify environment variables
   - Check firewall settings
   - Ensure database and user exist

2. **Permission Denied:**
   - Verify database user permissions
   - Check SSL mode settings
   - Ensure proper authentication method

3. **Migration Errors:**
   - Check database connection
   - Verify Django version compatibility
   - Check for conflicting migrations

### Debug Commands

```bash
# Test database connection
python manage.py dbshell

# Check Django settings
python manage.py check

# Validate models
python manage.py validate

# Show database info
python manage.py setup_db --check
```

## Performance Considerations

### PostgreSQL Optimizations

1. **Connection Pooling:**
   ```python
   DATABASES = {
       'default': {
           # ... other settings
           'CONN_MAX_AGE': 60,
           'OPTIONS': {
               'sslmode': 'require',
               'connect_timeout': 10,
           },
       }
   }
   ```

2. **Indexing:**
   - Use `db_index=True` on frequently queried fields
   - Consider composite indexes for complex queries
   - Monitor query performance with `django-debug-toolbar`

3. **Caching:**
   - Use `select_related()` and `prefetch_related()` for queries
   - Implement database query optimization

## Backup and Recovery

### PostgreSQL Backups

```bash
# Create backup
pg_dump -h localhost -U krill_user krill > backup.sql

# Restore backup
psql -h localhost -U krill_user krill < backup.sql

# Automated backups (add to crontab)
0 2 * * * pg_dump -h localhost -U krill_user krill > /backups/krill_$(date +\%Y\%m\%d).sql
```

### SQLite Backups

```bash
# Simple copy
cp krill/db.sqlite3 krill/db.sqlite3.backup

# Using sqlite3
sqlite3 krill/db.sqlite3 ".backup 'krill/db.sqlite3.backup'"
```

## Security Considerations

### Production Security

1. **Environment Variables:**
   - Never commit `.env` files
   - Use strong, unique passwords
   - Rotate credentials regularly

2. **Database Security:**
   - Use SSL connections
   - Limit database user permissions
   - Regular security updates
   - Network access restrictions

3. **Application Security:**
   - Enable HTTPS
   - Use secure cookies
   - Implement rate limiting
   - Regular security audits

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review Django and PostgreSQL documentation
3. Check project issues and discussions
4. Contact the development team

## Additional Resources

- [Django Database Documentation](https://docs.djangoproject.com/en/stable/topics/db/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [PostgreSQL Performance Tuning](https://www.postgresql.org/docs/current/runtime-config-query.html)
