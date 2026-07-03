"""frontend_implementation_roadmap/urls.py — routes (mounted at /frontend-implementation-roadmap/)."""
from django.urls import path

from frontend_implementation_roadmap import views

app_name = 'frontend_implementation_roadmap'

urlpatterns = [
    path('', views.overview, name='overview'),
]
