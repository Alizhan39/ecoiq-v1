# Reform Intelligence — 12 capability contracts (v0.1)

**Status:** internal planning catalogue only; not twelve working AI engines. No
models, migrations, endpoints, automatic judgements, or production changes.

## Relation to governance research

The original 12 *governance domains* describe **what public values and sectors
are being examined**. These 12 *reform capabilities* describe **how EcoIQ
might examine problems and prepare evidence-backed proposals**. They are
different axes, not a second set of 12 KPI formulas.

`governance_domain_codes` are advisory references to proposed domain IDs from
PR #383; this module does not import the unmerged domain registry or assert
that all these mappings have been reviewed.

| # | Proposed capability | Existing components that may be reused | Not yet implemented |
|---|---|---|---|
| 01 | Root Cause Intelligence | `poverty_justice/contracts.py`, `ecoiq_os/evidence.py` | Universal causal-inference pipeline |
| 02 | Regulatory Conflict Graph | `ai_agents/regulatory_agent/README.md` (agent specification) | Dated law database and contradiction detector |
| 03 | Economic Digital Twin | `digital_twin/services/scenario_simulation.py` | Macroeconomic calibrated twin |
| 04 | Anti-Corruption Intelligence | `evidence_memory/services/retrieval_policy.py` (access policy) | Procurement anomaly investigation system |
| 05 | Wealth Distribution Analysis | `poverty_justice/contracts.py` | Complete distributional dataset and model |
| 06 | Public Budget Intelligence | `companies/provenance.py` (metric lineage) | Government budget-outcome linking |
| 07 | Legal Access Intelligence | No established working subsystem | Legal access datasets and analysis |
| 08 | Islamic Finance Research | `ml/finance/islamic_finance_fit.py`, `islamic_knowledge/contracts.py` | Contract-specific legal/scholar determination |
| 09 | Future Generations Impact | `digital_twin/services/scenario_simulation.py` | Intergenerational welfare methodology |
| 10 | AI Accountability Engine | `islamic_knowledge/contracts.py`, `evidence_memory/services/retrieval_policy.py` | End-to-end AI model safety auditing |
| 11 | Reform Experiment Lab | `poverty_justice/contracts.py`, `poverty_justice/falsification.py` | Pilot evaluation platform |
| 12 | Institutional Memory | `companies/provenance.py`, `evidence_memory/models.py` | Reviewed, access-controlled decision memory |

Existing components are reuse **candidates**, not evidence the named capability
works end to end.

## Data-first planning interface

`intelligence_analytics_engine.reform_capabilities.build_research_plan(slug,
input_presence)` lists which declared input **types** are present according
to a caller, and which are missing. It cannot authenticate data. All results
explicitly return:

- `status = RESEARCH_PLAN_ONLY`
- `evidence_authentication = NOT_PERFORMED`
- `expert_review = NOT_PERFORMED`
- `decision_ready = False`

This has no HTTP route or database writes. The registry does not assign a
numerical moral/legality score, generate allegations, certify financial
instruments or claim causal effects.

## Governance requirements before promoting a capability

1. Identify an authorised data owner, jurisdiction, lawful processing purpose,
   version, retention controls and evidence provenance.
2. Validate each proposed output and its units, relevant law, protected rights,
   domain-specific uncertainty and alternative explanations.
3. Require independent subject-matter review before any assertion affecting
   persons, legal compliance, investment decisions or religion.
4. Keep objections, corrections and adverse review outcomes. Absence of data
   must remain visible rather than zero or success.
5. Only then implement one narrow vertical slice with permissions, tests,
   explicit rollout review and a reproducible outcome record.

## Priority engineering sequence

- First integrate PR #381 and harden its source/evidence linkage; do not use
  this catalogue to bypass the current frontend build-artefact CI blocker.
- Start with **01 Root Cause Intelligence** as a hypothesis register using
  existing poverty-justice causal/falsification contracts, and **12 Institutional
  Memory** as audit-linked decision history. Both depend on confirmed evidence.
- Implement a single pilot, e.g. a procurement decision audit, before
  expanding regulatory or corruption detection. Review risks of false
  accusations and due process separately.
- Use the existing industrial `digital_twin` only within its verified scope;
  a calibrated national economic twin would be a separate research programme.

## Local test

`python -m unittest intelligence_analytics_engine.test_reform_capabilities`

The test checks catalogue completeness, unknown inputs, research-only status
and safety guardrails. CI, runtime performance and model accuracy require
separate validation.
