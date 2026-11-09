# Deployment Guide

How to build, configure and deploy Krill. For local development setup see the
[top-level README](../../README.md); for database specifics see
[Database Setup](../database.md).

- [How the container is built](#how-the-container-is-built)
- [Running the Docker images](#running-the-docker-images)
- [Environment variables](#environment-variables)
- [Deploying](#deploying) (DigitalOcean App Platform: [digitalocean.md](digitalocean.md))
- [Validation, security and operations](#validation-security-and-operations)
- [Troubleshooting](#troubleshooting)

## How the container is built

The multi-stage [`Dockerfile`](../../Dockerfile) installs dependencies with `uv` from
`pyproject.toml` / `uv.lock` and has three targets:

| Target | Purpose | Command |
|--------|---------|---------|
| `development` | Local container with dev dependencies | `runserver 0.0.0.0:8000` |
| `testing` | Isolated test run | `manage.py test --verbosity=2` |
| `production` | Non-root user, static files collected | `manage.py migrate` then `gunicorn krill.wsgi:application` (3 workers) |

The Django project lives in the `krill/` subdirectory, so the production stage sets
`WORKDIR /app/krill`. That is what makes `krill.wsgi:application` resolve to
`/app/krill/krill/wsgi.py`. Keep the working directory in the Dockerfile rather than in
platform settings, which are not always overridable. Migrations run on container start
(see the production `CMD`), so a deploy needs no separate migration job.

```
/app/
├── pyproject.toml, uv.lock
├── krill/            # WORKDIR in production: manage.py, apps, krill/wsgi.py
├── media/  staticfiles/  logs/
```

## Running the Docker images

[`scripts/build.sh`](../../scripts/build.sh) (also `make build-*` / `make test-docker`) builds the images:

```bash
./scripts/build.sh all            # or: development | testing | production
./scripts/build.sh test           # build and run the test image
docker run -p 8000:8000 krill:development
```

Production, against an external PostgreSQL database:

```bash
docker run -p 8000:8000 --env-file .env \
  -v krill_media:/app/media -v krill_logs:/app/logs \
  krill:production
```

For local PostgreSQL only, `docker-compose up -d postgres` (initialized by
[`scripts/init.sql`](../../scripts/init.sql)); see [Database Setup](../database.md).

## Environment variables

Templates: [`env.example`](../../env.example) (development) and
[`env.production.example`](env.production.example) (production). Only the variables below are
read by `krill/krill/settings_production.py`; never commit real values.

| Variable | Required | Notes |
|----------|----------|-------|
| `DJANGO_SETTINGS_MODULE` | Yes | `krill.settings_production` |
| `DJANGO_SECRET_KEY` | Yes | Unique and secret. Generate: `python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"` |
| `DJANGO_DEBUG` | Yes | Must be `False` |
| `DJANGO_ALLOWED_HOSTS` | Yes | Comma-separated hostnames |
| `DATABASE_ENGINE` | Yes | `postgresql` |
| `DB_NAME` `DB_USER` `DB_PASSWORD` `DB_HOST` `DB_PORT` | Yes | PostgreSQL connection |
| `DB_SSLMODE` | Recommended | `require` in production (default `prefer`) |
| `DB_STATEMENT_TIMEOUT_MS` | No | Default 30000 |
| `SECURE_SSL_REDIRECT` | No | Defaults to `true`; `/health/` is exempt |
| `EMAIL_HOST` `EMAIL_PORT` `EMAIL_HOST_USER` `EMAIL_HOST_PASSWORD` `DEFAULT_FROM_EMAIL` | For email | SMTP; TLS is always on |
| `SENTRY_DSN` `SENTRY_ENVIRONMENT` | No | Error tracking |
| `BACKUP_DB_NAME` `BACKUP_DB_USER` `BACKUP_DB_PASSWORD` `BACKUP_DB_HOST` `BACKUP_DB_PORT` | No | Optional backup database |

## Deploying

The image runs anywhere that runs Docker (DigitalOcean App Platform, ECS, Cloud Run, Heroku
container deploys, a VM). Set the variables above using the platform's secret management
(`heroku config:set`, `eb setenv`, `docker run -e`, …).

- **DigitalOcean App Platform** (current target): [digitalocean.md](digitalocean.md).

## Validation, security and operations

Run from the `krill/` directory (or prefix with `cd krill &&`):

```bash
python manage.py setup_db --check     # database configuration
python manage.py check --deploy       # Django deployment checks
python manage.py migrate
```

The app exposes `GET /health/` (database connectivity) for platform health checks.

Security checklist:

- [ ] `DJANGO_DEBUG=False` and a unique `DJANGO_SECRET_KEY`
- [ ] `DJANGO_ALLOWED_HOSTS` set to your real domains
- [ ] `DB_SSLMODE=require`, strong DB password, least-privilege DB user
- [ ] HTTPS enforced (`SECURE_SSL_REDIRECT`; HSTS is already configured)
- [ ] Secrets only in the platform's secret store, rotated regularly
- [ ] Logging/Sentry and database backups configured

Backups: `pg_dump -h $DB_HOST -U $DB_USER $DB_NAME > backup_$(date +%Y%m%d).sql`
(more in [Database Setup](../database.md#backup-and-recovery)). Also keep a secure copy of
your environment configuration. See also the [Security Notes](../../krill/SECURITY.md).

## Which header carries the client's IP?

Behind DigitalOcean's proxy, the address Django sees as the caller's can be forged: Sentry has recorded `127.0.0.1`, `10.0.0.1` and similar values from internet scanners. `krill.middleware.ClientIPDiagnosticMiddleware` tags every request in Sentry with the headers it arrived with (`ip.remote_addr`, `ip.do_connecting_ip`, `ip.x_forwarded_for`, `ip.x_real_ip`, `ip.cf_connecting_ip`), so you can see which one is trustworthy. To test, send one request with made-up values for each header:

```bash
curl -s -o /dev/null https://YOUR-APP/health/ \
  -H 'X-Forwarded-For: 203.0.113.7' -H 'DO-Connecting-IP: 203.0.113.8' \
  -H 'X-Real-IP: 203.0.113.9' -H 'CF-Connecting-IP: 203.0.113.10'
```

Then find that request in Sentry (Explore > Traces, filter on the tag, for example `ip.do_connecting_ip:203.0.113.8`). A header whose tag still shows your **real** address, not the made-up one, is set by the proxy and cannot be forged by a caller. A header that echoes the made-up value is caller-controlled and must not be used for IP-based limits.

This is a diagnostic. Set `SENTRY_CLIENT_IP_TAGS=false` to switch it off without a deploy-time code change, and remove the middleware once per-IP rate limiting uses a verified header.

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `No module named krill.wsgi` / `manage.py not found` | Commands running outside `/app/krill`; confirm `WORKDIR /app/krill` in the production stage (`pwd`, `ls` in a shell: `docker run -it krill:production bash`) |
| Database connection failed | Check `DATABASE_ENGINE`, `DB_*` values, network/firewall access and `DB_SSLMODE`; try `python manage.py dbshell` |
| `DisallowedHost` / allowed hosts error | Add the domain to `DJANGO_ALLOWED_HOSTS` |
| Secret key error | Set `DJANGO_SECRET_KEY` (generator above) |
| Static files missing | `python manage.py collectstatic --noinput` with `DJANGO_SETTINGS_MODULE=krill.settings_production` |
| Need verbose errors | Temporarily set `DJANGO_DEBUG=True`, read logs, then set it back to `False` |

## Resources

[Django deployment checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/) ·
[Docker docs](https://docs.docker.com/) · [Gunicorn](https://gunicorn.org/) ·
[PostgreSQL docs](https://www.postgresql.org/docs/)
