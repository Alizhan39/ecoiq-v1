"""command_centre/urls.py — routes (mounted at /command-centre/)."""
from django.urls import path

from command_centre import views

app_name = 'command_centre'

urlpatterns = [
    path('', views.overview, name='overview'),
]
