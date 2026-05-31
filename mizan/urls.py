"""
mizan/urls.py — EcoIQ Mizan Engine URL patterns.

Mounted at /api/mizan/ from the root urls.py.

Four endpoints only:
  GET  /api/mizan/company/<slug>/
  GET  /api/mizan/country/<slug>/
  POST /api/mizan/project/
  GET  /api/mizan/explain/
"""
from django.urls import path
from . import views

app_name = 'mizan'

urlpatterns = [
    path('company/<slug:slug>/', views.mizan_company, name='company'),
    path('country/<slug:slug>/', views.mizan_country, name='country'),
    path('project/',             views.mizan_project, name='project'),
    path('explain/',             views.mizan_explain, name='explain'),
]
