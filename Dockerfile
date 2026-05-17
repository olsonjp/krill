# Multi-stage Dockerfile for Krill Django Application
# Supports both development and production environments

# Base stage with common dependencies
FROM python:3.10-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_CACHE=1 \
    UV_SYSTEM_PYTHON=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create app directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv sync --frozen --no-dev

# Development stage
FROM base as development

# Install dev dependencies
RUN uv sync --frozen

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p /app/media /app/staticfiles /app/logs

# Set permissions
RUN chmod +x /app/krill/manage.py

# Expose port
EXPOSE 8000

# Development command
CMD ["uv", "run", "python", "krill/manage.py", "runserver", "0.0.0.0:8000"]

# Production stage
FROM base as production

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p /app/media /app/staticfiles /app/logs

# Set permissions
RUN chmod +x /app/krill/manage.py

# Collect static files
RUN DJANGO_SETTINGS_MODULE=krill.settings_production uv run python krill/manage.py collectstatic --noinput

# Create non-root user for security
RUN groupadd -r krill && useradd -r -g krill krill
RUN chown -R krill:krill /app
USER krill

# Set working directory to krill subdirectory for production
WORKDIR /app/krill

# Expose port
EXPOSE 8000

# Production command
CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "krill.wsgi:application"]

# Testing stage
FROM base as testing

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p /app/media /app/staticfiles /app/logs

# Set permissions
RUN chmod +x /app/krill/manage.py

# Test command
CMD ["uv", "run", "python", "krill/manage.py", "test", "--verbosity=2"]
