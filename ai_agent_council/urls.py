"""ai_agent_council/urls.py — routes (mounted at /ai-agent-council/)."""
from django.urls import path

from ai_agent_council import views

app_name = 'ai_agent_council'

urlpatterns = [
    path('', views.overview, name='overview'),
]
