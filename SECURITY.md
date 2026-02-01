# Security Implementation & Deployment Guide for Krill

## 🎯 Overview

This document provides a comprehensive security implementation and deployment guide for the Krill Django application. It combines security requirements, implementation details, and deployment procedures into a single reference.

## 📁 Security Implementation Status

### ✅ **Completed Security Files**

#### 1. Security Test Suite (`security_tests.py`)
- **Status**: ✅ **IMPLEMENTED** - 29 comprehensive security tests
- **Coverage**: Authentication, Authorization, CSRF, SQL Injection, XSS, Input Validation, Session Security, Security Headers, Audit Logging, Configuration
- **Test Categories**:
  - Authentication Security Tests (5 tests)
  - Authorization Security Tests (4 tests)
  - CSRF Protection Tests (3 tests)
  - SQL Injection Tests (2 tests)
  - XSS Protection Tests (3 tests)
  - Input Validation Tests (3 tests)
  - Session Security Tests (2 tests)
  - Security Headers Tests (2 tests)
  - Audit Logging Tests (2 tests)
  - Configuration Security Tests (3 tests)

#### 2. Production Settings (`settings_production.py`)
- **Status**: ✅ **IMPLEMENTED** - Production-ready configuration
- **Features**:
  - Security headers (HSTS, X-Frame-Options, X-Content-Type-Options)
  - HTTPS enforcement with SSL redirect
  - Secure session settings (HTTPOnly cookies, secure flags)
  - PostgreSQL with SSL connections
  - Enhanced password validation (12+ characters)
  - Rate limiting configuration
  - Comprehensive logging setup
  - File upload security (type validation, size limits)
  - Backup configuration with encryption

#### 3. Deployment Script (`deploy.py`)
- **Status**: ✅ **IMPLEMENTED** - Automated deployment with security validation
- **Features**:
  - Environment validation (Python version, dependencies)
  - Security checks (SECRET_KEY, database connection)
  - Test execution (security tests, Django deployment checks)
  - Backup creation before deployment
  - Comprehensive security report generation

#### 4. Quick Security Check (`run_security_check.py`)
- **Status**: ✅ **IMPLEMENTED** - Lightweight security validation
- **Features**:
  - Basic security checks without full test setup
  - Critical issue detection (DEBUG, SECRET_KEY, middleware)
  - Dependency vulnerability scanning
  - File permissions validation

#### 5. Updated Requirements (`requirements.txt`)
- **Status**: ✅ **IMPLEMENTED** - Production dependencies with security packages
- **Added Packages**:
  - `psycopg2-binary` - PostgreSQL adapter
  - `redis`, `django-redis` - Caching and sessions
  - `django-ratelimit`, `django-axes` - Rate limiting and login tracking
  - `python-dotenv`, `django-environ` - Environment management
  - `sentry-sdk` - Error tracking and monitoring
  - `bandit`, `safety` - Security analysis tools
  - `gunicorn`, `whitenoise` - Production server and static files

## 🔒 **Critical Security Issues - Current Status**

### ❌ **Issues Requiring Immediate Attention**

#### 1. SECRET_KEY Configuration
- **Status**: ❌ **CRITICAL** - Still using default Django key
- **Impact**: High security risk
- **Solution**:
  ```bash
  # Generate new key:
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```

#### 2. DEBUG Mode
- **Status**: ❌ **CRITICAL** - Set to True in development
- **Impact**: Information disclosure in production
- **Solution**: Set `DEBUG = False` in production settings

#### 3. ALLOWED_HOSTS Configuration
- **Status**: ⚠️ **NEEDS CONFIGURATION** - Not set for production domain
- **Impact**: Potential security vulnerability
- **Solution**: Configure with actual domain names in production

#### 4. Environment Variables
- **Status**: ⚠️ **MISSING** - Critical variables not set
- **Impact**: Application won't function in production
- **Solution**: Create `.env` file with required variables

### ✅ **Security Features Successfully Implemented**

#### Authentication & Authorization
- ✅ Login required protection on all views
- ✅ Role-based access control (viewer, lab_member, lab_manager, lab_admin)
- ✅ Object-level permissions
- ✅ Session security with timeout
- ✅ CSRF protection on all forms
- ✅ Password strength validation

#### Data Protection
- ✅ SQL injection prevention (parameterized queries)
- ✅ XSS protection (input sanitization)
- ✅ File upload validation
- ✅ Input validation and sanitization
- ✅ Secure file storage

#### Infrastructure Security
- ✅ HTTPS enforcement configuration
- ✅ Security headers (HSTS, X-Frame-Options, etc.)
- ✅ Secure cookie settings
- ✅ Database SSL connections
- ✅ Rate limiting configuration
- ✅ Audit logging implementation

## 🚀 **Deployment Procedure**

### **Step 1: Environment Setup**

#### 1.1 Generate New SECRET_KEY
```bash
# Generate a new secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

#### 1.2 Create Environment File
```bash
# Create .env file with your actual values
cat > .env << EOF
DJANGO_SECRET_KEY=your-generated-secret-key-here
DB_NAME=krill_production
DB_USER=krill_user
DB_PASSWORD=secure-database-password
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://127.0.0.1:6379/1
EMAIL_HOST=smtp.your-provider.com
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=noreply@your-domain.com
EOF
```

#### 1.3 Install Dependencies
```bash
# Install production dependencies
pip install -r requirements.txt
```

### **Step 2: Database Setup**

#### 2.1 PostgreSQL Database Creation
```sql
-- Create database and user
CREATE DATABASE krill_production;
CREATE USER krill_user WITH PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE krill_production TO krill_user;
ALTER USER krill_user CREATEDB;
```

### **Step 3: Security Validation**

#### 3.1 Run Quick Security Check
```bash
# Run basic security validation
python run_security_check.py
```

#### 3.2 Run Full Security Test Suite
```bash
# Run comprehensive security tests
python manage.py test security_tests --verbosity=2
```

#### 3.3 Run Django Deployment Checks
```bash
# Run Django's built-in deployment checks
python manage.py check --deploy
```

### **Step 4: Production Deployment**

#### 4.1 Configure Production Settings
```bash
# Set production settings
export DJANGO_SETTINGS_MODULE=krill.settings_production
```

#### 4.2 Database Migration
```bash
# Run database migrations
python manage.py migrate
```

#### 4.3 Static Files Collection
```bash
# Collect static files
python manage.py collectstatic --noinput
```

#### 4.4 Create Superuser
```bash
# Create initial admin user
python manage.py createsuperuser
```

#### 4.5 Start Production Server
```bash
# Start with Gunicorn
gunicorn krill.wsgi:application --bind 0.0.0.0:8000
```

## 🔧 **Configuration Examples**

### **Nginx Configuration**
```nginx
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Static files
    location /static/ {
        alias /path/to/your/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /path/to/your/media/;
        expires 1y;
        add_header Cache-Control "public";
    }
    
    # Application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### **Firewall Configuration**
```bash
# Configure firewall
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (redirect to HTTPS)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

## 📋 **Pre-Deployment Checklist**

### **Critical Security Requirements**
- [ ] **SECRET_KEY**: Generate new secret key for production
- [ ] **DEBUG**: Set to `False` in production
- [ ] **ALLOWED_HOSTS**: Configure with actual domain names
- [ ] **Database**: Use PostgreSQL with SSL connections
- [ ] **HTTPS**: Configure SSL/TLS certificates

### **Security Headers**
- [ ] **HSTS**: Enable HTTP Strict Transport Security
- [ ] **X-Frame-Options**: Set to DENY
- [ ] **X-Content-Type-Options**: Set to nosniff
- [ ] **X-XSS-Protection**: Enable XSS protection
- [ ] **Content-Security-Policy**: Configure CSP headers
- [ ] **Referrer-Policy**: Set to strict-origin-when-cross-origin

### **Authentication & Authorization**
- [ ] **Password Policy**: Enforce strong passwords (12+ characters)
- [ ] **Session Security**: Configure secure session settings
- [ ] **CSRF Protection**: Ensure CSRF tokens on all forms
- [ ] **Rate Limiting**: Implement login attempt limits
- [ ] **Multi-Factor Authentication**: Consider implementing MFA

### **Database Security**
- [ ] **Database User**: Create dedicated database user with minimal privileges
- [ ] **SSL Connections**: Require SSL for database connections
- [ ] **Backup Encryption**: Encrypt database backups
- [ ] **Connection Pooling**: Configure connection limits

### **File Upload Security**
- [ ] **File Type Validation**: Restrict allowed file extensions
- [ ] **File Size Limits**: Set maximum file upload size
- [ ] **Virus Scanning**: Implement file scanning
- [ ] **Secure Storage**: Store files outside web root

### **Logging & Monitoring**
- [ ] **Audit Logging**: Log all security events
- [ ] **Error Logging**: Configure proper error logging
- [ ] **Access Logging**: Log all access attempts
- [ ] **Alert System**: Set up security alerts

## 🧪 **Security Testing**

### **Automated Tests**
```bash
# Run security test suite
python manage.py test security_tests

# Run Django deployment checks
python manage.py check --deploy

# Run security analysis tools
pip install bandit safety
bandit -r krill/
safety check
```

### **Manual Security Checks**
- [ ] Test authentication bypass attempts
- [ ] Verify CSRF protection on all forms
- [ ] Test SQL injection prevention
- [ ] Check XSS protection
- [ ] Verify file upload restrictions
- [ ] Test session security

### **External Security Scans**
- [ ] Run SSL Labs test on your domain
- [ ] Use OWASP ZAP for vulnerability scanning
- [ ] Test with security headers checker
- [ ] Verify CSP implementation

## 📊 **Monitoring & Maintenance**

### **Regular Security Tasks**
- **Weekly**: Review security logs
- **Monthly**: Update dependencies
- **Quarterly**: Security audit
- **Annually**: Penetration testing

### **Security Monitoring Configuration**
```python
# Example monitoring configuration
SECURITY_MONITORING = {
    'LOG_FAILED_LOGINS': True,
    'LOG_PERMISSION_DENIED': True,
    'LOG_SUSPICIOUS_ACTIVITY': True,
    'ALERT_ON_MULTIPLE_FAILURES': True,
    'MAX_LOGIN_ATTEMPTS': 5,
    'LOCKOUT_DURATION': 300,  # 5 minutes
}
```

### **Log Monitoring**
```python
# Configure log rotation
LOGGING = {
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/django.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
        }
    }
}
```

### **Health Checks**
```python
# Implement health check endpoint
def health_check(request):
    return JsonResponse({
        'status': 'healthy',
        'database': check_database_connection(),
        'cache': check_cache_connection(),
        'disk_usage': get_disk_usage(),
    })
```

## 🚨 **Incident Response**

### **Security Incident Procedures**
1. **Immediate Response**: Isolate affected systems
2. **Assessment**: Determine scope and impact
3. **Containment**: Stop the attack
4. **Eradication**: Remove threat
5. **Recovery**: Restore systems
6. **Lessons Learned**: Document and improve

### **Emergency Contacts**
- **Security Team**: security@your-domain.com
- **System Administrator**: admin@your-domain.com
- **Legal Team**: legal@your-domain.com

### **Recovery Procedures**
- [ ] Document system recovery steps
- [ ] Prepare rollback procedures
- [ ] Test disaster recovery plan
- [ ] Maintain emergency access procedures

## 📋 **Compliance Considerations**

### **Data Protection**
- **GDPR**: User consent, data portability, right to be forgotten
- **HIPAA**: If handling medical data, implement additional safeguards
- **SOX**: If applicable, maintain audit trails
- **PCI DSS**: If handling payment data

### **Audit Requirements**
- [ ] Maintain audit trails
- [ ] Regular compliance reviews
- [ ] Document security procedures
- [ ] Train staff on security policies

## 🔗 **Additional Resources**

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)
- [Mozilla Security Guidelines](https://infosec.mozilla.org/guidelines/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

## 📈 **Current Implementation Status**

### **✅ Completed (Ready for Production)**
- Comprehensive security test suite (29 tests)
- Production settings with security configurations
- Deployment automation scripts
- Security validation tools
- Updated dependencies with security packages

### **⚠️ Requires Configuration**
- SECRET_KEY generation and configuration
- Environment variables setup
- Production domain configuration
- SSL certificate installation

### **📋 Next Steps**
1. Generate new SECRET_KEY
2. Create production environment file
3. Configure production domain settings
4. Install SSL certificates
5. Run security validation
6. Deploy to production

---

**Remember**: Security is an ongoing process, not a one-time setup. Regular reviews and updates are essential for maintaining a secure application.
