"""product_analytics_kpi_engine/urls.py — routes (mounted at /product-analytics-kpi-engine/)."""
from django.urls import path

from product_analytics_kpi_engine import views

app_name = 'product_analytics_kpi_engine'

urlpatterns = [
    path('', views.overview, name='overview'),
]
