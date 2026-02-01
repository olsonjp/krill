# AGENTS.md

## Project summary
Krill is a Django application for managing biological sample storage,
tracking, and reporting.

## Key locations
- `krill/`: Django project and apps (person, sample, storage, reports,
  transaction)
- `templates/`: top-level template overrides (admin UI)
- `tests/`: anonymized test data, fixtures, scripts, `run_tests.py`
- `scripts/`: utility scripts (e.g., `clean_whitespace.py`)
- `config/`: configuration files
- `Dockerfile`, `docker-compose.yml`, `build.sh`, `Makefile`: build and
  runtime tooling

## Local setup
1. Python 3.10+, pip, and (recommended) a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Database defaults to SQLite; for PostgreSQL set env vars from
   `env.example` or `env.production`.
4. `manage.py` lives under `krill/`:
   - From repo root: `python krill/manage.py <command>`
   - Or `cd krill` then `python manage.py <command>`

## Common commands (Makefile helpers)
- Run server: `make server`
- Migrations: `make migrate`
- Create superuser: `make createsuperuser`
- Django tests: `make test-local`
- Test data scripts: `make test-data`
- Lint/whitespace cleanup: `make lint`
- Docker tests: `make test-docker` or `./build.sh test`

## Test data notes
- Anonymized fixtures live in `tests/fixtures/sample_fixtures.json`.
- Regenerating anonymized data requires the original
  `ln2_cane4_export.csv` in the repo root (not committed).
- `make setup-test` loads fixtures and creates a test superuser
  (`admin` / `admin`).

## Change guidance
- Add or update tests for custom business logic.
- Keep docs in sync when changing setup, env vars, or tooling.
- Never commit secrets; use env files or platform secret stores.
