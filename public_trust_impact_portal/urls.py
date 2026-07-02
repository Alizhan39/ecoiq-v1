"""public_trust_impact_portal/urls.py — routes (mounted at /public-trust-impact-portal/)."""
from django.urls import path

from public_trust_impact_portal import views

app_name = 'public_trust_impact_portal'

urlpatterns = [
    path('', views.overview, name='overview'),
]
