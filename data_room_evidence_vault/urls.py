"""data_room_evidence_vault/urls.py — routes (mounted at /data-room-evidence-vault/)."""
from django.urls import path

from data_room_evidence_vault import views

app_name = 'data_room_evidence_vault'

urlpatterns = [
    path('', views.overview, name='overview'),
]
