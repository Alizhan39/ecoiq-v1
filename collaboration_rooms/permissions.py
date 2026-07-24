"""
collaboration_rooms/permissions.py — access isolation (Phase 4). A user
may access a room ONLY via a real, non-revoked RoomParticipant row —
never inferred from organisation membership alone, never from being
staff (staff still need an explicit coordinator participant row, added
at room-creation time). Mirrors partner_participation.permissions'
own membership_required() pattern exactly.
"""
import functools

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404

from collaboration_rooms.models import ACTING_ROOM_ROLES, CollaborationRoom, RoomParticipant


def get_active_participant(room, user):
    if not user.is_authenticated:
        return None
    return RoomParticipant.objects.filter(room=room, user=user, revoked_at__isnull=True).first()


def has_room_access(room, user):
    return get_active_participant(room, user) is not None


def room_access_required(view_func):
    """Requires login AND an active RoomParticipant row. Attaches request.room / request.room_participant."""
    @functools.wraps(view_func)
    @login_required(login_url='/login/')
    def wrapped(request, room_pk, *args, **kwargs):
        room = get_object_or_404(CollaborationRoom, pk=room_pk)
        participant = get_active_participant(room, request.user)
        if participant is None:
            # Never leak whether the room exists to an unauthorised user beyond a flat 403 —
            # no room enumeration (Phase 4's own "no leakage through IDs" rule).
            return HttpResponseForbidden('You do not have access to this collaboration room.')
        request.room = room
        request.room_participant = participant
        return view_func(request, room_pk, *args, **kwargs)
    return wrapped


def acting_participant_required(view_func):
    """Same as room_access_required, but the participant's role must be one that may act (propose/consent/answer/share)."""
    @functools.wraps(view_func)
    @room_access_required
    def wrapped(request, room_pk, *args, **kwargs):
        if request.room_participant.role not in ACTING_ROOM_ROLES:
            return HttpResponseForbidden('Your room role does not permit this action.')
        return view_func(request, room_pk, *args, **kwargs)
    return wrapped
