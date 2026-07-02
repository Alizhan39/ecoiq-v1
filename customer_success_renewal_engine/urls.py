"""customer_success_renewal_engine/urls.py — routes (mounted at /customer-success-renewal-engine/)."""
from django.urls import path

from customer_success_renewal_engine import views

app_name = 'customer_success_renewal_engine'

urlpatterns = [
    path('', views.overview, name='overview'),
]
