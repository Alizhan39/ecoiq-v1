"""financial_intelligence_cloud/urls.py — routes (mounted at /financial-intelligence-cloud/)."""
from django.urls import path

from financial_intelligence_cloud import views

app_name = 'financial_intelligence_cloud'

urlpatterns = [
    path('', views.overview, name='overview'),
    path('accounting-operations/', views.accounting_operations, name='accounting_operations'),
    path('accounting-operations/reminders/add/', views.add_accounting_reminder, name='add_accounting_reminder'),
    path('accounting-operations/reminders/<int:reminder_id>/update/', views.update_accounting_reminder, name='update_accounting_reminder'),
    path('accounting-operations/services/add/', views.add_client_service, name='add_client_service'),
    path('accounting-operations/payments/add/', views.add_client_payment, name='add_client_payment'),
    path('accounting-operations/payments/<int:payment_id>/record/', views.record_client_payment, name='record_client_payment'),
    path('opportunity-feed/', views.opportunity_feed, name='opportunity_feed'),
    path('clients-to-call/', views.clients_to_call, name='clients_to_call'),
    path('portfolio/', views.portfolio_view, name='portfolio'),
    path('ask/', views.ask, name='ask'),
    path('daily-brief/', views.daily_brief, name='daily_brief'),
    path('subscription/', views.subscription, name='subscription'),
    path('demo/accounting/', views.demo_accounting, name='demo_accounting'),
    path('demo/investment/', views.demo_investment, name='demo_investment'),
    path('demo/bank/', views.demo_bank, name='demo_bank'),
]
