"""outreach_readiness/urls.py — routes (mounted at /outreach-readiness/). All staff-only."""
from django.urls import path

from outreach_readiness import views

app_name = 'outreach_readiness'

urlpatterns = [
    path('', views.candidate_review_list, name='candidate_review_list'),
    path('<int:opportunity_pk>/', views.assessment_detail, name='assessment_detail'),
    path('<int:opportunity_pk>/suitability/', views.record_suitability_view, name='record_suitability'),
    path('<int:opportunity_pk>/recipient-responsibility/', views.recipient_responsibility_view, name='recipient_responsibility'),
    path('<int:opportunity_pk>/sensitivity/', views.sensitivity_view, name='sensitivity_review'),
    path('<int:opportunity_pk>/ask/', views.minimum_viable_ask_view, name='minimum_viable_ask'),
    path('<int:opportunity_pk>/route/', views.add_route_view, name='add_route'),
    path('<int:opportunity_pk>/message/', views.create_message_version_view, name='create_message_version'),
    path('message/<int:version_pk>/review/', views.mark_reviewed_view, name='mark_message_reviewed'),
    path('message/<int:version_pk>/founder-approve/', views.founder_approve_message_view, name='founder_approve_message'),
    path('message/<int:version_pk>/risk-review/', views.record_risk_review_view, name='record_risk_review'),
    path('message/<int:version_pk>/dry-run/', views.run_dry_run_view, name='run_dry_run'),
    path('<int:opportunity_pk>/founder-review/', views.founder_send_review, name='founder_send_review'),
    path('<int:opportunity_pk>/founder-decision/', views.record_founder_decision_view, name='record_founder_decision'),
]
