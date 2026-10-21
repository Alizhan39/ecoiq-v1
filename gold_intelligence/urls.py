"""gold_intelligence/urls.py — routes (mounted at /gold-intelligence/)."""
from django.urls import path

from gold_intelligence import views

app_name = 'gold_intelligence'

urlpatterns = [
    path('', views.directory, name='directory'),
    path('map/', views.mine_map, name='mine_map'),
    path('public-benchmarks/', views.public_benchmarks_view, name='public_benchmarks'),
    path('public-time-series/', views.public_time_series_view, name='public_time_series'),
    path('<slug:slug>/', views.investor_view, name='investor_view'),
    path('<slug:slug>/dashboard/', views.investment_dashboard, name='investment_dashboard'),
    path('<slug:slug>/stewardship/', views.stewardship_view, name='stewardship'),
    path('<slug:slug>/risk/', views.risk_intelligence_view, name='risk_intelligence'),
    path('<slug:slug>/timeline/', views.timeline_view, name='timeline'),
    path('<slug:slug>/capital/', views.capital_tracker_view, name='capital_tracker'),
    path('<slug:slug>/equipment/', views.equipment_intelligence_view, name='equipment_intelligence'),
]
