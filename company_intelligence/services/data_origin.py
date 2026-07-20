"""
company_intelligence/services/data_origin.py — feat/company-evidence-
ingestion (PR 10): "a production user must never confuse fixture data with
real analysis."

Deliberately NOT a stored field on CompanyProfile: origin is derived live
from the real is_demo flags already on every company_intelligence row for
that company (PR9's own convention), so it can never drift from what the
data actually is. A company doesn't have one static "real" or "demo"
label baked in — it honestly reflects whatever mix of rows currently
exists for it.
"""
DEMO = 'demo'
REAL_PUBLIC_DATA = 'real_public_data'
MIXED = 'mixed'
UNVERIFIED_IMPORT = 'unverified_import'

DATA_ORIGIN_LABELS = {
    DEMO: 'Demo / Illustrative',
    REAL_PUBLIC_DATA: 'Real Public Data',
    MIXED: 'Mixed (Real + Demo)',
    UNVERIFIED_IMPORT: 'Unverified Import',
}


def company_data_origin(company_profile):
    """
    Inspects every is_demo-flagged row this company actually has (financial
    facts, Shariah screens, KPI assessments, controversies) and returns
    {'origin', 'label', 'demo_count', 'real_count'}.

    - No rows at all                  -> UNVERIFIED_IMPORT (nothing to
      classify yet — never silently defaults to "real").
    - Every row is_demo=True          -> DEMO
    - Every row is_demo=False         -> REAL_PUBLIC_DATA
    - A genuine mix                   -> MIXED (flagged loudly, never
      quietly blended into either label)
    """
    demo_count = 0
    real_count = 0
    for qs in (
        company_profile.financial_facts.all(), company_profile.shariah_screens.all(),
        company_profile.kpi_assessments.all(), company_profile.controversies.all(),
    ):
        for row in qs:
            if row.is_demo:
                demo_count += 1
            else:
                real_count += 1

    if demo_count == 0 and real_count == 0:
        origin = UNVERIFIED_IMPORT
    elif demo_count and real_count:
        origin = MIXED
    elif demo_count:
        origin = DEMO
    else:
        origin = REAL_PUBLIC_DATA

    return {
        'origin': origin, 'label': DATA_ORIGIN_LABELS[origin],
        'demo_count': demo_count, 'real_count': real_count,
    }
