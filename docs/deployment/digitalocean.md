# DigitalOcean App Platform

Platform-specific steps. General build, environment variable and security information is in
the [deployment guide](README.md).

## How it deploys

App Platform builds the repository [`Dockerfile`](../../Dockerfile) (production stage). The
container's `CMD` runs migrations and then starts gunicorn, so no pre-deploy job is needed.
[`app.yaml`](../../app.yaml) is a reference spec; edits to it are not applied automatically to
an existing app, so change live settings with `doctl apps update` or the console.

## Setup

1. **Create the app**: `doctl apps create --spec app.yaml`, or Console → Apps → Create App.
2. **Bind a PostgreSQL database**: app → Settings → Resources → Link Resource → Database.
   The binding provides `${db.DATABASE}`, `${db.USERNAME}`, `${db.PASSWORD}`, `${db.HOST}`,
   `${db.PORT}`.
3. **Set environment variables** (console: Settings → Environment Variables, or in the spec's `envs:`):

   ```bash
   DATABASE_ENGINE=postgresql
   DB_NAME=${db.DATABASE}
   DB_USER=${db.USERNAME}
   DB_PASSWORD=${db.PASSWORD}
   DB_HOST=${db.HOST}
   DB_PORT=${db.PORT}
   DB_SSLMODE=require
   DJANGO_SECRET_KEY=<generate; store as an encrypted secret>
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=${APP_DOMAIN}
   DJANGO_SETTINGS_MODULE=krill.settings_production
   ```

   Add the email/Sentry variables from the [reference table](README.md#environment-variables) as needed.
4. **Deploy**: `doctl apps create-deployment <app-id>` or the Console's Deploy button.

HTTPS is automatic. Point the platform health check at `/health/`.

## Common commands

```bash
doctl apps list
doctl apps get <app-id> --format YAML        # inspect env vars and bindings
doctl apps logs <app-id> --follow            # add --type build for build logs
doctl apps update <app-id> --set-env-vars KEY=value
doctl apps update <app-id> --instance-count 2
doctl apps create-deployment <app-id>        # redeploy
```

[`scripts/deploy.sh`](../../scripts/deploy.sh) wraps some of these steps with `doctl`.

## Troubleshooting

- **Won't start**: check build logs, then runtime logs; confirm the database is bound and the
  env vars above are set (`doctl apps get <app-id> --format YAML`).
- **`no module named krill.wsgi`**: the working directory must be `/app/krill`, which the
  Dockerfile sets; see the [deployment guide](README.md#troubleshooting).
- **Cost**: start with `basic-xxs` and a small dev database; scale up when needed.

[App Platform docs](https://docs.digitalocean.com/products/app-platform/) ·
[DO Community](https://www.digitalocean.com/community)
