from pathlib import Path
import os
import sys
import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# override=False: a real environment variable (Render dashboard, CI secret,
# shell export) always wins over a .env file. With override=True — the previous
# setting — a stray .env on a production host silently replaced real
# configuration, including DEBUG, which in turn disabled every `if not DEBUG`
# security setting below.
load_dotenv(override=False)

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Environment ───────────────────────────────────────────────────────────────
# Three distinguishable modes: production (the default — nothing is assumed),
# local development (DEBUG=True), and the test runner. Only the latter two get
# generated fallbacks; production must be configured explicitly or refuse to
# start.

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

RUNNING_TESTS = 'test' in sys.argv or Path(sys.argv[0]).name in ('pytest', 'py.test')

# True only when this process must be fully configured from the environment.
IS_PRODUCTION = not (DEBUG or RUNNING_TESTS)

# ── Core ──────────────────────────────────────────────────────────────────────

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')

if not SECRET_KEY:
    if IS_PRODUCTION:
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY is required when DEBUG is False. Set it in the '
            'Render dashboard (the blueprint generates one automatically for '
            'new services). Refusing to start with an insecure fallback key.'
        )
    # Development and test only — never reachable in production.
    SECRET_KEY = 'django-insecure-local-development-and-test-only'


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


# Accepts: "ecoiq.uk", "ecoiq.uk www.ecoiq.uk", "ecoiq.uk,www.ecoiq.uk"
ALLOWED_HOSTS = _parse_env_list('ALLOWED_HOSTS', 'localhost 127.0.0.1')

if IS_PRODUCTION:
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            'ALLOWED_HOSTS is required when DEBUG is False. Set it to the '
            'explicit hostnames this service answers on.'
        )
    if '*' in ALLOWED_HOSTS:
        # A wildcard disables Django's Host-header validation entirely, which
        # re-opens Host-header poisoning of password-reset and absolute URLs.
        raise ImproperlyConfigured(
            'ALLOWED_HOSTS must not contain "*" in production. List the exact '
            'hostnames instead, e.g. '
            '"ecoiq.uk www.ecoiq.uk ecoiq.onrender.com".'
        )

# Accepts: "https://ecoiq.uk", "https://ecoiq.uk,https://www.ecoiq.uk",
#           "https://ecoiq.uk https://www.ecoiq.uk", "https://*.ecoiq.uk"
# Note: bare "https://*" is not valid in Django — use explicit origins or "https://*.domain.com"
CSRF_TRUSTED_ORIGINS = _parse_env_list('CSRF_TRUSTED_ORIGINS', '')

# Startup diagnostic so Gunicorn logs show exactly what Django parsed (helps
# diagnose a 400 without needing a shell). Written to stderr directly rather
# than via `logging` because LOGGING below is not applied until Django finishes
# loading this module. Host names only — never a secret or a credential.
_startup_banner = (
    f'[ecoiq] ALLOWED_HOSTS={ALLOWED_HOSTS}  '
    f'CSRF_TRUSTED_ORIGINS={CSRF_TRUSTED_ORIGINS}  '
    f'DEBUG={DEBUG}'
)
if not RUNNING_TESTS:
    print(_startup_banner, file=sys.stderr, flush=True)

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
    'gcc_investors',
    'league',
    'api',
    # 'cms' removed — Wagtail CMS unregistered (tables orphaned in DB, harmless)
    'ingestion',
    'intelligence',
    'transition',
    'companies',
    'platform_registry',

    # Investor portfolios and watchlists — user-owned holdings valued from the
    # market data already on league.Company. No new market-data source.
    'investor_portfolio',
    'ecoiq_commerce',
    'mobile_auth',
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

    # 114 Good Agents — the 114 canonical EcoIQ principles re-expressed as
    # specialised opportunity-discovery lenses, plus the orchestrator,
    # GoodOpportunity/GoodDeedsEngine, Opportunity Cost, Red Team and Impact
    # Receipt models that sit in front of the existing capital pipeline
    # above. Reuses agent_runtime_model_router / ai_agent_council /
    # langgraph_orchestration for reasoning and capital_guardian /
    # waste_to_value_capital_allocation_engine / evidence_memory for
    # everything downstream of "opportunity qualified" — no new Evidence,
    # Project or MRV model.
    'good_agents',
    # Evidence-backed Organisation/Capability/PublicRoute graph — reusable
    # infrastructure good_agents (ResponsibleParty, FundingMatch) is the
    # first real consumer of; not good_agents-private, so it's listed as
    # its own app rather than a submodule.
    'capability_graph',
    # Consented organisation participation (claims, roles, capability/
    # resource/funding declarations, opportunity routing) — the reciprocal
    # half of capability_graph's externally-discovered evidence.
    'partner_participation',
    # Narrow, opportunity-scoped coordination protocol from "organisation
    # interested" to "consented next step" — reuses partner_participation's
    # RoutingCandidate as its anchor and good_agents/PR5's project/connection
    # bridges for actual promotion; never a generic messaging platform.
    'collaboration_rooms',
    # First Real Outreach Readiness (PR12) — a stricter, separate
    # governance layer for "the first time EcoIQ contacts a real external
    # organisation": candidate suitability review, recipient responsibility
    # test, route provenance, message versioning, risk review, dry run,
    # founder send decision. Deliberately does not reuse PR5's OutreachDraft
    # send path — no code here can perform a real send.
    'outreach_readiness',
    # Actionable Public-Need Discovery (PR13) — sits between discovery
    # (GoodOpportunity, already evidence-gated) and outreach_readiness
    # (which governs contacting a real organisation): resolves jurisdiction,
    # separates evidence-publisher from responsible-authority/implementer/
    # funder roles, generates the smallest legitimate next action, and
    # prefers an existing official public process over EcoIQ outreach where
    # one exists. Never weakens or bypasses outreach_readiness's own
    # recipient-responsibility test.
    'public_need_discovery',
    # First Legitimate Public Action (PR14) — takes ONE real actionable
    # candidate from public_need_discovery and prepares the exact
    # legitimate action (official process / clarification / referral /
    # data request / funding surfacing / zero-capital connection /
    # outreach handoff), never defaulting to email, never executing
    # anything externally. EXTERNAL_PUBLIC_ACTIONS_ENABLED stays False.
    'public_action_preparation',

    # Industrial Digital Twin & Modernisation Engine — a living baseline
    # model of an industrial asset (manufacturing facility, mine, mineral
    # deposit, processing plant, energy asset, infrastructure project, or
    # generic industrial asset): components, process graph, resource flows,
    # governed metrics and data gaps, deterministic loss detection and
    # scenario simulation, a draft/versioned Qur'anic Stewardship KPI
    # engine, and Agent Council + human-approval promotion into the existing
    # waste_to_value_capital_allocation_engine capital-allocation workflow.
    'digital_twin',

    # Global Research, Technology & Manufacturer Discovery Engine — governed
    # discovery of technologies, manufacturers and products worldwide to
    # solve a verified Digital Twin problem: supplier-neutral requirements,
    # multi-layer evidence search, structured claim extraction with a
    # deterministic evidence hierarchy, mandatory-requirement compatibility
    # gating, transparent comparative scoring, Agent Council review, and
    # human-approved promotion into the existing Digital Twin / capital-
    # allocation workflow. Never auto-contacts a vendor or commits capital.
    'global_research',

    # EcoIQ AI Gateway — one provider-neutral, free-only AI system in front of
    # OpenRouter, Bytez and NVIDIA NIM. EcoIQ selects the model automatically;
    # normal users never see or send a model selection.
    # Distinct from agent_runtime_model_router (which governs *agent* execution
    # against Anthropic/OpenAI/Gemini/Azure) — this is the user-facing chat
    # gateway, and it never routes to a paid model.
    'ai_gateway',
]

# PR14 — hardcoded false; no code path in public_action_preparation reads
# this to perform a real submission, referral, application, or contact.
EXTERNAL_PUBLIC_ACTIONS_ENABLED = False

# ── Middleware ────────────────────────────────────────────────────────────────

MIDDLEWARE = [
    # First, so the request id covers everything below it — including anything
    # logged by security middleware.
    'core.logging_middleware.RequestContextMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise, subclassed so the Vite-hashed SPA bundle under
    # /static/spa/assets/ is cached as immutable. See core/whitenoise.py.
    'core.whitenoise.SpaAwareWhiteNoiseMiddleware',   # static files — must be 2nd
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',   # language detection from cookie/Accept-Language
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Immediately after authentication, because it reads request.user.
    # De-publishes the experimental and legacy surfaces — see core/access.py
    # for the list and the reasoning.
    'core.access.ExperimentalSurfaceMiddleware',
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
                'ecoiq.context_processors.analytics',
            ],
        },
    },
]

WSGI_APPLICATION = 'ecoiq.wsgi.application'

# ── Database ──────────────────────────────────────────────────────────────────
# DATABASE_URL set → PostgreSQL (production)
# Not set         → SQLite (local development and tests only)
#
# Production must never fall through to SQLite: on Render that would create an
# empty database file on ephemeral disk, so the deploy would look healthy while
# serving no data and losing every write on the next restart.

if IS_PRODUCTION and not os.environ.get('DATABASE_URL', '').strip():
    raise ImproperlyConfigured(
        'DATABASE_URL is required when DEBUG is False. The Render blueprint '
        'supplies it from the ecoiq-db service; refusing to start on a local '
        'SQLite fallback in production.'
    )

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
# STORAGES, not STATICFILES_STORAGE.
#
# `STATICFILES_STORAGE` was removed in Django 5.1. This project pins Django
# 5.2, so the line that used to live here — naming
# CompressedManifestStaticFilesStorage — was silently ignored, and production
# has been serving static files through the plain StaticFilesStorage: no gzip,
# no brotli, no content hashing. Verified by reading
# `settings.STORAGES['staticfiles']` on a booted instance.
#
# Compression is restored here. Content HASHING deliberately is not: the
# manifest backend rewrites every url() and sourceMappingURL it finds and fails
# the build when a referenced file is missing, and this repository has 338
# templates and a large legacy asset tree that has never been through that
# check. Turning it on is its own piece of work with its own failure mode, not
# a side effect of a frontend deployment.
#
# The SPA does not need it. Vite content-hashes its own filenames, and
# core.whitenoise.SpaAwareWhiteNoiseMiddleware marks that directory immutable —
# so the bundle gets far-future caching without the manifest machinery.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

# ── Media files ───────────────────────────────────────────────────────────────

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── Durable media storage (Cloudflare R2) ─────────────────────────────────────
#
# MEDIA_ROOT above is the web service's own filesystem, which Render replaces on
# every deploy. An uploaded evidence document therefore survived until the next
# release while its database row survived forever — a reference to a file that
# no longer exists, which the application reads as "the document is on file".
#
# Measured on production before this was written: MEDIA_ROOT did not exist,
# 0 files, 0 bytes, 0 database references across all six upload fields. Nothing
# had been lost because nothing had been uploaded. That is the good moment.
#
# OPT-IN. The filesystem stays the default so local development and the test
# suite need no credentials and no network. R2 is selected only by setting
# MEDIA_STORAGE_BACKEND=r2.
MEDIA_STORAGE_BACKEND = os.environ.get('MEDIA_STORAGE_BACKEND', 'filesystem').strip().lower()

#: Presigned read URLs expire in five minutes by default. A URL that leaks —
#: pasted into a ticket, captured by an intermediary — stops working quickly.
#: The signature is derived from the credentials and never contains them.
R2_SIGNED_URL_EXPIRY_SECONDS = int(os.environ.get('R2_SIGNED_URL_EXPIRY_SECONDS', '300'))

MEDIA_USES_R2 = MEDIA_STORAGE_BACKEND == 'r2'

if MEDIA_USES_R2:
    _r2 = {name: os.environ.get(name, '').strip() for name in (
        'R2_ACCOUNT_ID', 'R2_BUCKET_NAME', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY')}
    _missing = sorted(k for k, v in _r2.items() if not v)
    if _missing:
        # FAIL CLOSED. Falling back to the local filesystem here would write
        # uploads to a disk that is destroyed on the next deploy, and would do
        # it silently — the exact failure this configuration exists to end.
        raise ImproperlyConfigured(
            'MEDIA_STORAGE_BACKEND=r2 but these variables are missing: '
            f'{", ".join(_missing)}. Refusing to start on ephemeral local '
            'storage. Unset MEDIA_STORAGE_BACKEND to use the filesystem.'
        )

    # Account-scoped S3 endpoint. Derived rather than configured so the endpoint
    # can never disagree with the account the credentials belong to.
    R2_ENDPOINT_URL = os.environ.get(
        'R2_ENDPOINT_URL', f'https://{_r2["R2_ACCOUNT_ID"]}.r2.cloudflarestorage.com').strip()

    STORAGES['default'] = {
        'BACKEND': 'core.storage_r2.R2MediaStorage',
        'OPTIONS': {
            'bucket_name': _r2['R2_BUCKET_NAME'],
            'access_key': _r2['R2_ACCESS_KEY_ID'],
            'secret_key': _r2['R2_SECRET_ACCESS_KEY'],
            'endpoint_url': R2_ENDPOINT_URL,
            # R2 implements neither ACLs nor regions; 'auto' is what it expects,
            # and signature v4 is required.
            'region_name': 'auto',
            'signature_version': 's3v4',
            'querystring_expire': R2_SIGNED_URL_EXPIRY_SECONDS,
        },
    }


# ── Misc ──────────────────────────────────────────────────────────────────────

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Public-form abuse protection (notifications/antispam) ─────────────────────
# Cloudflare Turnstile. Both keys come from the environment and are never
# committed. TURNSTILE_SITE_KEY is public (rendered in the form);
# TURNSTILE_SECRET_KEY is server-side only.
#
# Unconfigured behaviour is deliberately asymmetric: development and tests pass
# through so no Cloudflare account is needed to work locally, while production
# fails closed — an unprotected public form in production is exactly the defect
# that produced 937 spam notifications.
TURNSTILE_SITE_KEY = os.environ.get('TURNSTILE_SITE_KEY', '')
TURNSTILE_SECRET_KEY = os.environ.get('TURNSTILE_SECRET_KEY', '')
TURNSTILE_TIMEOUT_SECONDS = float(os.environ.get('TURNSTILE_TIMEOUT_SECONDS', '5'))

# Rate limits per public form: {scope: (limit, window_seconds)}.
ANTISPAM_LIMITS = {
    'ip':      (int(os.environ.get('ANTISPAM_IP_LIMIT', '5')), 60 * 60),
    'email':   (int(os.environ.get('ANTISPAM_EMAIL_LIMIT', '3')), 60 * 60 * 24),
    'message': (int(os.environ.get('ANTISPAM_MESSAGE_LIMIT', '2')), 60 * 60 * 24),
    'global':  (int(os.environ.get('ANTISPAM_GLOBAL_LIMIT', '200')), 60 * 60),
}

# Volume alert thresholds (notifications/antispam/monitoring.py).
ANTISPAM_ALERT_REJECTIONS_PER_10MIN = int(os.environ.get('ANTISPAM_ALERT_REJECTIONS', '30'))
ANTISPAM_ALERT_FINGERPRINT_PER_DAY = int(os.environ.get('ANTISPAM_ALERT_FINGERPRINT', '100'))

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# /api/v1/semantic-search/ vector path. OFF by default and must stay off until
# BOTH are true: sentence-transformers + torch are installed (they are
# deliberately absent from requirements.txt), and league.Company actually has an
# `embedding` column. Until then the endpoint serves keyword search and reports
# `"method": "text"` honestly in its response.
ECOIQ_SEMANTIC_SEARCH_ENABLED = os.environ.get(
    'ECOIQ_SEMANTIC_SEARCH_ENABLED', 'false'
).strip().lower() in ('true', '1', 'yes', 'on')

# AI Findings Engine — model selection (override in .env if needed)
ECOIQ_AI_MODEL = os.environ.get('ECOIQ_AI_MODEL', 'claude-opus-4-5')

# EcoIQ Commercial Platform — billing provider seam (see ecoiq_commerce/services/billing.py).
# 'none'   = NullBillingProvider (manual/invoiced billing, no payment gateway).
# 'stripe' = StripeBillingProvider (Stripe Checkout / Billing / Customer Portal).
# Exactly one provider is ever active — see services/billing.py:require_provider.
ECOIQ_BILLING_PROVIDER = os.environ.get('ECOIQ_BILLING_PROVIDER', 'none')


def _env_flag(key: str, default: bool = False) -> bool:
    """Parse a boolean env var the same way ECOIQ_SEMANTIC_SEARCH_ENABLED does."""
    raw = os.environ.get(key)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in ('true', '1', 'yes', 'on')


# ── Stripe (ecoiq_commerce billing) ───────────────────────────────────────────
# Merchant of record: Stoke Share Ltd, trading as EcoIQ (https://ecoiq.uk).
#
# Every credential is read from the environment ONLY — never a literal in
# source, never a committed .env. Blank is a safe, supported state: with no
# secret key the gateway refuses to create sessions and the /billing/ checkout
# endpoints return an explicit "billing is not configured" error rather than
# half-working. Nothing here is ever rendered into a page except the
# PUBLISHABLE key, which is designed to be public.

STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '').strip()
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '').strip()
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '').strip()

# Recurring price IDs. `price_…` values are not secrets, but they are still
# env-driven so a test-mode and a live-mode catalogue can never be confused
# with each other in source control.
STRIPE_PRICE_STARTER_MONTHLY = os.environ.get('STRIPE_PRICE_STARTER_MONTHLY', '').strip()
STRIPE_PRICE_STARTER_YEARLY = os.environ.get('STRIPE_PRICE_STARTER_YEARLY', '').strip()
STRIPE_PRICE_PRO_MONTHLY = os.environ.get('STRIPE_PRICE_PRO_MONTHLY', '').strip()
STRIPE_PRICE_PRO_YEARLY = os.environ.get('STRIPE_PRICE_PRO_YEARLY', '').strip()

# Blank = use the version the installed stripe SDK pins (stripe 15.4.0 →
# 2026-07-29.dahlia). Set explicitly only when deliberately pinning to an
# older version; ecoiq_commerce.services.stripe_sync reads both the current
# and the pre-"basil" shapes of Subscription/Invoice, so either works.
STRIPE_API_VERSION = os.environ.get('STRIPE_API_VERSION', '').strip()

# ── Stripe Tax ────────────────────────────────────────────────────────────────
# OFF by default and must stay off until Stoke Share Ltd's relevant tax
# registrations are confirmed and entered in the Stripe Dashboard. Enabling
# automatic_tax without registrations produces incorrect tax on real invoices,
# so this is a deliberate configuration latch rather than a code change:
# set STRIPE_AUTOMATIC_TAX_ENABLED=true once registrations are live.
STRIPE_AUTOMATIC_TAX_ENABLED = _env_flag('STRIPE_AUTOMATIC_TAX_ENABLED', False)
# Collecting a customer VAT/GST number only makes sense alongside Stripe Tax.
STRIPE_TAX_ID_COLLECTION_ENABLED = _env_flag('STRIPE_TAX_ID_COLLECTION_ENABLED', False)

# Optional Customer Portal configuration id (bpc_…). Blank = the Stripe
# Dashboard's default portal configuration for the account.
STRIPE_BILLING_PORTAL_CONFIGURATION_ID = os.environ.get(
    'STRIPE_BILLING_PORTAL_CONFIGURATION_ID', '').strip()

# ── Live-mode latch ───────────────────────────────────────────────────────────
# The integration is built and tested against Stripe TEST mode. Pointing it at
# a live secret key is a commercial decision (real money, real customers), not
# something that should happen as a side effect of pasting a key into a
# dashboard — so a live key is refused unless this flag is explicitly set too.
STRIPE_LIVE_MODE_ALLOWED = _env_flag('STRIPE_LIVE_MODE_ALLOWED', False)

if STRIPE_SECRET_KEY.startswith('sk_live_') and not STRIPE_LIVE_MODE_ALLOWED:
    raise ImproperlyConfigured(
        'STRIPE_SECRET_KEY is a LIVE key but STRIPE_LIVE_MODE_ALLOWED is not '
        'set. Live mode charges real customers. Set '
        'STRIPE_LIVE_MODE_ALLOWED=true only after the Stripe account, tax '
        'registrations and webhook endpoint have been verified in live mode.'
    )


# EcoIQ Mobile/Desktop App — device-session token lifetimes (mobile_auth app).
# Access tokens are short-lived and re-checked against a live, non-revoked
# DeviceSession on every request; refresh tokens are long-lived and rotate
# on every use (see mobile_auth/models.py:DeviceSession).
import datetime as _datetime
MOBILE_AUTH_ACCESS_TOKEN_TTL = _datetime.timedelta(
    minutes=int(os.environ.get('MOBILE_AUTH_ACCESS_TOKEN_TTL_MINUTES', '15')))
MOBILE_AUTH_REFRESH_TOKEN_TTL = _datetime.timedelta(
    days=int(os.environ.get('MOBILE_AUTH_REFRESH_TOKEN_TTL_DAYS', '60')))

# EcoIQ Mobile/Desktop App — remote configuration served at /api/v1/app-config/
# (api/app_views.py). Kept in settings (env-overridable) rather than hard-coded
# in the client binary, per the app spec's "do not hard-code important
# commercial or compliance decisions into the application binary".
ECOIQ_APP_MIN_SUPPORTED_VERSION = os.environ.get('ECOIQ_APP_MIN_SUPPORTED_VERSION', '1.0.0')
ECOIQ_APP_LATEST_VERSION = os.environ.get('ECOIQ_APP_LATEST_VERSION', '1.0.0')
ECOIQ_APP_MAINTENANCE_MODE = os.environ.get('ECOIQ_APP_MAINTENANCE_MODE', 'false').lower() == 'true'
ECOIQ_APP_FORCE_UPDATE = os.environ.get('ECOIQ_APP_FORCE_UPDATE', 'false').lower() == 'true'


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

# ── Analytics & search-engine verification ──────────────────────────────────
# All blank by default — no script or verification meta tag renders until the
# corresponding env var is set on Render. Never hardcode real IDs here.
# Set at most one of GTM_CONTAINER_ID / GA4_MEASUREMENT_ID: if GTM is present
# it owns tag firing (configure GA4 as a tag inside the GTM container) so the
# raw gtag.js loader is skipped — this is what keeps analytics scripts from
# ever loading twice on the same page.
GA4_MEASUREMENT_ID       = os.environ.get('GA4_MEASUREMENT_ID', '').strip()
GTM_CONTAINER_ID         = os.environ.get('GTM_CONTAINER_ID', '').strip()
GOOGLE_SITE_VERIFICATION = os.environ.get('GOOGLE_SITE_VERIFICATION', '').strip()
BING_SITE_VERIFICATION   = os.environ.get('BING_SITE_VERIFICATION', '').strip()

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

# The console backend is the right default for development and the wrong one in
# production: lead-notification and enquiry emails are written to the deploy log
# and silently never delivered. Not fatal (the site still serves), so this is a
# loud startup banner rather than an ImproperlyConfigured — but it must not be
# silent. Set EMAIL_BACKEND explicitly in the Render dashboard to clear it.
if IS_PRODUCTION and EMAIL_BACKEND.endswith('console.EmailBackend'):
    print(
        '[ecoiq] WARNING: EMAIL_BACKEND is the console backend in production — '
        'outbound email (lead notifications, enquiries) is written to the log '
        'and NOT delivered. Set EMAIL_BACKEND to an SMTP backend.',
        file=sys.stderr,
        flush=True,
    )

# ── First Real Outreach Readiness (PR12) ──────────────────────────────────────
# The master switch for ever performing a real send to a genuinely external
# organisation via outreach_readiness. Hardcoded False, not read from the
# environment — flipping it on is a deliberate code change for a later,
# explicit PR to make (with its own review), never a deploy-time config
# toggle someone could accidentally leave on. No code in this PR reads this
# flag to perform a send; it exists so that later PR can gate on it.
EXTERNAL_OUTREACH_ENABLED = False

# Max upload size: 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# ── Production security ───────────────────────────────────────────────────────
# All of these are harmless in dev and critical in prod.

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ── Trusted client origin ─────────────────────────────────────────────────────
# Measured against production on 2026-08-07 by classifying forwarding hops
# (never addresses). Probes with 0, 1 and 3 forged RFC 5737 TEST-NET-3 entries
# returned 2, 3 and 5 hops respectively, always ending [.., real client,
# Cloudflare edge] — identical on ecoiq.uk and ecoiq.onrender.com. The
# infrastructure appends exactly TWO entries, so the client sits at index -2.
#
# This was previously 1, which selected the Cloudflare edge address. Not
# forgeable, but Cloudflare answers from a large rotating edge fleet, so one
# person's requests scattered across buckets and the per-origin rate limits
# never accumulated.
TRUSTED_PROXY_COUNT = int(os.environ.get('TRUSTED_PROXY_COUNT',
                                         '2' if IS_PRODUCTION else '0'))

# A header whose value the edge guarantees. Cloudflare sets CF-Connecting-IP
# itself and rejects any request that supplies one — a probe sending it got
# HTTP 403 "error code: 1000" before reaching the origin — so it cannot be
# forged, and unlike the hop count it does not depend on chain length.
# Empty means trust no header. Naming one is an explicit assertion about the
# deployment, so adding or removing a CDN is a configuration change rather than
# a silent shift in trust.
TRUSTED_CLIENT_IP_HEADER = os.environ.get(
    'TRUSTED_CLIENT_IP_HEADER', 'CF-Connecting-IP' if IS_PRODUCTION else '')

# Dedicated key for origin fingerprints, separate from SECRET_KEY so it can be
# rotated to expire abuse correlation without invalidating sessions. There is
# no literal fallback: absent in production, fingerprinting switches off.
REQUEST_ORIGIN_HMAC_KEY = os.environ.get('REQUEST_ORIGIN_HMAC_KEY', '')
REQUEST_ORIGIN_HMAC_KEY_VERSION = os.environ.get('REQUEST_ORIGIN_HMAC_KEY_VERSION', 'v1')

# IS_PRODUCTION, not `not DEBUG`: the test runner imports this module with
# whatever DEBUG the surrounding environment carries, and CI sets DEBUG=False
# so the `check` steps are production-like. Under `not DEBUG` that turned
# SECURE_SSL_REDIRECT on for the test process too, so every test-client request
# answered 301 and roughly 1400 tests failed — invisibly, because the CI test
# step also carried continue-on-error. IS_PRODUCTION is already
# `not (DEBUG or RUNNING_TESTS)`, so this keeps production and
# `check --deploy` unchanged while excluding the test process.
if IS_PRODUCTION:
    SECURE_SSL_REDIRECT      = True
    SESSION_COOKIE_SECURE    = True
    CSRF_COOKIE_SECURE       = True
    SECURE_HSTS_SECONDS      = 31536000   # 1 year — set low (60) first deploy, raise after
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD      = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# The one path SECURE_SSL_REDIRECT must not redirect: the Render health check.
#
# Render probes the service on its internal port, so the request does not pass
# through the edge that sets X-Forwarded-Proto: https. SECURE_PROXY_SSL_HEADER
# therefore does not mark it secure, SecurityMiddleware answers 301, and Render
# — which wants a 2xx — reads a healthy process as unhealthy and replaces it.
# Pointing healthCheckPath at an endpoint that always 301s is worse than having
# no health check at all, so this exemption is a correctness requirement of the
# health check, not a convenience.
#
# What it does NOT do, so this is not a security relaxation in disguise:
#   - The pattern is anchored `^healthz/$`. SecurityMiddleware matches it
#     against request.path.lstrip('/'), so it matches `/healthz/` and nothing
#     else — not a prefix, not a subpath, not a query variant.
#   - SECURE_REDIRECT_EXEMPT is read only in SecurityMiddleware.process_request,
#     and only to skip the HTTP->HTTPS redirect. process_response is untouched,
#     so HSTS, X-Content-Type-Options and Referrer-Policy still apply to every
#     response including this one.
#   - Nothing here touches TRUSTED_PROXY_COUNT, TRUSTED_CLIENT_IP_HEADER, or
#     any forwarding-header trust. Client-origin resolution is unchanged.
#   - The endpoint's entire response is the constant `ok`. There is no session,
#     no cookie, no user data and no secret that plaintext could expose.
#
# Set unconditionally rather than inside the IS_PRODUCTION block: it is inert
# whenever SECURE_SSL_REDIRECT is off, and being able to assert on it without
# re-importing settings under a production environment keeps the test honest.
# `readyz/` is exempt for the same reason and on the same terms: it is probed
# over the internal network where X-Forwarded-Proto is absent, and its body is
# a fixed set of check names with boolean outcomes — no session, no cookie, no
# credential. See core/health.py for what it deliberately does not report.
SECURE_REDIRECT_EXEMPT = [r'^healthz/$', r'^readyz/$']

# ── Logging ───────────────────────────────────────────────────────────────────
# Explicit configuration so application code can rely on `logging.getLogger()`
# reaching the Render log stream instead of falling back to Django's implicit
# defaults (which drop anything below WARNING from non-Django loggers).
#
# Console-only by design: Render captures stdout/stderr. Never add a handler
# that writes request bodies, headers, or cookies — see
# docs/security/admin-credential-rotation.md for what must never be logged.

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG' if DEBUG else 'INFO').upper()

# Structured logging. JSON in production (one event per line, machine-readable),
# human-readable console elsewhere. Chosen from configuration, never sniffed
# from a hostname, so tests are deterministic.
from core.logging_setup import build_formatter_config, configure_structlog  # noqa: E402

STRUCTLOG_JSON_LOGS = os.environ.get(
    'STRUCTLOG_JSON_LOGS', '1' if IS_PRODUCTION else '0') == '1'

# Optional release marker, surfaced on every event and read by a future error
# tracker for release attribution.
RELEASE_VERSION = os.environ.get('RENDER_GIT_COMMIT', '')[:12]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        # Built by dictConfig itself. Attaching a ProcessorFormatter after the
        # settings module imports does not survive: Django's configure_logging()
        # runs dictConfig during setup() and replaces every handler below, so
        # the formatter went with them and production emitted raw event dicts
        # through the plain formatter instead of JSON.
        'structured': build_formatter_config(json_logs=STRUCTLOG_JSON_LOGS),
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'structured',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        # Unhandled view exceptions. Django logs these at ERROR with the full
        # traceback server-side; the client still gets Django's generic 500.
        #
        # This is the logger a future Sentry breadcrumb reads, so it must go
        # through the same processors as everything else — it previously had its
        # own handler with the plain formatter and propagate=False, which put
        # the most important lines in production outside the pipeline entirely.
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        # Django's runserver access log. Only used by `manage.py runserver`;
        # gunicorn serves production. Routed anyway so development and
        # production render the same way, and so its default ServerFormatter —
        # which is neither structured nor redacted — is not left in place.
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Very chatty at DEBUG (one line per query) — pin it above that.
        # SQL parameters must never reach a log.
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ── Django REST Framework ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # mobile_auth MUST run before APIKeyAuthentication: both read an
        # `Authorization: Bearer <token>` header, and APIKeyAuthentication
        # raises AuthenticationFailed (not None) for anything that isn't a
        # valid APIKey, which would short-circuit DRF's authenticator chain
        # before APIKeyAuthentication got a turn. MobileTokenAuthentication
        # only claims tokens shaped like its own (colon-separated,
        # signing.dumps() format) and defers (returns None) otherwise, so a
        # real APIKey hex string correctly falls through to the next
        # authenticator instead of being misclaimed.
        'mobile_auth.authentication.MobileTokenAuthentication',
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
        # core.throttling's subclass, not the stock class: DRF's default
        # get_ident() returns the concatenated X-Forwarded-For chain when
        # NUM_PROXIES is unset, which is partly client-supplied behind
        # Cloudflare. Same scope, same rate — a real identity.
        'core.throttling.TrustedAnonRateThrottle',
        'api.throttles.APIKeyRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        # WHY THIS IS PER-HOUR AND NOT 20/day
        #
        # 20/day was a DATA-API quota, set when /api/ was something a third
        # party called deliberately. The frontend migration made API v2 the way
        # the WEBSITE renders: /platform/, /companies/, /leaderboard/,
        # /projects/ and one call per investigation are all fetched by the SPA
        # on ordinary page views.
        #
        # So every visitor was spending a developer quota to read the site. At
        # 2-4 calls per page view, roughly five to seven pages exhausted it —
        # after which /companies/ rendered "Could not load this section" for the
        # rest of the DAY, and a shared NAT could exhaust it for a whole office
        # in minutes. Observed in production: Retry-After 22248, six hours.
        #
        # Third-party data consumers are unaffected by this number: an API key
        # carries its own tier below, and those are the real quotas. This one
        # only has to permit a person reading the site while still bounding a
        # scraper — 600/hour is ~150-300 page views an hour per address, and
        # recovers in an hour rather than at midnight.
        'anon':    '600/hour',
        'explorer':   '100/day',
        'professional': '2000/day',
        'enterprise':   '50000/day',
        # ── EcoIQ Mobile/Desktop App (mobile_auth/throttles.py) ──
        # Per-IP brute-force protection on /api/v1/auth/login/.
        'auth_login': '10/hour',
        # ── EcoIQ AI Gateway (ai_gateway/throttles.py) ──
        # A generation costs a shared free allowance, so both a per-identity
        # and a per-IP ceiling apply to every chat request. The catalogue is
        # cheap (cached registry) but still bounded so a stuck client cannot
        # spin on it.
        'ai_chat_user': '60/hour',
        'ai_chat_ip':   '120/hour',
        'ai_catalog':   '120/hour',
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

#: Whether Redis is a dependency this deployment actually expects.
#:
#: Derived from the ENVIRONMENT, not from REDIS_URL, and that distinction is the
#: whole point: REDIS_URL above always has a value because of its localhost
#: default, so a truthiness check on it would report Redis as required on any
#: deployment that had never heard of Redis, and the readiness probe would fail
#: permanently against a perfectly healthy web service.
#:
#: This comment used to justify itself with "production, where no Redis service
#: is deployed (render.yaml keeps the Key Value and worker blocks commented
#: out)". That stopped being true on 2026-08-24, when ecoiq-keyvalue and
#: ecoiq-celery-worker were created by hand — render.yaml still carries them
#: commented out and never learned. /readyz/ now reports redis: ok, which only
#: happens when REDIS_URL is set explicitly, so production genuinely runs on a
#: shared Redis cache. See docs/operations/PRODUCTION_RUNBOOK.md.
#:
#: The MECHANISM below is unchanged and was never the problem: keying off
#: explicit configuration rather than a defaulted URL is right either way, and
#: it is why this deployment reports its Redis dependency correctly today
#: without anyone having to edit this line.
#:
#: Setting REDIS_URL explicitly is therefore the act that makes Redis a
#: dependency worth failing readiness over.
REDIS_CONFIGURED = 'REDIS_URL' in os.environ

# ── Cache ─────────────────────────────────────────────────────────────────────
#
# Until now `CACHES` was never configured at all, so Django fell back to a
# per-process LocMemCache — and every DRF throttle counts in it. On the current
# service (`--workers 1 --threads 4`) the four threads share one process, so
# rate limiting was not broken. It was fragile in a way that fails SILENTLY:
# counters reset on every deploy and on each `--max-requests 300` worker
# recycle, and raising WEB_CONCURRENCY above 1 would multiply every configured
# limit by the worker count with no error and no log line.
#
# This block makes the choice explicit in both directions. It does NOT change
# any throttle policy — that is the next package, and it depends on this one.
#
# SAME SIGNAL AS READINESS
# ------------------------
# Redis is used when REDIS_CONFIGURED — i.e. when REDIS_URL was set in the
# environment — never on REDIS_URL's own truthiness, which is always true
# because of its localhost default above. core/health.py's readiness probe
# keys off exactly the same flag, so "readiness enforces Redis" and "the cache
# is Redis" can never disagree.
#
# NO SILENT FALLBACK
# ------------------
# When Redis IS configured there is no LocMem fallback: Django's RedisCache
# raises on a connection failure, which is the intended behaviour. A cache that
# quietly degrades to per-process memory when the shared backend is unreachable
# would reintroduce exactly the multiplied-rate-limit bug this exists to remove,
# and would do it during an outage, when nobody is looking for it.
#
# When Redis is NOT configured the backend is LocMem and that is a deliberate,
# documented state — not a failure. Production runs this way today, because no
# Key Value instance is provisioned (render.yaml keeps that block commented
# out). A warning is logged rather than raising, because refusing to start
# would take down a service that is otherwise healthy.
# ── Authentication rate limits ────────────────────────────────────────────────
#
# Per-IP ceilings on the two unauthenticated write surfaces the estate exposes:
# the sign-in form and registration. Both were previously unlimited — DRF's
# throttles cover /api/, not Django's own auth views.
#
# Chosen as brute-force ceilings, not cost controls, and deliberately generous
# enough not to interfere with ordinary pilot use: a real person mistyping a
# password a few times, or a shared office NAT with several people signing in
# at once, stays well inside them. They are per-minute so a tripped limit
# clears in under a minute rather than locking someone out of their account —
# this throttles an ADDRESS, never an account, so no attacker can lock a named
# user out by attacking them.
LOGIN_RATE_PER_MIN = int(os.environ.get('LOGIN_RATE_PER_MIN', '10'))
REGISTER_RATE_PER_MIN = int(os.environ.get('REGISTER_RATE_PER_MIN', '5'))

CACHE_ENVIRONMENT = os.environ.get(
    'ECOIQ_CACHE_ENVIRONMENT', 'production' if IS_PRODUCTION else 'development')

#: Namespaces every key by environment, so a staging service pointed at the
#: same Redis instance can never read or overwrite production's entries.
#:
#: The RELEASE is deliberately NOT part of this prefix. Including it would
#: invalidate the entire cache on every deploy, which sounds safe and is
#: actively wrong here: it would also reset every throttle counter on every
#: deploy — the precise fragility this package exists to remove, reintroduced
#: as a side effect. A value whose correctness depends on a version must carry
#: that version IN ITS OWN KEY (see the cache-key rules in
#: docs/architecture/reliability.md); it must not lean on a global prefix.
CACHE_KEY_PREFIX = f'ecoiq:{CACHE_ENVIRONMENT}'

#: Django's own default. Set explicitly so a `cache.set()` without a timeout has
#: a stated lifetime rather than an inherited one.
CACHE_DEFAULT_TIMEOUT = 300

#: Never use Redis for the test suite, even on a developer machine that has
#: REDIS_URL exported. A test run must not depend on an external service being
#: up, and must never read or write another process's cache.
CACHE_USES_REDIS = REDIS_CONFIGURED and not RUNNING_TESTS

if CACHE_USES_REDIS:
    _redis_cache_options = {
        # Bounded so a stalled Redis cannot hold a web thread open. A cache is
        # an optimisation; waiting indefinitely for one inverts that.
        'socket_connect_timeout': 2,
        'socket_timeout': 2,
        # Retry once on a timeout — covers a dropped idle connection without
        # turning a real outage into a long stall.
        'retry_on_timeout': True,
        # Detects a silently-dead connection from the pool before it is used.
        'health_check_interval': 30,
        # Comfortably above `--workers 1 --threads 4` plus a worker's
        # concurrency, and far below any managed instance's connection ceiling.
        'max_connections': 24,
    }
    if REDIS_URL.startswith('rediss://'):
        # Only meaningful for a TLS URL. Set under the scheme test rather than
        # unconditionally so the intent is visible at the point it applies.
        _redis_cache_options['ssl_cert_reqs'] = 'required'

    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            # Django 5.2's built-in Redis backend over redis-py, which this
            # repository already depends on for Celery. No new package: adding
            # django-redis would mean a second Redis client and a second set of
            # connection semantics for no capability this needs.
            'LOCATION': REDIS_URL,
            'KEY_PREFIX': CACHE_KEY_PREFIX,
            'TIMEOUT': CACHE_DEFAULT_TIMEOUT,
            'OPTIONS': _redis_cache_options,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            # Named, not left to Django's implicit default. Two LocMem caches
            # with the same LOCATION share one dict; an explicit unique name
            # means a future second cache alias cannot silently collide.
            'LOCATION': 'ecoiq-locmem-default',
            'KEY_PREFIX': CACHE_KEY_PREFIX,
            'TIMEOUT': CACHE_DEFAULT_TIMEOUT,
        }
    }

    if IS_PRODUCTION:
        # Visible, not fatal. Production genuinely runs this way today and
        # refusing to start would be a self-inflicted outage — but it must not
        # be silent, because the consequence (throttle counters that are
        # per-process and reset on deploy) is invisible from the outside.
        # stderr directly, matching the ALLOWED_HOSTS banner above: LOGGING is
        # not applied until Django finishes loading this module. No URL, no
        # credential — the message states a configuration fact, not a value.
        print(
            '[ecoiq] WARNING: REDIS_URL is not set — cache is a process-local '
            'LocMemCache. Throttle counters are NOT shared between processes and '
            'reset on every deploy and worker recycle. '
            'See docs/architecture/reliability.md.',
            file=sys.stderr, flush=True,
        )


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
# ══════════════════════════════════════════════════════════════════════════════
# EcoIQ AI Gateway (ai_gateway app)
#
# One provider-neutral AI system in front of OpenRouter, Bytez and NVIDIA NIM.
# Users pick a model per request from a simple selector; the browser only ever
# sends an opaque server-issued `model_key`. A raw provider slug, base URL or
# model name submitted by a client is never trusted.
#
# This is NOT a replacement for agent_runtime_model_router (governed *agent*
# execution against Anthropic/OpenAI/Gemini/Azure) or for core/ai.py (the
# Anthropic ESG scoring path). Both are untouched and keep their own budgets.
# ══════════════════════════════════════════════════════════════════════════════


def _env_bool(key: str, default: str = 'false') -> bool:
    return os.environ.get(key, default).strip().strip('"').strip("'").lower() in (
        'true', '1', 'yes', 'on',
    )


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)).strip().strip('"').strip("'"))
    except ValueError:
        return default


# ── Global policy ─────────────────────────────────────────────────────────────
# Master on/off for the whole gateway. Off means the endpoints stay mounted but
# no provider is contacted — useful for turning the feature off in an incident
# without a redeploy of code.
AI_ENABLED = _env_bool('AI_ENABLED', 'true')

# AI_FREE_ONLY is the free-spend switch. While it is on: paid models are neither
# displayed nor callable, no request is ever silently upgraded to a paid model,
# and a free model failing can only ever fall back to another *free* model.
AI_FREE_ONLY = _env_bool('AI_FREE_ONLY', 'true')
AI_ALLOW_PAID_MODELS = _env_bool('AI_ALLOW_PAID_MODELS', 'false')

# Who chooses the model.
#   'automatic' (default) — EcoIQ chooses. Normal users never see or send a
#                           model selection; a submitted model_key is ignored.
#                           Staff may still override (see below).
#   'user'                 — legacy per-request selector. Retained so the
#                           behaviour can be restored deliberately, but it is
#                           no longer the product decision.
AI_MODEL_SELECTION_MODE = os.environ.get('AI_MODEL_SELECTION_MODE', 'automatic').strip() or 'automatic'

# How the server builds the attempt chain once it is choosing.
#   'automatic' (default) — capability-scored: filter by required capabilities,
#                           context length and health, rank by task benchmark
#                           then priority, and put the free router last as the
#                           catch-all rather than first.
#   'static'               — plain priority order (the pre-automatic behaviour).
AI_ROUTING_MODE = os.environ.get('AI_ROUTING_MODE', 'automatic').strip() or 'automatic'

# Staff may pin a specific model for benchmarking and comparison. This is
# permission-gated, accepts only registered model keys, and cannot reach a paid
# model — the registry's own free-only gate still applies. Set false to remove
# the capability entirely.
AI_STAFF_MODEL_OVERRIDE_ENABLED = _env_bool('AI_STAFF_MODEL_OVERRIDE_ENABLED', 'true')

# The public catch-all route, used when no better approved free model applies.
# It is the last entry in the automatic chain, not the only possible model.
AI_DEFAULT_MODEL_KEY = os.environ.get('AI_DEFAULT_MODEL_KEY', 'openrouter:auto-free').strip()

# Provider catalogues are fetched at most this often — never per page load and
# never per chat request. A failed refresh serves the last known-good registry
# from an extended-TTL cache copy (see ai_gateway/registry.py).
AI_MODEL_CATALOG_CACHE_SECONDS = _env_int('AI_MODEL_CATALOG_CACHE_SECONDS', 3600)

AI_ALLOW_AUTOMATIC_FALLBACK = _env_bool('AI_ALLOW_AUTOMATIC_FALLBACK', 'true')
AI_MAX_PROVIDER_ATTEMPTS = _env_int('AI_MAX_PROVIDER_ATTEMPTS', 3)

# Ceiling applied before each provider's own max-output setting; the lower of
# the two wins.
AI_MAX_OUTPUT_TOKENS = _env_int('AI_MAX_OUTPUT_TOKENS', 1600)

# ── OpenRouter ────────────────────────────────────────────────────────────────
OPENROUTER_ENABLED = _env_bool('OPENROUTER_ENABLED', 'true')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
OPENROUTER_BASE_URL = os.environ.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
OPENROUTER_SITE_URL = os.environ.get('OPENROUTER_SITE_URL', 'https://ecoiq.ai')
OPENROUTER_APP_NAME = os.environ.get('OPENROUTER_APP_NAME', 'EcoIQ')
OPENROUTER_TIMEOUT_SECONDS = _env_int('OPENROUTER_TIMEOUT_SECONDS', 60)
OPENROUTER_MAX_OUTPUT_TOKENS = _env_int('OPENROUTER_MAX_OUTPUT_TOKENS', 1600)
OPENROUTER_FREE_ROUTER_ENABLED = _env_bool('OPENROUTER_FREE_ROUTER_ENABLED', 'true')
OPENROUTER_FREE_ROUTER_MODEL = os.environ.get('OPENROUTER_FREE_ROUTER_MODEL', 'openrouter/free')
# Zero-data-retention preference, sent server-side in the request body. The
# frontend can never set, unset or override it.
OPENROUTER_ZDR_ENABLED = _env_bool('OPENROUTER_ZDR_ENABLED', 'true')

# ── Bytez ─────────────────────────────────────────────────────────────────────
# Bytez is DISABLED by default. Its provider, free-policy check, catalogue
# survey command and tests all remain in the codebase and are still
# exercised by the test suite — this switch only keeps it out of the
# runtime registry until its catalogue schema has been verified with a
# real key. Set BYTEZ_ENABLED=true to bring it back.
BYTEZ_ENABLED = _env_bool('BYTEZ_ENABLED', 'false')
BYTEZ_API_KEY = os.environ.get('BYTEZ_API_KEY', '')
BYTEZ_OPENAI_BASE_URL = os.environ.get(
    'BYTEZ_OPENAI_BASE_URL', 'https://api.bytez.com/models/v2/openai/v1')
BYTEZ_MODELS_URL = os.environ.get(
    'BYTEZ_MODELS_URL', 'https://api.bytez.com/models/v2/list/models')
BYTEZ_TIMEOUT_SECONDS = _env_int('BYTEZ_TIMEOUT_SECONDS', 60)
BYTEZ_MAX_OUTPUT_TOKENS = _env_int('BYTEZ_MAX_OUTPUT_TOKENS', 1200)
BYTEZ_FREE_ONLY = _env_bool('BYTEZ_FREE_ONLY', 'true')
# Bytez free-plan access can draw down included credits. EcoIQ never enables
# auto-reload, never purchases credits, and treats exhausted credits as
# "unavailable" (a free-pool fallback trigger), not as a reason to spend.
BYTEZ_ALLOW_PAID_CREDITS = _env_bool('BYTEZ_ALLOW_PAID_CREDITS', 'false')
BYTEZ_ALLOW_CLOSED_MODELS = _env_bool('BYTEZ_ALLOW_CLOSED_MODELS', 'false')

# The documented free-access meter indicator, and the free-plan model-size
# ceiling. Both are configurable rather than hard-coded because Bytez may
# change them; confirm against current Bytez documentation before widening.
BYTEZ_FREE_METERS = frozenset(
    _parse_env_list('BYTEZ_FREE_METERS', 'sm-free') or ['sm-free'])
BYTEZ_FREE_MAX_PARAMETERS_B = float(os.environ.get('BYTEZ_FREE_MAX_PARAMETERS_B', '10'))

# ── NVIDIA NIM ────────────────────────────────────────────────────────────────
# NVIDIA Developer Program hosted endpoints are prototype/development access,
# not permanently free production inference. Both latches below must be flipped
# before a NVIDIA model is offered to ordinary production users.
NVIDIA_NIM_ENABLED = _env_bool('NVIDIA_NIM_ENABLED', 'true')
NVIDIA_NIM_API_KEY = os.environ.get('NVIDIA_NIM_API_KEY', '')
NVIDIA_NIM_BASE_URL = os.environ.get('NVIDIA_NIM_BASE_URL', 'https://integrate.api.nvidia.com/v1')
NVIDIA_NIM_TIMEOUT_SECONDS = _env_int('NVIDIA_NIM_TIMEOUT_SECONDS', 60)
NVIDIA_NIM_MAX_OUTPUT_TOKENS = _env_int('NVIDIA_NIM_MAX_OUTPUT_TOKENS', 1600)
NVIDIA_NIM_PROTOTYPE_ONLY = _env_bool('NVIDIA_NIM_PROTOTYPE_ONLY', 'true')
NVIDIA_NIM_PUBLIC_PRODUCTION_ENABLED = _env_bool('NVIDIA_NIM_PUBLIC_PRODUCTION_ENABLED', 'false')

# Manually reviewed, per-model NVIDIA configuration. NVIDIA models do not all
# accept the same parameters, so capabilities and parameter defaults live here
# rather than being assumed uniform. A model id absent from this map is
# rejected by the registry even if it is in the allowlist.
#
# Both ids below were verified present in the live NVIDIA API catalogue
# (GET https://integrate.api.nvidia.com/v1/models) on 2026-08-03. Nothing here
# was invented; add entries only after the same check.
NVIDIA_MODEL_CONFIG = {
    'meta/llama-3.1-8b-instruct': {
        'display_name': 'Llama 3.1 8B',
        'description': 'Fast general-purpose chat model. NVIDIA prototype endpoint.',
        'capabilities': {'chat'},
        'context_length': 131072,
        'temperature': 0.2,
        'top_p': None,
        'public': False,
        'development_only': True,
    },
    'nvidia/llama-3.1-nemotron-70b-instruct': {
        'display_name': 'Nemotron 70B',
        'description': 'Larger reasoning-oriented chat model. NVIDIA prototype endpoint.',
        'capabilities': {'chat'},
        'context_length': 131072,
        'temperature': 0.2,
        'top_p': None,
        'public': False,
        'development_only': True,
    },
}

# ── EcoIQ allowlist ───────────────────────────────────────────────────────────
# The server-side allowlist. A model is selectable only if it appears here AND
# passes its provider's free-eligibility check AND is present in that
# provider's live catalogue AND supports the requested capability.
#
# OpenRouter entries below were each verified against the live public
# catalogue (GET https://openrouter.ai/api/v1/models) on 2026-08-03: every one
# reported "prompt": "0" and "completion": "0", text-in/text-out (except the
# Gemma entry, which also accepts images), and no expiration date. They are
# re-verified on every registry refresh — a model that stops being free drops
# out automatically rather than being billed.
#
# Bytez ships EMPTY: its catalogue endpoint requires a key, so its free-tier
# field names could not be verified. Populate only after running
# `manage.py refresh_ai_models --explain` with a real key.
#
# NVIDIA ships EMPTY by default too: uncomment an id from NVIDIA_MODEL_CONFIG
# above only once the licensing question for your use has been settled.
#
# BYTEZ_APPROVED_MODELS lets an operator curate the Bytez allowlist from the
# environment *after* running the verification command below — deliberately not
# a long stale literal list in render.yaml. It stays empty until someone has
# actually seen the authenticated catalogue:
#
#     python manage.py refresh_ai_models --provider bytez --dry-run --explain
#
BYTEZ_APPROVED_MODELS = frozenset(_parse_env_list('BYTEZ_APPROVED_MODELS', ''))

AI_MODEL_ALLOWLIST = {
    'openrouter': {
        'openrouter/free',
        'openai/gpt-oss-20b:free',
        'nvidia/nemotron-3-super-120b-a12b:free',
        'nvidia/nemotron-3-nano-30b-a3b:free',
        'google/gemma-4-31b-it:free',
        'inclusionai/ling-3.0-flash:free',
    },
    'bytez': set(BYTEZ_APPROVED_MODELS),
    # Staff / development only. Both ids were verified present in the live
    # NVIDIA API catalogue (GET https://integrate.api.nvidia.com/v1/models)
    # on 2026-08-03, and both have a reviewed entry in NVIDIA_MODEL_CONFIG
    # below. They are public=False / development_only=True, and the two
    # environment latches keep them out of public routing entirely.
    'nvidia_nim': {
        'meta/llama-3.1-8b-instruct',
        'nvidia/llama-3.1-nemotron-70b-instruct',
    },
}

# ── Automatic routing ─────────────────────────────────────────────────────────
# Per-module routing requirements. The *module* (supplied by EcoIQ's own code
# in the request context, never chosen by the user) decides task type,
# structured-output need, privacy level and minimum context. A module absent
# from this map gets AI_ROUTING_DEFAULT_PROFILE.
AI_ROUTING_DEFAULT_PROFILE = {
    'task': 'chat',
    'structured_output': False,
    'privacy_level': 'standard',
    'min_context_length': 8_000,
}

AI_MODULE_ROUTING = {
    'company-analysis': {
        'task': 'analysis',
        'structured_output': False,
        'privacy_level': 'sensitive',
        'min_context_length': 32_000,
    },
    'decision-studio': {
        'task': 'analysis',
        'structured_output': False,
        'privacy_level': 'sensitive',
        'min_context_length': 32_000,
    },
}

# Answer modes offered in the UI. These adjust ROUTING REQUIREMENTS only — they
# never name a model and never appear in the provider request.
AI_ROUTING_MODES = {
    'auto':  {'min_context_length': 0,      'max_output_tokens': None, 'prefer': 'balanced'},
    'quick': {'min_context_length': 0,      'max_output_tokens': 700,  'prefer': 'fast'},
    'deep':  {'min_context_length': 100_000, 'max_output_tokens': None, 'prefer': 'capable'},
}
AI_DEFAULT_ROUTING_MODE = os.environ.get('AI_DEFAULT_ROUTING_MODE', 'auto').strip() or 'auto'

# Task-specific benchmark scores, highest wins, used to rank otherwise-eligible
# models. INTENTIONALLY EMPTY: EcoIQ has not run its own benchmarks yet, and
# inventing scores would make routing look principled while being arbitrary.
# With no entries the scorer falls back to AI_MODEL_PRESENTATION priority.
# Shape: {provider_model_id: {task: score_0_to_100}}
AI_MODEL_BENCHMARKS: dict[str, dict[str, float]] = {}

# Friendly presentation for the selector. `key_slug` mints the opaque model key
# (`openrouter/free` → `openrouter:auto-free`); `priority` orders the selector,
# lower first. Anything not listed falls back to the provider's own name and a
# slug derived from the model id — so this map is optional polish, never a
# requirement for a model to work.
AI_MODEL_PRESENTATION = {
    'openrouter/free': {
        'key_slug': 'auto-free',
        'display_name': 'Auto — Free',
        'description': 'Automatically selects an available free model.',
        'priority': 0,
    },
    'openai/gpt-oss-20b:free': {
        'key_slug': 'gpt-oss-20b-free',
        'display_name': 'GPT-OSS 20B',
        'priority': 10,
    },
    # PRIMARY model for ordinary users. Lower priority number ranks higher, so
    # this is the first thing automatic routing tries; openrouter/free remains
    # the final reserve (it holds the last slot in every chain).
    'nvidia/nemotron-3-super-120b-a12b:free': {
        'key_slug': 'nemotron-super-free',
        'display_name': 'Nemotron 3 Super',
        'priority': 1,
    },
    'nvidia/nemotron-3-nano-30b-a3b:free': {
        'key_slug': 'nemotron-nano-free',
        'display_name': 'Nemotron 3 Nano',
        'priority': 30,
    },
    'google/gemma-4-31b-it:free': {
        'key_slug': 'gemma-4-31b-free',
        'display_name': 'Gemma 4 31B',
        'priority': 40,
    },
    'inclusionai/ling-3.0-flash:free': {
        'key_slug': 'ling-3-flash-free',
        'display_name': 'Ling 3.0 Flash',
        'priority': 50,
    },
    'meta/llama-3.1-8b-instruct': {
        'key_slug': 'llama-31-8b-preview',
        'priority': 200,
    },
    'nvidia/llama-3.1-nemotron-70b-instruct': {
        'key_slug': 'nemotron-70b-preview',
        'priority': 210,
    },
}

# A configuration that would let a "free" request become a paid one is a
# deployment mistake, not a runtime decision — fail loudly at startup.
if AI_FREE_ONLY and AI_ALLOW_PAID_MODELS:
    raise ImproperlyConfigured(
        'AI_FREE_ONLY=true and AI_ALLOW_PAID_MODELS=true are contradictory. '
        'Set AI_ALLOW_PAID_MODELS=false, or turn AI_FREE_ONLY off deliberately.'
    )


# structlog's own configuration — processors, logger factory, wrapper class.
# Handler formatting is NOT done here: LOGGING['formatters']['structured'] does
# it, and Django applies that via dictConfig during setup(). Calling dictConfig
# ourselves as well would be a second, conflicting configuration pass.
configure_structlog(json_logs=STRUCTLOG_JSON_LOGS)

# ── Sentry ───────────────────────────────────────────────────────────────────
# Initialised exactly once, here, and disabled unless SENTRY_DSN is set. No
# network call happens at init; the SDK connects only when an event is queued.
#
# Environment comes from configuration and never defaults to 'production' —
# a local machine must not be able to file issues into the production project.
from core.sentry_setup import initialise as _init_sentry  # noqa: E402

SENTRY_ENVIRONMENT = os.environ.get(
    'SENTRY_ENVIRONMENT', 'production' if IS_PRODUCTION else 'development')
SENTRY_ACTIVE = _init_sentry(
    environment=SENTRY_ENVIRONMENT,
    # Same release identifier the log pipeline already publishes, so an issue
    # and a log line agree on which build produced them.
    release=RELEASE_VERSION,
)
