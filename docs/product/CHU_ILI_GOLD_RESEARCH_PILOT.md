# Gold Targeting / Qonaev–Chu–Ili pilot: source-backed research only

## What exists now
The `/gold-intelligence/targets/?pilot=chu_ili_qonaev` authenticated Folium map
shows a **user-defined research envelope** and sourced geographic orientation markers.
The separately served `/gold-intelligence/targets/pilot/research-queue.json`
returns three qualitative literature-investigation workstreams (not gold/grade/rights
probabilities). An unsigned/anonymous request cannot read the priority API.

The parallel source bibliography API at `/gold-intelligence/targets/pilot/named-deposits.json` lists **eight operator-reported existing gold deposits**: Akbakay, Beskempir, Karyernoye, Aksakal, Svetinskoye, Kenzhem from [Altynalmas (7 June 2022)](https://www.altynalmas.kz/blog/news/37); Shokpar and Gagarinskoye from [Tau-Ken Samruk](https://tks.kz/ru/investmentprojects/razvedka-zolota-na-mestorozhdeniyah-shokpar-i-gagarinskoe-v-zhambylskoj-oblasti/). These are cited *names*, **not geocoded mineral occurrence points**, and no Au grade, vacant land, drill coordinates, or current legal status is inferred.

No field evidence or historical MRDS points have been ingested into production
by this pull request. `GoldTarget` records, if any, remain separately sourced,
rights-tagged, access-controlled and subject to review.

## Literature and geographical anchors
- [Tau-Ken Samruk](https://tks.kz/ru/investmentprojects/razvedka-zolota-na-mestorozhdeniyah-shokpar-i-gagarinskoe-v-zhambylskoj-oblasti/)
  — describes Shokpar/Gagarinskoye *known* gold deposits. NOT an assertion that
  they are new or unlicensed targets.
- [Zhambyl Gold Reference](https://www.geokniga.org/bookfiles/geokniga-zhambylskaya-oblast-zoloto-spravochnik.pdf)
  — regional mining districts of the Chu-Ili belt. This document is not a
  georeferenced polygons file or current cadastral dataset.
- [NGA GeoNames Qonaev](https://geonames.nga.mil/geon-ags/rest/services/RESEARCH/GIS_OUTPUT/MapServer/0/query?outFields=%2A&where=ufi+%3D+-2342674)
  — geographical centre of the city, NOT a deposit.
- [Chu-Ili Range](https://en.wikipedia.org/wiki/Chu-Ili_Range)
  — approximate regional centre, NOT a drill coordinate.
- [E-Qazyna Minerals](https://minerals.e-qazyna.kz/ru/contracts-map)
  — official source for checking mining rights. No programmatic licence
  bulk data has been imported.

## Getting genuine historical USGS records
1. Merge this code only after full CI / peer review, and deploy the application.
2. On the repository's **Actions** tab, open **Kazakhstan Gold Historical Records (Review Only)**,
   select **Run workflow** (default bbox 74,42,80,46).
3. The workflow uses the already existing `fetch_usgs_mrds_gold` logic to download
   directly from the verified official USGS MRDS FeatureServer; it prepares a
   versioned, hashed evidence artifact and checks importer validation.
4. Download the GeoJSON+provenance artifact. Check data-use terms, record IDs,
   spatial accuracy, duplicates, geological relevance and actual localities.
5. An operator with approved database access may explicitly stage the checked
   file using `python manage.py import_gold_targets ... --apply --real-records --confirm-data-rights`.
   This leaves records **pending review and rights UNKNOWN**; independently review
   them in Django Admin. A source record is a historical reference, never proof
   of commercial mineralization, a resource, vacant land or drilling permission.

The GitHub workflow performs **no database writes and no deployment**. If USGS
cannot be reached or no records are found, the workflow fails transparently.
No synthetic results or silent sample coordinates are substituted.

## Follow-on geological assessment (not accomplished)
- Acquire licensed geology and geophysics map layers, validate positional
  uncertainties, original map scale and allowed redistribution.
- Cross-check gold occurrences against original geological reports, including
  field-sampling and assay credentials before defining drill targets.
- Obtain official, currently reviewed licensing and exclusion geometries via
  lawful channels. Historical screenshots do not establish free land.
- Use expert-validated normalized geological feature layers and spatially held-out
  model validation before constructing a true target prospectivity score.

## Tests
`python manage.py test gold_intelligence.tests_chu_ili_research gold_intelligence.tests_kazakhstan_references`
