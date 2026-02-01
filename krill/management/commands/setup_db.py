"""
Management command to set up and configure databases.

Usage:
    python manage.py setup_db --engine=postgresql
    python manage.py setup_db --engine=sqlite
    python manage.py setup_db --check
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
import os


class Command(BaseCommand):
    help = 'Set up and configure database connections'

    def add_arguments(self, parser):
        parser.add_argument(
            '--engine',
            type=str,
            choices=['sqlite', 'postgresql'],
            help='Database engine to use'
        )
        parser.add_argument(
            '--check',
            action='store_true',
            help='Check current database configuration'
        )
        parser.add_argument(
            '--create-user',
            action='store_true',
            help='Create PostgreSQL user (requires superuser privileges)'
        )

    def handle(self, *args, **options):
        if options['check']:
            self.check_database()
            return

        if options['engine']:
            self.switch_database(options['engine'])
            return

        if options['create_user']:
            self.create_postgresql_user()
            return

        # Show current configuration
        self.stdout.write("Current database configuration:")
        self.check_database()

    def check_database(self):
        """Check current database configuration and connection."""
        current_engine = getattr(settings, 'DATABASE_ENGINE', 'sqlite')
        self.stdout.write(f"Database Engine: {current_engine}")

        db_config = settings.DATABASES['default']
        self.stdout.write(f"Database Engine: {db_config['ENGINE']}")

        if 'NAME' in db_config:
            self.stdout.write(f"Database Name: {db_config['NAME']}")

        if 'HOST' in db_config:
            self.stdout.write(f"Database Host: {db_config['HOST']}")

        if 'PORT' in db_config:
            self.stdout.write(f"Database Port: {db_config['PORT']}")

        # Test connection
        try:
            db_conn = connections['default']
            db_conn.cursor()
            self.stdout.write(
                self.style.SUCCESS("✓ Database connection successful")
            )
        except OperationalError as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Database connection failed: {e}")
            )

    def switch_database(self, engine):
        """Switch to specified database engine."""
        if engine == 'sqlite':
            self.stdout.write("Switching to SQLite...")
            os.environ['DATABASE_ENGINE'] = 'sqlite'
            self.stdout.write(
                self.style.SUCCESS("✓ Switched to SQLite. Restart Django to apply changes.")
            )

        elif engine == 'postgresql':
            self.stdout.write("Switching to PostgreSQL...")
            os.environ['DATABASE_ENGINE'] = 'postgresql'

            # Check if required environment variables are set
            required_vars = ['DB_NAME', 'DB_USER', 'DB_PASSWORD']
            missing_vars = [var for var in required_vars if not os.environ.get(var)]

            if missing_vars:
                self.stdout.write(
                    self.style.WARNING(
                        f"Missing environment variables: {', '.join(missing_vars)}"
                    )
                )
                self.stdout.write("Please set these variables before switching to PostgreSQL")
                return

            self.stdout.write(
                self.style.SUCCESS("✓ Switched to PostgreSQL. Restart Django to apply changes.")
            )

    def create_postgresql_user(self):
        """Create PostgreSQL user and database."""
        try:
            import psycopg2
        except ImportError:
            raise CommandError("psycopg2 is required for PostgreSQL operations")

        db_name = os.environ.get('DB_NAME', 'krill')
        db_user = os.environ.get('DB_USER', 'krill_user')
        db_password = os.environ.get('DB_PASSWORD', '')

        if not db_password:
            raise CommandError("DB_PASSWORD environment variable is required")

        try:
            # Connect to PostgreSQL as superuser (usually postgres)
            conn = psycopg2.connect(
                host=os.environ.get('DB_HOST', 'localhost'),
                port=os.environ.get('DB_PORT', '5432'),
                user='postgres',  # Default superuser
                password=os.environ.get('POSTGRES_PASSWORD', ''),
                database='postgres'
            )

            conn.autocommit = True
            cursor = conn.cursor()

            # Create user
            cursor.execute(f"CREATE USER {db_user} WITH PASSWORD '{db_password}';")
            self.stdout.write(f"✓ Created user: {db_user}")

            # Create database
            cursor.execute(f"CREATE DATABASE {db_name} OWNER {db_user};")
            self.stdout.write(f"✓ Created database: {db_name}")

            # Grant privileges
            cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};")
            self.stdout.write(f"✓ Granted privileges to {db_user}")

            cursor.close()
            conn.close()

            self.stdout.write(
                self.style.SUCCESS("✓ PostgreSQL user and database created successfully")
            )

        except psycopg2.Error as e:
            raise CommandError(f"Failed to create PostgreSQL user/database: {e}")
        except Exception as e:
            raise CommandError(f"Unexpected error: {e}")
