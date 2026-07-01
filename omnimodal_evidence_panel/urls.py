"""omnimodal_evidence_panel/urls.py — routes (mounted at /omnimodal-evidence-panel/)."""
from django.urls import path

from omnimodal_evidence_panel import views

app_name = 'omnimodal_evidence_panel'

urlpatterns = [
    path('', views.overview, name='overview'),
]
