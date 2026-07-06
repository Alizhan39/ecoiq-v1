"""
financial_intelligence_cloud/services/entity_generation.py — deterministic
generator for the bulk, non-flagship portfolio entities in each demo
portfolio (the ~49 other Northstar clients, ~8 other Atlas companies, ~499
other Civic borrowers).

Never uses `random.random()` — every value is a pure function of
`(portfolio.slug, index)`, so re-running a seed command produces identical
rows (idempotency) rather than a fresh random draw each time. Every
generated PortfolioSignal.source_run stays None — this is the field that
honestly distinguishes generated demo rows from the one real-agent-pipeline
flagship entity per portfolio (see services/demo_flagship_pipeline.py).

Severity/sector weights are deliberately capped so a generated entity can
never exceed ~85% of the ceiling passed in by the caller — this keeps the
flagship entity's ranking as a designed, tested outcome (see
FinancialIntelligenceCloudRankingTests) rather than an accident of arbitrary
numbers.
"""
from financial_intelligence_cloud.services.accounts import add_portfolio_entity
from financial_intelligence_cloud.services.signals import evidence_quality_score, generate_portfolio_signal

ADJECTIVES = [
    'Meridian', 'Cobalt', 'Northgate', 'Silverline', 'Crestview', 'Amber', 'Ironwood', 'Bluepeak',
    'Redstone', 'Harbor', 'Willowbrook', 'Granite', 'Cedarfield', 'Brightwater', 'Eastfield', 'Westgate',
    'Highland', 'Riverside', 'Oakhaven', 'Stonebridge',
]
NOUNS = [
    'Foods', 'Logistics', 'Manufacturing', 'Engineering', 'Retail Group', 'Textiles', 'Agritech',
    'Construction', 'Energy', 'Healthcare', 'Hospitality', 'Automotive Supply', 'Chemicals', 'Packaging',
    'Electronics', 'Timber', 'Dairy', 'Seafood', 'Beverages', 'Materials',
]
SUFFIXES = ['Ltd', 'Group', 'Holdings', 'Partners', 'Co']

_MAX_POOL_SIZE = len(ADJECTIVES) * len(NOUNS) * len(SUFFIXES)  # 2000 — comfortably above any demo portfolio's size

SECTOR_POOL = [
    'Food & Beverage', 'Light Manufacturing', 'Logistics', 'Professional Services', 'Retail',
    'Construction', 'Energy', 'Agritech', 'Healthcare', 'Hospitality', 'Textiles', 'Automotive Supply',
]
# Deliberately <= 0.95 so, combined with SEVERITY_MULTIPLIER (also <= 0.90),
# a generated entity's capital_at_risk can never reach the ceiling passed in.
SECTOR_WEIGHT = dict(zip(SECTOR_POOL, [0.95, 0.85, 0.75, 0.60, 0.90, 0.80, 0.70, 0.65, 0.55, 0.50, 0.45, 0.40]))

SEVERITY_MULTIPLIER = {0: 0.90, 1: 0.70, 2: 0.50, 3: 0.35, 4: 0.20}
RECOVERY_RATE_CYCLE = [0.55, 0.65, 0.45]
EVIDENCE_QUALITY_CYCLE = ['strong', 'medium', 'weak']


def generated_entity_name(index):
    n_adj, n_noun = len(ADJECTIVES), len(NOUNS)
    adj = ADJECTIVES[index % n_adj]
    noun = NOUNS[(index // n_adj) % n_noun]
    suffix = SUFFIXES[(index // (n_adj * n_noun)) % len(SUFFIXES)]
    return f'{adj} {noun} {suffix}'


def generated_entity_sector(index):
    return SECTOR_POOL[index % len(SECTOR_POOL)]


def generate_portfolio_entities(portfolio, count, capital_at_risk_ceiling, entity_type, signal_type,
                                 currency='GBP', start_index=0):
    """
    Deterministically creates/updates `count` non-flagship PortfolioEntity +
    PortfolioSignal rows for `portfolio`, indexed `start_index..start_index+count-1`.
    Idempotent: re-running with the same arguments produces identical rows.
    Stale-row cleanup is scoped to names within this generator's own
    combinatorial name space, so it never touches flagship or hand-authored
    entities (e.g. Atlas's 4 real-ranked companies), regardless of naming.
    """
    created = []
    current_names = []
    for i in range(start_index, start_index + count):
        name = generated_entity_name(i)
        sector = generated_entity_sector(i)
        current_names.append(name)

        severity = SEVERITY_MULTIPLIER[i % 5]
        capital_at_risk = round(capital_at_risk_ceiling * SECTOR_WEIGHT[sector] * severity, 2)
        recoverable_value = round(capital_at_risk * RECOVERY_RATE_CYCLE[i % 3], 2)
        urgency_score = round(30 + 60 * severity, 1)
        evidence_quality = EVIDENCE_QUALITY_CYCLE[i % 3]

        entity = add_portfolio_entity(
            portfolio, name, entity_type, sector=sector,
            relationship_stage='at_risk' if i % 7 == 0 else 'active',
        )
        generate_portfolio_signal(
            entity, signal_type, f'{name}: {signal_type.replace("_", " ").title()} detected',
            capital_at_risk=capital_at_risk, potential_recoverable_value=recoverable_value,
            currency=currency, urgency_score=urgency_score, evidence_quality=evidence_quality,
            confidence=evidence_quality_score(evidence_quality), source_run=None,
        )
        created.append(entity)

    all_possible_names = {generated_entity_name(i) for i in range(_MAX_POOL_SIZE)}
    portfolio.entities.filter(name__in=all_possible_names).exclude(name__in=current_names).delete()
    portfolio.entity_count = portfolio.entities.count()
    portfolio.save(update_fields=['entity_count'])
    return created
