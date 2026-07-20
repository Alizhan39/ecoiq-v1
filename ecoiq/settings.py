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
    'projects',
    'heating',
    'notifications',
    'hikma',
    'harvester',
    'qdf',

    # Hackathon module (started 2026-07-01) — Conduct AI / BasedAI bounty
    'legacy_safe',

    # Overnight ethical AI agent product module
    'amanah_autopilot',

    # Live visual evidence interface product module
    'omnimodal_evidence_panel',

    # Microsoft ecosystem readiness architecture module
    'microsoft_core_stack',

    # Living digital passport for industrial assets
    'asset_passport',

    # Measurement, reporting and verification of modernisation impact
    'impact_mrv_layer',

    # Reusable industrial modernisation pathways
    'industrial_playbook_library',

    # Supplier and funding matching for financed implementation
    'supplier_funding_marketplace',

    # Investor-grade financial modelling and decision memos
    'institutional_finance_engine',

    # Mobile-first field inspection and evidence capture
    'mobile_inspection_mode',

    # Central operational view of the modernisation project pipeline
    'command_centre',

    # Human-in-the-loop expert review and approval layer
    'governance_expert_review_board',

    # API and enterprise integration connectivity layer
    'api_integration_layer',

    # Investor-grade evidence and due diligence storage
    'data_room_evidence_vault',

    # Country-scale and portfolio-scale transition mapping
    'portfolio_country_transition_atlas',

    # Investor, board and government decision-pack generation
    'executive_briefing_board_pack_generator',

    # Commercial productisation and pricing model
    'revenue_pricing_engine',

    # Approved public-facing verified impact reporting
    'public_trust_impact_portal',

    # Sales, partnership and funder pipeline management
    'sales_crm_partner_pipeline',

    # Post-sale customer success, health scoring and renewal
    'customer_success_renewal_engine',

    # Platform usage, conversion, revenue and impact analytics
    'product_analytics_kpi_engine',

    # Observability and control layer for AI agents
    'ai_agent_operations_console',

    # Security, privacy and compliance governance layer
    'security_privacy_compliance_centre',

    # Production readiness, monitoring and incident response
    'deployment_devops_reliability_centre',

    # Connected relationship graph across assets, evidence and impact
    'knowledge_graph_relationship_map',

    # Visual design system, frontend library stack and Google Stitch prompt library
    'frontend_experience_google_stitch_design_system',

    # Readiness, verification and trust badges across evidence, MRV, finance and governance
    'certification_trust_badge_engine',

    # Frontend delivery plan across Django, Next.js, Microsoft and Google Stitch
    'frontend_implementation_roadmap',

    # Training, evaluation and human-review workflow for EcoIQ AI agents
    'agent_training_evaluation_lab',

    # Training pack for the agent that extracts facts from bills, reports and MRV evidence
    'document_reader_agent_training_pack',

    # Training pack for the agent that separates estimated impact from verified impact
    'mrv_agent_training_pack',

    # Public presentation and control page for the EcoIQ multi-agent Council
    'ai_agent_council',

    # Governed execution layer connecting agent training packs to the Council runtime
    'agent_runtime_model_router',

    # Homepage discovery + interactive testing layer for the 12 operational AI agents
    # (presentation-only: reuses the registry, runtime and Council models above)
    'ai_agent_workbench',

    # Geo-spatial climate intelligence: company/asset locations, climate risk
    # zones and investment opportunities on an interactive map (Phase 1: Kazakhstan)
    'geo_intelligence',

    # Backend Intelligence Engine — Celery/Redis background execution + task
    # observability for company/geo/AI refresh workflows (Phase 1)
    'backend_intelligence_engine',

    # Evidence Memory + Vector Search — evidence/finding chunks embedded and
    # searchable via pgvector, so agents can reuse prior knowledge (Phase 1)
    'evidence_memory',
    'ai_observatory',

    # Pandas Scoring Engine — explainable composite intelligence score
    # (climate risk, evidence quality, investment opportunity, modernisation
    # priority, governance/ESG, geo exposure, confidence). No models of its
    # own — persists onto the existing companies.CompanyScoreSnapshot (Phase 1)
    'pandas_scoring_engine',

    # Intelligence Analytics Engine — explainable classical ML (scikit-learn):
    # similarity, clustering, ranking, distribution and outlier analysis over
    # existing scoring/evidence/geo data. Stateless service layer, no models
    # of its own, no dashboards yet (Phase 1)
    'intelligence_analytics_engine',

    # LangGraph Orchestration — coordinates the existing intelligence modules
    # (Evidence Memory, Geo Intelligence, Pandas Scoring Engine, Intelligence
    # Analytics Engine, the agent execution pipeline) into one structured
    # workflow per request. Does not create new agents/runtime — every node
    # calls an existing service (Phase 1)
    'langgraph_orchestration',

    # Plotly Visual Intelligence — the visual decision-intelligence layer over
    # every module above: KPI overview, explainable score charts, risk/
    # opportunity matrix, similarity, clusters, evidence distribution and the
    # LangGraph orchestration trace. No new models — reads existing data only
    # (Phase 1)
    'plotly_visual_intelligence',

    # Natural-Language Decision Studio — the user-facing orchestration layer
    # above every module in this list: turns a free-text decision question
    # into intent + resolved entities + an explicit capability plan, then
    # calls the existing services directly (never a second orchestrator, a
    # second vector search, or a second scoring formula) (Phase 1)
    'decision_studio',

    # Fintech / capital-allocation layer: operational waste -> financial loss -> governed investment decision
    'waste_to_value_capital_allocation_engine',

    # Commercial subscription layer: institutional accounts, portfolios, ranked opportunities
    'financial_intelligence_cloud',

    # EcoIQ mission layer: AI-planned, human-led, financed and verified stewardship tours
    'khalifa_stewardship_tour_operating_system',

    # EcoIQ's first flagship vertical: institutional-grade gold mining investment
    # intelligence, built entirely on the engines above (Geo Intelligence, Pandas
    # Scoring, Intelligence Analytics, Evidence Memory, AI Agent Workbench,
    # Decision Studio, Plotly Visual Intelligence) — no duplicate engines.
    'gold_intelligence',

    # Investor transparency and capital intelligence layer over gold_intelligence
    # projects — capital traceability, SPV/governance, equipment & insurance
    # lifecycle, a mining digital twin, milestone-based capital control, a
    # deterministic red flag engine and Decision Studio integration.
    'capital_guardian',

    # Evidence-driven company research intelligence: Shariah eligibility
    # screening and EcoIQ 114-KPI (Capital Ethics Compendium) alignment as
    # two explicitly separate lenses over companies.CompanyProfile — never
    # investment advice, never a buy/sell recommendation. Reuses league/
    # companies/evidence_memory/ai_observatory; no duplicate company model.
    'company_intelligence',
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
    # ru / kk / ar / tr disabled for now — translation files kept in locale/
    # for future use. Re-enable by un-commenting the entries below and
    # restoring the language switcher in templates/base.html.
    # ('ru', _('Russian')),
    # ('kk', _('Kazakh')),
    # ('ar', _('Arabic')),
    # ('tr', _('Turkish')),
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

# Agent Runtime & Model Router — live-provider credentials. Blank by default,
# same pattern as ANTHROPIC_API_KEY above: live adapters must fail safely
# (not silently substitute simulated output) whenever these are unset.
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
AZURE_OPENAI_API_KEY = os.environ.get('AZURE_OPENAI_API_KEY', '')
AZURE_OPENAI_ENDPOINT = os.environ.get('AZURE_OPENAI_ENDPOINT', '')

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
# Khalifa Heat lead notifications — falls back to LEAD_NOTIFY_EMAIL if unset.
HEATING_LEADS_NOTIFY_EMAIL = os.environ.get('HEATING_LEADS_NOTIFY_EMAIL', LEAD_NOTIFY_EMAIL)
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

# ── EcoIQ Backend Intelligence Engine — Celery + Redis ────────────────────────
# REDIS_URL is the single source of truth for both broker and result backend
# (one dependency, not two) — set in Render's dashboard for production, or in
# .env locally. Never hardcoded. Defaults to a plain local Redis instance so
# `redis-server` on localhost:6379 (the standard homebrew/apt default) just
# works in development with zero configuration.
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Hard ceilings so a stuck task can never run forever: soft limit raises an
# exception the task can catch and record; hard limit kills it unconditionally
# 30s later. Both intentionally generous (5 min) — these wrap real network
# calls (Meteostat, Anthropic, company-website monitors), not instant jobs.
CELERY_TASK_SOFT_TIME_LIMIT = 270
CELERY_TASK_TIME_LIMIT = 300

# Bounded, explicit retries only — no task in this codebase retries forever.
# Every real task sets its own autoretry_for/retry_backoff/max_retries directly
# on the @shared_task decorator (see backend_intelligence_engine/tasks.py) —
# deliberately NOT also set here via CELERY_TASK_ANNOTATIONS, which overrides
# (not merely defaults) a task's own decorator kwargs and would silently
# change a task's real retry ceiling out from under it.

# A worker takes on one task at a time and re-fetches only after finishing —
# safer for the mix of short (cache-only) and slower (network/LLM) tasks here
# than Celery's default prefetch-4 behaviour, which can let a slow task starve
# others queued behind it on the same worker.
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
# Restart each worker process after 100 tasks — the same "recycle to avoid
# creeping memory" defence start.sh already applies to gunicorn workers.
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100

# Track when a task starts executing (not just when it finishes) — needed so
# BackgroundTaskRun can honestly distinguish QUEUED from RUNNING.
CELERY_TASK_TRACK_STARTED = True

# Available for any code path that calls `.delay()`/`.apply_async()` and
# needs it to run inline without a broker (e.g. a one-off script). The test
# suite itself doesn't rely on this — it calls `task.apply(...)`, Celery's
# own always-synchronous test entrypoint, regardless of this setting.
CELERY_TASK_ALWAYS_EAGER = os.environ.get('CELERY_TASK_ALWAYS_EAGER', 'False') == 'True'
CELERY_TASK_EAGER_PROPAGATES = True
