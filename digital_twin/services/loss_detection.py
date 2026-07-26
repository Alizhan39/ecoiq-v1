"""
digital_twin/services/loss_detection.py — deterministic loss detection and
the two-stage promotion into the EXISTING OperationalLoss workflow.

Stage 1 (`detect_loss_candidates`): pure rule-based scan over a twin's
already-stored ProcessNode/ResourceFlow data. Every rule compares a real
stored number against an explicit threshold constant — no LLM, no
inference from absence. Candidates are persisted as `LossDetection` rows
with status='candidate' and are NEVER auto-approved.

Stage 2 (`promote_loss_detection`): only once a human has moved a
LossDetection to status='approved' does this create the REAL
`waste_to_value_capital_allocation_engine.OperationalLoss` row, via the
existing `services.loss_intake.create_operational_loss()` — this app never
re-implements that model or its creation path.
"""
from django.utils import timezone

from waste_to_value_capital_allocation_engine.services.loss_intake import create_operational_loss

LOSS_DETECTION_FORMULA_VERSION = '1.0.0'

# Thresholds are explicit and documented — not tuned to any real asset.
# A twin operator can always create/edit a LossDetection by hand if a
# threshold doesn't fit their asset; these rules only ever produce
# candidates, never a final loss.
DOWNTIME_HOURS_THRESHOLD = 100.0
LOW_YIELD_PCT_THRESHOLD = 85.0
LOW_UTILISATION_PCT_THRESHOLD = 50.0
DEFAULT_UNIT_VALUE_USD = 1.0


class PromotionNotAllowedError(Exception):
    """Raised when promote_loss_detection is called on a LossDetection that
    has not been explicitly human-approved."""


def _confidence_for(*values):
    """A candidate's confidence is the minimum of the confidence values of
    the real records it was derived from — never higher than its weakest
    input. Falls back to a conservative 40 when no input carries a
    confidence value at all (never fabricated as high)."""
    present = [v for v in values if v is not None]
    return round(min(present), 2) if present else 40.0


def _make_candidate(twin, component, process_node, loss_type, title, description, calculation_notes,
                     estimated_annual_impact, confidence, evidence_references=None):
    from digital_twin.models import LossDetection

    # Lookup key deliberately excludes `status`: once a candidate has been
    # human-reviewed (approved/rejected/promoted), re-running detection must
    # find and leave that same row alone, never spawn a fresh 'candidate'
    # duplicate of something a human has already acted on.
    candidate, created = LossDetection.objects.get_or_create(
        twin=twin, component=component, process_node=process_node, loss_type=loss_type, title=title,
        defaults={
            'description': description,
            'calculation_notes': calculation_notes,
            'estimated_annual_impact': estimated_annual_impact,
            'confidence': confidence,
            'evidence_references': evidence_references or [],
            'status': 'candidate',
        },
    )
    if not created:
        candidate.description = description
        candidate.calculation_notes = calculation_notes
        candidate.estimated_annual_impact = estimated_annual_impact
        candidate.confidence = confidence
        candidate.save(update_fields=['description', 'calculation_notes', 'estimated_annual_impact', 'confidence', 'updated_at'])
    return candidate, created


def detect_loss_candidates(twin):
    """Scans a twin's ProcessNode and ResourceFlow rows for the deterministic
    rules below and returns the list of (candidate, created) LossDetection
    results. Every rule's numeric trigger is quoted in `calculation_notes`."""
    results = []

    for node in twin.process_nodes.select_related('component').all():
        if node.downtime_hours is not None and node.downtime_hours > DOWNTIME_HOURS_THRESHOLD:
            results.append(_make_candidate(
                twin, node.component, node, 'production_downtime',
                f'Excessive downtime at {node.name}',
                f'{node.name} recorded {node.downtime_hours} hours of downtime, above the {DOWNTIME_HOURS_THRESHOLD}-hour threshold.',
                f'Rule: downtime_hours ({node.downtime_hours}) > threshold ({DOWNTIME_HOURS_THRESHOLD}). '
                f'Estimated impact = downtime_hours * cost_per_unit ({node.cost_per_unit or "unknown"}).',
                round(node.downtime_hours * node.cost_per_unit, 2) if node.cost_per_unit else None,
                _confidence_for(node.confidence),
            ))
        if node.yield_pct is not None and node.yield_pct < LOW_YIELD_PCT_THRESHOLD:
            results.append(_make_candidate(
                twin, node.component, node, 'defect_rejection_losses',
                f'Low yield at {node.name}',
                f'{node.name} recorded a yield of {node.yield_pct}%, below the {LOW_YIELD_PCT_THRESHOLD}% threshold.',
                f'Rule: yield_pct ({node.yield_pct}) < threshold ({LOW_YIELD_PCT_THRESHOLD}).',
                None,
                _confidence_for(node.confidence),
            ))
        if (
            node.utilisation_pct is not None and node.utilisation_pct < LOW_UTILISATION_PCT_THRESHOLD
            and node.energy_use is not None and node.energy_use > 0
        ):
            results.append(_make_candidate(
                twin, node.component, node, 'idle_machinery',
                f'Low utilisation at {node.name} while still consuming energy',
                f'{node.name} is at {node.utilisation_pct}% utilisation (below {LOW_UTILISATION_PCT_THRESHOLD}%) '
                f'while consuming {node.energy_use} {node.energy_unit.symbol if node.energy_unit else ""} of energy.',
                f'Rule: utilisation_pct ({node.utilisation_pct}) < threshold ({LOW_UTILISATION_PCT_THRESHOLD}) '
                f'AND energy_use ({node.energy_use}) > 0.',
                None,
                _confidence_for(node.confidence),
            ))

    flow_loss_type_map = {
        'water': 'water_leakage',
        'heat': 'heat_loss',
        'energy': 'energy_loss',
        'material': 'material_waste',
        'emissions': 'avoidable_emissions',
        'waste': 'industrial_by_products',
    }
    for flow in twin.resource_flows.select_related('unit', 'source_component', 'source_node').all():
        if not flow.loss_quantity or flow.loss_quantity <= 0:
            continue
        loss_type = flow_loss_type_map.get(flow.resource_type, 'material_waste')
        unit_cost = flow.cost / flow.quantity if flow.cost and flow.quantity else None
        estimated_impact = round(flow.loss_quantity * unit_cost, 2) if unit_cost else None
        results.append(_make_candidate(
            twin, flow.source_component, flow.source_node, loss_type,
            f'{flow.get_resource_type_display()} loss in {flow.unit.name if flow.unit else "flow"}',
            f'A {flow.get_resource_type_display().lower()} flow recorded a loss quantity of {flow.loss_quantity} '
            f'{flow.unit.symbol if flow.unit else ""} out of {flow.quantity}.',
            f'Rule: resource_flow.loss_quantity ({flow.loss_quantity}) > 0 for resource_type={flow.resource_type}. '
            f'Estimated impact = loss_quantity * (cost / quantity) when cost is known.',
            estimated_impact,
            _confidence_for(flow.confidence),
        ))

    return results


def promote_loss_detection(loss_detection, organisation='', location='', country='', sector=''):
    """Promotes a human-approved LossDetection into a REAL
    waste_to_value_capital_allocation_engine.OperationalLoss row. Refuses
    (raises) unless status == 'approved' — this is the only path by which a
    twin-detected candidate becomes a real, capital-allocation-visible loss.
    Idempotent: if already promoted, returns the existing OperationalLoss
    rather than creating a second one. Self-healing: `status` is an
    invariant of `promoted_loss` being set, never the other way round — if a
    caller re-sets status='approved' on an already-promoted row (e.g. by
    re-running an approval script), that status is corrected back to
    'promoted' rather than left in a self-contradictory state."""
    if loss_detection.promoted_loss_id:
        if loss_detection.status != 'promoted':
            loss_detection.status = 'promoted'
            loss_detection.save(update_fields=['status', 'updated_at'])
        return loss_detection.promoted_loss

    if loss_detection.status != 'approved':
        raise PromotionNotAllowedError(
            f"LossDetection {loss_detection.pk} has status='{loss_detection.status}', not 'approved' — "
            'a candidate must be explicitly human-approved before it can become a real OperationalLoss.'
        )

    asset = loss_detection.twin.asset
    real_loss = create_operational_loss(
        organisation=organisation or (asset.company.name if asset.company_id else ''),
        asset=asset.name,
        project=asset.source_project_reference,
        location=location or asset.region,
        country=country or asset.country,
        sector=sector or asset.industry,
        loss_type=loss_detection.loss_type,
        title=loss_detection.title,
        description=loss_detection.description,
        financial_loss_amount=loss_detection.estimated_annual_impact or 0.0,
        projected_future_loss=loss_detection.estimated_annual_impact,
        currency=loss_detection.currency,
        evidence_quality='medium' if loss_detection.evidence_references else 'missing',
        confidence=loss_detection.confidence,
        status='quantified',
    )
    loss_detection.promoted_loss = real_loss
    loss_detection.status = 'promoted'
    loss_detection.save(update_fields=['promoted_loss', 'status', 'updated_at'])
    return real_loss
