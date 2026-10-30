# EcoIQ Situation Intelligence v1 — evidence, formulas, Qur'anic research

## Product goal

An authenticated construction (and other domain) client selects an existing
process analysis in **Business OS → Process Intelligence → Review questions**.
The decision brief now returns a distinct `situation_guidance` object with:

1. Deterministic triage: incomplete evidence / no recorded loss / recorded
   positive loss requiring investigation. No moral or causal accusation.
2. Explicit formulas, units, measured arithmetic outputs where justified,
   and clear unknowns (especially recoverable financial savings).
3. A contextually selected set of **editorial research lenses** with exact
   verse locators from the *existing* `islamic_knowledge.principles` catalogue.
4. Hypothesis questions and missing-data requirements from the existing
   Decision & Islah service, preserving `COLLECT_EVIDENCE`.
5. Hardcoded denial of `implementation_permitted`, `shariah_verdict`,
   `religious_approval`, `causal_conclusion` and `savings_forecast`.

This is the beginning of a commercial *decision-support product*, not yet a
religiously certified advisor or real generative AI reasoning layer.

## Illustrative, fictional example

Input: 1,000 kg received; 120 kg recorded as loss; both records in one
2026-10 accounting boundary (source identifiers NOT independently verified).

- Reported loss rate = 120 / 1000 × 100 = **12%**.
- Reported arithmetic difference = 1000 - 120 = **880 kg**.
  This does **not** prove that 880 kg was actually delivered as product.
- Recoverable savings = `verified_avoidable_quantity ×
  verified_unit_economic_value - verified_intervention_cost` → **unknown**.
  The case does not establish whether any loss is avoidable.
- Stage: **COLLECT_EVIDENCE**. Verify stock movements, expected yield, safety
  constraints, disposal records, and worker/environmental impacts.

## Qur'anic research lens — explicitly not a fatwa

The existing draft operational principles contain source **locators** such
as Amanah (4:58), Mizan (55:7–9), Israf (7:31), Islah (11:88, 7:56) and
Adl (4:135, 5:8, 16:90). These are only possible starting points for
scholarly contextual interpretation, not the words of verses, verified
tafsir, a licence to train a model, or a finding that a company or action is
Islamically compliant.

No verse wording/translation is copied into this feature. Links go to the
specific verse locator on quran.com; the original text/translation,
context, scholarly differences and contractual usage rights require
independent checking. UI must visibly distinguish:

- Reported/derived operational observation.
- Human-authored draft EcoIQ question.
- Qur'anic verse locator (NOT an approved meaning).
- Reviewed interpretation (NONE delivered in v1).
- Religious/legal approval (NONE delivered in v1).

The 114-surah catalogue and 99 Names inventory are still metadata. A
combinatorial 33×114 matrix is NOT a validated scripture-to-business mapping;
the system never silently infers a linkage for each verse or scores a company
by a Divine Name.

For any question about specific religious duties, rights, prohibitions,
financial contracts or competing scholarly interpretations, the system
should **abstain from prescribing a ruling** and route to a qualified
scholar alongside relevant business, environmental and legal experts.

## AI integration boundary

The UI uses `DETERMINISTIC_EVIDENCE_TRIAGE`, with `ai_model_called=false`.
This is not a generative model pretending to be one. The existing Stage 6
`ecoiq_os.grounded_ai.prepare_grounded_draft` may, in a separately
approved workflow, ask an AI model for *falsifiable questions citing independently
reviewed project-private evidence*, but it is DISABLED by default and cannot
generate scriptural rulings or override this API.

A later read-only AI narrative must use strictly validated input schemas,
source citations, explicit abstention and human scrutiny. Approved verses,
tafsir and qualified reviews must be stored with provenance in the
existing `islamic_knowledge.contracts` and not invented by prompts.

## Rust / C++ commercialisation

Stage 9 is stacked on native candidate PR #370. No native module is called
by this API yet because a spawned Rust CLI per request would likely be slower
than the trivial Python calculation, and the C++ geometry model has no
approved engineering calibration for real digital twins. Their standalone
tests and Python/Rust parity make a future production path feasible.
Measure actual throughput and latency against Python first; if materially
beneficial, integrate the **same typed mathematical contract** with Rust
via a reviewed, feature-flagged PyO3/maturin wheel. C++ via a validated
pybind11 interface can later serve digital-twin simulations, with tests
for physical units, coordinate systems and engineering assumptions.
Keep Python fallback and RBAC/evidence/Mizan/human authorisation as the
canonical decision authority.

## Test and security constraints

- No new public endpoint: extends a pre-existing READ-authorised,
  project-scoped `/api/v2/projects/.../decision-brief/` GET response.
- No DB writes, raw CSV re-read, third-party JS, provider keys or model calls.
- No client-driven `verified`, savings, approval or religious authority.
- HTML escapes dynamic text via `textContent`. JS only opens HTTPS links
  matching a fixed quran.com numeric path pattern; no arbitrary links.
- Private/no-store response and authenticated role checks inherited from
  the existing API.
- Unknown ≠ zero. Positive recorded loss ≠ confirmed Israf or Fasad.
- Changes must pass existing Process Workspace, stage 6/7 and kernel tests.

Run:
```bash
python manage.py test ecoiq_os.test_situation_guidance api.tests_v2_decision_islah core.tests_process_workspace --noinput
node --check static/js/process-workspace.js
```

## To reach paid customer readiness

1. Obtain explicit rights and sector data contracts; use real private staging
   and independent security review.
2. Validate resource and financial formula definitions, unit conversions,
   missingness, materiality and professional interpretations.
3. Add controlled benchmarks for native Rust/C++ kernels based on bottlenecks,
   not language prestige.
4. Qualify and review the source-specific Qur'anic lenses with scholars,
   versioned translation/tafsir rights, ikhtilaf handling and revocation.
5. Give the client separate **business recommendations** and **possible
   Qur'anic reflection questions**, never claim religious certification.
6. Quantify and independently verify pilot impact, costs and human decisions.
