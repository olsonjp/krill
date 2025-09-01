# Docker Container Builds for Krill

This document explains how to use the Docker container builds for the Krill Django application. The setup preserves your current development flow while adding container-based builds for different environments.

## 🐳 Overview

The Docker setup includes three build targets:
- **Development**: For local development with debug tools
- **Testing**: For running tests in an isolated environment
- **Production**: For production deployment with security optimizations

## 🚀 Quick Start

### Build All Images
```bash
./build.sh all
```

### Build Specific Image
```bash
# Development
./build.sh development

# Testing
./build.sh testing

# Production
./build.sh production
```

### Run Tests in Container
```bash
./build.sh test
```

## 📋 Detailed Usage

### Development Environment

Build the development image:
```bash
./build.sh development
```

Run the development container:
```bash
docker run -p 8000:8000 krill:development
```

**Features:**
- Django development server
- Debug tools enabled
- Hot reloading (when using volume mounts)
- Development dependencies included

### Testing Environment

Build the testing image:
```bash
./build.sh testing
```

Run tests in container:
```bash
docker run --rm krill:testing
```

**Features:**
- Isolated test environment
- All test dependencies included
- Runs Django test suite
- Coverage reporting available

### Production Environment

Build the production image:
```bash
./build.sh production
```

Run the production container:
```bash
docker run -p 8000:8000 \
  -e DJANGO_SECRET_KEY=your-secret-key \
  -e DB_NAME=your_db_name \
  -e DB_USER=your_db_user \
  -e DB_PASSWORD=your_db_password \
  -e DB_HOST=your_db_host \
  -e REDIS_URL=redis://your_redis_host:6379/1 \
  krill:production
```

**Features:**
- Gunicorn WSGI server
- Security optimizations
- Non-root user
- Static files collected
- Production settings

## 🔧 Environment Variables

### Development
- `DJANGO_SETTINGS_MODULE=krill.settings`
- `DEBUG=True`
- `DJANGO_SECRET_KEY=dev-secret-key-change-in-production`

### Production
- `DJANGO_SETTINGS_MODULE=krill.settings_production`
- `DEBUG=False`
- `DJANGO_SECRET_KEY` (required)
- `DB_NAME` (required)
- `DB_USER` (required)
- `DB_PASSWORD` (required)
- `DB_HOST` (required)
- `DB_PORT=5432`
- `REDIS_URL` (required)

## 🗄️ Database Configuration

The containers are designed to work with external databases. You'll need to:

1. **Set up PostgreSQL** for production
2. **Set up Redis** for caching and sessions
3. **Configure environment variables** to point to your databases

### Example with External Database
```bash
docker run -p 8000:8000 \
  -e DJANGO_SECRET_KEY=your-secret-key \
  -e DB_NAME=krill_production \
  -e DB_USER=krill_user \
  -e DB_PASSWORD=secure_password \
  -e DB_HOST=your-postgres-host \
  -e REDIS_URL=redis://your-redis-host:6379/1 \
  krill:production
```

## 📁 Volume Mounts

### Development with Code Changes
```bash
docker run -p 8000:8000 \
  -v $(pwd):/app \
  -v krill_static:/app/staticfiles \
  -v krill_media:/app/media \
  krill:development
```

### Production with Persistent Data
```bash
docker run -p 8000:8000 \
  -v krill_static:/app/staticfiles \
  -v krill_media:/app/media \
  -v krill_logs:/app/logs \
  -e DJANGO_SECRET_KEY=your-secret-key \
  krill:production
```

## 🔒 Security Considerations

### Production Security
- Non-root user in production container
- Security headers configured
- HTTPS enforcement ready
- Secure session settings
- CSRF protection enabled

### Environment Variables
- Never commit secrets to version control
- Use environment variables for sensitive data
- Generate new SECRET_KEY for production
- Use strong database passwords

## 🧪 Testing

### Run All Tests
```bash
./build.sh test
```

### Run Specific Test Suite
```bash
docker run --rm krill:testing python krill/manage.py test security_tests
```

### Run with Coverage
```bash
docker run --rm krill:testing python krill/manage.py test --verbosity=2 --coverage
```

## 🔄 Integration with Current Workflow

### Preserving Development Flow
The Docker setup is designed to complement your existing workflow:

1. **Local Development**: Continue using your virtual environment
2. **Testing**: Use containers for isolated testing
3. **CI/CD**: Use containers for automated builds
4. **Production**: Use containers for deployment

### Development Commands
```bash
# Your current workflow (unchanged)
source venv/bin/activate
python krill/manage.py runserver

# New container-based testing
./build.sh test

# New container-based production build
./build.sh production
```

## 🛠️ Troubleshooting

### Common Issues

**Build fails with permission errors:**
```bash
sudo chown -R $USER:$USER .
```

**Container can't connect to database:**
- Check database host and port
- Verify network connectivity
- Ensure database is running

**Static files not loading:**
```bash
# Collect static files
docker run --rm krill:production python krill/manage.py collectstatic --noinput
```

**Memory issues:**
```bash
# Increase Docker memory limit
docker run --memory=2g krill:production
```

### Debug Commands

**Check container logs:**
```bash
docker logs <container_id>
```

**Access container shell:**
```bash
docker exec -it <container_id> /bin/bash
```

**Check container resources:**
```bash
docker stats <container_id>
```

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Django Deployment](https://docs.djangoproject.com/en/stable/howto/deployment/)
- [Gunicorn Documentation](https://gunicorn.org/)
- [Krill Security Guide](SECURITY.md)

## 🤝 Contributing

When adding new dependencies or changing the build process:

1. Update `requirements.txt`
2. Test all build targets: `./build.sh all`
3. Run tests: `./build.sh test`
4. Update this documentation

---

**Note**: This Docker setup is designed to work alongside your existing development environment, not replace it. Use containers for testing and production deployment while continuing to use your virtual environment for local development.
