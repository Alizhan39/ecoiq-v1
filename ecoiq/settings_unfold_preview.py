"""Isolated Django Unfold visual pilot for Python 3.12 development/CI only.

NEVER point production DJANGO_SETTINGS_MODULE here. This settings module
deliberately fails closed outside DEBUG/test environments, and leaves
ecoiq.settings and the Render Blueprint unchanged.
"""
from __future__ import annotations

import sys

from django.core.exceptions import ImproperlyConfigured

from ecoiq.settings import *  # noqa: F401,F403
from ecoiq.settings import DEBUG, INSTALLED_APPS, RUNNING_TESTS

if sys.version_info < (3, 12):
    raise ImproperlyConfigured("Unfold staging preview requires Python >=3.12.")
if not (DEBUG or RUNNING_TESTS):
    raise ImproperlyConfigured("Unfold staging preview is disabled in production.")

# The theme must precede django.contrib.admin; it does not create a second
# admin site, and the existing /admin/ authorization remains Django-owned.
ECOIQ_UNFOLD_PREVIEW = True
INSTALLED_APPS = ["unfold", *INSTALLED_APPS]

# Existing commercial Feature admin is the ONLY model opted into Unfold's
# ModelAdmin in this pilot; other models continue using their current admins.
