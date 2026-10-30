# EcoIQ Decision & Islah Engine — Stage 5 (evidence-planning foundation)

**Status: internal, read-only, deterministic pilot.** The name "AI Decision
& Islah" expresses the product direction, not a claim that a generative agent
has already discovered and verified causes. This increment makes a useful,
auditable foundation and does **not** invoke an LLM, connect new company data
or authorise intervention.

## Existing contracts reused

- `ecoiq_os.evidence`: UNTESTED through causal-support stages; no TRUE.
- `ecoiq_os.kernel.evaluate_case`: central decision stage and intervention gate.
- `ecoiq_os.islah.IslahProposal`: explicitly stated current/proposed rules.
- `mizan.system_balance`: multiple human, environmental, economic and resource
  dimensions; a breached hard constraint blocks action. No moral master score.
- `api.ProcessAnalysisRun`: project-scoped history of reported, unverified
  CSV totals; no authenticated source documents or raw CSV retained.
- `gold_intelligence.access`: project READ grant on every brief request.

## Delivered first working capability

`ecoiq_os.decision_islah.build_preliminary_brief` takes a known process,
resource, month, unit, and reported input/loss (possibly unknown). The output:

1. Retains **reported**, not verified, input/loss and their unit/period.
2. If the reported loss is positive and input usable, creates **three
   competing testable questions**. They ask whether a discrepancy stems
   from measurement boundaries, legitimate process yield, or handling/storage
   conditions; none is asserted to be true.
3. Each hypothesis includes a *disconfirming observation* and the data
   necessary to test it. All statuses remain `UNTESTED`.
4. Produces corresponding **STUDY_ONLY** Islah investigation ideas and
   lists side effects to examine (worker burden, unfair attribution, safety,
   environmental shifts). These are **not** IslahProposal approvals.
5. Unknown input/loss or a reported zero loss generates only a measurement
   baseline study. **No avoidable loss is invented.**
6. Explicitly returns null for causal conclusion, savings forecast and
   Mizan master score; `implementation_permitted` is always false.
7. Refuses invalid numeric data, negative quantities, mixed-up loss > input,
   invalid resource domains and invalid reporting periods.

The independent `check_islah_readiness(case, proposal)` is for **trusted,
internal reviewed evidence only**. It applies `evaluate_case` and reports
whether design or simulation studies are justified. It cannot disable Mizan
simulation/human review and **never issues implementation permission**.

## New private GET API

`GET /api/v2/projects/<project_slug>/process-analyses/<run_id>/decision-brief/`

- Uses existing Django session authentication (not new credentials).
- Requires current **project READ** role (Viewer, Analyst, Reviewer, Manager
  or existing active staff authority).
- Scoped by BOTH the project and analysis record; inaccessible projects
  return 404. Revocation blocks subsequent reads.
- Returns `Cache-Control: private, no-store`; does not expose source IDs,
  file fingerprints, uploaded files or user identity details.
- Never trusts an old run's `next_stage`, `verified` or `hypothesis_status`
  fields as proof of verification. An incomplete run returns an explicit
  unavailable (422) response rather than fabricated decision advice.
- Supports **GET only**, with no operation that approves a policy or executes
  a physical/financial change.

## Browser entry point

In the existing private dashboard `/business-os/processes/`, each history
row gains **Review questions**. The opened panel displays falsifiable
hypotheses, needed sources, possible Islah studies and known evidence gaps.
HTML is built with text nodes (no unsanitised `innerHTML`). Changing the
project or refreshing history aborts and clears the previous project's panel.
An empty or zero-loss analysis explicitly shows "No causal hypothesis justified".

## Boundaries before genuine AI

The persisted process history holds aggregates, not original provenance.
No retrieval can turn this into a verified source. Before enabling LLM
generation, add a permissioned evidence resolver, controlled prompts from
approved data, strict structured output validation, data exfiltration guards,
red-team tests, independent domain and religious review where applicable,
falsification datasets and measured evaluations. Generative proposals must
never set review status, implementation approval or causal truth.

Before any real intervention:

- Resolve primary evidence and establish a complete measurement boundary.
- Verify affected workers, local communities and environmental effects.
- Complete a justified causal test, not merely observe a ratio.
- Establish current and proposed system rules and document alternatives.
- Simulate effects across all relevant Mizan dimensions with sourced bounds.
- Obtain authorised human review and explicit separate execution approval.
- Measure genuine before/after outcomes and any unintended consequences.

No actual business file, client savings, ethics certification, financial
optimisation or automated action is claimed in this PR.

## Tests to execute

```bash
python -m unittest ecoiq_os.test_decision_islah
python manage.py test api.tests_v2_decision_islah core.tests_process_workspace --noinput
python manage.py test api.tests_v2_process_analyses --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
ruff check ecoiq_os/decision_islah.py ecoiq_os/test_decision_islah.py api/v2_decision_islah.py api/tests_v2_decision_islah.py
```

This is stacked on PR #361 and must be retargeted onto main and fully tested
after prior feature branches are merged in order. Browser and device
validation remain required. No production deployment or mutation was made.
