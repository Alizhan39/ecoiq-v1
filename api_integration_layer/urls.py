"""api_integration_layer/urls.py — routes (mounted at /api-integration-layer/)."""
from django.urls import path

from api_integration_layer import views

app_name = 'api_integration_layer'

urlpatterns = [
    path('', views.overview, name='overview'),
]
