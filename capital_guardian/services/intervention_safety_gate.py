"""
capital_guardian/services/intervention_safety_gate.py — vertical-slice
PR 4: deterministic eligible/conditional/blocked classification for a
proposed InterventionOption, before it's allowed into ranking.

No live AI, no inference over free-text evidence. Two, and only two,
sources of truth:

1. capital_guardian.services.resource_purpose_review's reviewed pathway
   table (reused via reviewed_pathways_for_project(), never re-authored
   here) — matched against the option's OWN `intervention_type` choice
   field, a controlled/structured value, not free text. This is where
   "raw coal as fertiliser" stays blocked and "coal ash in construction" /
   "agricultural reuse of by-products" / "reuse of other industrial
   by-products" stay conditional on the exact same real-world safety
   conditions the resource-purpose review already states.
2. An explicit, reviewed, narrow safety denylist over the option's own
   declared title/description — checking for a small, fixed set of
   specific unsafe-reuse phrases (fertiliser, ash, by-product/byproduct).
   This is a safety filter (a denylist, like a profanity filter), not an
   engineering-conclusion inference engine: it never derives a positive
   recommendation from free text, it only ever downgrades toward
   conditional/blocked when a known-sensitive term appears.

INTERVENTION_TYPE_CHOICES not already reviewed as safe for this pilot
('resale', 'disposal', 'processing_recovery', 'transfer_redistribution',
'operational_optimisation') default to 'conditional' — never silently
'eligible' for something nobody has actually reviewed.
"""
from capital_guardian.services.resource_purpose_review import reviewed_pathways_for_project

# intervention_type values already reviewed as safe, general-purpose heating-
# transition pathways for this pilot (insulation/demand reduction=prevention,
# heat pump/electric heating/hybrid=equipment_upgrade, district heating/grid
# upgrade=infrastructure_upgrade, the baseline=do_nothing).
_REVIEWED_SAFE_TYPES = {'prevention', 'equipment_upgrade', 'infrastructure_upgrade', 'do_nothing'}

# Narrow, explicit safety denylist — never a general inference engine.
_BLOCKED_PHRASES = ('fertiliser', 'fertilizer')
_CONDITIONAL_PHRASES = ('ash', 'by-product', 'byproduct', 'industrial reuse', 'agricultural reuse')


def _pathway_status_for_text(project, text):
    """Case-insensitive match against the project's own reviewed pathway names."""
    text = text.lower()
    for pathway in reviewed_pathways_for_project(project):
        name_words = pathway['name'].lower()
        if name_words in text or any(word in text for word in name_words.split() if len(word) > 4):
            return pathway['status'], pathway['notes']
    return None, None


def classify_intervention_safety(project, option, classification='estimated'):
    """
    option: an unsaved or saved InterventionOption-shaped object (needs
    .title, .description, .intervention_type).
    classification: 'real' | 'estimated' | 'illustrative' — same vocabulary
    as the value-loss confirmation form (PR 3). Illustrative-only options
    are never reported as fully 'eligible', matching PR 3's convention of
    never upgrading illustrative content past what it honestly is.

    Returns {'status': 'eligible'|'conditional'|'blocked', 'reason': str}.
    """
    text = f'{option.title} {option.description}'.lower()

    if any(phrase in text for phrase in _BLOCKED_PHRASES):
        return {
            'status': 'blocked',
            'reason': 'Raw coal or ash is not a validated fertiliser — this option is blocked regardless of other inputs.',
        }

    if any(phrase in text for phrase in _CONDITIONAL_PHRASES):
        pathway_status, pathway_notes = _pathway_status_for_text(project, text)
        reason = pathway_notes or (
            'Resource-redirection/reuse options require chemical, technical, and regulatory review before '
            'being treated as eligible — never assumed safe by default.'
        )
        return {'status': 'conditional', 'reason': reason}

    if option.intervention_type not in _REVIEWED_SAFE_TYPES:
        return {
            'status': 'conditional',
            'reason': (
                f'"{option.get_intervention_type_display()}" has not been reviewed as a safe pathway for this '
                f'pilot yet — a domain expert should confirm it before treating it as fully eligible.'
            ),
        }

    if classification == 'illustrative':
        return {
            'status': 'conditional',
            'reason': 'Based only on illustrative/demo claims — needs real evidence before being treated as a fully eligible option.',
        }

    return {'status': 'eligible', 'reason': ''}
