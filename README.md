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
- [uv](https://docs.astral.sh/uv/) (dependencies are defined in `pyproject.toml` / `uv.lock`)

### Local Development Setup

```bash
git clone <repository-url>
cd krill
uv sync                       # creates .venv and installs dependencies
source .venv/bin/activate     # On Windows: .venv\Scripts\activate
make migrate                  # SQLite by default
make createsuperuser
make server                   # http://localhost:8000 (admin at /admin)
```

To start with anonymized sample data instead (creates `admin` / `admin`), run `make setup-test`.
See [Testing](tests/README.md) and `make help` for all available commands.

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
├── krill/                 # Django project root (manage.py lives here)
│   ├── krill/             # Settings, URLs, WSGI
│   ├── person/ sample/ storage/ reports/ transaction/   # Django apps
│   └── management/        # Custom management commands
├── templates/             # Admin template overrides
├── tests/                 # Anonymized data, fixtures, test scripts
├── scripts/               # Build, deploy and utility scripts
├── docs/                  # Guides (see Documentation below)
├── Dockerfile, docker-compose.yml, app.yaml   # Container and DO App Platform config
├── env.example            # Environment template
└── pyproject.toml, uv.lock
```

## Environment Configuration

Create a `.env` file based on the provided templates:

- `env.example` - Basic configuration for development
- [`docs/deployment/env.production.example`](docs/deployment/env.production.example) - Production configuration with PostgreSQL

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
5. Ensure all tests pass (`make test-local`)
6. Commit your changes (`git commit -m 'Add some amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Documentation

**Getting started and contributing**
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development workflow and guidelines
- [Testing Guide](tests/README.md) - Running tests and using anonymized test data
- [Test Data Anonymization](tests/ANONYMIZATION_README.md) - How the anonymized dataset is produced
- [Utility Scripts](scripts/README.md) - Helper scripts (whitespace cleanup, PostgreSQL migration)
- [Security Notes](krill/SECURITY.md) - Security configuration and checks

**Data**
- [Data Import Guide](docs/DATA_IMPORT.md) - How to structure CSV files for importing sample data
- [Database Setup Guide](docs/database.md) - SQLite and PostgreSQL configuration

**Deployment**
- [Deployment Guide](docs/deployment/README.md) - Docker images, environment variables, security checklist, troubleshooting
- [DigitalOcean App Platform](docs/deployment/digitalocean.md) - Platform-specific setup and `doctl` commands

See also the [docs index](docs/README.md).

## Support

For issues and questions:

1. Check the [documentation](#documentation) above
2. Search [existing issues](https://github.com/yourusername/krill/issues)
3. Create a [new issue](https://github.com/yourusername/krill/issues/new) with detailed information

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Django framework and community
- PostgreSQL database
- Open source contributors
