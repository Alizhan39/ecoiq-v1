# EcoIQ Foundation Training v1 — 20/33 KPI and 114-surah review boundary

**Scope:** Business Plan 2.0 operational foundation, no real-company data,
no published scores and no autonomous decisions.

This lab trains a *synthetic anomaly triage model*, NOT a Qur'anic model.
All outputs should remain in R&D until real, legally usable labels and
independent external validation exist.

## Existing capabilities kept canonical

- `ecoiq_os/kernel.py`: evidence-driven next-stage decisions.
- `ecoiq_os/flow.py`: Universal Flow Graph, observed flows and units.
- `mizan/system_balance.py`: non-compensable balance constraints, unknowns.
- `ecoiq_os/islah.py`: controlled hypotheses for change, not automatic implementation.
- `islamic_knowledge/catalog.py`: offline metadata of 114 surahs and a particular
  99-name inventory (pending scholarly review, not a consensus interpretation).
- `islamic_knowledge/contracts.py`: binding, rights, attribution and
  scholar-review receipts. All source-sensitive knowledge checks remain in
  this existing system.
- `ml/`: existing score prediction, anomaly and model-training pipeline.
  Stage foundation does not change production ML artefacts or training writes.

The new `foundation_catalog.py` provides a **versioned candidate catalogue**
of 33 operational questions across six categories (financial, resource,
environmental, social, justice, accountability). Twenty are flagged for
early Business Plan 2.0 experiments. This is a **provisional reconstruction**
of the intended 20/33 framework, not a claim to have recovered exact older
source definitions or to have created 33 real verified indicators.

Some examples use unit hints rather than validated formulae; they cannot
produce meaningful KPI values until an authorised owner specifies numerator,
denominator, legal basis, reporting boundary, period, source and QA/QC.

## Mizan, Amanah, Adl, Islah, Israf and Fasad

The six keys are metadata for analyst **questions**, not automatic moral
judgments or tafsir. The default relationship is "may help ask this question".
A high recorded material-loss ratio alone does not prove avoidable waste,
responsibility, injustice, corruption or serious harm.

- Mizan: balance and trade-offs, never one blended moral score.
- Amanah: responsibility, measurement ownership, trustworthy audit.
- Adl: distribution of benefits and burdens, not accusations from one ratio.
- Islah: corrective proposals that must pass the causal and human gates.
- Israf: possible waste requiring corroborated measurement and counterfactual.
- Fasad: investigate systemic mechanisms, do not impute moral guilt.

## 33 × 114 matrix: 3,762 **review requests**, NOT 3,762 meanings

`foundation_catalog.review_queue_page` enumerates every possible KPI/surah
pair with `UNREVIEWED`. Every item has:
`verse_locator=None`, `interpretation=None`, `source_record_id=None`,
`scholarly_receipt=None`, `approved_for_training=False`.

Only a qualified scholarly/domain review process linked to the existing
`islamic_knowledge.contracts` and licensed text can later propose a
particular KPI-source connection. An unsigned catalogue or generated
cross-product is not religious evidence or a 0–100 Shariah score.
99 Names inventory is used for counting/identity validation only,
not as ML labels.

## Synthetic operational training task

`ecoiq_os/foundation_training.py` simulates 14 existing EcoIQ sectors
(`DOMAINS`), site-level latent risk, three time slices and 33 synthetic
0..1 *risk-signal channels*. **These are artificial normalized signals, not
real quantities in kg, kWh, tonnes CO2e, salary or water litres.**
Unknown observations are NaN and get a missingness indicator; zero stays
measured zero. No imputation into an imaginary company score.

Two research models use RandomForestClassifier:
1. 20 initial KPI signal channels;
2. all 33 signal channels.

Comparison includes a DummyClassifier majority baseline, 25% held-out
**sites** with no site crossing train/test, and a separate **construction
domain holdout** (no construction projects in training).

The target is an artificially simulated process-alert event. Training
optimises only a demonstration of handling noisy, partially missing inputs;
it cannot establish that any observed KPI truly warrants an intervention.

Model artefacts are NOT saved or deployed. Code does not read the production
database, call an LLM, mutate data, run a cloud trainer, or bypass the
existing Stage 6/7 source and human-approval gates.

## Reproduce using pinned development dependencies

```bash
python -m unittest ecoiq_os.test_foundation_training
python -m ecoiq_os.foundation_training
python manage.py test ecoiq_os.test_kernel ecoiq_os.test_knowledge --noinput
```

CI also runs the first two commands on Python 3.11.16. The module prints
input hash, seed, sample count, domain coverage, balanced accuracy, recall
and confusion matrices for both models and their baselines. **Those
percentages measure synthetic agreement only, not customer outcomes**.

## Milestones before business deployment

1. Customer interviews: confirm the real Business Plan 2.0 list of 20 KPI
   owners/formulae and whether the 33 KPI expansion is useful.
2. Data dictionary per metric: unit, frequency, system boundary, source,
   missingness, tolerance, uncertainty, stakeholder and objective.
3. Independent labels, project-separated and time-forward validation with
   legally permitted business data, fairness analysis and adversarial testing.
4. Establish accepted false-positive and missed-incident operating
   tolerances; monitor drift and retraining governance.
5. Source-rights/tafsir review before any scripture-derived training.
6. Human-review integration and Mizan hard constraints are required for any
   consequential workflow, separate from predictive metrics.

Until then the foundation is a reproducible research skeleton only.
