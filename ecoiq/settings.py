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

DEBUG = os.environ.get('DEBUG', 'False') == 'True'


def _parse_env_list(key: str, default: str = '') -> list:
    """
    Parse an env var that may be comma- OR space-separated, or both.
    Also strips surrounding and inner quote characters that some platforms
    (Render dashboard, shell quoting) accidentally include in the value.

    Examples that all work:
        ALLOWED_HOSTS=*
        ALLOWED_HOSTS=ecoiq.uk
        ALLOWED_HOSTS=ecoiq.uk www.ecoiq.uk ecoiq.onrender.com
        ALLOWED_HOSTS=ecoiq.uk,www.ecoiq.uk,ecoiq.onrender.com
        ALLOWED_HOSTS=ecoiq.uk, www.ecoiq.uk          (comma + space)
        ALLOWED_HOSTS="ecoiq.uk www.ecoiq.uk"          (quoted)
    """
    raw = os.environ.get(key, default)
    # Strip outer quotes the whole string might be wrapped in
    raw = raw.strip().strip('"').strip("'")
    # Normalise: commas → spaces, then split on any whitespace
    parts = raw.replace(',', ' ').split()
    # Strip residual inner quotes from individual values
    return [p.strip('"').strip("'") for p in parts if p.strip('"').strip("'")]


# Accepts: "ecoiq.uk", "ecoiq.uk www.ecoiq.uk", "ecoiq.uk,www.ecoiq.uk", "*"
ALLOWED_HOSTS = _parse_env_list('ALLOWED_HOSTS', 'localhost 127.0.0.1')

# Accepts: "https://ecoiq.uk", "https://ecoiq.uk,https://www.ecoiq.uk",
#           "https://ecoiq.uk https://www.ecoiq.uk", "https://*.ecoiq.uk"
# Note: bare "https://*" is not valid in Django — use explicit origins or "https://*.domain.com"
CSRF_TRUSTED_ORIGINS = _parse_env_list('CSRF_TRUSTED_ORIGINS', '')

# Log at startup so Gunicorn logs show exactly what Django parsed
# (helps diagnose future 400s without needing a shell)
import sys as _sys
print(
    f"[ecoiq] ALLOWED_HOSTS={ALLOWED_HOSTS}  "
    f"CSRF_TRUSTED_ORIGINS={CSRF_TRUSTED_ORIGINS}  "
    f"DEBUG={DEBUG}",
    file=_sys.stderr,
    flush=True,
)

# ── Applications ──────────────────────────────────────────────────────────────

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sitemaps',

    # REST API
    'rest_framework',

    # Project apps
    'core',
    'audit',
    'leads',
    'league',
    'api',
    # 'cms' removed — Wagtail CMS unregistered (tables orphaned in DB, harmless)
    'ingestion',
    'intelligence',
    'transition',
    'companies',
    'countries',
    'ethics',
    'financing',
]

# ── Middleware ────────────────────────────────────────────────────────────────

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # static files — must be 2nd
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',   # language detection from cookie/Accept-Language
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # wagtail.contrib.redirects.middleware removed — site-specific redirects
    # are handled by Django RedirectView entries in core/urls.py and ecoiq/urls.py
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
                'django.template.context_processors.i18n',   # LANGUAGE_CODE + LANGUAGES in every template
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

from django.utils.translation import gettext_lazy as _

LANGUAGE_CODE = 'en'          # default when no preference is stored

LANGUAGES = [
    ('en', _('English')),
    ('ru', _('Russian')),
    ('kk', _('Kazakh')),
    ('ar', _('Arabic')),
    ('tr', _('Turkish')),
]

# Where Django looks for .po / .mo files
LOCALE_PATHS = [BASE_DIR / 'locale']

# Cookie name for language preference (distinct from django_language default)
LANGUAGE_COOKIE_NAME = 'ecoiq_lang'
LANGUAGE_COOKIE_AGE  = 60 * 60 * 24 * 365   # 1 year

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

# AI Findings Engine — model selection (override in .env if needed)
ECOIQ_AI_MODEL = os.environ.get('ECOIQ_AI_MODEL', 'claude-opus-4-5')

# ── Site URL (used for og:image and share links) ──────────────────────────────
# (Wagtail settings removed — Wagtail uninstalled June 2026)
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
LEAD_NOTIFY_EMAIL  = os.environ.get('LEAD_NOTIFY_EMAIL', 'alizhan@ecoiq.uk')
CALENDLY_URL       = os.environ.get('CALENDLY_URL', '')

# ── Data ingestion API keys ───────────────────────────────────────────────────
# Companies House (UK): free at developer.companieshouse.gov.uk
COMPANIES_HOUSE_API_KEY = os.environ.get('COMPANIES_HOUSE_API_KEY', '')

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

# ── Django REST Framework ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'api.authentication.APIKeyAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'api.throttles.APIKeyRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon':    '20/day',
        'explorer':   '100/day',
        'professional': '2000/day',
        'enterprise':   '50000/day',
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}
