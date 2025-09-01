# Krill Makefile
# Provides convenient commands for both local development and Docker containers

.PHONY: help build-dev build-test build-prod build-all test run-dev run-prod clean
.PHONY: server migrate makemigrations shell collectstatic createsuperuser
.PHONY: test-local test-docker security-check deploy-check

# Default target
help:
	@echo "Krill Development Commands"
	@echo "=========================="
	@echo ""
	@echo "Local Development Commands:"
	@echo "  server        - Run Django development server"
	@echo "  migrate       - Run database migrations"
	@echo "  makemigrations - Create new migrations"
	@echo "  shell         - Open Django shell"
	@echo "  collectstatic - Collect static files"
	@echo "  createsuperuser - Create admin user"
	@echo "  dbshell       - Open database shell"
	@echo "  showmigrations - Show migration status"
	@echo "  check         - Run Django system checks"
	@echo ""
	@echo "Testing Commands:"
	@echo "  test-local    - Run tests locally"
	@echo "  test-docker   - Run tests in Docker container"
	@echo "  security-check - Run security validation"
	@echo ""
	@echo "Docker Commands:"
	@echo "  build-dev     - Build development image"
	@echo "  build-test    - Build testing image"
	@echo "  build-prod    - Build production image"
	@echo "  build-all     - Build all images"
	@echo "  run-dev       - Run development container"
	@echo "  run-prod      - Run production container"
	@echo "  docker-shell  - Access container shell"
	@echo ""
	@echo "Data Management:"
	@echo "  flush         - Flush database"
	@echo "  loaddata      - Load sample data"
	@echo "  setup         - Setup development environment"
	@echo "  reset         - Reset development environment"
	@echo ""
	@echo "Utility Commands:"
	@echo "  clean         - Remove all krill images"
	@echo "  logs          - Show container logs"
	@echo "  deploy-check  - Run deployment checks"

# Build commands
build-dev:
	@echo "Building development image..."
	./build.sh development

build-test:
	@echo "Building testing image..."
	./build.sh testing

build-prod:
	@echo "Building production image..."
	./build.sh production

build-all:
	@echo "Building all images..."
	./build.sh all

# Run commands
run-dev:
	@echo "Running development container..."
	docker run -p 8000:8000 krill:development

run-prod:
	@echo "Running production container..."
	@echo "Note: Set environment variables for database connection"
	docker run -p 8000:8000 \
		-e DJANGO_SECRET_KEY=your-secret-key \
		-e DB_NAME=your_db_name \
		-e DB_USER=your_db_user \
		-e DB_PASSWORD=your_db_password \
		-e DB_HOST=your_db_host \
		-e REDIS_URL=redis://your_redis_host:6379/1 \
		krill:production

# Local Development Commands
server:
	@echo "Starting Django development server..."
	cd krill && python manage.py runserver

migrate:
	@echo "Running database migrations..."
	cd krill && python manage.py migrate

makemigrations:
	@echo "Creating new migrations..."
	cd krill && python manage.py makemigrations

shell:
	@echo "Opening Django shell..."
	cd krill && python manage.py shell

collectstatic:
	@echo "Collecting static files..."
	cd krill && python manage.py collectstatic --noinput

createsuperuser:
	@echo "Creating superuser..."
	cd krill && python manage.py createsuperuser

# Testing Commands
test-local:
	@echo "Running tests locally..."
	cd krill && python manage.py test --verbosity=2

test-docker:
	@echo "Building and running tests in Docker..."
	./build.sh test

security-check:
	@echo "Running security validation..."
	cd krill && python run_security_check.py

# Docker Commands
test:
	@echo "Building and running tests..."
	./build.sh test

# Utility Commands
clean:
	@echo "Removing all krill images..."
	docker rmi krill:development krill:testing krill:production 2>/dev/null || true

logs:
	@echo "Container logs (if running):"
	docker logs $$(docker ps -q --filter ancestor=krill:development) 2>/dev/null || \
	docker logs $$(docker ps -q --filter ancestor=krill:production) 2>/dev/null || \
	echo "No krill containers running"

docker-shell:
	@echo "Accessing container shell..."
	@if [ "$$(docker ps -q --filter ancestor=krill:development)" ]; then \
		docker exec -it $$(docker ps -q --filter ancestor=krill:development) /bin/bash; \
	elif [ "$$(docker ps -q --filter ancestor=krill:production)" ]; then \
		docker exec -it $$(docker ps -q --filter ancestor=krill:production) /bin/bash; \
	else \
		echo "No krill containers running. Start one first with 'make run-dev' or 'make run-prod'"; \
	fi

deploy-check:
	@echo "Running deployment checks..."
	cd krill && python manage.py check --deploy

# Additional Development Commands
flush:
	@echo "Flushing database..."
	cd krill && python manage.py flush

loaddata:
	@echo "Loading sample data..."
	cd krill && python manage.py loaddata sample_fixtures.json

dbshell:
	@echo "Opening database shell..."
	cd krill && python manage.py dbshell

showmigrations:
	@echo "Showing migration status..."
	cd krill && python manage.py showmigrations

check:
	@echo "Running Django system checks..."
	cd krill && python manage.py check

# Development Setup Commands
setup:
	@echo "Setting up development environment..."
	cd krill && python manage.py migrate
	@echo "Development setup complete!"

reset:
	@echo "Resetting development environment..."
	cd krill && python manage.py flush --noinput
	cd krill && python manage.py loaddata sample_fixtures.json
	@echo "Development environment reset complete!"
