"""
Portfolio change tracking — pure diff over two PortfolioSnapshot.holding_snapshots
lists (and the two snapshots' own top-level fields). No AI involved: every
"reason" a number changed is calculated here from stored data, and
investor_portfolio/briefing.py may only narrate what this module already
computed — it never invents its own explanation for a numeric change.

Three change types are kept explicitly distinct per company, because they
have very different implications:
  user_holding_change    — the user's share count changed
  market_weight_change   — share count is unchanged, but market value/weight
                            moved (price movement)
  company_analysis_change — the EcoIQ classification or evidence confidence
                            changed for this company (a new/updated report)
"""
from decimal import Decimal


def _by_company(snapshot):
    return {row['company_slug']: row for row in (snapshot.holding_snapshots or [])}


def diff_snapshots(prior, current) -> dict:
    """
    prior may be None (current is the portfolio's first-ever snapshot).
    Returns a dict describing what changed, grouped by cause.
    """
    if prior is None:
        return {
            'has_prior': False,
            'exposure_score_delta': None,
            'known_exposure_pct_delta': None,
            'unknown_exposure_pct_delta': None,
            'added_companies': [row['company_name'] for row in (current.holding_snapshots or [])],
            'removed_companies': [],
            'user_holding_changes': [],
            'market_weight_changes': [],
            'company_analysis_changes': [],
        }

    prior_by_slug = _by_company(prior)
    current_by_slug = _by_company(current)

    added = [current_by_slug[s]['company_name'] for s in current_by_slug if s not in prior_by_slug]
    removed = [prior_by_slug[s]['company_name'] for s in prior_by_slug if s not in current_by_slug]

    user_holding_changes = []
    market_weight_changes = []
    company_analysis_changes = []

    for slug, cur in current_by_slug.items():
        prev = prior_by_slug.get(slug)
        if prev is None:
            continue

        shares_changed = prev.get('shares') != cur.get('shares')
        if shares_changed:
            user_holding_changes.append({
                'company_name': cur['company_name'],
                'from_shares': prev.get('shares'), 'to_shares': cur.get('shares'),
            })
        else:
            prev_val = Decimal(prev['market_value']) if prev.get('market_value') else None
            cur_val = Decimal(cur['market_value']) if cur.get('market_value') else None
            if prev_val is not None and cur_val is not None and prev_val != cur_val:
                market_weight_changes.append({
                    'company_name': cur['company_name'],
                    'from_value': str(prev_val), 'to_value': str(cur_val),
                    'from_weight_pct': prev.get('weight_pct'), 'to_weight_pct': cur.get('weight_pct'),
                })

        if prev.get('classification') != cur.get('classification'):
            company_analysis_changes.append({
                'company_name': cur['company_name'],
                'change_type': 'classification',
                'from_classification': prev.get('classification'),
                'to_classification': cur.get('classification'),
            })
        prev_conf = prev.get('evidence_confidence')
        cur_conf = cur.get('evidence_confidence')
        if prev_conf is not None and cur_conf is not None and round(prev_conf, 2) != round(cur_conf, 2):
            company_analysis_changes.append({
                'company_name': cur['company_name'],
                'change_type': 'evidence_confidence',
                'from_confidence': prev_conf, 'to_confidence': cur_conf,
            })

    return {
        'has_prior': True,
        'prior_calculated_at': prior.calculated_at.isoformat(),
        'exposure_score_delta': (
            round(current.exposure_score - prior.exposure_score, 1)
            if current.exposure_score is not None and prior.exposure_score is not None else None
        ),
        'known_exposure_pct_delta': (
            round(current.known_exposure_pct - prior.known_exposure_pct, 2)
            if current.known_exposure_pct is not None and prior.known_exposure_pct is not None else None
        ),
        'unknown_exposure_pct_delta': (
            round(current.unknown_exposure_pct - prior.unknown_exposure_pct, 2)
            if current.unknown_exposure_pct is not None and prior.unknown_exposure_pct is not None else None
        ),
        'added_companies': added,
        'removed_companies': removed,
        'user_holding_changes': user_holding_changes,
        'market_weight_changes': market_weight_changes,
        'company_analysis_changes': company_analysis_changes,
    }
