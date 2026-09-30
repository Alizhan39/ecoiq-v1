# EcoIQ OS

## Product definition

EcoIQ is an operating system for evidence-backed systemic improvement.

It is **not** architected as a catalogue of autonomous agents. Models, prompts,
tools and specialised workflows are replaceable services behind one shared OS
kernel.

The OS exists to trace how resources, energy, water, money, labour, time, data,
risk and value move through a system; identify imbalances and avoidable loss;
test causal explanations; design system changes; simulate their consequences;
and measure whether the real-world result improved.

## Kernel

The deterministic kernel is implemented under `ecoiq_os/`.

```text
EVIDENCE
   ↓
UNIVERSAL FLOW GRAPH
   ↓
KHALIFAH / AMANAH CONTEXT
   ↓
ADL / DISTRIBUTION
   ↓
MIZAN SYSTEM BALANCE
   ↓
ISRAF / LOSS
   ↓
FASAD / SYSTEMIC HARM
   ↓
CAUSAL HYPOTHESIS
   ↓
FALSIFICATION
   ↓
SURVIVING MECHANISM
   ↓
ISLAH DESIGN
   ↓
MIZAN SIMULATION
   ↓
UNINTENDED CONSEQUENCES
   ↓
HUMAN / SHURA REVIEW
   ↓
IMPLEMENTATION
   ↓
MRV / OUTCOMES
   ↓
AUDIT / LEARNING
   ↺
```

AI can assist individual stages, but it does not own the lifecycle or override
deterministic evidence gates.

## Universal Flow Graph

`ecoiq_os.flow` gives every domain the same data grammar:

```text
SOURCE
→ INPUT
→ PROCESS
→ OUTPUT
→ VALUE
→ LOSS
→ WASTE / HARM
→ BENEFICIARY / AFFECTED PARTY
```

Resource types include material, mineral, energy, water, money, labour, land,
time, data, emissions, waste and service.

Known quantities require explicit units. Missing values remain missing. The OS
does not silently convert units or infer absent quantities.

## Mizan

Mizan is a cross-cutting constraint and balance layer, implemented in
`mizan/system_balance.py`.

It prevents local optimisation from being treated as system optimisation. A
factory may improve profit while worsening water security, worker risk or
future liabilities. These are exposed as separate dimensions rather than
hidden inside a weighted master score.

Hard verified constraints such as life safety are non-tradeable.

## Causality and falsification

The shared evidence lifecycle lives in `ecoiq_os.evidence`. Poverty & Justice
reuses it instead of defining a parallel truth system.

```text
UNTESTED
→ ASSOCIATION_ONLY
→ ROBUST_ASSOCIATION
→ CAUSAL_SUPPORT
→ REPLICATED_CAUSAL_SUPPORT
```

The lifecycle also permits rejection, reformulation and insufficient-data
states. It never permits `TRUE`.

The maximum action allowed by evidence is deterministic:

- below robust association: no systemic intervention;
- robust association: exploratory Islah modelling;
- causal support: system/policy simulation;
- replicated causal support: implementation proposal, still human-reviewed.

## Islah

`ecoiq_os.islah` represents system change as an explicit transition from a
current rule to a proposed rule:

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

An Islah proposal is not implementation permission. It requires Mizan
simulation and consequential change requires human review.

## One OS, many domains

`ecoiq_os.domains` defines domain profiles. They reuse the same kernel.

Current profiles:

- Mining & Minerals
- Oil & Gas
- Processing & Metallurgy
- Manufacturing & Assembly
- Energy & Power
- Water Systems
- Agriculture & Food
- Construction & Built Environment
- Transport & Logistics
- Finance & Capital
- Healthcare Systems
- Education Systems
- Government & Public Systems
- Households & Poverty / Justice

Domain code should provide data adapters and domain-specific measurements, not
duplicate causal logic, Mizan logic or intervention gates.

## Kernel decision gate

`ecoiq_os.kernel.evaluate_case` decides only what stage is justified next.

Examples:

- invalid flow graph → repair data structure;
- insufficient Mizan evidence → collect evidence;
- association only → continue falsification;
- robust association + imbalance → exploratory Islah design;
- causal support + imbalance → simulate Islah;
- replicated causal support → human review before implementation;
- hard Mizan constraint → block automated progression and require human review;
- explicit Mizan trade-off conflict → require human allocation/review before continuing.

This is deliberately deterministic.

## Efficiency principle

EcoIQ should avoid parallel architectures.

Reuse:

- one Universal Flow Graph;
- one evidence-state model;
- one Mizan system-balance contract;
- one Islah contract;
- one audit/provenance path;
- one model gateway;
- one human-approval boundary;
- domain adapters instead of domain-specific reasoning stacks.

This keeps the platform explainable, testable and cheaper to operate.

## Relationship to AI

AI is a capability inside the OS, not the OS itself.

Generative components may help with retrieval synthesis, hypothesis generation,
counterexample search, scenario narration or document interpretation. Their
output remains subject to the same evidence, schema, safety and human-review
contracts as any other input.

No unevaluated prompt should be presented as an operational OS capability.

## Next implementation boundary

The next reviewable increments are:

1. persist Universal Flow Graph cases and evidence references;
2. connect existing industrial data modules to domain adapters;
3. implement secure statistical execution for Poverty & Justice;
4. add Mizan re-simulation for proposed Islah changes;
5. connect real MRV outcomes back into the same case;
6. expose an OS case API only after access control, provenance and evaluation
   are covered.

The architecture should remain one OS throughout those increments.
