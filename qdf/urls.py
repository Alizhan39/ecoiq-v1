"""qdf/urls.py — Quranic Decision Filter API routes (mounted at /api/qdf/)."""
from django.urls import path

from qdf import api_views

app_name = 'qdf'

urlpatterns = [
    path('questions/',                      api_views.qdf_questions,       name='questions'),
    path('companies/<slug:slug>/',          api_views.qdf_company,         name='company'),
    path('companies/<slug:slug>/engine/',   api_views.qdf_decision_engine, name='engine'),
    path('companies/<slug:slug>/scenario/', api_views.qdf_scenario,        name='scenario'),
    path('evaluate/',                       api_views.qdf_evaluate,        name='evaluate'),
]
