"""good_agents/urls.py — routes (mounted at /good-agents/)."""
from django.urls import path

from good_agents import views

app_name = 'good_agents'

urlpatterns = [
    path('', views.opportunity_list, name='opportunity_list'),
    path('morning-brief/', views.morning_brief, name='morning_brief'),
    path('action-centre/', views.impact_action_centre, name='impact_action_centre'),
    path('mission-control/', views.mission_control_view, name='mission_control'),
    path('api/map/', views.good_map_api, name='good_map_api'),
    path('api/observatory-health/', views.observatory_health_api, name='observatory_health_api'),

    # PR5 — governed action network mutations. All staff-only, POST-only
    # (except the read-only project-candidate confirm screen).
    path('<int:pk>/gate/transition/', views.gate_transition, name='gate_transition'),
    path('<int:pk>/pathway/create/', views.pathway_create, name='pathway_create'),
    path('outreach/<int:draft_pk>/approve/', views.outreach_approve, name='outreach_approve'),
    path('outreach/<int:draft_pk>/send/', views.outreach_send, name='outreach_send'),
    path('connection/<int:candidate_pk>/approve/', views.connection_approve, name='connection_approve'),
    path('<int:pk>/project-candidate/propose/', views.project_candidate_propose, name='project_candidate_propose'),
    path('project-candidate/<int:candidate_pk>/approve/', views.project_candidate_approve, name='project_candidate_approve'),
    path('project-candidate/<int:candidate_pk>/create/', views.project_candidate_create_confirm, name='project_candidate_create_confirm'),
    path('project-candidate/<int:candidate_pk>/create/execute/', views.project_candidate_create_execute, name='project_candidate_create_execute'),

    path('<int:pk>/', views.opportunity_detail, name='opportunity_detail'),

    # PR11 — Real-World Pilot Launchpad
    path('pilot-launchpad/', views.pilot_launchpad_redirect, name='pilot_launchpad_redirect'),
    path('<int:pk>/pilot-launchpad/', views.pilot_launchpad_view, name='pilot_launchpad'),
    path('<int:pk>/pilot-launchpad/dossier/', views.pilot_dossier_view, name='pilot_dossier'),
    path('<int:pk>/pilot-launchpad/public/', views.pilot_launchpad_public_view, name='pilot_launchpad_public'),
    path('responsible-party/<int:party_pk>/add-contact/', views.add_contact_view, name='add_contact'),
    path('<int:pk>/resolve-responsible-party/', views.resolve_responsible_party_view, name='resolve_responsible_party'),
    path('pathway/<int:pathway_pk>/create-outreach-draft/', views.create_outreach_draft_view, name='create_outreach_draft'),
]
