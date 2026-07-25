"""
public_action_preparation/services/process_verification.py — Phase 3:
official process verification. Every field is a real, human-checked
fact — never invented. `status` is only ever 'open' when a real human
explicitly recorded it as currently open at `last_checked_at`; a
`closing_date` in the past is a structural override to 'expired'
regardless of what a reviewer types, so a stale form submission can
never leave a lapsed process looking open.
"""
from django.utils import timezone

from public_action_preparation.models import VerifiedOfficialProcess


class ProcessVerificationNotAllowedError(Exception):
    pass


def get_or_create_process(opportunity):
    process, _ = VerifiedOfficialProcess.objects.get_or_create(opportunity=opportunity)
    return process


def record_process_verification(opportunity, *, actor, process_name, owning_organisation, official_url='',
                                 route_type='', opening_date=None, closing_date=None, eligibility='',
                                 required_information='', submission_format='', evidence_allowed='',
                                 acknowledgement_semantics='', status='unknown', checked_notes=''):
    if actor is None:
        raise ProcessVerificationNotAllowedError('Official process verification requires a real actor.')
    process = get_or_create_process(opportunity)
    process.process_name = process_name
    process.owning_organisation = owning_organisation
    process.official_url = official_url
    process.route_type = route_type
    process.opening_date = opening_date
    process.closing_date = closing_date
    process.eligibility = eligibility
    process.required_information = required_information
    process.submission_format = submission_format
    process.evidence_allowed = evidence_allowed
    process.acknowledgement_semantics = acknowledgement_semantics
    process.checked_notes = checked_notes
    process.last_checked_at = timezone.now()
    process.last_checked_by = actor

    # A real recorded closing_date in the past always wins over a
    # reviewer's status choice — never trust "open" against a real,
    # already-passed date (Phase 3's own "do not invent still-open
    # status" discipline, made structural rather than advisory).
    if closing_date is not None and closing_date < timezone.now().date():
        process.status = 'expired'
    else:
        process.status = status
    process.save()
    return process
