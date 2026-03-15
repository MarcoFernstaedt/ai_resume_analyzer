"""
Django settings for resume_analyzer project.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY: SECRET_KEY must be set via environment variable in production.
# Never commit a real secret key. The fallback below is only for local dev.
_default_secret = 'local-dev-only-change-in-production-!!unsecure!!'
SECRET_KEY = os.environ.get('SECRET_KEY', _default_secret)

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# In production set ALLOWED_HOSTS to your actual domain(s).
# Example: ALLOWED_HOSTS=mysite.com,www.mysite.com
_raw_hosts = os.environ.get('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(',') if h.strip()] or (['*'] if DEBUG else ['localhost'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'resumes',
    'assessments',
    'companies',
    'jobsniper',
    'onboarding',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'onboarding.middleware.OnboardingMiddleware',
]

ROOT_URLCONF = 'resume_analyzer.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'resume_analyzer.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Security headers (enforced in production; no-op in DEBUG) ──────────────
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Upgrade HTTP → HTTPS only when not in local dev
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000  # 1 year in production
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# Cookies
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG   # HTTPS-only in production
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 2 weeks

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = not DEBUG

# Auth
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/auth/login/'

# Ensure onboarding URLs work without 'onboarding/' prefix
# Auth is under /auth/; onboarding wizard is also under /auth/step/

# Claude AI API
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# File upload limits (10MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# JobSniper settings
JOBSNIPER_DB_PATH = os.environ.get(
    'DATABASE_PATH',
    str(BASE_DIR.parent / 'data' / 'jobsniper.db')
)
JOBSNIPER_CONFIG_PATH = os.environ.get(
    'CONFIG_PATH',
    str(BASE_DIR.parent / 'config.yaml')
)
JOBSNIPER_RESUME_PATH = os.environ.get(
    'RESUME_PATH',
    str(BASE_DIR.parent / 'data' / 'resume.txt')
)
