"""geo_intelligence/urls.py — routes (mounted at /geo-intelligence/)."""
from django.urls import path

from geo_intelligence import views

app_name = 'geo_intelligence'

urlpatterns = [
    path('', views.command_centre, name='command_centre'),
]
