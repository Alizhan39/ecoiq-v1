"""Opt-in, fail-closed Django settings for the isolated Stage 8 synthetic pilot.

DO NOT use against production databases. Setting this module alone never
provisions a private Render network, firewall, backup or data-processing terms.
"""
from __future__ import annotations

import os

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F403 — explicit isolated override of existing Django settings
from ecoiq_os.pilot_security import assess_pilot_preflight

# Hard-disable features with monetary, outbound data and background effects.
DEBUG = False
AI_ENABLED = False
ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED = False
ECOIQ_BILLING_PROVIDER = "none"
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_HTTPONLY = True

PILOT_PREFLIGHT = assess_pilot_preflight(
    config=type("PilotRuntimeSettings", (), {
        "DATABASES": DATABASES,
        "DEBUG": DEBUG,
        "ALLOWED_HOSTS": ALLOWED_HOSTS,
        "AI_ENABLED": AI_ENABLED,
        "ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED": ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED,
        "ECOIQ_BILLING_PROVIDER": ECOIQ_BILLING_PROVIDER,
        "EMAIL_BACKEND": EMAIL_BACKEND,
        "SESSION_COOKIE_SECURE": SESSION_COOKIE_SECURE,
        "CSRF_COOKIE_SECURE": CSRF_COOKIE_SECURE,
        "SECURE_SSL_REDIRECT": SECURE_SSL_REDIRECT,
    })(),
    environ=os.environ,
)
if not PILOT_PREFLIGHT["ready_for_synthetic_staging_preflight"]:
    missing = sorted(key for key, ok in PILOT_PREFLIGHT["checks"].items() if not ok)
    raise ImproperlyConfigured(
        "Synthetic pilot staging preflight failed: " + ", ".join(missing)
    )
