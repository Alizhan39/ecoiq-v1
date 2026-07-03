"""agent_training_evaluation_lab/urls.py — routes (mounted at /agent-training-evaluation-lab/)."""
from django.urls import path

from agent_training_evaluation_lab import views

app_name = 'agent_training_evaluation_lab'

urlpatterns = [
    path('', views.overview, name='overview'),
]
