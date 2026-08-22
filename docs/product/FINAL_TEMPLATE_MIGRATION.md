# Final Template Migration — Route Inventory

Every anonymously-reachable server-rendered HTML route at `776ffaa`, classified. **102 routes, 102 classified, no gaps** — asserted, not asserted-to.

Classification used three measured signals, not the route name: whether the page is linked from any public entry point, whether it is in the sitemap, and what `platform_registry/agents.py` says about the module behind it.

The result was blunt. **67 of the 102 were reachable only by typing the URL** — linked from no public page and absent from the sitemap. Measured against every public entry point the site has, not estimated. Existence was not usefulness.

---

## Summary

| class | | routes |
|---|---|---|
| **A** | PUBLIC PRODUCT — MUST MIGRATE | 1 |
| **B** | PUBLIC MARKETING — MIGRATE OR CONSOLIDATE | 29 |
| **C** | COMPANY DATA SURFACE — PARITY REQUIRED | 6 |
| **D** | ECOIQ LABS / EXPERIMENTAL — MOVE TO LABS OR RESTRICT | 29 |
| **E** | LEGACY — DELETE/REDIRECT | 23 |
| **F** | DUPLICATE — CONSOLIDATE | 2 |
| **I** | AUTH FLOW — KEEP DJANGO IF INTENTIONAL | 12 |
| | **total** | **102** |

| action | routes |
|---|---|
| AUTHENTICATE | 58 |
| KEEP DJANGO (documented) | 32 |
| REDIRECT 301 | 11 |
| MIGRATE (Phase 3) | 1 |

---

## A. PUBLIC PRODUCT — MUST MIGRATE

| route | view | template | React replacement | action |
|---|---|---|---|---|
| `/companies/` | `companies.directory` | `companies/directory.html` | /companies (React) | MIGRATE (Phase 3) |

**/companies/** — The public company directory. 822 kB uncompressed for 467 cards. Containment already holds — every card reads "Evidence assessment pending" — so this is a weight and consistency migration, not a truthfulness one.

---

## B. PUBLIC MARKETING — MIGRATE OR CONSOLIDATE

| route | view | template | React replacement | action |
|---|---|---|---|---|
| `/api-docs/` | `core.api_docs` | `api/docs.html` | — | KEEP DJANGO (documented) |
| `/ar/gcc-investors/` | `gcc_investors.gcc_hub_ar` | `—` | — | KEEP DJANGO (documented) |
| `/ar/kw/investors/` | `gcc_investors.kuwait_investors_ar` | `—` | — | KEEP DJANGO (documented) |
| `/ar/qa/investors/` | `gcc_investors.qatar_investors_ar` | `—` | — | KEEP DJANGO (documented) |
| `/ar/sa/investors/` | `gcc_investors.saudi_investors_ar` | `—` | — | KEEP DJANGO (documented) |
| `/ethical-governance/` | `core.ethical_governance` | `ethical_governance.html` | — | KEEP DJANGO (documented) |
| `/gcc-investors/` | `gcc_investors.gcc_hub_en` | `—` | — | KEEP DJANGO (documented) |
| `/global-intelligence/` | `core.global_intelligence` | `global_intelligence.html` | /intelligence | REDIRECT 301 |
| `/governance-principles/` | `core.governance_principles` | `governance_principles.html` | — | KEEP DJANGO (documented) |
| `/heating/` | `heating.overview` | `heating/overview.html` | — | KEEP DJANGO (documented) |
| `/heating/calculator/` | `heating.calculator` | `heating/calculator.html` | — | KEEP DJANGO (documented) |
| `/heating/company-sponsorship/` | `heating.company_sponsorship` | `heating/company_sponsorship.html` | — | KEEP DJANGO (documented) |
| `/heating/packages/` | `heating.packages` | `heating/packages.html` | — | KEEP DJANGO (documented) |
| `/heating/pilot-application/` | `heating.pilot_application` | `heating/pilot_application.html` | — | KEEP DJANGO (documented) |
| `/investors/` | `core.investors` | `investors.html` | — | KEEP DJANGO (documented) |
| `/kazakhstan-map/` | `core.kazakhstan_map` | `kazakhstan_map.html` | /intelligence | REDIRECT 301 |
| `/kazakhstan-transition-brief/` | `core.kazakhstan_transition_brief` | `kazakhstan_transition_brief.html` | /intelligence | REDIRECT 301 |
| `/khalifa-impact/` | `core.khalifa_impact` | `khalifa_impact.html` | /intelligence | REDIRECT 301 |
| `/khalifa-tours/` | `core.khalifa_stewardship_tours` | `khalifa_stewardship_tours.html` | — | KEEP DJANGO (documented) |
| `/kuwait/investors/` | `gcc_investors.kuwait_investors_en` | `—` | — | KEEP DJANGO (documented) |
| `/methodology/` | `core.methodology` | `methodology.html` | /trust | REDIRECT 301 |
| `/platform/` | `core.platform` | `platform.html` | /about | REDIRECT 301 |
| `/press/` | `core.press` | `press.html` | — | KEEP DJANGO (documented) |
| `/products/` | `ecoiq_commerce.products` | `ecoiq_commerce/products.html` | — | AUTHENTICATE |
| `/qatar/investors/` | `gcc_investors.qatar_investors_en` | `—` | — | KEEP DJANGO (documented) |
| `/sample-report/` | `core.sample_report` | `sample_report.html` | /intelligence | REDIRECT 301 |
| `/saudi-arabia/investors/` | `gcc_investors.saudi_investors_en` | `—` | — | KEEP DJANGO (documented) |
| `/stewardship/` | `core.stewardship` | `stewardship.html` | /intelligence | REDIRECT 301 |
| `/value-distribution/` | `core.value_distribution` | `value_distribution.html` | /about | REDIRECT 301 |

**/api-docs/** — Developer documentation for API v1/v2. Server-generated reference material, in the sitemap.

**/ar/gcc-investors/ … (8 routes)** — Eight bilingual EN/AR investor landing pages, all in the sitemap, all indexed. This is the estate's only real SEO asset. Re-rendering indexed bilingual pages client-side risks their rankings for no product gain.

**/ethical-governance/ … (2 routes)** — The Ethical Governance framework and the 114-principle Capital Ethics Compendium: 191 kB of original written material with no React equivalent and no claim of implemented capability. Redirecting them to /trust/ would delete the content, not relocate it.

**/global-intelligence/ … (5 routes)** — Visual-intelligence concept pages. Each presents an illustrative analysis of a place or company; none is generated from the evidence graph, and Intelligence is where a real assessment now lives.

**/heating/ … (5 routes)** — Khalifa Heat: a real programme with a working retrofit calculator and a pilot application form carrying server-side validation and abuse screening. A live commercial funnel; porting the forms buys nothing and risks the funnel.

**/investors/** — Pre-seed opportunity page, in the sitemap. Investor material, not product UI.

**/khalifa-tours/** — The Khalifa Stewardship Tours programme narrative, in the sitemap and linked from the React /tours/ page. Its copy overclaims ("verified", "measured legacy") for expeditions that have not run — flagged, not silently rewritten.

**/methodology/** — Its subject — how EcoIQ handles evidence, provenance and confidence — is what the Trust Center now states, with the current architecture rather than the pre-Evidence-Integrity one.

**/platform/** — 176 kB describing five "intelligence modules". The honest version of that claim is About (what EcoIQ does today) plus Labs (what is experimental), both of which read their status from the registry.

**/press/** — Press kit and media contact. A real function, corrected for truthfulness earlier in this programme, with no product claim to restate.

**/products/** — Commerce catalogue for a billing provider set to "none". Unlinked and unindexed; it should not answer anonymously while nothing is purchasable.

**/stewardship/** — Climate intelligence and stewardship framing, superseded by the Intelligence assessment flow.

**/value-distribution/** — Stakeholder value framing. Concept content with no backing capability; About states the model without the diagram.

---

## C. COMPANY DATA SURFACE — PARITY REQUIRED

| route | view | template | React replacement | action |
|---|---|---|---|---|
| `/companies/compare/` | `company_intelligence.company_comparison_view` | `company_intelligence/compare.html` | — | AUTHENTICATE |
| `/companies/discover/` | `company_intelligence.discover_companies_view` | `company_intelligence/discover.html` | — | AUTHENTICATE |
| `/companies/strongest-alignment/` | `company_intelligence.strongest_alignment_view` | `company_intelligence/strongest_alignment.html` | — | AUTHENTICATE |
| `/countries/` | `countries.country_directory` | `countries/directory.html` | — | KEEP DJANGO (documented) |
| `/evidence/` | `harvester.evidence_explorer` | `harvester/evidence_explorer.html` | — | AUTHENTICATE |
| `/rankings/utilities/` | `harvester.utilities_ranking` | `harvester/utilities_ranking.html` | — | AUTHENTICATE |

**/companies/compare/ … (3 routes)** — company_intelligence discovery surfaces. Unlinked from the public nav, absent from the sitemap, already Disallow-ed in robots.txt. Discover alone is 818 kB. They are analyst tooling that happens to answer anonymously.

**/countries/** — Country directory, in the sitemap and linked. Country intelligence has no React surface and no API v2 resource; building one is its own phase, and the page publishes no company score.

**/evidence/ … (2 routes)** — harvester evidence explorer and the UK utilities ranking. Unlinked, unindexed. A ranking surface outside the eligibility gate is exactly the shape of the league leak; it is not leaking today, and it should not be anonymous.

---

## D. ECOIQ LABS / EXPERIMENTAL — MOVE TO LABS OR RESTRICT

| route | view | template | React replacement | action |
|---|---|---|---|---|
| `/agent-runtime-model-router/` | `agent_runtime_model_router.overview` | `agent_runtime_model_router/overview.html` | /labs (listed with real status) | AUTHENTICATE |
| `/ai-agent-council/` | `ai_agent_council.overview` | `ai_agent_council/overview.html` | /labs (listed with real status) | AUTHENTICATE |
| `/ai-agent-council/memory/` | `ai_agent_council.memory` | `ai_agent_council/memory.html` | /labs (listed with real status) | AUTHENTICATE |
| `/ai-agent-council/reliability/` | `ai_agent_council.reliability` | `ai_agent_council/reliability.html` | /labs (listed with real status) | AUTHENTICATE |
| `/ai-agent-council/training/` | `ai_agent_council.training` | `ai_agent_council/training.html` | /labs (listed with real status) | AUTHENTICATE |
| `/ai-agents/` | `ai_agent_workbench.directory` | `ai_agent_workbench/directory.html` | /labs (listed with real status) | AUTHENTICATE |
| `/ai-agents/council-demo/` | `ai_agent_workbench.council_demo` | `ai_agent_workbench/council_demo.html` | /labs (listed with real status) | AUTHENTICATE |
| `/ai-agents/performance/` | `ai_agent_workbench.performance` | `ai_agent_workbench/performance.html` | /labs (listed with real status) | AUTHENTICATE |
| `/ai-agents/presentation/` | `ai_agent_workbench.presentation` | `ai_agent_workbench/presentation.html` | /labs (listed with real status) | AUTHENTICATE |
| `/ai-agents/workbench/` | `ai_agent_workbench.workbench` | `ai_agent_workbench/workbench.html` | /labs (listed with real status) | AUTHENTICATE |
| `/capital-guardian/` | `capital_guardian.directory` | `capital_guardian/directory.html` | /labs (listed with real status) | AUTHENTICATE |
| `/capital-guardian/portfolio/` | `capital_guardian.portfolio_view` | `capital_guardian/portfolio.html` | /labs (listed with real status) | AUTHENTICATE |
| `/capital-guardian/suppliers/` | `capital_guardian.supplier_comparison_view` | `capital_guardian/supplier_comparison.html` | /labs (listed with real status) | AUTHENTICATE |
| `/decision-studio/` | `decision_studio.studio` | `decision_studio/studio.html` | /labs (listed with real status) | AUTHENTICATE |
| `/decisions/` | `qdf.stewardship_dashboard` | `qdf/stewardship_dashboard.html` | /labs (listed with real status) | AUTHENTICATE |
| `/digital-twin/` | `digital_twin.asset_list` | `digital_twin/asset_list.html` | /labs (listed with real status) | AUTHENTICATE |
| `/digital-twin/scenarios/compare/` | `digital_twin.scenario_compare` | `digital_twin/scenario_compare.html` | /labs (listed with real status) | AUTHENTICATE |
| `/financial-intelligence-cloud/` | `financial_intelligence_cloud.overview` | `financial_intelligence_cloud/overview.html` | /labs (listed with real status) | AUTHENTICATE |
| `/financial-intelligence-cloud/ask/` | `financial_intelligence_cloud.ask` | `financial_intelligence_cloud/ask.html` | /labs (listed with real status) | AUTHENTICATE |
| `/financial-intelligence-cloud/portfolio/` | `financial_intelligence_cloud.portfolio_view` | `financial_intelligence_cloud/portfolio.html` | /labs (listed with real status) | AUTHENTICATE |
| `/financial-intelligence-cloud/subscription/` | `financial_intelligence_cloud.subscription` | `financial_intelligence_cloud/subscription.html` | /labs (listed with real status) | AUTHENTICATE |
| `/geo-intelligence/` | `geo_intelligence.command_centre` | `geo_intelligence/command_centre.html` | /labs (listed with real status) | AUTHENTICATE |
| `/global-research/` | `global_research.mission_list` | `global_research/mission_list.html` | /labs (listed with real status) | AUTHENTICATE |
| `/gold-intelligence/` | `gold_intelligence.directory` | `gold_intelligence/directory.html` | /labs (listed with real status) | AUTHENTICATE |
| `/gold-intelligence/map/` | `gold_intelligence.mine_map` | `gold_intelligence/mine_map.html` | /labs (listed with real status) | AUTHENTICATE |
| `/good-agents/` | `good_agents.opportunity_list` | `good_agents/opportunity_list.html` | /labs (listed with real status) | AUTHENTICATE |
| `/good-agents/morning-brief/` | `good_agents.morning_brief` | `good_agents/morning_brief.html` | /labs (listed with real status) | AUTHENTICATE |
| `/intelligence-dashboard/` | `plotly_visual_intelligence.dashboard` | `plotly_visual_intelligence/dashboard.html` | /labs (listed with real status) | AUTHENTICATE |
| `/waste-to-value-capital-allocation/` | `waste_to_value_capital_allocation_engine.overview` | `waste_to_value_capital_allocation_engine/overview.html` | /labs (listed with real status) | AUTHENTICATE |

**/agent-runtime-model-router/** — agent_runtime_model_router. Experimental or unregistered module UI. Anonymous access makes an experiment look like a shipped capability; Labs already lists it with its real status.

**/ai-agent-council/ … (4 routes)** — ai_agent_council. Experimental or unregistered module UI. Anonymous access makes an experiment look like a shipped capability; Labs already lists it with its real status.

**/ai-agents/ … (5 routes)** — ai_agent_workbench. Experimental or unregistered module UI. Anonymous access makes an experiment look like a shipped capability; Labs already lists it with its real status.

**/capital-guardian/ … (3 routes)** — capital_guardian. Experimental or unregistered module UI. Anonymous access makes an experiment look like a shipped capability; Labs already lists it with its real status.

**/decision-studio/** — decision_studio.engine (EXPERIMENTAL). Experimental or unregistered module UI. Anonymous access makes an experiment look like a shipped capability; Labs already lists it with its real status.

**/decisions/** — qdf.decision_integrity (PRODUCTION engine, prototype UI). Experimental or unregistered module UI. Anonymous access makes an experiment look like a shipped capability; Labs already lists it with its real status.

**/digital-twin/ … (2 routes)** — digital_twin.council (EXPERIMENTAL). Experimental or unregistered module UI. Anonymous access makes an experiment look like a shipped capability; Labs already lists it with its real status.

**/financial-intelligence-cloud/ … (4 routes)** — financial_intelligence_cloud. Experimental or unregistered module UI. Anonymous access makes an experiment look like a shipped capability; Labs already lists it with its real status.

**/geo-intelligence/** — geo_intelligence. Experimental or unregistered module UI. Anonymous access makes an experiment look like a shipped capability; Labs already lists it with its real status.

**/global-research/** — global_research.council (EXPERIMENTAL). Experimental or unregistered module UI. Anonymous access makes an experiment look like a shipped capability; Labs already lists it with its real status.

**/gold-intelligence/ … (2 routes)** — gold_intelligence. Experimental or unregistered module UI. Anonymous access makes an experiment look like a shipped capability; Labs already lists it with its real status.

**/good-agents/ … (2 routes)** — good_agents.orchestrator (EXPERIMENTAL). Experimental or unregistered module UI. Anonymous access makes an experiment look like a shipped capability; Labs already lists it with its real status.

**/intelligence-dashboard/** — plotly_visual_intelligence. Experimental or unregistered module UI. Anonymous access makes an experiment look like a shipped capability; Labs already lists it with its real status.

**/waste-to-value-capital-allocation/** — waste_to_value_capital_allocation_engine. Experimental or unregistered module UI. Anonymous access makes an experiment look like a shipped capability; Labs already lists it with its real status.

---

## E. LEGACY — DELETE/REDIRECT

| route | view | template | React replacement | action |
|---|---|---|---|---|
| `/khalifa-tour-operating-system/` | `khalifa_stewardship_tour_operating_system.overview` | `khalifa_stewardship_tour_operating_system/overview.html` | /tours | AUTHENTICATE |
| `/khalifa-tour-operating-system/funding/` | `khalifa_stewardship_tour_operating_system.funding` | `khalifa_stewardship_tour_operating_system/funding.html` | /tours | AUTHENTICATE |
| `/khalifa-tour-operating-system/kazakhstan-clean-heat-demo/` | `khalifa_stewardship_tour_operating_system.kazakhstan_demo` | `khalifa_stewardship_tour_operating_system/kazakhstan_demo.html` | /tours | AUTHENTICATE |
| `/khalifa-tour-operating-system/legacy/` | `khalifa_stewardship_tour_operating_system.legacy` | `khalifa_stewardship_tour_operating_system/legacy.html` | /tours | AUTHENTICATE |
| `/khalifa-tour-operating-system/mrv/` | `khalifa_stewardship_tour_operating_system.mrv` | `khalifa_stewardship_tour_operating_system/mrv.html` | /tours | AUTHENTICATE |
| `/khalifa-tour-operating-system/presentation/` | `khalifa_stewardship_tour_operating_system.presentation` | `khalifa_stewardship_tour_operating_system/presentation.html` | /tours | AUTHENTICATE |
| `/khalifa-tour-operating-system/problems/` | `khalifa_stewardship_tour_operating_system.problems` | `khalifa_stewardship_tour_operating_system/problems.html` | /tours | AUTHENTICATE |
| `/khalifa-tour-operating-system/tours/` | `khalifa_stewardship_tour_operating_system.tours` | `khalifa_stewardship_tour_operating_system/tours.html` | /tours | AUTHENTICATE |
| `/legacy-safe/` | `legacy_safe.dashboard` | `legacy_safe/dashboard.html` | /labs | AUTHENTICATE |
| `/legacy-safe/agent-repository-map/` | `legacy_safe.agent_repository_map` | `legacy_safe/agent_repository_map.html` | /labs | AUTHENTICATE |
| `/legacy-safe/ai-agent-ecosystem-200/` | `legacy_safe.ai_agent_ecosystem_200` | `legacy_safe/ai_agent_ecosystem_200.html` | /labs | AUTHENTICATE |
| `/legacy-safe/ask/` | `legacy_safe.ask_agent` | `legacy_safe/ask.html` | /labs | AUTHENTICATE |
| `/legacy-safe/audit-logs/` | `legacy_safe.audit_logs` | `legacy_safe/audit_logs.html` | /labs | AUTHENTICATE |
| `/legacy-safe/dependency-graph/` | `legacy_safe.dependency_graph` | `legacy_safe/dependency_graph.html` | /labs | AUTHENTICATE |
| `/legacy-safe/justice-maqasid/` | `legacy_safe.justice_maqasid` | `legacy_safe/justice_maqasid.html` | /labs | AUTHENTICATE |
| `/legacy-safe/microsoft-ecosystem-readiness/` | `legacy_safe.microsoft_ecosystem_readiness` | `legacy_safe/microsoft_ecosystem_readiness.html` | /labs | AUTHENTICATE |
| `/legacy-safe/model-integration-readiness/` | `legacy_safe.model_integration_readiness` | `legacy_safe/model_integration_readiness.html` | /labs | AUTHENTICATE |
| `/legacy-safe/permission-demo/` | `legacy_safe.permission_demo` | `legacy_safe/permission_demo.html` | /labs | AUTHENTICATE |
| `/legacy-safe/process-optimisation/` | `legacy_safe.process_optimisation` | `legacy_safe/process_optimisation.html` | /labs | AUTHENTICATE |
| `/legacy-safe/repository-support/` | `legacy_safe.repository_support` | `legacy_safe/repository_support.html` | /labs | AUTHENTICATE |
| `/legacy-safe/revocation-demo/` | `legacy_safe.revocation_demo` | `legacy_safe/revocation_demo.html` | /labs | AUTHENTICATE |
| `/legacy-safe/upload/` | `legacy_safe.upload_document` | `legacy_safe/upload.html` | /labs | AUTHENTICATE |
| `/tazkiyah-114/` | `core.tazkiyah_landing` | `tazkiyah_landing.html` | — | AUTHENTICATE |

**/khalifa-tour-operating-system/ … (8 routes)** — An eight-page pitch deck for a tours operating system that does not exist, including a "presentation" page. Concept material, publicly reachable, describing MRV and funding as though operating.

**/legacy-safe/ … (14 routes)** — A fourteen-page surface named "legacy", including two pages named "demo". Unlinked and unindexed. Authenticated rather than deleted: the app has its own tests and models, and deletion is a separate decision from de-publication.

**/tazkiyah-114/** — Public concept landing for the Tazkiyah 114 reflection project. Unrelated to the decision-intelligence product and unlinked from it.

---

## F. DUPLICATE — CONSOLIDATE

| route | view | template | React replacement | action |
|---|---|---|---|---|
| `/khalifa-tours-impact/` | `core.khalifa_tours_impact` | `khalifa_tours_impact.html` | /tours | REDIRECT 301 |
| `/surah-map/` | `core.tazkiyah_landing` | `tazkiyah_landing.html` | /tazkiyah-114/ | REDIRECT 301 |

**/khalifa-tours-impact/** — Third Eco Tours surface alongside /tours/ and /khalifa-tours/. One product, one destination.

**/surah-map/** — Byte-identical alias of /tazkiyah-114/ — same view, same template.

---

## I. AUTH FLOW — KEEP DJANGO IF INTENTIONAL

| route | view | template | React replacement | action |
|---|---|---|---|---|
| `/login/` | `django.View.as_view.<locals>.view` | `—` | — | KEEP DJANGO (documented) |
| `/register/` | `core.register` | `register.html` | — | KEEP DJANGO (documented) |
| `/request-access/` | `leads.request_access` | `leads/request_access.html` | — | KEEP DJANGO (documented) |
| `/request-access/claim/` | `leads.claim_profile_page` | `claim_profile.html` | — | KEEP DJANGO (documented) |
| `/request-access/enterprise/` | `leads.enterprise_enquiry` | `leads/enterprise_enquiry.html` | — | KEEP DJANGO (documented) |
| `/request-access/enterprise/success/` | `leads.enterprise_enquiry_success` | `leads/enterprise_enquiry_success.html` | — | KEEP DJANGO (documented) |
| `/request-access/investors/` | `leads.investor_enquiry` | `leads/investor_enquiry.html` | — | KEEP DJANGO (documented) |
| `/request-access/investors/success/` | `leads.investor_enquiry_success` | `leads/investor_enquiry_success.html` | — | KEEP DJANGO (documented) |
| `/request-access/review/` | `leads.request_review` | `leads/review_request.html` | — | KEEP DJANGO (documented) |
| `/request-access/review/success/` | `leads.review_success` | `leads/review_success.html` | — | KEEP DJANGO (documented) |
| `/request-access/success/` | `leads.success` | `leads/success.html` | — | KEEP DJANGO (documented) |
| `/request-access/thank-you/` | `leads.thank_you` | `leads/thank_you.html` | — | KEEP DJANGO (documented) |

**/login/ … (2 routes)** — Django auth. The SPA deliberately implements no credential handling; session and CSRF stay server-owned.

**/request-access/ … (10 routes)** — The commercial lead funnel. Server-rendered forms with validation, abuse screening and their own lead models — including the engagement pre-selection the React pricing page depends on. Forms that work, carrying no product claim.

---

## Phase 5–7 outcome

| | |
|---|---|
| routes de-published (sign-in required) | **58** |
| routes 301-redirected to a React page | **10** |
| duplicate alias gated with its twin | 1 (`/surah-map/`) |
| templates deleted | 10 (330 → 320) |
| public rendering views deleted | 10 |
| **anonymous Django HTML routes** | **102 → 33** |
| `core/views.py` | 3,013 → 2,146 lines |

### What "AUTHENTICATE" did and did not do

It removed 58 pages from the anonymous web. It removed nothing from the
repository: every view, template, model and test survives, and a signed-in user
sees exactly what an anonymous one saw before. The policy is one tuple in
`core/access.py`, iterated by its own tests, and reversing it is deleting a
line.

### Two defects this work surfaced

**A `@staff_member_required` was silently stripped.** Deleting a view by cutting
from its `def` to the next one takes the *next* function's decorators with it.
`core.views.visual_lab` lost its staff gate that way and began answering
anonymously. Caught by `VisualLabAccessTests`, then re-audited across all three
edited view modules by comparing every function's decorator set against
`776ffaa` — one loss, now restored, none elsewhere.

**Automation put `force_login` on a response object.** A mechanical pass that
appended an authentication line after every `X = Client(...)` matched
`response = Client().get(...)` too. Two occurrences, both caught by the suite,
both replaced with the assertion the class actually wanted.

### The 90 `/platform/` tests

Thirty-five apps each carried a test asserting that its module was *mentioned
on the marketing page* — 90 methods in total, plus 31 test classes that existed
for nothing else. `/platform/` listed ~40 "modules", of which the registry
counts 8 as PRODUCTION and 33 as specification packs: documents, not software.

They are gone with the page. The guarantee they were reaching for — that a
module is publicly listed with its status — is what EcoIQ Labs provides, from
the registry, with the status attached.
