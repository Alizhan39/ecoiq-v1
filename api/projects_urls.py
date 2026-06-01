"""
api/projects_urls.py — EcoIQ Project Intelligence API URL patterns.

Mounted at /api/projects/ from the root urls.py.

Endpoints:
  POST /api/projects/readiness/   Project Readiness Score
"""
from django.urls import path
from api import views

app_name = 'projects'

urlpatterns = [
    path('readiness/', views.project_readiness_score, name='readiness'),
]
