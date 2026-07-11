"""
institutional_finance_engine/urls.py — routes (mounted at /institutional-finance-engine/).

DEPRECATED (Phase 1A) — see apps.py's module docstring. Left mounted so the
existing page and its own test suite keep working; not to be extended.
"""
from django.urls import path

from institutional_finance_engine import views

app_name = 'institutional_finance_engine'

urlpatterns = [
    path('', views.overview, name='overview'),
]
