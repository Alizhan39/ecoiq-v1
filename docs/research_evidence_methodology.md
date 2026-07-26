# Research Evidence Methodology

This document explains how the Global Research, Technology & Manufacturer
Discovery Engine (`global_research` app) classifies sources, extracts
claims, scores evidence, handles contradictions, compares candidates, and
draws the line between what AI may decide and what a human must decide.
All formulas below are implemented in `global_research/services/` and
versioned (`formula_version` on every scored model) — nothing here is
tuned in a way that isn't visible in code and tests.

## 1. How sources are classified

Every `ResearchSource` is assigned exactly one `source_type` from a fixed,
extensible list (`global_research/constants.py::SOURCE_TYPE_CHOICES`) —
peer-reviewed paper, patent, technical standard, government publication,
regulator publication, manufacturer documentation, product datasheet,
engineering case study, university report, independent test report,
tender, public procurement record, conference paper, certification record,
news article, distributor listing, commercial database, other. This list
extends (does not replace) the vocabulary already used by
`harvester.constants.SOURCE_TYPES`.

Each `source_type` maps to exactly one **evidence tier** (A/B/C/D) via
`EVIDENCE_TIER_BY_SOURCE_TYPE`, adapted directly from
`harvester.constants.SOURCE_TIER_BY_TYPE`:

- **A** — regulator publication, formal certification record, independent
  test report, peer-reviewed paper (with `independently_reproduced=True`),
  government publication.
- **B** — engineering case study, university report, conference paper,
  peer-reviewed paper (not yet reproduced), public procurement record.
- **C** — manufacturer documentation, product datasheet, distributor
  listing, tender.
- **D** — news article, commercial database (undated/unverified), other.

A source's tier is a **ceiling**, not the final evidence score — see §3.

## 2. How claims are extracted

A `ResearchClaim` is a structured `(subject, predicate, object/value,
unit, conditions)` tuple attached to exactly one `ResearchSource`.
Extraction in this phase is **deterministic and rule-based**
(`services/claim_extraction.py`), operating over the *structured* fields a
provider already returns (title, snippet, labelled numeric fields, unit
strings) — never by feeding raw document prose into a live LLM prompt. See
`docs/adr/ADR-global-research-engine.md` decision 4 for why: this
platform has no live LLM execution runtime wired to real traffic anywhere
today, and an ungoverned prompt-concatenation extractor is exactly the
failure mode (`ingestion/pipeline.py`) this module is designed not to
repeat.

Every extracted claim is schema-validated
(`services/claim_extraction.py::validate_claim_schema()`) before it is
persisted — a claim missing `subject`/`predicate`/`object_value` or with a
non-numeric `object_value` where numeric is required is **discarded and
logged**, never coerced or defaulted.

Two flags are set at extraction time and never overwritten later:
- `vendor_provided` — `True` whenever the claim's source is manufacturer
  documentation, a product datasheet, a distributor listing, or any
  `source_owner_type='vendor'` source. A vendor-provided claim can support
  *discovery* but can never, by itself, justify a `shortlist_manufacturer`
  or `shortlist_technology` recommendation (enforced in
  `services/comparison.py` and `services/council.py`, not just documented).
- `verified` — `True` only when an **independent** (non-vendor) source
  corroborates the same claim within its stated operating conditions (see
  §4). Never set from the claim's own source alone.

A claim without stated operating conditions (`conditions` field empty) is
never treated as universally applicable — `services/compatibility.py`
treats such a claim as `insufficient_data` for any requirement that
depends on operating conditions (temperature, load, climate), rather than
assuming best-case applicability.

## 3. How evidence quality is calculated

`ClaimAssessment` (one per claim) computes a deterministic `overall_evidence_score`
(0-100), adapting `harvester.services.verification`'s pure functions:

```
source_authority_score      = tier_score[source.evidence_tier]           # A=95, B=75, C=50, D=20
methodological_quality_score = 80 if independently_reproduced else 55 if peer_reviewed else 35
independence_score           = 10 if vendor_provided else 90
reproducibility_score        = harvester.verification.corroboration(n_independent_corroborations)
recency_score                = harvester.verification.freshness(publication_date)   # 5-year linear decay
applicability_score          = 100 if conditions_match_target else 50 if conditions_partial else 0
contradiction_penalty        = 15 * count(unresolved_contradictions_involving_this_claim)

overall_evidence_score = round(
    0.25*source_authority_score + 0.15*methodological_quality_score
    + 0.20*independence_score + 0.15*reproducibility_score
    + 0.10*recency_score + 0.15*applicability_score
    - contradiction_penalty
, 2)  # clamped to [0, 100]
```

`formula_version` is stamped on every `ClaimAssessment`; changing a weight
requires bumping it. **A D-tier or vendor-only claim may score high enough
to support "continue research," but `services/comparison.py` hard-caps any
claim with `vendor_provided=True and independent_corroboration_count==0`
from contributing to a `shortlist_*` recommendation** — evidence score
alone can never buy past that gate (this is what the task means by "a
D-level claim may support discovery but must not justify capital
approval").

LLMs may be used (in a future phase) only to help *structure* extraction
and *explain* a score in plain language — the `overall_evidence_score`
number itself is always this deterministic formula's output, never an
LLM's own assertion, mirroring `agent_runtime_model_router`'s
`calibrated_confidence` pattern from the Digital Twin phase.

## 4. How contradictions are handled

`services/contradiction.py::detect_contradictions(claims)` compares every
pair of claims sharing the same `(subject, predicate)` normalized key. A
`ContradictionRecord` is created when:
- numeric values differ by more than a configurable tolerance (default
  15%) under materially the same conditions, or
- one claim asserts a certification/status the other explicitly denies, or
- a vendor claim's `object_value` is not corroborated (or is contradicted)
  by any independent-source claim for the same `(subject, predicate)`.

Contradictions are **never averaged away**. `ContradictionRecord` stores
both claims, the delta, and a `resolution_status`
(`unresolved`/`resolved_by_evidence`/`resolved_by_human`) — `resolved_by_evidence`
only fires when a strictly higher-tier independent claim supersedes a
lower-tier one for the identical conditions; everything else requires
`resolved_by_human`. An unresolved contradiction on a claim feeding a
mandatory `TechnicalRequirement` forces that requirement's compatibility
result to `insufficient_data`, never a guessed pass.

## 5. How candidates are compared

`ComparativeEvaluation` scores every `TechnologyCandidate`/`ProductCandidate`
against the 20 dimensions listed in the product spec. Each dimension has an
explicit, versioned weight (`services/comparison.py::DEFAULT_WEIGHTS`,
missions may override weights but the override is itself versioned and
stored on the `ComparativeEvaluation` row, never silently applied). Every
dimension's raw score, normalized score, and the evidence it's based on are
stored — never just the total. **A candidate whose
`CompatibilityAssessment.mandatory_pass` is `False` is excluded from
ranking entirely** (shown, but marked `incompatible`, never given a rank
number), regardless of how high its weighted score would otherwise be.
`evidence_score` (from §3, aggregated across the candidate's supporting
claims) is always displayed as an independent column next to `total_score`
/ `rank` — the UI and API never blend the two into one number.

## 6. What AI may and may not decide

AI (deterministic services in this phase; a future live-LLM adapter must
honor the same boundary) **may**:
- propose a `TechnicalRequirement`, `TechnologyCandidate`,
  `ManufacturerProfile`, or `ResearchClaim` as a candidate for human review;
- compute `ClaimAssessment`, `CompatibilityAssessment`, and
  `ComparativeEvaluation` scores via the fixed formulas above;
- draft a `ResearchRecommendation` and a `ResearchDocumentDraft` (RFI/RFQ);
- convene a `CouncilRun` and produce `AgentTask` positions.

AI **may never**:
- mark a `ResearchRecommendation`, `TechnologyCandidate`, or
  `ManufacturerProfile` as human-shortlisted or approved
  (`HumanDecision`/`human_approved` is always a real, explicit user action);
- promote a recommendation into a `digital_twin.ModernisationScenario` or a
  `CapitalAllocationDecision` (`services/scenario_bridge.py` and
  `digital_twin.services.promotion.promote_scenario()` both require
  `human_approved is True`, enforced by
  `agent_runtime_model_router.services.human_approval_gate`);
- send, publish, or transmit a `ResearchDocumentDraft` to any external
  party (no send/email/HTTP function is ever imported into this app);
- treat a vendor-only or D-tier claim as sufficient for a `shortlist_*`
  recommendation (§3);
- treat text found inside a `ResearchSource`/`ResearchClaim` as an
  instruction to itself or any other part of the system (§ADR decision 5).

## 7. What requires human review

Per the task's explicit human-review stages, a real `HumanDecision`
(reusing `digital_twin.models.HumanDecision`'s pattern — a new
`ResearchHumanDecision` model, since the *subject* differs, but the same
`decision`/`human_approved`-derived-from-decision/audit-trail shape) is
required before: (1) a `ResearchMission`'s problem definition is approved
for external research; (2) `TechnicalRequirement`s are approved; (3) any
`TechnologyCandidate`/`ManufacturerProfile`/`ProductCandidate` is
shortlisted; (4) an RFI/RFQ draft is finalized (never sent — that stays
manual, outside this system, forever); (5) a `ModernisationScenario` is
created from a recommendation; (6) that scenario is promoted into capital
allocation (the existing `digital_twin`/`waste_to_value_capital_allocation_engine`
gate, unchanged).
