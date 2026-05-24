"""
EcoIQ Good Deeds League — scoring utilities.

Weights
-------
  Pollution Footprint   35 %   (lower absolute pollution = higher score)
  Reduction Progress    25 %   (year-on-year trend)
  Investment            20 %   (capex relative to revenue)
  Transparency          10 %   (quality of public reporting)
  Community Impact      10 %   (households helped, health outcomes)
"""
from decimal import Decimal
from typing import NamedTuple


WEIGHTS = {
    'pollution_footprint': Decimal('0.35'),
    'reduction_progress':  Decimal('0.25'),
    'investment':          Decimal('0.20'),
    'transparency':        Decimal('0.10'),
    'community_impact':    Decimal('0.10'),
}


class StatusTier(NamedTuple):
    label:  str
    css:    str
    colour: str  # hex for template inline styles


_TIERS = [
    (85, StatusTier('Restorative Leader',      'restorative', '#2d6a4f')),
    (70, StatusTier('Transition Leader',       'transition',  '#40916c')),
    (55, StatusTier('Improving but Polluting', 'improving',   '#52b788')),
    (40, StatusTier('High Impact / Weak Repair', 'high-impact', '#f4a261')),
    (0,  StatusTier('Major Polluter',          'polluter',    '#e63946')),
]


def compute_ecoiq_score(
    pollution_footprint: int,
    reduction_progress:  int,
    investment:          int,
    transparency:        int,
    community_impact:    int,
) -> Decimal:
    """Return the weighted EcoIQ score as a Decimal with 1 decimal place."""
    raw = (
        Decimal(pollution_footprint) * WEIGHTS['pollution_footprint'] +
        Decimal(reduction_progress)  * WEIGHTS['reduction_progress']  +
        Decimal(investment)          * WEIGHTS['investment']           +
        Decimal(transparency)        * WEIGHTS['transparency']         +
        Decimal(community_impact)    * WEIGHTS['community_impact']
    )
    return raw.quantize(Decimal('0.1'))


def get_tier(score: float | Decimal) -> StatusTier:
    s = float(score)
    for threshold, tier in _TIERS:
        if s >= threshold:
            return tier
    return _TIERS[-1][1]


def rerank_all():
    """
    Recompute every company's ecoiq_score, then assign integer ranks 1-N.
    Call after bulk score updates.
    """
    from .models import Company  # local import avoids circular at module load

    companies = list(Company.objects.all())
    for co in companies:
        co.ecoiq_score = co.compute_score()

    # Sort descending by score, then alphabetically
    companies.sort(key=lambda c: (-float(c.ecoiq_score), c.name))
    for i, co in enumerate(companies, start=1):
        co.rank = i

    Company.objects.bulk_update(companies, ['ecoiq_score', 'rank'])
    return companies
