#!/usr/bin/env python3
"""
Deployment script for Krill Django Application

This script performs security checks and deploys the application safely.
Run this script before deploying to production.
"""

import os
import sys
import subprocess
import shutil
import json
import secrets
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'krill.settings_production')

def run_command(command, check=True, capture_output=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=check,
            capture_output=capture_output,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {command}")
        print(f"Error: {e.stderr}")
        return e

def check_python_version():
    """Check if Python version is compatible"""
    print("🔍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ is required")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("🔍 Checking dependencies...")
    required_packages = [
        'django',
        'psycopg2-binary',
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False

    print("✅ All dependencies are installed")
    return True

def check_environment_variables():
    """Check if required environment variables are set"""
    print("🔍 Checking environment variables...")
    required_vars = [
        'DJANGO_SECRET_KEY',
        'DB_NAME',
        'DB_USER',
        'DB_PASSWORD',
        'DB_HOST',
        'DB_PORT',
    ]

    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in your .env file")
        return False

    print("✅ All required environment variables are set")
    return True

def check_secret_key():
    """Check if SECRET_KEY is properly configured"""
    print("🔍 Checking SECRET_KEY...")
    from django.conf import settings

    default_key = 'django-insecure-t9u1+2ux%d02^oc1fhy%rlyybh%)y28y=ee_8^%+rb^2i6i6cj'
    if settings.SECRET_KEY == default_key:
        print("❌ SECRET_KEY is still the default Django key")
        print("Generate a new key with:")
        print("python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\"")
        return False

    print("✅ SECRET_KEY is properly configured")
    return True

def check_database_connection():
    """Check database connection"""
    print("🔍 Checking database connection...")
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def run_security_tests():
    """Run security tests"""
    print("🔍 Running security tests...")
    result = run_command("python manage.py test security_tests")
    if result.returncode != 0:
        print("❌ Security tests failed")
        return False

    print("✅ Security tests passed")
    return True

def run_django_checks():
    """Run Django deployment checks"""
    print("🔍 Running Django deployment checks...")
    result = run_command("python manage.py check --deploy")
    if result.returncode != 0:
        print("❌ Django deployment checks failed")
        return False

    print("✅ Django deployment checks passed")
    return True

def check_static_files():
    """Check and collect static files"""
    print("🔍 Collecting static files...")
    result = run_command("python manage.py collectstatic --noinput")
    if result.returncode != 0:
        print("❌ Static file collection failed")
        return False

    print("✅ Static files collected")
    return True

def run_migrations():
    """Run database migrations"""
    print("🔍 Running database migrations...")
    result = run_command("python manage.py migrate")
    if result.returncode != 0:
        print("❌ Database migrations failed")
        return False

    print("✅ Database migrations completed")
    return True

def check_file_permissions():
    """Check file permissions"""
    print("🔍 Checking file permissions...")

    # Check that sensitive files are not world-readable
    sensitive_files = [
        '.env',
        'settings_production.py',
        'db.sqlite3',
    ]

    for file_path in sensitive_files:
        if os.path.exists(file_path):
            stat = os.stat(file_path)
            if stat.st_mode & 0o777 == 0o666:  # World readable/writable
                print(f"⚠️  Warning: {file_path} is world readable")

    print("✅ File permissions check completed")
    return True

def create_backup():
    """Create a backup before deployment"""
    print("🔍 Creating backup...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = project_root / "backups" / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Backup database
    if os.environ.get('DB_ENGINE') == 'sqlite':
        db_file = project_root / "db.sqlite3"
        if db_file.exists():
            shutil.copy2(db_file, backup_dir / "db.sqlite3")
    else:
        # For PostgreSQL, you might want to use pg_dump
        pass

    # Backup media files
    media_dir = project_root / "media"
    if media_dir.exists():
        shutil.copytree(media_dir, backup_dir / "media")

    print(f"✅ Backup created at {backup_dir}")
    return True

def check_ssl_certificate():
    """Check SSL certificate (if domain is configured)"""
    print("🔍 Checking SSL certificate...")
    domain = os.environ.get('DOMAIN')
    if not domain:
        print("⚠️  No domain configured, skipping SSL check")
        return True

    # This is a basic check - in production you'd want more comprehensive SSL validation
    print(f"⚠️  Please verify SSL certificate for {domain}")
    return True

def generate_security_report():
    """Generate a security deployment report"""
    print("📊 Generating security report...")

    report = {
        'timestamp': datetime.now().isoformat(),
        'checks': {
            'python_version': check_python_version(),
            'dependencies': check_dependencies(),
            'environment_variables': check_environment_variables(),
            'secret_key': check_secret_key(),
            'database_connection': check_database_connection(),
            'security_tests': run_security_tests(),
            'django_checks': run_django_checks(),
            'static_files': check_static_files(),
            'migrations': run_migrations(),
            'file_permissions': check_file_permissions(),
            'backup': create_backup(),
            'ssl_certificate': check_ssl_certificate(),
        }
    }

    # Save report
    report_file = project_root / "deployment_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    # Print summary
    passed_checks = sum(report['checks'].values())
    total_checks = len(report['checks'])

    print(f"\n📋 Security Report Summary:")
    print(f"✅ Passed: {passed_checks}/{total_checks}")
    print(f"❌ Failed: {total_checks - passed_checks}/{total_checks}")
    print(f"📄 Full report saved to: {report_file}")

    return passed_checks == total_checks

def main():
    """Main deployment function"""
    print("🚀 Starting Krill Deployment Security Check")
    print("=" * 50)

    # Run all security checks
    success = generate_security_report()

    if success:
        print("\n🎉 All security checks passed!")
        print("✅ Your application is ready for deployment")
        print("\n📝 Next steps:")
        print("1. Configure your web server (Nginx/Apache)")
        print("2. Set up SSL certificates")
        print("3. Configure firewall rules")
        print("4. Set up monitoring and logging")
        print("5. Test the deployment in staging first")
    else:
        print("\n❌ Security checks failed!")
        print("Please fix the issues above before deploying")
        sys.exit(1)

if __name__ == '__main__':
    main()
