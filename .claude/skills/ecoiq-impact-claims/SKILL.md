---
name: ecoiq-impact-claims
description: Gate for any environmental, social, or financial impact claim shown to a user — emissions avoided, water saved, waste diverted, energy reduced, cost saved, lives improved, or a green/sustainable/net-zero label. Use when writing, generating, or reviewing such a claim in a page, report, PDF, badge, or marketing copy. Not for raw internal metrics that are never surfaced as an achievement.
---

# Impact claims

An impact claim asserts that something got **better because of an
intervention**. A number alone is not a claim; a number plus attribution is.
"CO₂e: 41,200 t" is a metric. "Reduced CO₂e by 12%" is a claim and needs the
full chain below.

## The six-link chain — all six or no claim

| Link | Must be |
|---|---|
| 1. Source evidence | A real evidence row (`harvester` / `hikma` / `league` / `EvidenceMemory`) with a source and a date. Not an LLM paraphrase. |
| 2. Metric | Named, with units and a defined boundary (Scope 1/2/3, site vs group, gross vs net). |
| 3. Baseline | A stated period and value the change is measured *from*. No baseline → no percentage. |
| 4. Intervention | The specific action credited. If several things changed, attribution is uncertain — say so. |
| 5. Result | Measured, with the same boundary as the baseline. Modelled results are labelled `model-estimate`. |
| 6. Verification | Who checked, when, and to what standard. `unverified` is an allowed value; an empty field is not. |

## Reject these outright

- **Unbaselined percentages.** "40% greener" with no baseline period.
- **Boundary switching.** Baseline Scope 1+2, result Scope 1 only.
- **Model output presented as measurement.** If it came from
  `pandas_scoring_engine` or an LLM, it is an estimate, and
  `hikma.Evidence.confidence_tier` must read `model-estimate`.
- **Integrity hash as proof of truth.** `EvidenceMemory.integrity_reference`
  is a SHA-256 of the stored text. It is not blockchain, not immutability,
  not proof the source document is genuine. The model docstring says this
  explicitly — never let UI or marketing copy imply otherwise.
- **Undated claims.** A result with no `date_collected` / period.
- **Qur'anic or Arabic framing on a public surface.** See below.
- **Absolute green labels** — "sustainable", "net zero", "clean" — without a
  standard named and a boundary stated.

## Governance overlay (public vs internal)

[`docs/governance-principles-surah-map.md`](../../../docs/governance-principles-surah-map.md)
is marked **INTERNAL ONLY**: no Surah names, Arabic terminology, or Qur'anic
references may appear in public-facing code, API responses, or marketing.
Public copy uses the professional English principle titles from that mapping
(e.g. principle 114 is surfaced as *Consumer Protection & Anti-Manipulation*).
That rule binds impact claims and growth copy alike.

## Uncertainty is a feature

`EvidenceMemory.confidence` is nullable on purpose and stays null until a
real value exists. Never populate it with a plausible default to make a
badge look confident. Where confidence is low, the claim is shown with its
uncertainty, or it is not shown.

## Where claims already surface

`companies/investment_report.py`, `companies/embed_views.py` (public badges),
`audit/` report generation, `certification_trust_badge_engine/`. A badge is
the highest-risk surface: it is embedded on third-party sites, stripped of
context, and read as certification.

## Done when

- All six links present, each traceable to a real record.
- Estimates labelled as estimates; verification state honest.
- No prohibited terminology on a public surface.
- `ecoiq-release-gate` run for the app that renders the claim.
