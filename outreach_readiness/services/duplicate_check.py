"""
outreach_readiness/services/duplicate_check.py — Phase 20: prior outreach
/ contact history. Reads existing real records only — this PR has no
do-not-contact registry yet (nothing has ever been sent from this app),
so this reports what genuinely exists today rather than fabricating a
history mechanism ahead of having any real data to check.
"""


def prior_outreach_history(assessment):
    """
    Checks for prior real contact to the SAME organisation via routes
    this repo already knows about: PR5's OutreachDraft (once actually
    'sent') and any earlier outreach_readiness FounderSendDecision on a
    different opportunity for the same organisation. Returns a list of
    human-readable strings — empty means genuinely no prior record found,
    not "not checked."
    """
    organisation = assessment.organisation
    if organisation is None:
        return []

    history = []

    from good_agents.models import OutreachDraft
    sent_drafts = OutreachDraft.objects.filter(
        contact__responsible_party__organisation=organisation, status__in=('sent', 'replied', 'no_response'),
    ).exclude(action_pathway__opportunity=assessment.opportunity).select_related('action_pathway__opportunity')
    for draft in sent_drafts:
        history.append(
            f'OutreachDraft #{draft.pk} ({draft.get_status_display()}) sent regarding '
            f'"{draft.action_pathway.opportunity.title}" on {draft.sent_at or "unknown date"}.'
        )

    from outreach_readiness.models import FounderSendDecision
    prior_decisions = FounderSendDecision.objects.filter(
        assessment__organisation=organisation, decision='send',
    ).exclude(assessment=assessment).select_related('assessment__opportunity')
    for decision in prior_decisions:
        history.append(
            f'Founder previously decided SEND for "{decision.assessment.opportunity.title}" on '
            f'{decision.decided_at:%Y-%m-%d} (decided by {decision.decided_by}).'
        )

    return history
