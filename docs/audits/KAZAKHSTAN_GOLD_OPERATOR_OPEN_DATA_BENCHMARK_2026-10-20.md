# Kazakhstan Gold Operations — public benchmarking pilot (20 October 2026)

## Purpose and scope

This is a **non-exhaustive historical public-source catalogue**, prepared as
a potential EcoIQ demonstration without claiming access to operators' private
SCADA, drilling, assays, mine plans, contract prices or mineral titles. It is
**not** a dataset of all gold mines currently producing as of October 2026;
2025 mine-level operating statements are not real-time evidence of 2026 output.

- 15 publicly reported operating mines, mining deposits or complexes
  (these are not all separate processing plants; Varvara Hub also receives
  ore from Komar, and other groups similarly move feed among assets).
- 24 site/circuit-level public observations, plus **7 company/group-level
  observations deliberately kept separate** to prevent wrong allocation.
- Eight testable process-modernisation hypotheses, not audits or predictions.
- Original citations preserved in
  `gold_intelligence/reference_data/kazakhstan_gold_public_seed_2026.json`.
- Read-only, logged-in explorer:
  `/gold-intelligence/public-benchmarks/`.
- No automatic importing into `MineKPIObservation`. Existing measurements
  require site-specific period-matched numerator/denominator and internal
  review before publication. Annual reports alone cannot certify the new
  engineering KPI methods.
- No resource/reserve calculation, no drone/satellite inference of gold, no
  claim an operator is performing poorly without baseline and site access.
- This module implements **no additional mining licence map**. Link the
  official Minerals e-Qazyna map, and verify rights/use terms before GIS reuse.

## Published operators / sites represented

| Reporting group | Mine / complex | 2025 public disclosures |
| --- | --- | --- |
| Solidcore | Kyzyl (Bakyrchik) | 2.470 Mt ore processed; 4.9 g Au/t feed; 88.9% flotation Au recovery, 347 Koz gold in concentrate and 234 Koz GE payable production. Metal at different stages, not comparable as a loss calculation. |
| Solidcore | Varvara Hub; Komar ore mine | Varvara's leach circuit: 3.396 Mt, 90.0% recovery; flotation circuit: 0.657 Mt, 88.8%; do NOT assign hub output to Varvara mine alone. |
| AK Altynalmas group | Pustynnoye, Dolinnoye, Baktai | Pustynnoye recovery 83%; Dolinnoye 86%; Baktai 411.3 kt mined but no Baktai-only plant output shown. |
| AK Altynalmas group | Akbakai | Reported gold recovery 80%, recovery comparable only on consistent mineralogy and stage. |
| AK Altynalmas / Kazakhaltyn | Aksu-2 / Oktyabrskyi-2, Quartz Hills, Zholymbet, Bestobe | 2025 mining and operating complexes; Aksu2 90%, Quartz Hills 88%, Zholymbet heap-leach 81%; Bestobe mined 128.5 kt, not automatically same as Bestobe processed feed. |
| Maikainzoloto (group) | Maikain | 2025 Au recovery 77%, grade 1.76 g/t. |
| Zijin RG Gold | Raygorodok (North + South) | 2025 reported Au produced 1.2 tonnes on 100%-project basis. New plant under construction, and 2025 tender to modernise leaching tanks. |
| Glencore / Kazzinc | Vasilkovskoye / Altyntau Kokshetau | Operating gold open pit; reported group-level Kazzinc gold 543 Koz **must not** be assigned to one gold mine. |
| AltynGold | Sekisovskoye | 2025 gold production 53.8 Koz, existing underground mine/plant. |
| Excluded from producing list | Teren-Sai; Ertis POX; Syrymbet | Teren-Sai exploration/permitting; Ertis POX downstream construction; Syrymbet tin development. |

**Disclosure caveats:**

1. Mine *metal in concentrate* is not end-product *payable gold equivalent*
   in the same month; logistics, processing time and metallurgical payability
   matter. Never compute direct resource recovery or production loss by
   subtracting these.
2. Gold and gold-equivalent (GE) ounces are distinct units. Group disclosures
   are not mine-level KPIs. Different flowsheets and mineralogy make raw
   recovery percentages non-comparable between mines.
3. AK Altynalmas 2025 report was read via a **filing mirror** and must be
   checked against the actual filed source before external publication.
   No long copyrighted source text or report binary is copied here.
4. The site and publisher's data licence requires review before an automated
   bulk importer, periodic scraping or redistribution. Public visibility
   does not necessarily authorise unrestricted reuse.

## Priority hypotheses, not proven weak processes

### Solidcore Kyzyl (priority research, known constraint)

- **Published evidence:** 2025 delays in third-party concentrate POX
  processing. H1 2026 disruptions linked to downstream shipments.
- **Already underway by operator:** Ertis POX construction and an October 2026
  Oman/Kazakhstan AI exploration collaboration. Solar/power and mine
  electrification initiatives are also disclosed; do not pitch these as if
  Solidcore has no automation.
- **EcoIQ pilot:** process-contract capacity modelling, inventory cohorts,
  concentration/shipment risk, payment lag, dry-port/rail route
  constraints. Need weekly inventory, toll-processing schedules, assay
  payability and costs. Test scenario by replaying disruptions and showing
  actual avoided holding costs — currently unknown.
- **Measured outcome:** shipped/payable conversion lag, concentrate inventory
  days, missed refining slots, handling cost and working capital, with
  separate gold/gold-equivalent units and safety constraints.

### Akbakai, Maikain (recovery investigation)

- **Published observations:** 80% and 77% Au recoveries respectively
  (2025). Neither alone proves a defective plant.
- **Pilot:** metallurgical variability clustering with expert ore-domain
  labels; measure losses in tailings and plant availability. Controlled
  lab/plant trials may test recovery interventions and estimate OPEX/CAPEX.
  No cross-mine recovery "league table" as evidence of inefficiency.
- **Sensitivity, not a prediction:** for Kyzyl 2025 2.47 Mt feed and 4.9 g/t,
  +1 absolute percentage point of recovery gives
  121,030 g ≈ 3,891 troy oz additional Au *to the specified stage* if
  technically achievable. This does not establish capability, refined
  ounces, revenue or profit.

### Raygorodok (public procurement use-case)

- **Published evidence:** a December 2025 technical specification for
  leaching-tank refurbishment and September 2026 announcement of a new
  processing plant. Expansion is operator-led.
- **EcoIQ pilot:** mass-balance evidence dashboard, engineering design-change
  provenance, residence-time sensitivity, maintenance and commissioning
  KPI acceptance tests. Any process changes require qualified metallurgists.

### Vasilkovskoye and Sekisovskoye (planning)

- Kazzinc says Vasilkovskoye open pit depth and expected head grade affected
  gold production: test grade control and haulage/strip/underground transition
  scenarios, not guessed ore reserves.
- Sekisovskoye may expand 1 Mtpa -> 2 Mtpa: evaluate fleet dispatch,
  mine ventilation energy/constraints and future plant/bottleneck utilisation
  **against the actual mine plan**, not fabricated timings.

## What EcoIQ should do in sequence

**Phase 1 — research readiness (now):**
store source ID/title/URL/date, operator, mine/hub scope, year, units,
observation, data-licence terms, and link to proposed measurable process test.
Flag missing or disputed items and prevent double counting.

**Phase 2 — source verification:**
download files into authorised secure storage, verify SHA-256, obtain
licence/legal reuse permissions, extraction controls and reviewer sign-off,
and update 2026 operating status based on current official disclosures and
Minerals e-Qazyna.

**Phase 3 — optional confidential operator pilot (paid):**
NDA, data rights, named mine process owner, read-only ingest (SCADA historian,
fleet dispatch, plant mass-balance, assay lab, water/energy sensors),
data quality tests, KPI review then causal validation/small intervention.

**Phase 4 — monetisation via Stoke Share Ltd / EcoIQ:**
sell an accurately scoped diagnostic and reproducible model before offering
performance optimisation. First commercial milestone: one named site and one
agreed workstream, with baseline, approval, safety/regulatory gates and
a written acceptance test. If the data remain unavailable, deliver only
a source-linked opportunity study, not a claimed process-efficiency gain.

## Sources (primary preferred)

- Solidcore 2025 integrated report:
  https://www.solidcore-resources.com/upload/files/Solidcore_integrated_report_2025_eng.pdf
- Solidcore H1 2026:
  https://www.solidcore-resources.com/en/investors-and-media/reports-and-results/latest-results/
- Solidcore Q2 2026:
  https://www.solidcore-resources.com/ru/investors-and-media/news/press-releases/31-07-2026/
- Solidcore AI exploration centre, 6 Oct 2026:
  https://www.solidcore-resources.com/en/investors-and-media/news/press-releases/06-10-2026-1/
- AK Altynalmas 2025 filing mirror:
  https://financialfilings.com/filings/ak-altynalmas-jsc/annual-report/2026/63719309/
- Zijin Raygorodok:
  https://www.zijinmining.com/global/program-detail-72040.htm
- Glencore 2025 resources/reserves:
  https://www.glencore.com/.rest/api/v1/documents/static/a17cc44b-7947-4169-9b6b-b882403fb42b/GLENCORE-Resources-and-Reserves-report-2025.pdf
- AltynGold:
  https://altyngold.uk/operations/current-operations/
- Kazakhstan cadastre: https://minerals.e-qazyna.kz/ru/contracts-map

## Code and review

- Data fixture: `gold_intelligence/reference_data/kazakhstan_gold_public_seed_2026.json`
- Validation and scenarios: `gold_intelligence/services/public_operator_benchmarks.py`
- User interface: `/gold-intelligence/public-benchmarks/`
- Contract/access tests: `python manage.py test gold_intelligence.tests_public_operator_benchmarks`

Do not make a live claim or merge source ingestion until legal, rights,
independent domain-methodology and operator-permission review.
