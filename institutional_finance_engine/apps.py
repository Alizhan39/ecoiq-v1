"""
DEPRECATED (Phase 1A, Canonical Architecture Decision Analysis).

This app is a 100% static mock: no models.py, no migrations, no database
writes, one view rendering hardcoded Python dicts. It has zero real
functionality and zero external Python imports anywhere in this repo.

financial_intelligence_cloud is the real institutional intelligence
interface going forward — it has real models, real seeded scale, and a real
(if demo-content) ranking layer. Do not build new functionality here.

Left in place, not deleted: its two page-level nav references (a CTA button
in governance_expert_review_board and a module card on /platform/) are each
covered by an existing passing test in their own app's test suite
(governance_expert_review_board.tests / institutional_finance_engine.tests).
Removing them requires editing those tests too, which is out of scope for a
"mark deprecated, don't delete" pass — see the Phase 1A report, Section 7.
"""
from django.apps import AppConfig


class InstitutionalFinanceEngineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'institutional_finance_engine'
    verbose_name = 'EcoIQ Institutional Finance Engine (DEPRECATED — see apps.py docstring)'
