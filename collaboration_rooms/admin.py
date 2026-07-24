from django.contrib import admin

from collaboration_rooms.models import (
    CollaborationRoom, InformationRequest, InformationRequestResponse, NextStepProposal, RoomActivityEvent,
    RoomConsent, RoomEvidenceItem, RoomMessage, RoomParticipant,
)


@admin.register(CollaborationRoom)
class CollaborationRoomAdmin(admin.ModelAdmin):
    list_display = ('title', 'routing_candidate', 'status', 'created_at', 'last_activity_at')
    list_filter = ('status',)
    search_fields = ('title',)


@admin.register(RoomParticipant)
class RoomParticipantAdmin(admin.ModelAdmin):
    list_display = ('room', 'user', 'organisation', 'role', 'added_at', 'revoked_at')
    list_filter = ('role',)


@admin.register(RoomEvidenceItem)
class RoomEvidenceItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'room', 'evidence_type', 'verification_state', 'visibility', 'created_at')
    list_filter = ('evidence_type', 'verification_state', 'visibility')


@admin.register(InformationRequest)
class InformationRequestAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'room', 'request_type', 'status', 'created_at')
    list_filter = ('request_type', 'status')


@admin.register(InformationRequestResponse)
class InformationRequestResponseAdmin(admin.ModelAdmin):
    list_display = ('request', 'responded_by', 'is_claim_only', 'created_at')


@admin.register(RoomMessage)
class RoomMessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'author', 'visibility', 'created_at', 'edited_at')
    list_filter = ('visibility',)


@admin.register(NextStepProposal)
class NextStepProposalAdmin(admin.ModelAdmin):
    list_display = ('proposal_type', 'room', 'status', 'requires_ecoiq_consent', 'created_at')
    list_filter = ('proposal_type', 'status')


@admin.register(RoomConsent)
class RoomConsentAdmin(admin.ModelAdmin):
    list_display = ('proposal', 'organisation', 'status', 'actor', 'decided_at')
    list_filter = ('status',)


@admin.register(RoomActivityEvent)
class RoomActivityEventAdmin(admin.ModelAdmin):
    list_display = ('room', 'event_type', 'actor', 'organisation', 'created_at')
    list_filter = ('event_type',)
