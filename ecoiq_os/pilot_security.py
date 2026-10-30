"""Stage 8 fail-closed *preflight*, not an infrastructure security attestation.

No network, database mutations, deployment, credential reads, model calls,
or customer content. Manual infrastructure attestations are never treated as
independently verified security controls.
"""
from __future__ import annotations

from collections.abc import Mapping

_TRUTHY = frozenset({"1", "true", "yes", "on"})
_PRODUCTION_HOSTS = frozenset({
    "ecoiq.uk", "www.ecoiq.uk", "ecoiq.onrender.com", "ecoiq-v1.onrender.com",
})
_SAFE_EMAIL_BACKENDS = frozenset({
    "django.core.mail.backends.dummy.EmailBackend",
    "django.core.mail.backends.locmem.EmailBackend",
})


def _is_true(value: object) -> bool:
    return str(value).strip().lower() in _TRUTHY


def assess_pilot_preflight(config: object, environ: Mapping[str, str]) -> dict[str, object]:
    """Return check IDs/results ONLY, never secrets, DB hosts or credentials.

    The checklist is conservative. Passing means *configuration prerequisites*
    are satisfied; it does not verify cloud isolation or authorise any release.
    """
    database = getattr(config, "DATABASES", {}).get("default", {})
    db_engine = str(database.get("ENGINE", ""))
    db_name = str(database.get("NAME") or "")
    hosts = getattr(config, "ALLOWED_HOSTS", []) or []
    if isinstance(hosts, str):
        hosts = hosts.replace(",", " ").split()
    hostnames = {str(host).strip().lower() for host in hosts}
    pilot_hosts = bool(hostnames) and all(
        host not in _PRODUCTION_HOSTS
        and host != "*"
        and ("pilot" in host or "staging" in host)
        for host in hostnames
    )
    checks = {
        "explicit_pilot_mode": _is_true(environ.get("ECOIQ_PILOT_STAGING_MODE", "")),
        "synthetic_data_only": _is_true(environ.get("ECOIQ_PILOT_SYNTHETIC_ONLY", "")),
        "private_access_attested": _is_true(environ.get("ECOIQ_PILOT_PRIVATE_ACCESS_ATTESTED", "")),
        "separate_database_attested": _is_true(environ.get("ECOIQ_PILOT_DB_ISOLATION_ATTESTED", "")),
        "no_background_jobs_attested": _is_true(environ.get("ECOIQ_PILOT_JOBS_DISABLED_ATTESTED", "")),
        "debug_disabled": getattr(config, "DEBUG", True) is False,
        "staging_only_hosts": pilot_hosts,
        "separate_postgres_name": (
            db_engine.endswith("postgresql")
            and db_name.startswith("ecoiq_pilot_")
        ),
        "external_model_disabled": (
            getattr(config, "ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED", False) is False
            and not _is_true(environ.get("ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED", ""))
        ),
        "all_gateway_models_disabled": (
            getattr(config, "AI_ENABLED", True) is False
            and not _is_true(environ.get("AI_ENABLED", ""))
        ),
        "billing_disabled": str(getattr(config, "ECOIQ_BILLING_PROVIDER", "none")).lower() == "none",
        "email_transport_disabled": getattr(config, "EMAIL_BACKEND", "") in _SAFE_EMAIL_BACKENDS,
        "secure_session_cookies": getattr(config, "SESSION_COOKIE_SECURE", False) is True,
        "secure_csrf_cookies": getattr(config, "CSRF_COOKIE_SECURE", False) is True,
        "https_redirect_enabled": getattr(config, "SECURE_SSL_REDIRECT", False) is True,
    }
    return {
        "stage": "enterprise_staging_preflight_v1",
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
        "ready_for_synthetic_staging_preflight": all(checks.values()),
        "cloud_isolation_independently_verified": False,
        "customer_data_authorised": False,
        "external_model_transfer_authorised": False,
        "production_deployment_authorised": False,
    }
