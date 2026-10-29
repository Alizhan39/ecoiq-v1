# EcoIQ OS — Process Diagnostic v1 (internal prototype)

This first executable vertical slice reuses the existing EcoIQ OS contracts.
It is **not** an OS replacement, an enterprise connector, an assessment
publication, a religious interpretation or an autonomous optimisation agent.

## Exact data boundary

One process snapshot accepts two *reported* observations for the same
resource, unit and period:

- **Input**: reported resource entering the process.
- **Loss**: reported subset of that input, with its own source references.

Both observations are non-negative, finite or explicitly unknown (`None`).
Known figures require non-empty evidence identifiers. Identifiers supplied by
the caller are **not authenticated or independently verified** by this adapter.
The adapter never retrieves documents, accesses an organisation's records, or
stores those identifiers. A missing observation must remain `null`; it must
never silently become zero.

The only numerical formula in v1 is:

```text
recorded_loss_rate (%) = reported_loss / reported_input * 100
```

It runs only when both operands exist, use identical unit/period boundaries,
and the input is greater than zero. A zero denominator remains unknown.
No statement about preventability, culpability or cause follows from this KPI.

## Internal example

```python
from ecoiq_os.process_diagnostic import (
    ProcessMeasurement, ProcessSnapshot, diagnose_process,
)

case = ProcessSnapshot(
    case_id="DEMO-CONSTRUCTION-001",
    domain="construction",
    process_name="Material receiving",
    resource_type="material",
    input_measurement=ProcessMeasurement(
        1000, "kg", "2026-10", ("demo-invoice",)
    ),
    loss_measurement=ProcessMeasurement(
        120, "kg", "2026-10", ("demo-waste-ticket",)
    ),
)
result = diagnose_process(case)
print(result.to_dict()["kpi"]["value"])            # 12.0
print(result.to_dict()["next_step"]["next_stage"])  # COLLECT_EVIDENCE
```

All quantities above are **fictional demonstration inputs**, not a measured
company outcome. `to_dict()` returns a structurally valid Universal Flow Graph,
the KPI, explicit source references, limitations and the existing kernel gate.

## Governance

- Default Mizan dimensions (resource efficiency, worker, environment) are
  `INSUFFICIENT_DATA`, so the next step is to collect evidence, not
  implement optimisation.
- Default hypothesis status is `UNTESTED`; observation does not confer
  causal support.
- `mizan` and `hypothesis_status` overrides are **internal privileged
  arguments only**. Callers must obtain reviewed evidence and scoped
  authorisation from existing services before supplying them. Never expose
  these as user-supplied API approval fields.
- Existing Mizan constraints, causal permission and human-review rules remain
  authoritative; no new competing decision kernel is introduced.
- No public or staff HTTP route, database table, connector, execution agent,
  99-name compliance score or production deployment is added.

## Next increment: local CSV pilot

A strict, offline, read-only CSV importer is documented in
[Stage 2: Process CSV v1](PROCESS_CSV_V1.md). It remains internal,
with no authenticated project API or verified company records.

## Run tests

```bash
python -m unittest ecoiq_os.test_process_diagnostic
python -m unittest ecoiq_os.test_kernel
ruff check ecoiq_os/process_diagnostic.py ecoiq_os/test_process_diagnostic.py
```

## Next bounded increment

1. Persist a project-scoped OS case and evidence references with verified
   user/project access and provenance.
2. Add one real read-only ERP/CSV adapter for a consenting pilot organisation;
   validate unit, period, baseline and the accounting boundary.
3. Add a reviewed threshold methodology and genuinely observed Mizan dimensions,
   never a convenience morality score.
4. Falsify candidate loss mechanisms, model an Islah proposal and re-run
   cross-dimensional Mizan before human approval.
5. Link measured before/after outcomes to the same case with an auditable
   comparison, then expose a permissioned API and the mobile/AR experience.

Until those gates exist, this module must not be marketed as verified AI
diagnosis or production-ready business automation.
