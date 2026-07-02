"""certification_trust_badge_engine/urls.py — routes (mounted at /certification-trust-badge-engine/)."""
from django.urls import path

from certification_trust_badge_engine import views

app_name = 'certification_trust_badge_engine'

urlpatterns = [
    path('', views.overview, name='overview'),
]
