"""ai_agent_operations_console/urls.py — routes (mounted at /ai-agent-operations-console/)."""
from django.urls import path

from ai_agent_operations_console import views

app_name = 'ai_agent_operations_console'

urlpatterns = [
    path('', views.overview, name='overview'),
]
