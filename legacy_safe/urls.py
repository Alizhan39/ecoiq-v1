"""legacy_safe/urls.py — EcoIQ LegacySafe AI web routes (mounted at /legacy-safe/)."""
from django.urls import path

from legacy_safe import views

app_name = 'legacy_safe'

urlpatterns = [
    path('',                   views.dashboard,         name='dashboard'),
    path('upload/',            views.upload_document,   name='upload'),
    path('ask/',               views.ask_agent,         name='ask'),
    path('permission-demo/',   views.permission_demo,   name='permission_demo'),
    path('audit-logs/',        views.audit_logs,        name='audit_logs'),
    path('dependency-graph/',  views.dependency_graph,  name='dependency_graph'),
    path('revocation-demo/',   views.revocation_demo,   name='revocation_demo'),
    path('model-integration-readiness/', views.model_integration_readiness, name='model_integration_readiness'),
    path('repository-support/', views.repository_support, name='repository_support'),
    path('process-optimisation/', views.process_optimisation, name='process_optimisation'),
    path('justice-maqasid/', views.justice_maqasid, name='justice_maqasid'),
    path('agent-repository-map/', views.agent_repository_map, name='agent_repository_map'),
]
