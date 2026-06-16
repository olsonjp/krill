# Krill

A Django-based application for managing biological sample storage, tracking, and reporting. Krill provides a comprehensive solution for laboratories to track samples, manage storage locations, and generate audit reports.

## Overview

Krill is designed for research laboratories and biobanks that need to:
- Track biological samples with detailed metadata
- Manage storage locations, boxes, and freezer capacity
- Control access with role-based permissions
- Generate reports and maintain audit trails
- Support multiple storage locations and organizational units

## Features

- **Sample Management**: Track biological samples with detailed metadata
- **Storage Management**: Manage storage locations, boxes, and capacity
- **User Management**: Role-based access control and permissions
- **Reporting**: Generate reports and audit logs
- **Multi-Database Support**: SQLite for development, PostgreSQL for production

## Quick Start

### Prerequisites

- Python 3.10+
- pip
- virtualenv (recommended)

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd krill
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run with SQLite (default):**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```

5. **Access the application:**
   - Web interface: http://localhost:8000
   - Admin interface: http://localhost:8000/admin

### Production Setup with PostgreSQL

1. **Set environment variables:**
   ```bash
   export DATABASE_ENGINE=postgresql
   export DB_NAME=krill_production
   export DB_USER=krill_user
   export DB_PASSWORD=your_secure_password
   export DB_HOST=localhost
   export DB_PORT=5432
   ```

2. **Run migrations:**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

3. **Start the application:**
   ```bash
   python manage.py runserver
   ```

## Database Configuration

The project supports both SQLite and PostgreSQL databases:

- **SQLite**: Default for local development (easiest setup)
- **PostgreSQL**: Recommended for production (better performance, features)

### Using Docker (Recommended)

```bash
# Start PostgreSQL service
docker-compose up -d postgres

# Set environment variables
export DATABASE_ENGINE=postgresql
export DB_NAME=krill
export DB_USER=krill_user
export DB_PASSWORD=krill_password

# Run migrations
python manage.py migrate
```

### Manual PostgreSQL Setup

```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE USER krill_user WITH PASSWORD 'your_password';
CREATE DATABASE krill OWNER krill_user;
GRANT ALL PRIVILEGES ON DATABASE krill TO krill_user;
\q
```

## Management Commands

### Database Operations

```bash
# Check database configuration
python manage.py setup_db --check

# Switch database engines
python manage.py setup_db --engine=postgresql
python manage.py setup_db --engine=sqlite

# Create PostgreSQL user
python manage.py setup_db --create-user
```

### Data Migration

```bash
# Migrate from SQLite to PostgreSQL
python scripts/migrate_to_postgresql.py

# Manual migration
export DATABASE_ENGINE=postgresql
python manage.py migrate
```

## Project Structure

```
krill/
├── krill/                 # Main Django project
│   ├── settings.py        # Base settings (environment-based)
│   ├── settings_local.py  # Local development overrides
│   ├── settings_production.py  # Production settings
│   └── management/        # Custom management commands
├── person/                # User management app
├── sample/                # Sample tracking app
├── storage/               # Storage management app
├── reports/               # Reporting app
├── transaction/           # Transaction tracking
├── docker-compose.yml     # Docker services
├── env.example            # Environment template
├── env.production         # Production environment template
└── DATABASE_SETUP.md      # Detailed database guide
```

## Environment Configuration

Create a `.env` file based on the provided templates:

- `env.example` - Basic configuration for development
- `env.production` - Production configuration with PostgreSQL

### Key Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_ENGINE` | Database engine (`sqlite` or `postgresql`) | `sqlite` |
| `DB_NAME` | Database name | `krill` |
| `DB_USER` | Database user | `krill_user` |
| `DB_PASSWORD` | Database password | - |
| `DJANGO_SECRET_KEY` | Django secret key | auto-generated |
| `DJANGO_DEBUG` | Debug mode | `True` |

## Development

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test sample
python manage.py test storage

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

### Code Quality

```bash
# Security linting
bandit -r .

# Dependency vulnerability check
safety check

# Code formatting
black .
```

## Deployment

### Production Checklist

- [ ] Set `DJANGO_DEBUG=False`
- [ ] Use PostgreSQL database
- [ ] Configure environment variables
- [ ] Set up SSL/HTTPS
- [ ] Configure static file serving
- [ ] Set up logging and monitoring
- [ ] Configure backups
- [ ] Set up CI/CD pipeline

### Docker Deployment

```bash
# Build and run with Docker
docker build -t krill .
docker run -p 8000:8000 --env-file .env krill

# Or use Docker Compose
docker-compose up -d
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`python manage.py test`)
6. Commit your changes (`git commit -m 'Add some amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Documentation

- [Database Setup Guide](DATABASE_SETUP.md) - Comprehensive database configuration
- [Data Import Guide](DATA_IMPORT.md) - How to structure CSV files for importing sample data
- [Production Deployment Guide](PRODUCTION_DEPLOYMENT.md) - Complete production deployment instructions
- [DigitalOcean App Platform Quick Reference](DO_APP_PLATFORM_QUICK_REF.md) - DO-specific deployment guide
- [Dockerfile Deployment Guide](DOCKERFILE_DEPLOYMENT.md) - How the Dockerfile handles working directory
- [API Documentation](docs/api.md) - API endpoints and usage (coming soon)

## Support

For issues and questions:

1. Check the [documentation](#documentation) below
2. Search [existing issues](https://github.com/yourusername/krill/issues)
3. Create a [new issue](https://github.com/yourusername/krill/issues/new) with detailed information

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Django framework and community
- PostgreSQL database
- Open source contributors
