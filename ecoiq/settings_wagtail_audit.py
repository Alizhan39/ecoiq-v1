"""Wagtail historical CMS schema audit, intentionally NOT a deployable config.

No Wagtail routes are registered; the production settings.py and requirements
stay untouched. Use only with an isolated, disposable staging database.
"""
from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured

from ecoiq.settings import *  # noqa: F401,F403
from ecoiq.settings import DEBUG, INSTALLED_APPS, RUNNING_TESTS

if not (DEBUG or RUNNING_TESTS):
    raise ImproperlyConfigured(
        "Wagtail CMS audit settings refuse production execution."
    )

# Preview owns no public CMS routing, publication jobs or indexer.
ECOIQ_WAGTAIL_AUDIT_MODE = True
WAGTAIL_SITE_NAME = "EcoIQ Legacy CMS — isolated schema audit"

_WAGTAIL_APPS = (
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "cms",
)
# These apps have old migration dependencies (wagtailcore 0097, wagtailimages
# 0027). They are loaded here to audit the REAL historical migration graph,
# not to create replacement models or silently fake an initial migration.
INSTALLED_APPS = [*INSTALLED_APPS, *_WAGTAIL_APPS]
