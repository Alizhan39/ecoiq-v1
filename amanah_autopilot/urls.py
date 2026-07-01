"""amanah_autopilot/urls.py — EcoIQ Amanah Autopilot routes (mounted at /amanah-autopilot/)."""
from django.urls import path

from amanah_autopilot import views

app_name = 'amanah_autopilot'

urlpatterns = [
    path('', views.overview, name='overview'),
]
