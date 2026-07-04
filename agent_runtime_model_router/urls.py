"""agent_runtime_model_router/urls.py — routes (mounted at /agent-runtime-model-router/)."""
from django.urls import path

from agent_runtime_model_router import views

app_name = 'agent_runtime_model_router'

urlpatterns = [
    path('', views.overview, name='overview'),
    path('run/<int:run_id>/', views.run_detail, name='run_detail'),
    path('case/<slug:case_slug>/', views.case_trace, name='case_trace'),
]
