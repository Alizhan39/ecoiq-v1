"""microsoft_core_stack/urls.py — routes (mounted at /microsoft-ecosystem-core-stack/)."""
from django.urls import path

from microsoft_core_stack import views

app_name = 'microsoft_core_stack'

urlpatterns = [
    path('', views.overview, name='overview'),
]
