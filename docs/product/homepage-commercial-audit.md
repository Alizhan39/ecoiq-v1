# Homepage commercial audit

Measured in a real browser at 1440×900 on branch
`feat/homepage-product-consolidation`, head `b31068d`, with all ten lazy
islands mounted the way a visitor scrolling the page would mount them. Every
figure below is rendered output, not an estimate from source.

The question the audit asks of each block:

> If a serious person gives EcoIQ 60 seconds, does every second help them
> **understand**, **trust**, or **buy** the product?

Anything doing none of the three needs a strong reason to stay.

## 1. Measured metrics

| | Value |
|---|---|
| scrollHeight | **17,650px** |
| `<section>` elements | 26 |
| Blocks ≥40px | 33 |
| Rendered words | 2,940 |
| Links | 92 |
| Distinct destinations (ignoring `#`/`?`) | 39 |
| EcoIQ Review CTAs | 4 |
| Enterprise/institutional CTAs | 2 |
| Pricing links | 2 |
| Islands mounted | 10 / 10 |

## 2. Rendered order

| # | Block | Top | Height | Words | Links | Category |
|---|---|---|---|---|---|---|
| 1 | Nav | 8 | 61 | 6 | 17 | CORE |
| 2 | Hero | 69 | 483 | 88 | 2 | CORE |
| 3 | Product Architecture | 552 | 551 | 118 | 11 | PRODUCT |
| 4 | Decision Brief | 1,104 | 807 | 131 | 2 | PROOF |
| 5 | Outcomes | 1,911 | 729 | 176 | 1 | PRODUCT |
| 6 | Impact Engine | 2,640 | 721 | 149 | 5 | PRODUCT |
| 7 | Living Earth | 3,361 | 1,268 | 226 | 5 | TRUST |
| 8 | UK infrastructure strip | 4,669 | 191 | 23 | 2 | LEGACY |
| 9 | Market access | 4,900 | 745 | 146 | 3 | LEGACY |
| 10 | Who uses EcoIQ | 5,645 | 287 | 79 | 3 | LEGACY |
| 11 | What EcoIQ helps you do | 5,995 | 372 | 139 | 1 | LEGACY |
| 12 | Amanah Autopilot | 6,432 | 494 | 82 | 1 | OPTIONAL |
| 13 | 6-Pillar Methodology | 6,926 | 649 | 109 | 1 | TRUST |
| 14 | Khalifah Field Intelligence | 7,575 | 845 | 195 | 2 | DIFFERENTIATOR |
| 15 | Projects Preview | 8,421 | 359 | 78 | 5 | PROOF |
| 16–27 | **InvestorScrollStory** | 8,780 | **8,191** | ~1,060 | 9 | LEGACY |
| 28 | Footer | 16,953 | 689 | 105 | 22 | CORE |

### The headline finding

**The InvestorScrollStory occupies 8,191px — 46% of the homepage** — for ~1,060
words and 9 links. The commercial core (blocks 1–6) is 3,361px, **19%**.

Blocks 18–25 retell the Impact Engine loop exactly — Evidence → RPR → Better
Way → Mandate → Human Decision → Capital Guardian → Verify → Learning. The
same twelve-stage argument, told twice, at roughly **11× the length**, 6,000px
after the version that says it well.

## 3. Ten-second test (first viewport only)

| Question | Verdict |
|---|---|
| What EcoIQ is | CLEAR — "From evidence to investment-ready decisions." |
| What problem it solves | CLEAR — transition risk, evidence quality, financing readiness |
| What it produces | **PARTIAL** — "says what should happen next" is a promise; the actual artefact is 1,104px away |
| Who it is for | CLEAR — three audiences named in the fold |
| What to click | CLEAR — "Request an EcoIQ Review" is the only filled button |

### Open defect — verify before anything else

The hero proof line renders **"0+ companies scored · 4 focus markets"**, and
blocks 8 and 10 render "0 companies". Locally this is an empty development
database, so it is probably not a production bug — but that was **not
verified against production**. If production renders `0+`, the first line a
visitor reads destroys credibility, and it outranks every other item here.

## 4. Sixty-second journey

| Viewport | Learns | Genuinely new | Trust | Intent | Fatigue |
|---|---|---|---|---|---|
| 1 (0–900) | What EcoIQ is, who for | Yes | ↑ | ↑ | — |
| 2 (900–1,900) | Three products, price anchor | Yes | ↑ | ↑↑ | — |
| 3 (1,900–2,600) | An actual decision output | Yes | ↑↑ | ↑↑ | — |
| 4 (2,600–3,300) | Outcomes chain | Weak | → | → | ↑ |
| 5 (3,300–4,600) | The operating loop | Yes | ↑↑ | ↑ | ↑ |
| 6 (4,600–7,500) | Legacy blocks 7–13 | Mostly no | → | ↓ | ↑↑ |
| 7 (7,500–8,800) | Khalifah, Projects | Yes | ↑ | → | ↑↑ |
| 8 (8,800–17,000) | Investor story | No — repeats viewport 5 | ↓ | ↓ | ↑↑↑ |

- **Understanding peaks at ~3,360px**, about 25 seconds in.
- **Marginal information value collapses at 4,669px.**
- Everything from 4,669px to 16,953px — **70% of the page** — adds little a
  buyer needs.

## 5. Product architecture clarity

| | Review | Intelligence | Institutional |
|---|---|---|---|
| Who buys | Companies / projects | Investors, funds, analysts | Banks, funds, corporates, governments |
| Purchase trigger | Needs a defensible position | Needs to screen at scale | Portfolio / sovereign mandate |
| Receives | The 71 / PROCEED brief | Platform access | Custom intelligence |
| CTA | Request Review (£4,900) | Explore Intelligence | Discuss Engagement |
| Next commercial step | Clear | Self-serve | **Dead end** |

Review is unambiguous. **Institutional is the weak link**: nothing sits
between "From £4,900" and "let's talk", and the £15k–£400k engagement ladder
appears nowhere on the homepage.

## 6. Section audits

| Section | Info efficiency | Conversion | Verdict |
|---|---|---|---|
| Impact Engine | 94 | 84 | **KEEP** — best section on the page |
| Decision Brief | 88 | 92 | **KEEP** — trim ~80px by moving the two read panels inside the disclosure |
| Hero | 86 | 90 | KEEP |
| Product Architecture | 84 | 88 | KEEP |
| Khalifah Field Intelligence | 72 | 58 | KEEP, position correct; compress ~245px |
| Projects Preview | 68 | 52 | KEEP — real project names are genuine proof |
| Living Earth | 55 | 40 | MERGE into a trust section |
| 6-Pillar Methodology | 52 | 35 | MERGE into a trust section |
| **Outcomes** | **41** | 55 | **COMPRESS to a 150–250px bridge** |
| Amanah Autopilot | 38 | 30 | MOVE to a deeper page |
| Who uses EcoIQ | 34 | 28 | MERGE into Product Architecture |
| Market access | 31 | 26 | MERGE into Product Architecture |
| What EcoIQ helps you do | 28 | 22 | MERGE into Product Architecture |
| UK infrastructure strip | 22 | 18 | REMOVE |
| **InvestorScrollStory** | **18** | **15** | **REMOVE from homepage** |

Nine sections score below 50 on information efficiency. The visually most
impressive section on the page ranks last on both scales.

### Decision Brief

Looks like a real output; "Illustrative" is unmissable; "Why 71?" teaches
explainability; the scenario levers teach that a decision is movable — the
strongest single idea on the homepage. 807px is earned.

### Outcomes

Its unique contribution is only "analysis leads to action and impact". The
Decision Brief already shows a recommendation, and the Impact Engine already
shows Act and Prove & Learn in the same four-beat shape — Risk → Decision →
Action → Impact is Understand → Decide → Act → Prove renamed. 729px and 176
words (the most of any commercial section) for the least new information.
Keep the four value statements and the "does not replace management
judgement" line; drop the four-stage chain the Impact Engine owns.

### Impact Engine

Four phases immediate; twelve stages visible without clicking; loop closes
explicitly; execution is not the endpoint; analyst review preserved; no
autonomy implication; specialists are four domains plus links rather than a
roster; 721px with zero layout shift when a phase opens.

### Khalifah Field Intelligence

Arrives at 7,575px, after the commercial core — the right moment. Reinforces
the loop rather than competing with it, and does not read as a tourism
company: the Impact Engine framing and the in-development label carry it.
Slightly generous at 845px for a differentiator.

## 7. Duplication matrix

| Concept | Section A | Section B | Should own it | Action |
|---|---|---|---|---|
| Evidence → decision → verify loop | Impact Engine | InvestorScrollStory 18–25 | Impact Engine | Remove B from homepage |
| Risk → Decision → Action → Impact | Outcomes | Impact Engine | Impact Engine | Compress Outcomes |
| Who EcoIQ serves | Product Architecture | Market access, Who uses | Product Architecture | Remove 9, 10 |
| Platform capabilities | Product Architecture | What EcoIQ helps you do | Product Architecture | Remove 11 |
| Human decision authority | Impact Engine trust rail | Outcomes trust line, block 22 | Impact Engine | Dedupe |
| Verification | Impact Engine | Blocks 23, 24 | Impact Engine | Remove |
| Methodology | 6-Pillar block | Decision Brief + Impact Engine CTAs | Deeper page | Compress |
| Brand slogan | Two tail blocks | — | Footer | Remove both |

## 8. CTA and conversion paths

92 links across 39 destinations.

- **CTA desert** 4,669 → 7,575px (~2,900px with one weak link).
- **CTA flood** 8,780 → 16,971px — 9 links across 8,191px, four of them
  `mailto:`.
- **Review** appears on three real surfaces — hero (0), Product Architecture
  (552), Decision Brief (1,104) — all inside the first 1,900px, then nothing
  for 15,000px. Three well-spaced surfaces beat three clustered ones: keep
  hero and Decision Brief, add one late commercial close.
- **Institutional path breaks** immediately after "Discuss Engagement".
- **Pricing: TOO HIDDEN.** One nav link and `From £4,900`. A serious
  institutional buyer cannot self-qualify.

## 9. Navigation

17 flat links, no grouping. Framework / Compendium / Stewardship /
Methodology / Geo Intelligence are Level-3 concepts competing with commercial
actions. Proposal derived from the routes that actually exist:

**Products** (Platform, Projects, Rankings, Countries) · **Intelligence** (Ask
EcoIQ AI, Geo Intelligence) · **Approach** (Methodology, Framework,
Compendium, Stewardship) · **Company** (About, Contact) · **Pricing** ·
**Request Review** (primary) · Sign In.

## 10. Level 1 / 2 / 3

- **Level 1 — homepage:** hero, product architecture, decision brief, impact
  engine, projects, khalifah, one commercial close.
- **Level 2 — product/sector pages:** market access, who uses, what helps,
  Amanah, UK infrastructure strip, Living Earth detail.
- **Level 3 — methodology/docs:** 6-Pillar detail, InvestorScrollStory,
  governance compendium.

Roughly **11,500px of Level 2/3 content currently occupies Level 1 space**.

## 11. Recommended homepage

| # | Section | Question answered | CTA | Target height | Source | Status |
|---|---|---|---|---|---|---|
| 1 | Hero | What is EcoIQ? | Request Review | 480 | existing | KEEP |
| 2 | Product Architecture | Which product is for me? | Per product | 550 | existing | KEEP |
| 3 | Decision Brief | What does it produce? | Request Review | 750 | existing | KEEP, trim 80 |
| 4 | Outcomes bridge | So what? | — | 200 | Outcomes | COMPRESS |
| 5 | Impact Engine | How does it create impact? | Explore Platform | 720 | existing | KEEP |
| 6 | Trust & evidence | Why should I trust it? | Methodology | 600 | Living Earth + 6-Pillar | MERGE |
| 7 | Institutional & pricing ladder | What does engagement cost? | Discuss Engagement | 450 | `/pricing/` | NEW |
| 8 | Khalifah Field Intelligence | What makes EcoIQ different? | Explore Eco Tours | 600 | existing | COMPRESS |
| 9 | Projects | Is any of this real? | View Projects | 360 | existing | KEEP |
| 10 | Commercial close | What should I do next? | Request Review | 350 | replaces tail | NEW |
| 11 | Footer | — | — | 690 | existing | KEEP |

### Target metrics

| | Now | Target |
|---|---|---|
| Major sections | 26 | **10–11** |
| scrollHeight | 17,650px | **5,500–6,500px** |
| Words | 2,940 | **1,600–1,900** |
| Links | 92 | **55–65** |
| Distinct destinations | 39 | **30–35** |
| Review CTAs | 4 | **3**, well spaced |

Substantial, not encyclopedic: enough to answer the seven journey questions
without requiring the visitor to reach the footer to understand the product.

## 12. Consolidation plan

| Phase | Change | Height saved | Content risk | SEO risk | Commercial risk |
|---|---|---|---|---|---|
| **A0** | Verify the "0+ companies scored" counter in production | — | — | — | **Critical if real** |
| **A1** | Remove InvestorScrollStory from homepage composition → `/about/` | **~8,190px** | Low (duplicate) | **Medium** — most prose on the page | Low |
| A2 | Remove UK infrastructure strip | 191px | None | Low | None |
| **B1** | Merge Market access + Who uses + What helps into Product Architecture | ~1,400px | Low | Medium | Low |
| B2 | Merge Living Earth + 6-Pillar into one trust section | ~1,300px | Medium | Medium | Low |
| B3 | Compress Outcomes to a bridge | ~530px | Low | Low | Low |
| B4 | Compress Khalifah | ~245px | Low | Low | Low |
| B5 | Move Amanah Autopilot to a deeper page | 494px | Low | Low | Low |
| **C** | Navigation: 17 flat links → 5 groups + Request Review | — | Low | Medium | Low |
| **D** | Add institutional engagement ladder section | +450px | — | Low | **High value** |
| **E** | Add late commercial close | +350px | — | Low | High value |

**Net effect: 17,650px → ~5,900px (−67%).**

### Test requirements for every phase

- The geometric CTA-overlap check (`boundingClientRect` intersection across a
  full scroll at 1440×900 and 390×844).
- All homepage suites.
- **The full Django suite.** Phase A1 removes an island other apps' tests may
  reference — this is exactly how the `TRY THE AI AGENTS` regression got
  through in the Impact Engine iteration: every focused suite passed and only
  the full run caught it.

## Priority

1. **A0** — verify the counter in production. A hero reading "0+ companies
   scored" outranks everything else here.
2. **A1** — one change, 46% of the page.
3. **D** — the institutional ladder is the only thing on this list that is
   *missing* rather than surplus.
