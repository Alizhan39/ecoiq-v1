"""portfolio_country_transition_atlas/urls.py — routes (mounted at /portfolio-country-transition-atlas/)."""
from django.urls import path

from portfolio_country_transition_atlas import views

app_name = 'portfolio_country_transition_atlas'

urlpatterns = [
    path('', views.overview, name='overview'),
]
