"""sales_crm_partner_pipeline/urls.py — routes (mounted at /sales-crm-partner-pipeline/)."""
from django.urls import path

from sales_crm_partner_pipeline import views

app_name = 'sales_crm_partner_pipeline'

urlpatterns = [
    path('', views.overview, name='overview'),
]
