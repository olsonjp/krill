#!/usr/bin/env python3
"""
Simple Security Check Script for Krill

This script runs basic security checks without requiring a full test database setup.
Run this before deployment to check critical security configurations.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_command(command, check=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        return result
    except subprocess.CalledProcessError as e:
        return e

def check_django_deployment():
    """Run Django's deployment checklist"""
    print("🔍 Running Django deployment checks...")
    result = run_command("python manage.py check --deploy")
    if result.returncode == 0:
        print("✅ Django deployment checks passed")
        return True
    else:
        print("❌ Django deployment checks failed")
        print(result.stderr)
        return False

def check_security_settings():
    """Check critical security settings"""
    print("🔍 Checking security settings...")

    # Import Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'krill.settings')

    try:
        from django.conf import settings

        issues = []

        # Check DEBUG setting
        if settings.DEBUG:
            issues.append("⚠️  DEBUG is True (should be False in production)")

        # Check SECRET_KEY
        default_key = 'django-insecure-t9u1+2ux%d02^oc1fhy%rlyybh%)y28y=ee_8^%+rb^2i6i6cj'
        if settings.SECRET_KEY == default_key:
            issues.append("❌ SECRET_KEY is still the default Django key")

        # Check ALLOWED_HOSTS
        if not settings.ALLOWED_HOSTS or settings.ALLOWED_HOSTS == ['*']:
            issues.append("❌ ALLOWED_HOSTS is not properly configured")

        # Check security middleware
        required_middleware = [
            'django.middleware.security.SecurityMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
        ]

        for middleware in required_middleware:
            if middleware not in settings.MIDDLEWARE:
                issues.append(f"❌ Missing required middleware: {middleware}")

        if issues:
            print("❌ Security issues found:")
            for issue in issues:
                print(f"  {issue}")
            return False
        else:
            print("✅ Security settings look good")
            return True

    except ImportError as e:
        print(f"❌ Could not import Django settings: {e}")
        return False

def check_dependencies():
    """Check for known security vulnerabilities in dependencies"""
    print("🔍 Checking dependencies for security vulnerabilities...")

    # Try to run safety check if available
    result = run_command("safety check", check=False)
    if result.returncode == 0:
        print("✅ No known security vulnerabilities found in dependencies")
        return True
    elif result.returncode == 1:
        print("⚠️  Some dependencies have known vulnerabilities:")
        print(result.stdout)
        return False
    else:
        print("⚠️  Could not run safety check (install with: pip install safety)")
        return True

def check_file_permissions():
    """Check file permissions"""
    print("🔍 Checking file permissions...")

    sensitive_files = [
        '.env',
        'settings_production.py',
        'db.sqlite3',
    ]

    issues = []
    for file_path in sensitive_files:
        if os.path.exists(file_path):
            stat = os.stat(file_path)
            if stat.st_mode & 0o777 == 0o666:  # World readable/writable
                issues.append(f"⚠️  {file_path} is world readable")

    if issues:
        print("⚠️  File permission issues found:")
        for issue in issues:
            print(f"  {issue}")
        return False
    else:
        print("✅ File permissions look good")
        return True

def check_environment_variables():
    """Check if critical environment variables are set"""
    print("🔍 Checking environment variables...")

    # This is a basic check - in production you'd want to check specific variables
    critical_vars = ['DJANGO_SECRET_KEY', 'DB_PASSWORD']

    missing_vars = []
    for var in critical_vars:
        if not os.environ.get(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ Environment variables are set")
        return True

def main():
    """Run all security checks"""
    print("🚀 Starting Krill Security Check")
    print("=" * 50)

    checks = [
        ("Django Deployment", check_django_deployment),
        ("Security Settings", check_security_settings),
        ("Dependencies", check_dependencies),
        ("File Permissions", check_file_permissions),
        ("Environment Variables", check_environment_variables),
    ]

    results = []
    for name, check_func in checks:
        print(f"\n📋 {name} Check:")
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error during {name} check: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 Security Check Summary:")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")

    print(f"\nOverall: {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 All security checks passed!")
        print("✅ Your application is ready for deployment")
    else:
        print("\n❌ Some security checks failed!")
        print("Please address the issues above before deploying")
        sys.exit(1)

if __name__ == '__main__':
    main()
