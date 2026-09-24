# Islamic Decision Intelligence — PR Plan

## Goal

Integrate Qur'anic principles and Maqasid into EcoIQ as an executable, evidence-gated decision architecture rather than a set of labels or parallel scoring systems.

This plan reuses the existing EcoIQ decision core and keeps the current boundaries intact:

- `qdf/` remains the governance/question layer.
- `mizan/` remains the ethical balance engine.
- `amanah_autopilot/` remains the monitored action-preparation layer.
- `evidence_memory/` remains the evidence and retrieval authority.
- `platform_registry/` remains the architecture/maturity authority.
- `ai_observatory/` and provenance remain the audit path.

The new work should create one shared semantic and decision layer that these modules consume, not a second competing framework.

## Non-negotiable rules

1. **Unknown stays unknown.** Missing evidence must be represented as `None/null`; never substitute `0`, `5`, `50`, or another neutral/default value when the output is presented as a finding.
2. **Evidence before interpretation.** Every principle or Maqasid finding must be linked to eligible evidence, provenance, and confidence.
3. **No compensation of red-line harm.** Severe harm, injustice, or prohibited mechanism cannot be averaged away by high profit, public benefit, or another positive dimension.
4. **Separate calculation from interpretation.** Deterministic scoring, retrieved evidence, model-generated explanation, and human/scholar review must remain auditable as distinct stages.
5. **No automatic fatwa or Shariah ruling.** Religious framing is decision intelligence only unless a separately governed, qualified review process explicitly says otherwise.
6. **Backward compatibility first.** Existing QDF, Mizan, API and report consumers must keep working while the shared layer is introduced incrementally.
7. **One ontology authority.** Definitions and mappings must live in one versioned registry rather than being copied into prompts, views, scorers and docs.

## Target architecture

```text
EcoIQ Evidence / Provenance
        |
        v
Islamic Knowledge & Meaning Layer
        |
        +----------------------+
        |                      |
        v                      v
Principle Engines        Maqasid Impact Engine
Adl / Amanah /           Din / Nafs / Aql /
Darar / Maslahah /       Nasl / Mal
Rahmah / Shura / etc.
        |                      |
        +----------+-----------+
                   |
                   v
               QDF Gates
                   |
                   v
              Mizan Engine
                   |
          imbalance / red line?
             /             \
            no             yes
            |               |
            |        Alternatives / Ihsan
            |               |
            +-------+-------+
                    |
                    v
              Amanah Autopilot
                    |
                    v
           Human / Scholar Approval
                    |
                    v
            Action + Monitoring
                    |
                    +----> Evidence Memory
```

## New shared package

Create one Python package:

```text
islamic_intelligence/
  __init__.py

  ontology/
    __init__.py
    registry.py
    schemas.py
    relationships.py

  knowledge/
    __init__.py
    sources.py
    provenance.py
    scholarly_review.py

  maqasid/
    __init__.py
    engine.py
    schemas.py

  principles/
    __init__.py
    adl.py
    amanah.py
    darar.py
    maslahah.py
    rahmah.py
    shura.py
    ihsan.py
    niyyah.py

  orchestration/
    __init__.py
    gates.py
    decision_pipeline.py
    alternatives.py

  evaluation/
    __init__.py
    fixtures.py
    benchmarks.py
```

Do not create one Django app per Arabic term.

## Ontology contract

Each concept should be represented as a versioned, structured definition with at least:

```python
ConceptDefinition(
    key="amanah",
    arabic="الأمانة",
    canonical_meaning=...,
    operational_meaning=...,
    positive_obligations=[...],
    prohibited_failures=[...],
    questions_it_asks=[...],
    observable_signals=[...],
    metrics=[...],
    red_flags=[...],
    related_maqasid=[...],
    related_principles=[...],
    source_refs=[...],
    interpretation_notes=[...],
    scholar_review_status="pending",
    version="1.0",
)
```

The ontology must distinguish:

- source text;
- translation;
- tafsir / commentary;
- EcoIQ operationalisation;
- machine-readable metric/rule;
- scholarly review status.

No model prompt may silently redefine a principle.

## Maqasid Impact Engine

The Maqasid engine answers:

> What is protected, strengthened, weakened, or harmed by this decision?

Initial dimensions:

- Hifz al-Din
- Hifz al-Nafs
- Hifz al-Aql
- Hifz al-Nasl
- Hifz al-Mal

Each impact record must support:

```text
benefit
harm
stakeholder
magnitude
probability
duration
reversibility
distribution
evidence
confidence
```

The engine must return `null` where evidence is absent.

It must not reduce every Maqasid dimension to one number if the underlying distribution, severity, or evidence quality would be lost.

## Principle engines

### Adl

Purpose: test fairness and distribution, not aggregate balance.

Detect:

- benefit concentration;
- harm concentration;
- vulnerable-group asymmetry;
- procedural unfairness;
- access inequality;
- compensation adequacy.

A distribution matrix should be available to downstream Mizan logic.

### Darar

Purpose: detect and characterise harm.

Evaluate:

- physical;
- environmental;
- financial;
- social;
- rights-related;
- future-generational;
- systemic.

Minimum attributes:

- severity;
- probability;
- scale;
- reversibility;
- affected population;
- vulnerability;
- duration.

Severe harm can trigger a hard gate.

### Amanah

Purpose: accountability and entrusted responsibility.

Evaluate:

- owner defined;
- responsibility defined;
- funds/data traceable;
- commitments met;
- conflicts disclosed;
- auditability;
- escalation path;
- accountability on failure.

### Maslahah

Purpose: distinguish claimed benefit from evidenced durable public benefit.

Separate:

- declared benefit;
- evidenced benefit;
- private benefit;
- public benefit;
- durable benefit.

### Shura

Purpose: evaluate participation and consultation.

Track:

- affected groups;
- consulted groups;
- omitted groups;
- vulnerable-group coverage;
- objections;
- response transparency;
- unresolved dissent.

### Rahmah

Purpose: identify avoidable human burden and whether vulnerable groups receive protection proportionate to their exposure.

### Niyyah

Purpose: record stated intent and test consistency between declared purpose, incentives, actual mechanism and observed outcomes.

Intent alone must never override measured harm.

### Ihsan

Purpose: optimise beyond minimum acceptability.

Given an acceptable or repairable decision, generate evidence-grounded alternatives that improve outcomes without violating hard constraints.

The Ihsan layer must never invent operational feasibility or savings; unknown assumptions remain explicit.

## Mizan v2 role

Mizan should become the system-level balance engine over Maqasid and principle outputs.

Processing order:

```text
1. Red-line gates
2. Distributional balance
3. Aggregate balance
4. Evidence sufficiency
5. Alternative comparison
```

A positive aggregate must never erase severe concentrated harm.

Mizan output should include:

- overall status;
- material imbalance findings;
- affected stakeholders;
- non-compensable red lines;
- evidence coverage/confidence;
- reasons;
- required changes;
- alternative paths.

Suggested status vocabulary:

- Balanced
- Tension
- Material Imbalance
- Insufficient Evidence

The current public Mizan score/labels should remain backward-compatible until a migration plan is explicitly approved.

## QDF role

QDF should become a governance gate/orchestrator rather than independently duplicating all principle logic.

Target mapping:

```text
Niyyah    -> intent gate
Halal     -> mechanism/permissibility gate
Adl       -> justice engine
Rahmah    -> human-impact engine
Mizan     -> balance engine
Amanah    -> accountability engine
Maslahah  -> genuine-benefit engine
Darar     -> harm gate
Shura     -> participation engine
Akhirah   -> long-horizon responsibility
```

Each QDF question should consume the relevant engine result and evidence state.

Do not remove the existing QDF API in the first implementation PR.

## Amanah Autopilot role

Amanah Autopilot should prepare and monitor actions, not silently make consequential decisions.

Target flow:

```text
monitor
 -> detect deviation
 -> verify evidence
 -> run Maqasid
 -> run Darar
 -> run Adl
 -> run Mizan
 -> generate alternatives
 -> prepare action
 -> request approval
 -> monitor outcome
```

Autonomous external writes remain behind existing human approval and connector governance.

## Evidence and source model

Every Islamic-intelligence finding must be able to answer:

- Which real-world evidence supports this?
- Which principle/Maqasid definition was applied?
- Which source/translation/tafsir mapping informed that definition?
- Which version was used?
- Was it scholar reviewed?
- Which deterministic rule or model produced the finding?
- Which human approved consequential use?

Islamic-source provenance must not be mixed with ordinary ESG/company evidence; both should be linked, but their roles are different.

## API strategy

Phase 1 should add internal typed contracts only.

Later API shape may expose:

```text
/api/v2/islamic-intelligence/ontology/
/api/v2/islamic-intelligence/assess/
/api/v2/islamic-intelligence/maqasid/
/api/v2/islamic-intelligence/mizan/
```

Public API exposure is not part of the first implementation PR unless separately approved.

## Platform registry

Register the shared layer in `platform_registry/` only when real code and tests exist.

Do not mark the Islamic Intelligence layer Production merely because ontology files exist.

Suggested maturity progression:

- ontology registry: Experimental -> Beta after review/versioning tests;
- Maqasid engine: Experimental until evaluation fixtures exist;
- principle engines: Experimental/Beta independently;
- Mizan integration: Beta only after regression + red-line tests;
- Amanah integration: Beta only after approval/audit tests;
- scholarly source layer: Planned until a reviewed corpus and governance process exist.

## Implementation phases

### PR A — Shared ontology and contracts

- create `islamic_intelligence/`;
- define typed ontology schemas;
- move duplicated conceptual definitions/mappings into one registry without changing existing public outputs;
- add versioning and review-status fields;
- add unit tests;
- document source/provenance boundaries.

No scoring behaviour change.

### PR B — Unknown propagation and evidence gates

- audit QDF and Mizan for neutral/default substitution;
- remove presentation-facing neutral fallbacks;
- preserve `None/null` for unsupported findings;
- add regression tests for unknown inputs;
- ensure evidence status is propagated into all downstream outputs.

This PR must explicitly cover the existing QDF path where missing questions can currently fall back to a neutral score.

### PR C — Maqasid impact engine

- implement Maqasid schemas and impact records;
- support stakeholder, magnitude, duration, reversibility, distribution and evidence;
- add deterministic fixtures for company/project/policy examples;
- no LLM is required for the core calculation.

### PR D — Principle engines

Implement Adl, Darar, Amanah, Maslahah, Shura and Rahmah first.

Niyyah and Ihsan can follow once the shared evidence contract is stable.

Each engine needs:

- typed input/output;
- explicit unknown handling;
- provenance;
- red-line behaviour where relevant;
- test fixtures.

### PR E — Mizan v2 integration

- consume Maqasid + principle results;
- implement non-compensable red lines;
- implement distributional balance before aggregate balance;
- retain current public Mizan compatibility;
- add comparison output and material-imbalance reasons.

### PR F — QDF orchestration integration

- route QDF questions to shared engines;
- remove duplicated principle calculations only after equivalence tests;
- keep existing API contracts;
- add compatibility tests comparing old/new paths where evidence is complete.

### PR G — Ihsan alternatives

- generate ranked improvement alternatives subject to Mizan/Darar/Adl constraints;
- alternatives must retain assumptions and evidence gaps;
- do not present model-generated assumptions as facts.

### PR H — Amanah Autopilot integration

- monitor supported events;
- run governed re-assessment;
- prepare recommended action;
- require human approval for consequential action;
- record Observatory + provenance + approval trail.

No external connector writes without separately approved connector/runtime work.

## Required evaluation fixtures

At minimum, add cases where:

1. high profit + severe community harm must not pass;
2. high aggregate public benefit + concentrated vulnerable-group harm must produce Material Imbalance;
3. missing evidence produces Insufficient Evidence, not a neutral score;
4. strong environmental outcome + exploitative labour distribution fails Adl;
5. transparent governance cannot compensate for severe Darar;
6. a lower-profit alternative is preferred by Ihsan only when its claimed benefits are evidenced;
7. conflicting evidence lowers confidence rather than being silently resolved;
8. revoked evidence invalidates the derived finding;
9. the same decision with different stakeholder distribution changes the Adl/Mizan result;
10. a model narrative cannot override deterministic red-line output.

## Acceptance criteria for the first implementation PR

- one authoritative ontology registry exists;
- no duplicated concept definition is introduced;
- no new public religious ruling claim is introduced;
- unknown values remain unknown;
- no current QDF/Mizan API breaks;
- tests prove a severe red line cannot be averaged away;
- provenance identifies both real-world evidence and ontology/source version;
- platform registry accurately reports maturity;
- docs explain what is implemented versus planned;
- no production deployment, migration, connector enablement or autonomous external action is performed as part of the planning PR.

## Explicitly out of scope for the planning PR

- production deployment;
- database migration;
- changing public Mizan labels;
- changing QDF scoring behaviour;
- ingesting an unreviewed Qur'an/Hadith/Tafsir corpus;
- claiming scholarly endorsement;
- issuing fatwa/Shariah rulings;
- enabling autonomous external actions;
- enabling new MCP/connectors;
- adding a second vector database or agent framework.

## First coding task

Start with **PR A — Shared ontology and contracts**.

Before implementation, Claude Code should read:

- `CLAUDE.md`
- `docs/repo-map/OBSIDIAN_BRIDGE.md`
- `docs/architecture/AI_DECISION_OS.md`
- `qdf/models.py`
- `qdf/scoring.py`
- `qdf/engine.py`
- `mizan/scoring.py`
- `mizan/project.py`
- `amanah_autopilot/`
- `evidence_memory/`
- `platform_registry/architecture.py`
- `platform_registry/agents.py`

Then implement only the smallest backward-compatible ontology slice and tests. Do not begin by creating new scoring formulas.
