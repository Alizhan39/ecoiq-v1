"""document_reader_agent_training_pack/urls.py — routes (mounted at /document-reader-agent-training-pack/)."""
from django.urls import path

from document_reader_agent_training_pack import views

app_name = 'document_reader_agent_training_pack'

urlpatterns = [
    path('', views.overview, name='overview'),
]
