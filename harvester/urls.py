"""Evidence Harvester — read-only dashboard routes (additive, standalone)."""
from django.urls import path

from . import views

app_name = "harvester"

urlpatterns = [
    # Evidence Explorer (read-only index)
    path("", views.evidence_explorer, name="evidence_explorer"),
    # Standalone Company Evidence Dashboard (read-only)
    path("<slug:slug>/", views.evidence_dashboard, name="evidence_dashboard"),
    path("<slug:slug>/data/", views.evidence_dashboard_data, name="evidence_dashboard_data"),
]
