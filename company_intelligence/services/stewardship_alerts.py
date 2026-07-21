"""
company_intelligence/services/stewardship_alerts.py — feat/stewardship-
monitor (PR 14): turns a real StewardshipChangeEvent into an internal,
staff-facing research/evidence alert. Never an investment alert — no
alert message anywhere in this module may use price/opportunity/buy/sell
language (see BANNED_PHRASES, enforced in tests).

Priority is a plain, documented integer sum — every component computed
here and stored on the alert (`priority_components`) so a reviewer can see
exactly why one alert outranks another, never a hidden/tuned model score.
"""
from django.utils import timezone

from company_intelligence.models import StewardshipAlert

SEVERITY_WEIGHT = {'info': 0, 'low': 1, 'medium': 2, 'high': 3, 'critical': 4}

# How much this change TYPE alone contributes — a potential conflict or an
# unreachable source is inherently more actionable than a routine new
# evidence row, independent of severity label.
CHANGE_TYPE_WEIGHT = {
    'potential_conflict': 3,
    'source_unreachable': 2,
    'new_document': 2,
    'document_updated': 2,
    'document_removed_or_unreachable': 2,
    'shariah_data_changed': 2,
    'new_kpi_candidate': 1,
    'source_recovered': 1,
    'evidence_stale': 1,
    'review_required': 1,
    'new_source': 1,
    'source_changed': 1,
    'new_evidence': 1,
    'evidence_changed': 1,
}

# Templated, deterministic message per event type — never AI-generated
# prose, never investment-recommendation framing (BANNED_PHRASES below is
# enforced by tests over every template here).
MESSAGE_TEMPLATES = {
    'new_source': '{company} — a new authoritative source was registered.',
    'source_changed': '{company} — a registered source changed.',
    'source_unreachable': '{company} — a previously available source is now unreachable.',
    'source_recovered': '{company} — a previously failing source is reachable again.',
    'new_document': '{company} published a new report.',
    'document_updated': "{company}'s report was updated.",
    'document_removed_or_unreachable': "{company}'s document is no longer reachable.",
    'new_evidence': '{company} — new evidence was extracted.',
    'evidence_changed': '{company} — existing evidence changed.',
    'new_kpi_candidate': '{company} — new KPI candidate(s) require review.',
    'potential_conflict': '{company} — potential conflict detected; human review required.',
    'evidence_stale': "{company}'s evidence may be stale.",
    'shariah_data_changed': "{company}'s Shariah screening data may require refresh.",
    'review_required': '{company} — items require human review.',
}

BANNED_PHRASES = (
    'buy', 'sell', 'hold', 'target price', 'undervalued', 'overvalued',
    'outperform', 'price opportunity', 'buy opportunity', 'sell signal',
)


def _source_authority_component(event):
    if event.source_id is None:
        return 0
    from harvester.verification import source_tier

    tier = source_tier(event.source.source_type)
    if tier <= 2:
        return 2
    if tier == 3:
        return 1
    return 0


def _priority_components(event):
    """Every component that contributes to an alert's priority, always
    returned alongside the total — never hidden."""
    components = {
        'severity_weight': SEVERITY_WEIGHT.get(event.severity, 0),
        'change_type_weight': CHANGE_TYPE_WEIGHT.get(event.event_type, 1),
        'source_authority': _source_authority_component(event),
        'review_required': 1 if event.review_required else 0,
    }
    return components, sum(components.values())


def alert_message_for_event(event):
    template = MESSAGE_TEMPLATES.get(event.event_type, '{company} — evidence change detected.')
    return template.format(company=event.company.company.name)


def generate_alert_for_event(event):
    """Idempotent — one StewardshipAlert per StewardshipChangeEvent (a
    OneToOne-shaped relationship enforced by get_or_create, not a DB
    constraint, since an alert's own lifecycle — acknowledged/resolved —
    must survive being looked up again without ever duplicating)."""
    existing = StewardshipAlert.objects.filter(change_event=event).first()
    if existing is not None:
        return existing, False

    components, total = _priority_components(event)
    alert = StewardshipAlert.objects.create(
        company=event.company, change_event=event, alert_type=event.event_type, severity=event.severity,
        message=alert_message_for_event(event), priority_score=total, priority_components=components,
    )
    return alert, True


def generate_alerts_for_refresh(company_profile, refresh_run, change_events):
    """Called once per refresh — one alert per real change event this run
    produced. Never generates an alert for a run that produced zero
    events (an unchanged refresh stays silent, exactly as Section 24
    requires: 'this source did not change, so EcoIQ generated no false
    alert')."""
    alerts = []
    for event in change_events:
        alert, created = generate_alert_for_event(event)
        if created:
            alerts.append(alert)
    return alerts


def acknowledge_alert(alert, actor):
    alert.state = 'acknowledged'
    alert.acknowledged_by = actor
    alert.acknowledged_at = timezone.now()
    alert.save(update_fields=['state', 'acknowledged_by', 'acknowledged_at'])
    return alert


def resolve_alert(alert, actor, reason=''):
    alert.state = 'resolved'
    if not alert.acknowledged_at:
        alert.acknowledged_by = actor
        alert.acknowledged_at = timezone.now()
    alert.resolved_at = timezone.now()
    alert.resolution_reason = reason
    alert.save(update_fields=['state', 'acknowledged_by', 'acknowledged_at', 'resolved_at', 'resolution_reason'])
    return alert


def dismiss_alert(alert, actor, reason=''):
    alert.state = 'dismissed'
    alert.resolved_at = timezone.now()
    alert.resolution_reason = reason
    alert.save(update_fields=['state', 'resolved_at', 'resolution_reason'])
    return alert
