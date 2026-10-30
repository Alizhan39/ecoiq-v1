# EcoIQ Formula Studio v1 — 20 KPI baseline + extensible AI Formula Designer

**State:** research-only proposed indicator definitions and AI formula drafts.
**No production feature flag enabled, no provider call or customer data used.**

## Architecture: three distinct responsibilities

1. **Formula Registry — 20 initial KPI candidates.** `ecoiq_os.formula_registry` versioned expressions, input/derived unit contracts, source IDs, reporting period, missingness and Decimal arithmetic.
2. **Situation templates — six additional candidates.** `ecoiq_os.formula_designer.EXTRA_SITUATION_FORMULAS` for equipment downtime, supplier performance, construction rework, mining processing, turnover and hours variance. More reviewed templates can be added without altering the original 20.
3. **AI Formula Designer — optional.** `propose_additional_formula` asks the existing AI Gateway for a **bounded expression candidate** only if active project ANALYSE permission, fresh independently reviewed project-private sources, an explicit internal per-transfer consent and **both** `ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=True` and `ECOIQ_FORMULA_AI_EXTERNAL_ENABLED=True`. Both off by default. No public browser/API endpoint exposes model calls or allows new variables.

Mathematical expression language is restricted to known variable names,
**integer constants**, `+ - * /` and parentheses. No `eval`, `exec`,
`import`, exponentiation, functions, loops, file/network/database access or
arbitrary Python. AST is capped by length, depth and node count.
Each declared variable has a unit; arithmetic dimensions must match the
declared result. Calculations use `Decimal`, no float rounding, reject NaN,
infinity, negatives, unknown variables/units, periods mismatch and division
by zero. `None` is unknown, **not zero**. The engine does not convert
currencies or physical units silently.

An AI candidate also requires exact quotations from source snippets; unknown
or fabricated citations, extra keys (such as `approved_for_implementation`)
and invalid schema are rejected. Valid syntax and units are **not** proof of
valid economics, accounting, causality, legal fairness, theology or
measurement quality. Human/domain review must approve any addition to the
official catalogue. AI output is not persisted and never becomes a formula
used by production automatically.

## 20 initial **draft** operational formulas

These are **proposals linked to the 20 KPI keys merged in PR #369**,
not recovered/final approved corporate metric definitions. Percent is
displayed in output-unit symbol `1` (dimensionless percentage number); the
formula multiplies a dimensionless ratio by 100. Further review should give
this representation a distinct semantic `percent` unit in a future API.

| Category | Candidate KPI | Expression | Essential caveat |
|---|---|---|---|
| Financial | Revenue | `reported_revenue` | Recognised revenue vs cash received |
| Financial | Gross margin | `(revenue - cost_of_goods_sold) / revenue * 100` | Consistent COGS and revenue policy |
| Financial | Operating cash flow | `operating_cash_inflows - operating_cash_outflows` | Simplified cash basis; classification |
| Financial | Liquidity ratio | `current_assets / current_liabilities` | Current ratio; liabilities cannot be zero |
| Resource | Material loss rate | `recorded_material_loss / material_input * 100` | Recorded ≠ avoidable |
| Resource | Energy intensity | `total_energy / produced_units` | Consistent functional unit |
| Resource | Water intensity | `water_withdrawal / produced_units` | Withdrawal ≠ consumption |
| Resource | Asset utilisation | `productive_asset_hours / available_asset_hours * 100` | Define available hours |
| Environmental | GHG intensity | `reported_emissions / produced_units` | Define Scope, factors and reporting boundary |
| Environmental | Waste recovery | `recovered_waste / total_generated_waste * 100` | Specify recovered waste process |
| Environmental | Freshwater stress exposure | `site_freshwater_withdrawal / local_available_freshwater * 100` | **Not an established watershed-stress metric** |
| Social | Incident rate | `recordable_incidents / worked_hours * 1000000` | Per million work hours; reporting definitions |
| Social | Training per worker | `total_training_hours / eligible_workers` | Eligible population |
| Social | Living wage coverage | `eligible_workers_at_or_above_local_benchmark / assessed_workers * 100` | Local benchmark and privacy |
| Justice | Adjusted pay gap | `(adjusted_reference_pay - adjusted_comparison_pay) / adjusted_reference_pay * 100` | **Adjusted pay inputs must come from legitimate comparability analysis**, not AI invention |
| Justice | Fair procurement process coverage | `audited_procedures_meeting_criteria / assessed_procurements * 100` | Process adherence is not a moral/legal verdict |
| Justice | Benefit distribution for one group | `documented_group_benefit / total_documented_benefit * 100` | Exact group, consent, consistent boundary |
| Accountability | Evidence coverage | `kpi_with_traceable_sources / eligible_kpi * 100` | Source reference ≠ authenticated evidence |
| Accountability | Independent verification share | `independently_reviewed_kpi / eligible_kpi * 100` | Independently reviewed inputs required |
| Accountability | Human-review coverage | `independently_reviewed_decisions / consequential_decisions * 100` | Reviewed ≠ approved implementation |

**Currency:** GBP for the synthetic UK accounting prototype; this does not
imply that every global EcoIQ customer's functional currency is GBP.
A later domain-reviewed schema must support ISO currency codes, FX dates,
entity consolidation, price levels and effective reporting units explicitly.

**Human rights / fairness:** Outputs must never automatically label an
employer, employee, group, region or contractor unjust, guilty or compliant.
**Religion:** 114 surahs and 99 Names are a separate reviewed knowledge
system; neither the initial 20 nor new AI proposals produce tafsir, fatwa,
Shariah compliance verdict or spiritual score.

## Example: formula for an unforeseen case

Construction site has a dated equipment register:
- `downtime_hours = 12`; `scheduled_hours = 80`.
- A reviewer checks whether scheduled hours include holidays and whether
  planned maintenance is included.
- Suggested mathematical formula:
  `downtime_hours / scheduled_hours * 100` → **15% reported downtime**.
- The number cannot prove which downtime is avoidable. AI may propose
  a different candidate, but must disclose its assumptions, source citations,
  units and the evidence required to test the definition.

When no known template exists, trusted code may *optionally* ask the
existing AI Gateway to suggest one, but it does not automatically apply it.
The API is OFF by default to prevent unnecessary per-request AI spending.

## User experience

The authenticated, project-scoped route:
`/business-os/formulas/<project_slug>/`
shows the full read-only 20+6 proposal catalogue with missing-input
requirements. A link is available in Process Intelligence, following the
selected project. Only users with active READ permissions for that project
can open its view. No export of clients' source values and no user-facing
button to send material to an external model.

## Verification and release gates

```bash
python -m unittest ecoiq_os.test_formula_registry
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test ecoiq_os.tests_formula_designer core.tests_formula_studio \
  core.tests_process_workspace ecoiq_os.test_foundation_training --noinput
node --check static/js/process-workspace.js
```

Require an independent accountant/engineer for formula content, a data
contract per metric and an explicit human acceptance/versioning workflow
before making this an operational production scoring system. The
provisional AI suggestion adapter is **internal-only** and does not create
a new billing, cloud, tenant or religious authority.
