# Twelve Governance Research Domains — internal catalogue v0.1

**Status: research-only. Not a religious ruling, legal opinion, Shariah compliance
certificate, verified Quran commentary, finance score, or approved formula.**

## Scope

The twelve fields requested for EcoIQ are now represented as immutable internal
Python metadata in `islamic_knowledge/governance_domains.py`. Every field has a
stable two-digit ID, a neutral operational English title, internal Russian
description, tagged Arabic vocabulary, two audit questions and *thematic*
Quran-locator hints checked against the existing Hafs index.

| ID | Internal research domain | English operational title |
| --- | --- | --- |
| 01 | Fair governance (adl, amanah, shura) | Fair Governance |
| 02 | Economy and capital (mal, rizq, qist) | Economy and Capital |
| 03 | Islamic finance (riba, gharar, zakat) | Finance Contract Integrity |
| 04 | Work and human dignity (haqq, ihsan, amanah) | Work and Human Dignity |
| 05 | Poverty and social wellbeing (maslaha, sadaqa, zakat) | Poverty and Social Wellbeing |
| 06 | Courts and dispute resolution (adl, bayyinah, insaf) | Courts and Dispute Resolution |
| 07 | Education and science (ilm, tabayyun, tafakkur) | Education and Science |
| 08 | Nature and resources (mizan, israf, fasad) | Nature and Resources |
| 09 | Family and future generations (rahma, haqq, masuliyya) | Family and Future Generations |
| 10 | Technology and AI ethics (amanah, adl, truthfulness) | Technology and AI Accountability |
| 11 | Consequences of public decisions (maslaha, fiqh al-maalat) | Public Decision Consequences |
| 12 | Moral responsibility (taqwa, muhasaba, hikmah) | Moral Accountability |

## Integration with current EcoIQ architecture

- Existing `islamic_knowledge.contracts.CONCEPTS` remain canonical for knowledge review. An unmapped tag is **not** silently added to that contract; `awaiting_contract_mapping` shows the gap.
- `QuranReference` locators are *navigation hints*, not authenticated verse texts or proof of a particular legal interpretation.
- `operational_domain_rows()` exposes a neutral **in-process** view with questions and `NOT_ASSESSED`; it does not publish an HTTP endpoint or include Arabic names or source locators.
- No KPI equation, 20-KPI result, review receipt, fake evidence, fatwa, legal compliance claim, permission or schema migration is created.
- The taxonomy does not replace `core/esg_principles_data.py` (114 operational principles) or `ethics/registry.py` (existing formulas). Those require deliberate separate crosswalks.
- Consumer applications must use trusted source/authentication and existing reviewer gates before promoting any source, interpretation or generated legal/finance guidance.

## Next incremental PRs

1. Scholar/editor review of each proposed locator and concept classification, with sources, schools of interpretation and provenance; retain differences of opinion.
2. Separate expert-reviewed mapping from domains to **existing** principle/metric IDs; no new score or automatic normative judgment.
3. An authenticated research interface only after access-control, publication language and sensitive-source tests.
4. A real evidence-backed pilot (e.g. procurement or fair finance) with project-scoped measurement records, error handling and human review.

## Test command

`python manage.py test islamic_knowledge.test_governance_domains`

This command is documented, not asserted as executed. Normal CI applies before merging.

## Research crosswalk to the 20 existing candidate KPIs

`islamic_knowledge/governance_kpi_crosswalk.py` links all twelve domain codes to existing keys in `ecoiq_os.formula_registry.FORMULAS_BY_KEY`; it does **not** clone or extend those formulas. All 20 existing candidates are referenced at least once. The links are contextual operational signals, not domain scores, proof of theological claims, verified source measurements, legal determinations or approved norms. The crosswalk has targeted tests in `islamic_knowledge/test_governance_kpi_crosswalk.py`. Any actual measurement needs a project-authorised provenance review and a validated observation-to-source binding.
