# EcoIQ Gold Intelligence — source rights and first real time series
**Research snapshot:** 20 October 2026 · **Version:** 1 · **Status:** Proposed PR, NOT deployed.

## Findings on data rights

| Source | Primary legal/rights evidence | Allowed within EcoIQ | NOT yet allowed |
| --- | --- | --- | --- |
| Kazakhstan Bureau of National Statistics (BNS) | https://stat.gov.kz/description/ and https://sdg.stat.gov.kz/en: published **official statistical information** may be copied, adapted, redistributed with attribution and used in software for any purpose | Open, aggregate national indicators, with source/date/region/unit/method/attribution; site is not a mine-level SCADA stream | Confidential original company responses; third-party restricted layers; automated feed without validating dataset-specific API/rate limits |
| World Bank Commodity Price Data (Pink Sheet) | https://datacatalog.worldbank.org/search/dataset/0038238/commodity-prices-history-and-projections and https://www.worldbank.org/ext/en/legal/terms-conditions/datasets: **CC BY 4.0** with World Bank supplementary terms | Monthly global gold market price reference (with attribution and changes indicated) | Claim that this market price measures ore processing, equipment telemetry or Kazakhstan mine performance |
| Solidcore investor production releases | Public press releases (links attached to every observation), but **no explicit licence for automated commercial extraction/bulk redistribution verified** | Limited, cited factual comparisons within this restricted research view; operator reported, not audited by EcoIQ | Commercial wholesale datasets, live scraper/API, reselling underlying tables or constructing site dashboards on protected operator data without permission |
| Kazakhstan mine SCADA/MES/drill/lab/fleet data | Not public. Rights depend on operator, supplier, lab and agreement | None ingested | All ingestion, modelling, onward sharing and commercial use until explicit owner permission, legal basis, NDA, security controls |

**Rights-status register:** `gold_intelligence/reference_data/source_rights_register_2026-10.json`. This is a preliminary permission assessment, not legal advice. Explicitly record the specific publisher's consent and terms before upgrading status.

## First connected observations (real history, not invented)

`gold_intelligence/reference_data/first_gold_time_series_2026-10.json`
contains four typed series with one publication URL per quarter:

| Series | Frequency | From | To | n | Unit |
| --- | --- | --- | --- | ---: | --- |
| Solidcore Kyzyl recovered gold in concentrate | Quarterly | 2025 Q1 | 2026 Q2 | 6 | thousand gold oz IN CONCENTRATE |
| Solidcore Kyzyl final payable gold-equivalent production | Quarterly | 2025 Q1 | 2026 Q2 | 6 | thousand GE oz PAYABLE |
| Solidcore Varvara Hub final metal output | Quarterly | 2025 Q1 | 2026 Q2 | 6 | thousand GE oz PAYABLE; includes feed from Komar/other locations |
| World Bank Gold Pink Sheet monthly global average price | Monthly | January 2026 | September 2026 | 9 | USD per troy ounce |

**27 observed points** in total: 18 site/hub reported quarters + 9 licensed monthly
global commodity-market observations. Values are explicit historical observations,
not estimated gaps or synthetic interpolations. Market price data have been
transcribed using public mirrors of the World Bank Gold Pink Sheet, and the
numeric series **has not yet been verified against the source XLSX bytes**,
which are linked but weren't downloadable in this working environment.
Therefore the global gold-price points must remain excluded from investment
and automated financial models until direct original reconciliation.

For Solidcore, production stage **must remain part of each series identity**:
- Mine recovered gold in concentrate is *not* the same as payable gold equivalent
  production following third-party toll processing.
- Different production and sale quarters, inventories, loss factors and offsite
  treatment terms prevent subtracting these two series as if they were losses.
- 2025 Q3 operator disclosures have a rounding caveat; sums of separately
  rounded site-level figures may differ from a consolidated number.
- 2025 Q1–2026 Q2 are historical public reports, **not** up-to-date hourly or
  current-month mine telemetry.
- No series is imported into `MineKPIObservation` or the geodata evidence
  layer; public reports do not fulfill the documented site-specific
  numerator/denominator, certificate and internal-review requirements.

## Source releases and observation verification

- Kyzyl/Varvara Q1 2025: https://www.solidcore-resources.com/en/investors-and-media/news/press-releases/28-04-2025/
- Q2 2025: https://www.solidcore-resources.com/ru/investors-and-media/news/press-releases/31-07-2025/
- Q3 2025: https://www.solidcore-resources.com/en/investors-and-media/news/press-releases/31-10-2025/
- Q4 2025: https://www.solidcore-resources.com/ru/investors-and-media/news/press-releases/30-01-2026/
- Q1 2026: https://www.solidcore-resources.com/en/investors-and-media/news/press-releases/30-04-2026/
- Q2 2026: https://www.solidcore-resources.com/ru/investors-and-media/news/press-releases/31-07-2026/
- World Bank Commodity Markets direct linked historical monthly XLSX:
  https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx
- Cross-check display (secondary, not licence provider): https://app.indexbox.io/indicators/symbol/pink-sheet-gold-world/

## Integration

`gold_intelligence/services/source_time_series.py` validates:
- non-duplicated, chronologically ordered historical periods, correct quarter
  boundaries, original publication date after quarter end;
- asset scope and unique stage/metric/unit bindings;
- finite real values; no invented missing periods;
- each quarter tied to its official original release URL;
- rights evidence must match the **exact source type**;
- no commercial dataset clearance for operator-reported quarters, even if
  some observations have public links;
- secondary-transcribed global prices are not yet originally verified.

Authenticated read-only page `/gold-intelligence/public-time-series/`.
This is not a downloader, polling data connector or public paid data service.
It shows the legal status and original release link for every observation.

Code refuses to upgrade data to a financial or ML feed:
- Solidcore: `OPERATOR_PERMISSION_PENDING`.
- World Bank price: `ORIGINAL_PRICE_WORKBOOK_RECONCILIATION_REQUIRED`.
- All: `automated_operational_ingestion_enabled=False`;
  `optimisation_outcome_claim_allowed=False`.

## Next concrete steps for a production-grade feed

1. **Solidcore written approval:** email `ir@solidcore-resources.com` to request
   reuse/automated extraction/API rights for quarterly datapacks, allowed
   attribution and public-facing vs client-side sharing. No email has been
   sent.
2. **World Bank XLSX verification:** download original historical monthly
   series in an authorised execution environment, verify the Gold USD/troy oz
   monthly 2026 dates/values, record original file SHA-256, the source row/column
   and import script version, and mark each verified only after full reconciliation.
3. **Kazakhstan official aggregate production feed:** obtain/inspect a machine
   readable BNS industrial gold-production series with classification SKPP,
   geographic scope, observations and release dates before creating new
   national monthly values. BNS `151102` is **aggregate product-level**
   data, not individual mine production; avoid fabrication.
4. **Paid mine pilot:** operator-signed DPA/NDA/data-use agreement, read-only
   secure export for one line (plant throughput, recovery, power, downtime),
   sensor quality rules, timezone/clock-sync, same-period numerator/denominator,
   data-retention/access policies, professional metallurgist and qualified
   safety/environmental review, intervention baseline with causal comparison.

## Example real finding — no false optimisation claim

Solidcore's own reports show Kyzyl quarterly concentrate metal output and
payable output do not evolve together during H1 2025 and H1 2026. The operator
has discussed third-party POX processing and shipment timing constraints. This
supports a **working-capital and processing-slot scenario hypothesis**, NOT
an inferred gold loss, higher ore recovery or savings.

Pilot success requires permissioned weekly/day-level production, inventory,
delivery and toll-refining schedules plus actual costs, and independent
confirmation of a model's prediction against a held-out future period.
No model has been trained or plant control system altered by this PR.

## Testing and rollout

`python manage.py test gold_intelligence.tests_source_time_series`
`python manage.py check`
`python manage.py makemigrations --check --dry-run`

No database migration. No new endpoint for private data. Review security,
licence notes and factual source values before merging; deploy only after
green CI and human approval.
