"""financial_intelligence_cloud/urls.py — routes (mounted at /financial-intelligence-cloud/)."""
from django.urls import path

from financial_intelligence_cloud import views

app_name = 'financial_intelligence_cloud'

urlpatterns = [
    path('', views.overview, name='overview'),
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
