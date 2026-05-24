from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

load_dotenv(override=True)   # local .env wins over shell-inherited vars

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Core ──────────────────────────────────────────────────────────────────────

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-dev-only-CHANGE-IN-PRODUCTION',
)

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# Space-separated list: "myapp.onrender.com localhost"
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost 127.0.0.1').split()

# Required for Render/Railway HTTPS reverse proxy
CSRF_TRUSTED_ORIGINS = [
    h.strip() for h in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split()
    if h.strip()
]

# ── Applications ──────────────────────────────────────────────────────────────

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'audit',
    'leads',
]

# ── Middleware ────────────────────────────────────────────────────────────────

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # static files — must be 2nd
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ecoiq.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ecoiq.wsgi.application'

# ── Database ──────────────────────────────────────────────────────────────────
# DATABASE_URL set → PostgreSQL (production)
# Not set         → SQLite (local development)

DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ── Auth ──────────────────────────────────────────────────────────────────────

LOGIN_URL             = '/login/'
LOGIN_REDIRECT_URL    = '/esg/'
LOGOUT_REDIRECT_URL   = '/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ──────────────────────────────────────────────────────

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ── Static files ──────────────────────────────────────────────────────────────

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Only include custom static dir if it actually exists (safe for fresh clones)
_static_src = BASE_DIR / 'static'
STATICFILES_DIRS = [_static_src] if _static_src.exists() else []
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Media files ───────────────────────────────────────────────────────────────

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── Misc ──────────────────────────────────────────────────────────────────────

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# ── Site URL (used for og:image and share links) ──────────────────────────────
SITE_URL = os.environ.get('SITE_URL', 'https://ecoiq.uk')

# ── Email ─────────────────────────────────────────────────────────────────────
# Dev default: print to console. Production: set EMAIL_* vars in Render dashboard.

EMAIL_BACKEND      = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST         = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT         = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS      = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER    = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'EcoIQ <noreply@ecoiq.uk>')
LEAD_NOTIFY_EMAIL  = os.environ.get('LEAD_NOTIFY_EMAIL', 'hello@ecoiq.uk')
CALENDLY_URL       = os.environ.get('CALENDLY_URL', '')

# Warn at startup if SMTP is configured but credentials are missing
_smtp_backend = 'django.core.mail.backends.smtp.EmailBackend'
if EMAIL_BACKEND == _smtp_backend and not EMAIL_HOST_USER:
    import warnings
    warnings.warn(
        "EMAIL_BACKEND is set to SMTP but EMAIL_HOST_USER is empty. "
        "Emails will fail. Set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in your environment.",
        RuntimeWarning,
        stacklevel=1,
    )

# Max upload size: 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# ── Production security ───────────────────────────────────────────────────────
# All of these are harmless in dev and critical in prod.

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG:
    SECURE_SSL_REDIRECT      = True
    SESSION_COOKIE_SECURE    = True
    CSRF_COOKIE_SECURE       = True
    SECURE_HSTS_SECONDS      = 31536000   # 1 year — set low (60) first deploy, raise after
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD      = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
