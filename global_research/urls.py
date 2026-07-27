from django.urls import path

from global_research import views

app_name = 'global_research'

urlpatterns = [
    path('', views.mission_list, name='mission_list'),
    path('missions/<int:mission_id>/', views.mission_dashboard, name='mission_dashboard'),
    path('missions/<int:mission_id>/requirements/', views.requirement_builder, name='requirement_builder'),
    path('missions/<int:mission_id>/discovery/', views.global_discovery_view, name='global_discovery_view'),
    path('missions/<int:mission_id>/evidence/', views.evidence_view, name='evidence_view'),
    path('missions/<int:mission_id>/manufacturers/', views.manufacturer_comparison, name='manufacturer_comparison'),
    path('missions/<int:mission_id>/documents/', views.document_draft_list, name='document_draft_list'),
    path('documents/<int:draft_id>/', views.document_draft_detail, name='document_draft_detail'),
    path('technology/<int:candidate_id>/', views.technology_candidate_detail, name='technology_candidate_detail'),
    path('products/<int:candidate_id>/', views.product_candidate_detail, name='product_candidate_detail'),
    path('council/technology/<int:candidate_id>/', views.council_view_technology, name='council_view_technology'),
    path('council/product/<int:candidate_id>/', views.council_view_product, name='council_view_product'),

    # API
    path('api/missions/', views.api_mission_list, name='api_mission_list'),
    path('api/missions/<int:mission_id>/', views.api_mission_detail, name='api_mission_detail'),
    path('api/missions/<int:mission_id>/run/', views.api_run_mission, name='api_run_mission'),
    path('api/missions/<int:mission_id>/sources/', views.api_sources, name='api_sources'),
    path('api/missions/<int:mission_id>/claims/', views.api_claims, name='api_claims'),
    path('api/missions/<int:mission_id>/contradictions/', views.api_contradictions, name='api_contradictions'),
    path('api/missions/<int:mission_id>/comparison/', views.api_comparison, name='api_comparison'),
    path('api/missions/<int:mission_id>/audit-trail/', views.api_audit_trail, name='api_audit_trail'),
]
