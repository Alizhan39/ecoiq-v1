"""gold_intelligence/urls.py — routes (mounted at /gold-intelligence/)."""
from django.urls import path

from gold_intelligence import views, targeting_views

app_name = 'gold_intelligence'

urlpatterns = [
    path('', views.directory, name='directory'),
    path('map/', views.mine_map, name='mine_map'),
    path('targets/', targeting_views.targets_map, name='targets_map'),
    path('targets/geojson/', targeting_views.targets_geojson, name='targets_geojson'),
    path('targets/cadastre.geojson', targeting_views.cadastre_geojson, name='cadastre_geojson'),
    path('targets/pilot/research-queue.json', targeting_views.pilot_research_queue_json, name='pilot_research_queue'),
    path('targets/pilot/named-deposits.json', targeting_views.named_gold_references_json, name='named_gold_references'),
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
