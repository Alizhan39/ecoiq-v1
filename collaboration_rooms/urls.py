"""collaboration_rooms/urls.py — routes (mounted at /collaboration/)."""
from django.urls import path

from collaboration_rooms import views

app_name = 'collaboration_rooms'

urlpatterns = [
    # Partner-facing (any authenticated user with an active RoomParticipant row)
    path('', views.rooms_list, name='rooms_list'),
    path('<int:room_pk>/', views.room_detail, name='room_detail'),
    path('<int:room_pk>/message/', views.post_message_view, name='post_message'),
    path('<int:room_pk>/evidence/', views.share_evidence_view, name='share_evidence'),
    path('<int:room_pk>/request/', views.create_request_view, name='create_request'),
    path('<int:room_pk>/request/<int:request_pk>/respond/', views.respond_to_request_view, name='respond_to_request'),
    path('<int:room_pk>/request/<int:request_pk>/status/', views.set_request_status_view, name='set_request_status'),
    path('<int:room_pk>/proposal/', views.create_proposal_view, name='create_proposal'),
    path('<int:room_pk>/proposal/<int:proposal_pk>/consent/', views.give_consent_view, name='give_consent'),
    path('<int:room_pk>/proposal/<int:proposal_pk>/reject-consent/', views.reject_consent_view, name='reject_consent'),
    path('<int:room_pk>/ai/summarise/', views.ai_summarise_view, name='ai_summarise'),
    path('<int:room_pk>/ai/open-questions/', views.ai_open_questions_view, name='ai_open_questions'),
    path('<int:room_pk>/ai/meeting-brief/', views.ai_meeting_brief_view, name='ai_meeting_brief'),

    # EcoIQ staff-facing
    path('staff/centre/', views.staff_collaboration_centre, name='staff_centre'),
    path('staff/routing-candidate/<int:candidate_pk>/create-room/', views.create_room_view, name='create_room'),
    path('staff/room/<int:room_pk>/add-participant/', views.add_participant_view, name='add_participant'),
    path('staff/room/<int:room_pk>/participant/<int:participant_pk>/revoke/', views.revoke_participant_view, name='revoke_participant'),
    path('staff/room/<int:room_pk>/withdraw/<int:org_pk>/', views.withdraw_organisation_view, name='withdraw_organisation'),
    path('staff/room/<int:room_pk>/close/', views.close_room_view, name='close_room'),
    path('staff/room/<int:room_pk>/evidence/<int:item_pk>/verify/', views.verify_evidence_view, name='verify_evidence'),
    path('staff/proposal/<int:proposal_pk>/promote/', views.promote_proposal_view, name='promote_proposal'),
]
