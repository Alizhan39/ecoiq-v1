"""industrial_playbook_library/urls.py — routes (mounted at /industrial-playbook-library/)."""
from django.urls import path

from industrial_playbook_library import views

app_name = 'industrial_playbook_library'

urlpatterns = [
    path('', views.overview, name='overview'),
]
