"""public_need_discovery/urls.py — routes (mounted at /public-need-discovery/). All staff-only."""
from django.urls import path

from public_need_discovery import views

app_name = 'public_need_discovery'

urlpatterns = [
    path('', views.candidate_queue, name='candidate_queue'),
    path('<int:opportunity_pk>/', views.candidate_detail, name='candidate_detail'),
    path('<int:opportunity_pk>/resolve-jurisdiction/', views.resolve_jurisdiction_view, name='resolve_jurisdiction'),
    path('<int:opportunity_pk>/resolve-responsible-party/', views.resolve_responsible_party_view, name='resolve_responsible_party'),
    path('<int:opportunity_pk>/suggest-roles/', views.suggest_roles_view, name='suggest_roles'),
    path('<int:opportunity_pk>/add-role/', views.add_role_view, name='add_role'),
    path('role/<int:role_pk>/confirm/', views.confirm_role_view, name='confirm_role'),
    path('<int:opportunity_pk>/small-action/', views.record_small_action_view, name='record_small_action'),
    path('<int:opportunity_pk>/official-process/', views.record_official_process_view, name='record_official_process'),
    path('<int:opportunity_pk>/sensitivity/', views.sensitivity_review_view, name='sensitivity_review'),
    path('<int:opportunity_pk>/set-state/', views.set_actionability_state_view, name='set_actionability_state'),
    path('<int:opportunity_pk>/promote/', views.promote_view, name='promote_to_outreach_readiness'),
]
