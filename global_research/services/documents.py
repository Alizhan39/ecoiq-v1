"""
global_research/services/documents.py — draft-only RFI/RFQ/etc generation.

Follows `outreach_readiness`'s exact versioned, immutable-once-approved
shape (docs/adr/ADR-global-research-engine.md decision 9). No send/email/
HTTP-POST-to-vendor function is ever imported anywhere in this module or
this app — a draft can be generated, edited (as a new version), and
approved, and that is the end of what this system does with it.
"""
from django.utils import timezone

from global_research.services.human_approval_gate import require_human_approval

EVIDENCE_REQUESTED_DEFAULT = ['Independent test reports', 'Certifications', 'Reference installations in comparable climates']
COMMERCIAL_QUESTIONS_DEFAULT = ['List price vs quotation', 'Currency and tax treatment', 'Delivery and installation inclusion', 'Lead time']
DELIVERY_SERVICE_QUESTIONS_DEFAULT = ['Local service coverage', 'Spare-parts lead time', 'Warranty terms']
CYBERSECURITY_QUESTIONS_DEFAULT = ['Remote-access requirements', 'Data residency', 'Communications protocol']
CERTIFICATION_QUESTIONS_DEFAULT = ['Applicable standards and certifications for the deployment jurisdiction']
STEWARDSHIP_QUESTIONS_DEFAULT = ['Installation worker-safety plan', 'Environmental impact during commissioning']


class DraftAlreadyApprovedError(Exception):
    """Raised when a caller tries to mutate an already-approved draft —
    editing must create a new version instead (mirrors
    outreach_readiness.OutreachMessageVersion)."""


def _shareable_context(mission):
    """Only the asset context explicitly authorised to share — an explicit
    allowlist, never raw Digital Twin metrics/financials, mirroring
    `leads.client_report_preview`'s field-allowlist pattern."""
    return (
        f'Industry: {mission.industry or "not specified"}. '
        f'Deployment country: {mission.country_of_deployment or "not specified"}. '
        f'Scope: {mission.scope or "not specified"}.'
    )


def _requirements_included(mission):
    lines = []
    for r in mission.requirements.filter(approved=True):
        unit_symbol = r.unit.symbol or r.unit.code if r.unit else ''
        bound = f'min {r.minimum_value}' if r.minimum_value is not None else (f'max {r.maximum_value}' if r.maximum_value is not None else 'see description')
        lines.append(f'{r.description} ({r.metric}: {bound} {unit_symbol})'.strip())
    return lines


def generate_document_draft(mission, document_type):
    """Creates a new version. If a prior draft version for this document
    type is still status='draft' (never approved), it is superseded rather
    than left as two live drafts."""
    from global_research.models import ResearchDocumentDraft

    previous = mission.document_drafts.filter(document_type=document_type).order_by('-version').first()
    next_version = (previous.version if previous else 0) + 1
    if previous and previous.status == 'draft':
        previous.status = 'superseded'
        previous.save(update_fields=['status', 'updated_at'])

    requirements_included = _requirements_included(mission)
    body_lines = [
        f'{dict(ResearchDocumentDraft.DOCUMENT_TYPE_CHOICES).get(document_type, document_type)} — {mission.title} (v{next_version})',
        '', 'Context (supplier-neutral; no sensitive Digital Twin data included):', _shareable_context(mission),
        '', 'Required technical specification:',
    ] + [f'- {line}' for line in requirements_included] + [
        '', 'Requested evidence: ' + '; '.join(EVIDENCE_REQUESTED_DEFAULT) + '.',
        '', 'Requested commercial breakdown: ' + '; '.join(COMMERCIAL_QUESTIONS_DEFAULT) + '.',
        '', 'Delivery and service: ' + '; '.join(DELIVERY_SERVICE_QUESTIONS_DEFAULT) + '.',
        '', 'Cybersecurity and data: ' + '; '.join(CYBERSECURITY_QUESTIONS_DEFAULT) + '.',
        '', 'Certification: ' + '; '.join(CERTIFICATION_QUESTIONS_DEFAULT) + '.',
        '', 'Stewardship and worker safety: ' + '; '.join(STEWARDSHIP_QUESTIONS_DEFAULT) + '.',
    ]

    return ResearchDocumentDraft.objects.create(
        mission=mission, document_type=document_type, version=next_version,
        title=f'{dict(ResearchDocumentDraft.DOCUMENT_TYPE_CHOICES).get(document_type, document_type)} — {mission.title} v{next_version}',
        shareable_context=_shareable_context(mission), requirements_included=requirements_included,
        evidence_requested=EVIDENCE_REQUESTED_DEFAULT, commercial_questions=COMMERCIAL_QUESTIONS_DEFAULT,
        delivery_service_questions=DELIVERY_SERVICE_QUESTIONS_DEFAULT, cybersecurity_data_questions=CYBERSECURITY_QUESTIONS_DEFAULT,
        certification_questions=CERTIFICATION_QUESTIONS_DEFAULT, stewardship_worker_safety_questions=STEWARDSHIP_QUESTIONS_DEFAULT,
        body_text='\n'.join(body_lines), status='draft',
    )


def approve_document_draft(draft, human_decision, approved_by):
    """Requires human approval; never sends anything — approval only marks
    the draft as ready for a human to use OUTSIDE this system."""
    require_human_approval('research_document_draft_approval', human_decision)
    if draft.status == 'approved':
        raise DraftAlreadyApprovedError(f'Draft {draft.pk} is already approved — create a new version to edit it, never mutate an approved draft.')
    draft.status = 'approved'
    draft.approved_by = approved_by
    draft.approved_at = timezone.now()
    draft.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
    return draft
