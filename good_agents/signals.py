"""
good_agents/signals.py — PR5 Phase 21-23, the second (verified) half of the
Impact Receipt / Evidence Memory loop closed by
good_agents.services.pipeline.record_verified_outcome_and_sync's docstring.

record_monitoring_outcome() refuses mrv_status='verified' by design (see
capital_guardian/services/execution_monitoring.py) — the ONLY real path to
independent verification in this repo is a staff member editing the
existing VerifiedCapitalOutcome admin change form directly. This receiver
reacts to that real event (a post_save on VerifiedCapitalOutcome, wherever
it's saved from) rather than adding a second, parallel "verify" button
anywhere in good_agents. It never fires on the ordinary monitoring path,
since that path is structurally prevented from ever setting mrv_status to
'verified' in the first place.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='waste_to_value_capital_allocation_engine.VerifiedCapitalOutcome')
def sync_good_opportunity_on_verification(sender, instance, **kwargs):
    if instance.mrv_status != 'verified':
        return

    from good_agents.models import ImpactReceipt
    from good_agents.services import notify
    from good_agents.services.timeline import record_event

    receipt = ImpactReceipt.objects.filter(decision_id=instance.decision_id).select_related('opportunity').first()
    if receipt is None:
        return
    opportunity = receipt.opportunity
    if opportunity.status == 'verified':
        return  # already synced — don't re-fire the notification/timeline event

    if receipt.verified_outcome_id != instance.pk:
        receipt.verified_outcome = instance
    receipt.measured_result = {**receipt.measured_result, 'stage': 'verified'}
    receipt.save(update_fields=['verified_outcome', 'measured_result'])

    opportunity.status = 'verified'
    opportunity.save(update_fields=['status'])

    record_event(
        opportunity, 'outcome_verified',
        source_object_reference=f'waste_to_value_capital_allocation_engine.VerifiedCapitalOutcome:{instance.pk}',
        notes='Independently verified — set via the existing VerifiedCapitalOutcome admin change form.',
    )
    record_event(
        opportunity, 'evidence_memory_updated',
        source_object_reference=f'good_agents.ImpactReceipt:{receipt.pk}',
    )
    notify.notify_verified_impact(opportunity)
