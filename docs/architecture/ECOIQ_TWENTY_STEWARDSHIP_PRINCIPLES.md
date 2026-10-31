# EcoIQ — 20 Environmental Stewardship Principles (draft v1)

This module expands the **existing** EcoIQ Qur'an/Maqasid-inspired knowledge
service. **It does not replace the EcoIQ OS, Mizan, industrial KPI methods,
causal-evidence lifecycle, rights/permission system or human review gates.**

## Religious-source boundary

These 20 are NOT a list of 20 literal Quranic commandments about
environmental reporting. The list mixes:
- Quranic concepts or locators interpreted for ecological stewardship;
- documented Sunnah and historic social practices;
- fiqh/usul legal reasoning and juristic maxims;
- modern EcoIQ-authored practical questions.

**Qur'an text ≠ translation ≠ tafsir ≠ hadith ≠ fiqh opinion ≠ EcoIQ KPI.**
The source hints are *locators only*: exact licensed passages, authentication,
scholarly interpretation, legal jurisdiction and independent approval remain
missing. Do not publish an environmental or religious compliance score from
them. All `PrincipleDefinition` objects have `source_ids=()` and therefore
cannot pass the existing `assess_definition` gate without real, authorised
source and scholarly-review receipts.

`islamic_knowledge/environmental_principles.py` holds 20 frozen,
versioned draft lenses in the exact user-requested order. Existing Mizan,
Khalifah, Islah, Amanah, Fasad and Israf definitions are **reused** from
`islamic_knowledge/principles.py` (no second canonical definitions).
Fourteen new concept keys extend the existing knowledge contract.

## Registry and mining crosswalk

| # | Concept | Source family | Suggested text/locator | Mining inquiry / indicator |
| --- | --- | --- | --- | --- |
| 1 | Mizan ميزان | Quran | 55:7–9 | Balanced resource, water, energy, tailings and worker outcomes, no single score |
| 2 | Khalifah خليفة | Quran | 2:30; 6:165 | Responsibility and site/beneficiary stewardship |
| 3 | Imarat al-Ard عمارة الأرض | Quran *interpretation* | 11:61 | Enduring public value, careful land management |
| 4 | Islah إصلاح | Quran | 11:88; 7:56 | Evidence-backed ecological restoration |
| 5 | Amanah أمانة | Quran | 4:58 | Accountable obligations, evidence chain, independent oversight |
| 6 | Fasad fil-Ard فساد في الأرض | Quran | 30:41 | Documented harm mechanisms, not moral accusations from a statistic |
| 7 | Israf إسراف | Quran | 7:31 | Unnecessary resource waste and loss |
| 8 | Tabdhir تبذير | Quran | 17:26–27 | Avoidable spending/waste; high CAPEX alone is not proof of waste |
| 9 | Iqtisad اقتصاد | Quran, contextual application | 25:67 | Proportionality; not a divine numerical discount rate |
| 10 | Tayyib طيب | Quran, contextual application | 2:168; 5:88 | Quality and safety; food verses do not certify mining products |
| 11 | Hima حمى | Hadith/historical practice | Sahih al-Bukhari 2370 | Protected-area and land-use rights |
| 12 | Harim حريم | Classical fiqh | Protective rights around wells and water | Legal buffers require local law and hydrology |
| 13 | Ihya al-Mawat إحياء الموات | Hadith/historical jurisprudence | Muwatta Malik Book 36 | Restoring land while respecting licensed land tenure |
| 14 | Ghars al-Ashjar غرس الأشجار | Hadith | Sahih al-Bukhari 2320 | Native planting survival (no direct gold KPI yet) |
| 15 | Rifq bil-Hayawan الرفق بالحيوان | Quran/Sunnah | 6:38; Sahih al-Bukhari 2363 | Wildlife and habitat impacts (data gap) |
| 16 | Hifz al-Ma حفظ الماء | EcoIQ application of general Quranic principles | 21:30 | Water footprint and recirculation (not a Quranic m³/t threshold) |
| 17 | La Darar wa La Dirar لا ضرر ولا ضرار | Hadith / legal maxim | Nawawi Forty 32 | Prevent verified harm; narrations and grades require review |
| 18 | Maslahah مصلحة | Usul al-fiqh | Public-interest jurisprudence | Distributed benefit, not a one-number social score |
| 19 | Dar al-Mafasid درء المفاسد | Fiqh maxim | Preventing harms | Avoidance/mitigation and legal constraints |
| 20 | Sadaqah Jariyah صدقة جارية | Hadith | Sahih Muslim 1631 | Durable, separately evidenced charitable outcomes |

**Source caution:** Imam Nawawi's Hadith 32 presents the no-harm maxim as
hasan with reinforcing chains; individual Ibn Majah 2340–2341 chains are
graded differently by specific classifiers. Do not flatten conflicting
authentication into one unquestioned source.

Some concepts (Harim, Maslahah, Dar al-Mafasid) have no simple one-verse
source equivalent. Environmental applications and thresholds are human
interpretations requiring subject experts and appropriate legal authority.

## Implementation and access

- `islamic_knowledge/environmental_principles.py`: provenance-aware
  **draft catalogue** and reuse of existing six canonical definitions.
- `gold_intelligence/services/stewardship_lenses.py`: a static
  twenty-row mapping to the **nine existing gold operational KPI definitions**
  from PR #350. A mapped observation is only a partial proxy: linked
  data can be measured and internally reviewed without proving adherence
  to a principle.
- `gold_intelligence/views.py` and the Gold Investor View: authenticated
  `/gold-intelligence/<slug>/stewardship/` page. Uses the existing
  `projects_for(request.user)` membership control; no public source records.
- No DB migration; no numerical scoring weights, religious verdict, or
  automatic Shariah approval; no AI model training. Full user-provided
  list remains available for non-mining industries via knowledge module.

The project-specific page shows both **available observations** and
**missing indicator coverage**. For seven concepts (including Hima, Harim,
Tayyib and Sadaqah Jariyah), no one of the current nine gold KPIs is
a defensible direct proxy. The absence is explicit rather than scored 0.

## External reference entry points (locator links only)

- Quran references: https://quran.com/55/7-9 ; https://quran.com/11/61
- Protected pasture: https://sunnah.com/bukhari:2370
- Tree planting: https://sunnah.com/bukhari:2320
- Animal kindness: https://sunnah.com/bukhari:2363
- No-harm maxim: https://sunnah.com/nawawi40:32
- Ihya al-Mawat tradition: https://sunnah.com/malik/36
- Sadaqah jariyah: https://sunnah.com/muslim:1631

These are navigation aids, not a licensed/reviewed tafsir corpus.

## Next verification gates

1. Qualified Shariah reviewers annotate translations/tafsir, hadith grades,
   fiqh differences, applicable scopes and register signed/versioned approval.
2. Environmental scientists/geologists establish mine-specific legal limits,
   baseline periods, adverse-impact thresholds and independent data sources.
3. For each indicator record time span, unit, uncertainty, issuer,
   evidence, measurement boundary, responsible party and QA/QC.
4. Add site-specific indicators for freshwater basin stress, protected
   territory overlap, riparian setback compliance, native vegetation survival,
   wildlife impacts and independently measured community benefit.
5. Causal review and human decision precede any critical mine-site action.

**Test commands:** `python manage.py test islamic_knowledge.test_environmental_principles`;
`python manage.py test gold_intelligence.tests_geological_kpis`;
`python manage.py check`. Observe CI before merging either stacked PR.
