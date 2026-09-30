# Islamic Decision Intelligence inside EcoIQ OS

## Status

This document is a roadmap for integrating Qur'anic principles, Maqasid and
reviewed Islamic knowledge **inside the existing EcoIQ OS**.

It is not a second operating system, a parallel scoring framework or a catalogue
of autonomous agents.

The canonical product architecture is:

- `docs/architecture/ECOIQ_OS.md`
- `ecoiq_os/`
- `mizan/system_balance.py`
- `platform_registry/`

This roadmap must remain subordinate to those contracts.

## Architectural rule

Islamic decision intelligence enters EcoIQ through governed knowledge,
principle definitions and decision constraints, while the shared OS lifecycle
remains unchanged:

```text
EVIDENCE
→ UNIVERSAL FLOW GRAPH
→ KHALIFAH / AMANAH
→ MAQASID
→ ADL
→ MIZAN
→ ISRAF / FASAD
→ CAUSAL HYPOTHESIS
→ FALSIFICATION
→ SURVIVING MECHANISM
→ ISLAH
→ MIZAN SIMULATION
→ IHSAN
→ SHURA / HUMAN REVIEW
→ IMPLEMENT
→ MRV
→ AUDIT / LEARN
↺
```

AI may assist individual services, but it does not own this lifecycle and may
not bypass deterministic evidence or human-review gates.

## Non-negotiable rules

1. **Unknown stays unknown.** Missing evidence remains `None/null`.
2. **Evidence before interpretation.** Operational conclusions must point to
   eligible real-world evidence and the knowledge definition applied.
3. **Source classes remain separate.** Qur'an text, translation, tafsir,
   fiqh/scholarly position and EcoIQ operationalisation are distinct records.
4. **No automatic fatwa or Shariah certification.**
5. **Recognised ikhtilaf remains visible.** EcoIQ must not collapse legitimate
   scholarly disagreement into one machine conclusion.
6. **No invented religious evidence.**
7. **Mizan is cross-cutting.** A local gain may not hide serious harm elsewhere.
8. **Adl is distributional.** Unequal outcome alone is not automatically
   injustice; mechanism, burden, benefit, risk and decision power must be
   examined.
9. **Causal discipline applies equally to moral language.** A harmful outcome
   is not evidence of a particular root cause until the mechanism survives
   testing.
10. **Consequential use remains human reviewed.**

## OS layers

### Khalifah

Purpose:

> What has been entrusted here?

The layer identifies the stewardship scope of the case without issuing a
religious ruling.

Typical entrusted objects include:

- people and families;
- land;
- water;
- air;
- biodiversity;
- minerals;
- energy;
- public funds;
- property;
- data;
- authority;
- labour;
- infrastructure;
- future generations.

### Amanah

Purpose:

> What responsibilities follow from what has been entrusted?

Amanah should map:

- responsible owner;
- delegated authority;
- obligations;
- commitments;
- traceability;
- accountability;
- escalation;
- failure ownership.

Amanah is a responsibility model, not an autonomous action engine.

### Maqasid

Purpose:

> Which fundamental goods may be protected, strengthened, weakened or harmed?

Initial reviewed dimensions may include:

- Din;
- Nafs;
- Aql;
- Nasl;
- Mal.

Each impact record should preserve, when evidence exists:

```text
stakeholder
benefit
harm
magnitude
probability
duration
reversibility
distribution
evidence
confidence
source interpretation version
review status
```

Maqasid outputs do not collapse automatically into one number.

### Adl

Purpose:

> How are value, burden, risk, opportunity and decision power distributed?

The OS should examine:

```text
WHO CREATES VALUE?
WHO RECEIVES VALUE?
WHO PAYS?
WHO BEARS RISK?
WHO OWNS?
WHO DECIDES?
WHO CAN APPEAL?
WHO HAS NO REPRESENTATION?
```

A distributional anomaly is a signal for investigation, not proof of malicious
intent or injustice.

### Mizan

Mizan remains the cross-cutting system-balance layer already implemented in
`mizan/system_balance.py`.

It checks economic, resource, energy, water, environmental, human, worker,
social, justice, resilience and intergenerational dimensions.

It must not be replaced by an Islamic-only aggregate score.

Hard verified constraints remain non-compensable.

### Israf

Purpose:

> Where is entrusted value or resource being used without sufficient useful
> outcome?

Examples:

- material loss;
- waste heat;
- unnecessary energy use;
- water leakage;
- idle capital;
- preventable food waste;
- avoidable process friction;
- unnecessary administrative burden.

Israf findings must retain measurable units wherever possible.

### Fasad / systemic harm

Purpose:

> Where is a process creating deterioration that compounds through the system?

Examples may include:

- water depletion;
- soil degradation;
- repeated unsafe work conditions;
- corruption-enabling process design;
- debt spirals;
- persistent waste;
- institutional erosion.

The label must not be applied merely because an outcome is undesirable.
Evidence and mechanism are required.

### Islah

Islah remains a system-change contract:

```text
CURRENT RULE
→ INCENTIVE
→ BEHAVIOUR
→ FLOW
→ OUTCOME

DESIRED OUTCOME
→ DESIRED FLOW
→ BEHAVIOUR
→ INCENTIVE
→ PROPOSED RULE
```

No Islah proposal becomes implementation permission merely because it sounds
ethically preferable.

It must pass:

- causal evidence gate;
- Mizan re-simulation;
- unintended-consequence testing;
- legal/domain review;
- Shariah review where the interpretation is material;
- human approval.

### Ihsan

Purpose:

> Once harm and imbalance have been addressed, what evidence-backed alternative
> produces a better outcome?

Ihsan is constrained optimisation beyond minimum acceptability.

It must not invent feasibility, savings or benefits.

### Shura

Shura is the human participation and review boundary.

Depending on the case this may include:

- affected stakeholders;
- domain experts;
- engineers;
- economists;
- legal reviewers;
- qualified Shariah reviewers;
- community representatives;
- authorised public decision-makers.

EcoIQ records disagreement rather than pretending consensus exists.

## Islamic knowledge layer

The religious knowledge layer is a governed evidence service behind the OS,
not a second decision engine.

Suggested package boundary:

```text
islamic_knowledge/
  ontology/
  sources/
  provenance/
  maqasid/
  principles/
  review/
  evaluation/
```

It should not contain a second orchestration framework, second Mizan, second
audit store or second causal lifecycle.

## Source model

Every knowledge record should preserve, as applicable:

```text
source_type
work
author / translator
edition
surah / ayah or other locator
exact passage
language
authentication / status
school / scholarly position
rights
version
content hash
reviewer
review date
interpretation notes
confidence
```

Required separation:

```text
SOURCE TEXT
≠ TRANSLATION
≠ TAFSIR
≠ FIQH POSITION
≠ ECOIQ OPERATIONALISATION
≠ AI INFERENCE
≠ RECOMMENDATION
```

## Ikhtilaf contract

Where recognised disagreement exists, the knowledge service returns multiple
positions with provenance and scope.

The OS may then return:

```text
SCHOLARLY_DISAGREEMENT_PRESENT
HUMAN_REVIEW_REQUIRED
```

It must not decide that one madhhab or scholarly view is universally correct.

## Relationship to Universal Flow Graph

Islamic principles operate on the same real system model as the rest of EcoIQ.

For example, mining:

```text
MINERAL
→ EXTRACTION
→ PROCESSING
→ ENERGY / WATER / LABOUR INPUTS
→ PRODUCT
→ VALUE
→ WASTE / TAILINGS / EMISSIONS
→ LOCAL BENEFIT / COST / RISK
→ RESTORATION / FUTURE LIABILITY
```

The knowledge layer may help frame Amanah, Adl, Mizan, Israf and
intergenerational responsibilities, but it does not replace the physical and
economic data.

## Relationship to Poverty & Justice

Poverty & Justice continues to use the shared causal evidence lifecycle in
`ecoiq_os.evidence`.

Religious framing cannot upgrade:

```text
ASSOCIATION_ONLY
```

into:

```text
CAUSAL_SUPPORT
```

without evidence.

Similarly:

```text
poverty
≠ automatic proof of injustice

wealth
≠ automatic proof of injustice

inequality
≠ automatic proof of injustice
```

The mechanism must be examined.

## Relationship to QDF

QDF remains an existing product/governance interface.

It should progressively consume OS outputs rather than duplicate them.

Potential mappings:

```text
intent / purpose     → Khalifah / Niyyah context
responsibility       → Amanah
distribution         → Adl
balance              → Mizan
harm                 → systemic-harm / Darar evidence
benefit              → Maslahah evidence
participation        → Shura
improvement          → Ihsan
repair               → Islah
long horizon         → intergenerational Mizan
```

Existing QDF APIs remain backward-compatible until a tested migration is
approved.

## Relationship to existing Mizan

The current public/company Mizan score is not silently replaced.

The OS-level Mizan contract is authoritative for new cross-system work.

Any migration from legacy/public scoring to the OS balance model requires:

- explicit compatibility tests;
- versioned definitions;
- no neutral fallback for unknowns;
- preserved provenance;
- documented public-output changes.

## Falsification

Any proposed mechanism should be attacked before Islah design.

Examples:

- Does high debt actually precede vulnerability, or does low buffer cause
  borrowing?
- Does a resource-rich region transmit value to households, or is the observed
  relationship explained by sector structure?
- Does an energy intervention reduce total system burden, or merely shift it to
  water, workers or future mineral dependence?

Islamic framing does not exempt a claim from this falsification requirement.

## Evaluation requirements

Before a religious knowledge service is described as operational, build
reviewed evaluation fixtures for:

1. exact Qur'an reference retrieval;
2. translation distinctions;
3. tafsir attribution;
4. recognised scholarly disagreement;
5. missing evidence;
6. adversarial instructions embedded in retrieved documents;
7. invented-verse detection;
8. source-version mismatch;
9. revoked review;
10. operationalisation that overstates the source.

For OS decisions, also test:

1. high profit + severe verified harm does not pass Mizan;
2. concentrated vulnerable-group burden remains visible;
3. missing data produces insufficient evidence;
4. one local efficiency improvement can fail system-level Mizan;
5. model narrative cannot override a hard constraint;
6. disputed interpretation triggers review rather than automatic ruling.

## Implementation sequence

### Phase A — Knowledge contracts

Implement only:

- typed ontology schema;
- source-type separation;
- provenance;
- versioning;
- scholarly-review status;
- ikhtilaf representation.

No new scoring formulas.

### Phase B — OS bindings

Bind reviewed definitions to existing OS concepts:

- Khalifah;
- Amanah;
- Maqasid;
- Adl;
- Mizan;
- Israf;
- Fasad/systemic harm;
- Islah;
- Ihsan;
- Shura.

No second orchestration stack.

### Phase C — Evidence-backed Maqasid records

Add typed impact records with stakeholder, harm/benefit, duration,
reversibility, distribution, evidence and confidence.

### Phase D — Mizan integration

Allow reviewed principle outputs to inform the existing system-balance
assessment while preserving hard constraints, unknowns and traceability.

### Phase E — Domain evaluation

Validate on real domain cases:

- mining and minerals;
- oil and gas;
- processing and metallurgy;
- energy;
- water;
- manufacturing;
- agriculture;
- construction;
- finance;
- government;
- households / Poverty & Justice.

### Phase F — Governed AI assistance

Only after labelled evaluation, allow model-assisted:

- source retrieval;
- comparison of interpretations;
- hypothesis generation;
- explanation;
- alternative generation.

The deterministic OS contracts remain authoritative.

## Platform registry

Register components only when code exists.

Do not present an ontology document, prompt or corpus folder as a running
capability.

Suggested maturity progression:

```text
SPECIFICATION
→ EXPERIMENTAL
→ BETA
→ PRODUCTION
```

Production requires real runtime use, evidence/provenance, tests, evaluation and
appropriate human-review controls.

## Explicitly out of scope for this planning document

- production deployment;
- database migration;
- public API changes;
- automatic fatwa;
- Shariah certification;
- declaring persons sinful;
- selecting one school as universally correct;
- ingesting an unreviewed religious corpus;
- autonomous external actions;
- a second Mizan implementation;
- a second vector database;
- a second agent/orchestration framework.

## First coding increment

The first implementation should be the smallest reviewed
`islamic_knowledge` contract slice:

```text
source type
+ exact reference
+ version
+ scholarly position
+ review status
+ provenance
+ tests
```

Then bind those records to the existing EcoIQ OS rather than creating new
decision infrastructure.
