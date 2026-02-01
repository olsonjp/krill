# Multi-stage Dockerfile for Krill Django Application
# Supports both development and production environments

# Base stage with common dependencies
FROM python:3.10-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir \
    django-debug-toolbar \
    django-extensions \
    ipython

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p /app/media /app/staticfiles /app/logs

# Set permissions
RUN chmod +x /app/manage.py

# Expose port
EXPOSE 8000

# Development command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# Production stage
FROM base as production

# Install production dependencies
RUN pip install --no-cache-dir \
    gunicorn \
    whitenoise

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p /app/media /app/staticfiles /app/logs

# Set permissions
RUN chmod +x /app/manage.py

# Collect static files
RUN DJANGO_SETTINGS_MODULE=krill.settings_production python manage.py collectstatic --noinput

# Create non-root user for security
RUN groupadd -r krill && useradd -r -g krill krill
RUN chown -R krill:krill /app
USER krill

# Expose port
EXPOSE 8000

# Production command
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "krill.wsgi:application"]

# Testing stage
FROM base as testing

# Install testing dependencies
RUN pip install --no-cache-dir \
    coverage \
    pytest \
    pytest-django

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p /app/media /app/staticfiles /app/logs

# Set permissions
RUN chmod +x /app/manage.py

# Test command
CMD ["python", "manage.py", "test", "--verbosity=2"]
