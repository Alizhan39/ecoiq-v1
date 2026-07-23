"""
good_agents/services/red_team.py — RedTeamReview (Phase 9): every
significant recommendation must be challengeable. A "good" intention alone
is not sufficient. This module builds the structured challenge from data
already on the opportunity/agent-activation records (concerns/conflicts
raised by lenses, missing evidence, zero-capital claims) — deterministic,
no LLM call, so it can run for every qualified opportunity at zero
marginal cost.
"""
from good_agents.models import RedTeamReview


def build_review(opportunity, activation_records):
    concerns = [r for r in activation_records if r.position in ('concerns', 'conflicts')]

    who_may_be_harmed = (
        '; '.join(f'{r.agent.name}: {r.concern}' for r in concerns if r.concern)
        or 'No lens raised a specific harm concern — does not mean none exists; see confidence/evidence fields.'
    )
    dependency_risk = (
        'Zero-capital action plan proposed — check it does not simply create a new dependency on EcoIQ '
        'facilitation without a durable resource transfer.' if opportunity.zero_capital_possible else ''
    )
    misleading_impact_risk = (
        'Opportunity carries no measured/verified impact yet — all potential_benefit figures are '
        'estimates/targets. Do not present as impact already created.'
        if opportunity.status in ('potential', 'qualified', 'approved') else ''
    )
    contradicting_evidence = (
        'insufficient_evidence flag is set — evidence base for this opportunity is incomplete.'
        if opportunity.insufficient_evidence else ''
    )

    review, _ = RedTeamReview.objects.update_or_create(
        opportunity=opportunity,
        defaults=dict(
            who_benefits=opportunity.affected_population or 'Not yet specified.',
            who_bears_cost=(
                f'Capital required: ${opportunity.capital_required_usd:,.0f}'
                if opportunity.capital_required_usd else 'No capital required (zero-capital path).'
            ),
            who_may_be_harmed=who_may_be_harmed,
            hidden_externalities='; '.join(r.concern for r in concerns if r.concern) or '',
            dependency_risk=dependency_risk,
            misleading_impact_risk=misleading_impact_risk,
            greenwashing_risk='',
            conflict_of_interest='',
            contradicting_evidence=contradicting_evidence,
            cleared=not concerns and not opportunity.insufficient_evidence,
        ),
    )
    return review
