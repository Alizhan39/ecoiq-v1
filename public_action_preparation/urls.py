"""public_action_preparation/urls.py — routes (mounted at /public-action-preparation/). All staff-only."""
from django.urls import path

from public_action_preparation import views

app_name = 'public_action_preparation'

urlpatterns = [
    path('', views.candidate_comparison, name='candidate_comparison'),
    path('<int:opportunity_pk>/', views.action_prep_detail, name='action_prep_detail'),
    path('<int:opportunity_pk>/action-type/', views.record_action_type_view, name='record_action_type'),
    path('<int:opportunity_pk>/process-verification/', views.record_process_verification_view, name='record_process_verification'),
    path('<int:opportunity_pk>/ethics-review/', views.record_ethics_review_view, name='record_ethics_review'),
    path('<int:opportunity_pk>/content-draft/', views.create_content_draft_view, name='create_content_draft'),
    path('draft/<int:draft_pk>/review/', views.mark_draft_reviewed_view, name='mark_draft_reviewed'),
    path('draft/<int:draft_pk>/founder-approve/', views.founder_approve_draft_view, name='founder_approve_draft'),
    path('<int:opportunity_pk>/review-role/', views.add_review_role_view, name='add_review_role'),
    path('<int:opportunity_pk>/founder-action-review/', views.founder_action_review, name='founder_action_review'),
    path('<int:opportunity_pk>/founder-action-decision/', views.record_founder_action_decision_view, name='record_founder_action_decision'),
    path('<int:opportunity_pk>/dossier/', views.dossier_view, name='dossier'),
]
