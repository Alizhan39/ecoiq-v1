# Homepage consolidation — legacy replacement map

Measured in a browser at 1440×900 against this branch, not estimated. Heights,
link counts and word counts are what the page actually rendered.

**Removing a section from the homepage does not delete its component, template,
route or backend capability.** This is a change to homepage *composition* only.
Every destination named below already exists and stays reachable.

## Baseline on this branch

| | Value |
|---|---|
| Rendered height | **11,124px** |
| Links | **93** |
| Words | **2,004** |
| Blocks ≥40px | **23** (incl. header and footer) |

Production before any of this work: 17 `<section>` elements, ~3,499 template
words, 86 links across 57 destinations.

## The map

| # | Old section | Height | Purpose | Unique info? | New homepage destination | Deeper route | Verdict | SEO risk | Capability loss |
|---|---|---|---|---|---|---|---|---|---|
| — | `CinematicHomeHero` | **3,316px** | Scrollytelling hero, "Find the Better Way" | No — hero role now served by the commercial hero | — | reusable on a future About/Story page | **REMOVE FROM HOMEPAGE** | Low — headline was brand copy, not indexed terms | None; component and island untouched |
| 1 | **New commercial hero** | 483px | Proposition + both CTAs | Yes | **KEEP** | — | KEEP | — | — |
| 2 | `living-earth` | 1,268px | "Trust infrastructure" narrative | Partly | Merge trust line into Trust section | — | **MERGE** | Low | None |
| 3 | UK infrastructure strip | 191px | Live counters | Yes (live data) | Merge into hero proof line | `/companies/` | **MERGE** | Low | None |
| 4 | Meet the EcoIQ AI Agents | 674px | Explains agents | Yes | **How EcoIQ Works** (not yet built) | `/ai-agents/` | MERGE *(after §5 exists)* | Medium — agent terms | None |
| 5 | From intelligence to action | 334px | Generic three-step | No | Outcomes | — | **REMOVE** | Low | None |
| 6 | Stats strip | 57px | Counters | Duplicate of #3 | hero proof | — | **REMOVE** | Low | None |
| 7 | Country flags | 95px | 4 markets | Duplicate of hero proof | hero proof | `/countries/` | **REMOVE** | Low | None |
| 8 | Market access | 745px | Who it serves | Yes | Product Architecture | — | MERGE *(after §2)* | Low | None |
| 9 | How it works (01–03) | 390px | Three-step process | No — superseded | **How EcoIQ Works** | — | MERGE *(after §5)* | Low | None |
| 10 | Who uses EcoIQ | 287px | Audiences | Yes | Intent Selector | — | MERGE *(after §1)* | Low | None |
| 11 | What EcoIQ helps you do | 372px | Capability list | Overlaps #10 | Intent Selector | — | MERGE *(after §1)* | Low | None |
| 12 | Intelligence modules (five) | **1,142px** | Module catalogue | Yes | Product Architecture → Intelligence | `/platform/` | MERGE *(after §2)* | **Medium — largest text block** | None |
| 13 | Amanah Autopilot | 494px | Product teaser | Yes | Institutional capability | deeper page | MERGE *(later)* | Low | None |
| 14 | 6-Pillar methodology | 649px | Scoring framework | Yes | "Why 71?" + methodology link | `/methodology/` | MERGE *(after §3)* | **Medium** | None |
| 15 | Terminal / sovereign monitor | 654px | Terminal teaser | Yes | Product Architecture → Institutional | `/platform/` | MERGE *(after §2)* | Low | None |
| 16 | Digital Twin preview | 79px | Caption only | No | — | deeper page | **REMOVE** | Low | None |
| 17 | Institutional country intelligence | 499px | Country report CTA | Yes | Product Architecture → Institutional | `/countries/` | MERGE *(after §2)* | Low | None |
| 18 | Get started | 422px | CTA block | No — hero CTA duplicates it | hero | — | **REMOVE** | Low | None |
| 19 | EcoIQ analytical review | 560px | Review CTA | Duplicate of hero primary CTA | hero + Product Architecture | `leads:request_review` | **REMOVE** | Low | None |
| 20 | Real-world projects | 417px | Project cards | Yes | Intelligence teaser | `/projects/` | MERGE *(later)* | Medium | None |
| 21 | `InvestorScrollStory` | 275px | Investor narrative | Yes | Outcomes / Intelligence | reusable | MERGE *(after §4)* | Low | None |
| 22 | Footer | 689px | Navigation | Yes | **KEEP** | — | KEEP | — | — |

### Removal sequencing

Sections marked *(after §N)* are **not** removed yet. Their information has a
named destination, but that destination is not built. Removing them first would
lose content rather than consolidate it, which is the opposite of the goal.

Executed in this pass: `CinematicHomeHero` only — the one case where the
replacement demonstrably exists and is verified above the fold.

Ready to remove the moment their replacements land: #5, #6, #7, #16, #18, #19
(≈1,624px of duplicated CTA and counter blocks with no unique information).

## SEO note

The three Medium-risk blocks (#4 agents, #12 modules, #14 methodology) carry the
most indexable prose. Each has an existing deeper route — `/ai-agents/`,
`/platform/`, `/methodology/` — which is where that text belongs and where it
can rank on its own intent. The homepage should target the brand/category term.
No route is removed by this plan, so no URL loses its index entry.
