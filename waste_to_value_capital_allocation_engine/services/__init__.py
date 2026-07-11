"""
waste_to_value_capital_allocation_engine/services/ — Phase 1A boundary note
(documentation only; no module was moved, no import path changed).

This package holds two logical responsibilities in one Django app — see
../models.py's module docstring for the full rationale for keeping them
together. Quick map of which file belongs to which:

  LOSS DETECTION
    loss_intake.py      — detect operational loss, quantify exposure
    capital_risk.py     — capital-at-risk + recoverable-value estimates

  ALLOCATION DECISION
    intervention_finance.py       — compare interventions, CAPEX/OPEX, payback
    capital_allocation_scoring.py — derive the 13 sub-scores from real fields
    ranking.py                    — deterministic weighted-composite ranking
    funding.py                    — match candidate capital routes
    governance.py                 — persist the governed investment case
    human_approval_gate.py        — enforce human approval before anything
                                     downstream of a decision fires

  Cross-cutting (not part of either boundary)
    mrv_outcomes.py               — post-implementation MRV verification +
                                     capital-reallocation feedback signal
    agent_bridge.py               — Waste & Leakage Agent orchestration glue
    capital_allocation_bridge.py  — Capital Allocation Agent orchestration glue
    demo_pipeline.py              — the Meat Cold-Chain Loss Prevention demo
    capital_guardian_handoff.py   — Phase 1A: promotes an approved
                                     CapitalAllocationDecision into
                                     capital_guardian.ProjectGovernance
                                     monitoring (human-approved only, never
                                     automatic)
"""
