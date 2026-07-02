"""institutional_finance_engine/urls.py — routes (mounted at /institutional-finance-engine/)."""
from django.urls import path

from institutional_finance_engine import views

app_name = 'institutional_finance_engine'

urlpatterns = [
    path('', views.overview, name='overview'),
]
