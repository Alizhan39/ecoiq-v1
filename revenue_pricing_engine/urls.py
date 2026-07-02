"""revenue_pricing_engine/urls.py — routes (mounted at /revenue-pricing-engine/)."""
from django.urls import path

from revenue_pricing_engine import views

app_name = 'revenue_pricing_engine'

urlpatterns = [
    path('', views.overview, name='overview'),
]
