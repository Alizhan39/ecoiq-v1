"""partner_participation/urls.py — routes (mounted at /partner-network/)."""
from django.urls import path

from partner_participation import views

app_name = 'partner_participation'

urlpatterns = [
    # Partner-facing (any authenticated user / verified members)
    path('', views.my_organisations, name='my_organisations'),
    path('<int:org_pk>/claim/', views.claim_organisation, name='claim_organisation'),
    path('<int:org_pk>/portal/', views.organisation_portal, name='organisation_portal'),
    path('<int:org_pk>/portal/declare-capability/', views.declare_capability_view, name='declare_capability'),
    path('<int:org_pk>/portal/capability/<int:capability_pk>/attach-evidence/', views.attach_evidence_view, name='attach_evidence'),
    path('<int:org_pk>/portal/set-preference/', views.set_preference_view, name='set_preference'),
    path('<int:org_pk>/portal/declare-resource/', views.declare_resource_view, name='declare_resource'),
    path('<int:org_pk>/portal/declare-funding-programme/', views.declare_funding_programme_view, name='declare_funding_programme'),
    path('<int:org_pk>/portal/capability/<int:capability_pk>/propose-route/', views.propose_route_view, name='propose_route'),
    path('<int:org_pk>/portal/routing/<int:candidate_pk>/respond/', views.respond_to_routing_candidate_view, name='respond_to_routing_candidate'),
    path('<int:org_pk>/portal/consent/', views.consent_view, name='consent'),

    # Invitation acceptance (any authenticated user, token-gated)
    path('invitation/<str:token>/accept/', views.accept_invitation_view, name='accept_invitation'),

    # EcoIQ staff-facing
    path('staff/membership-review/', views.membership_review_queue, name='membership_review_queue'),
    path('staff/membership/<int:membership_pk>/review/', views.review_membership_view, name='review_membership'),
    path('staff/declaration-review/', views.declaration_review_queue, name='declaration_review_queue'),
    path('staff/capability/<int:capability_pk>/review/', views.human_review_capability_view, name='human_review_capability'),
    path('staff/conflict/<int:conflict_pk>/resolve/', views.resolve_conflict_view, name='resolve_conflict'),
    path('staff/routing/<int:candidate_pk>/approve/', views.approve_routing_candidate_view, name='approve_routing_candidate'),
    path('staff/network-overview/', views.network_overview, name='network_overview'),

    # PR9 — invitations
    path('staff/invitations/<int:org_pk>/create/', views.create_invitation_view, name='create_invitation'),
    path('staff/invitations/<int:invitation_pk>/send/', views.send_invitation_view, name='send_invitation'),
    path('staff/invitations/<int:invitation_pk>/mark-manually-sent/', views.mark_manually_sent_view, name='mark_manually_sent'),
    path('staff/invitations/<int:invitation_pk>/revoke/', views.revoke_invitation_view, name='revoke_invitation'),

    # PR9 — share approval + delivery
    path('staff/routing/<int:candidate_pk>/share-confirm/', views.share_confirm_view, name='share_confirm'),
    path('staff/routing/<int:candidate_pk>/approve-share/', views.approve_share_view, name='approve_share'),
    path('staff/routing/<int:candidate_pk>/reject-share/', views.reject_share_view, name='reject_share'),
    path('staff/routing/<int:candidate_pk>/deliver-real-email/', views.deliver_real_email_view, name='deliver_real_email'),
    path('staff/routing/<int:candidate_pk>/deliver-manual/', views.deliver_manual_view, name='deliver_manual'),
    path('staff/routing/<int:candidate_pk>/record-response/', views.record_response_view, name='record_response'),
    path('staff/routing/<int:candidate_pk>/next-step/', views.create_next_step_view, name='create_next_step'),

    # PR9 — Activation Dashboard
    path('staff/activation-dashboard/', views.activation_dashboard, name='activation_dashboard'),
]
