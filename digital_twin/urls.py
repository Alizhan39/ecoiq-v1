from django.urls import path

from digital_twin import views

app_name = 'digital_twin'

urlpatterns = [
    path('', views.asset_list, name='asset_list'),
    path('assets/<int:asset_id>/', views.asset_detail, name='asset_detail'),
    path('twins/<int:twin_id>/', views.twin_baseline, name='twin_baseline'),
    path('twins/<int:twin_id>/process-map/', views.twin_process_map, name='twin_process_map'),
    path('twins/<int:twin_id>/data-gaps/', views.twin_data_gaps, name='twin_data_gaps'),
    path('twins/<int:twin_id>/losses/', views.twin_losses, name='twin_losses'),
    path('twins/<int:twin_id>/scenarios/', views.twin_scenarios, name='twin_scenarios'),
    path('scenarios/compare/', views.scenario_compare, name='scenario_compare'),
    path('scenarios/<int:scenario_id>/', views.scenario_detail, name='scenario_detail'),
    path('scenarios/<int:scenario_id>/stewardship/', views.scenario_stewardship, name='scenario_stewardship'),
    path('scenarios/<int:scenario_id>/council/', views.scenario_council, name='scenario_council'),
    path('scenarios/<int:scenario_id>/approve/', views.scenario_approve, name='scenario_approve'),
    path('scenarios/<int:scenario_id>/promote/', views.scenario_promote, name='scenario_promote'),
    path('scenarios/<int:scenario_id>/implementation/', views.scenario_implementation, name='scenario_implementation'),

    # API (DRF), mounted under /digital-twin/api/
    path('api/assets/', views.api_asset_list, name='api_asset_list'),
    path('api/twins/<int:twin_id>/baseline/', views.api_twin_baseline, name='api_twin_baseline'),
    path('api/scenarios/<int:scenario_id>/simulation/', views.api_scenario_simulation, name='api_scenario_simulation'),
]
