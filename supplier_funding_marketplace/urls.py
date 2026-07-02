"""supplier_funding_marketplace/urls.py — routes (mounted at /supplier-funding-marketplace/)."""
from django.urls import path

from supplier_funding_marketplace import views

app_name = 'supplier_funding_marketplace'

urlpatterns = [
    path('', views.overview, name='overview'),
]
