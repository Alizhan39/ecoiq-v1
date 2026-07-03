"""mrv_agent_training_pack/urls.py — routes (mounted at /mrv-agent-training-pack/)."""
from django.urls import path

from mrv_agent_training_pack import views

app_name = 'mrv_agent_training_pack'

urlpatterns = [
    path('', views.overview, name='overview'),
]
