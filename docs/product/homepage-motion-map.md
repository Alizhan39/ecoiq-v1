# Homepage motion map

Required by the motion brief before implementation begins. Every entry answers
the brief's own test: **what information becomes easier to understand because of
this movement?** Anything that failed that test is not in this document.

## Foundation already present

Framer Motion **11.18.2** is installed and imported in **46 places**. The
primitives the brief lists as "potential reusable components" mostly exist:

| Brief asks for | Already in the repo | Where |
|---|---|---|
| `MotionReveal` | `Reveal` | `frontend/app/src/motion/Reveal.tsx` |
| `AnimatedNumber` / `AnimatedScore` | `useCountUp` | `hooks/useCountUp.ts` |
| reduced-motion handling | `MotionConfig reducedMotion="user"` | `motion/MotionProvider.tsx` |
| score visual | `ScoreRing` | `components/shared/ScoreRing.tsx` |
| mobile adaptation | `useMediaQuery` | `hooks/useMediaQuery.ts` |

Three consequences worth stating, because they change what needs building:

1. **Reduced motion is already solved architecturally.** `MotionProvider` wraps
   every island in `MotionConfig reducedMotion="user"`, so OS-level preference
   is honoured with no per-component opt-in. The brief's §22 requirement to call
   `useReducedMotion()` everywhere would duplicate this. Explicit checks are
   still needed only in count-up style animations, which `useCountUp` already
   does (`matchMedia` check, snaps to target).
2. **Animation fatigue is already solved for counters.** `useCountUp` gates on
   `IntersectionObserver` and **disconnects after the first trigger — never
   replays**. §21 is satisfied for that primitive; new sequences must copy the
   pattern rather than invent one.
3. **`LazyMotion` is used rather than importing full `motion`**, which is the
   §24 performance requirement, already met. New work must not regress it by
   importing `motion` directly.

## Token conflict, and how it resolves

`docs/motion-library-v1.md` is marked **LOCKED**, and CLAUDE.md rule 1 says it
defines motion regardless of any other opinion. The brief proposes different
numbers:

| Brief's tier | Brief's value | Locked token | Locked value | Verdict |
|---|---|---|---|---|
| fast | 120–180 ms | `duration.fast` | **0.18 s** | matches at the top of the range |
| standard | 220–320 ms | `duration.base` | **0.42 s** | **conflicts** — locked is slower |
| educational | 400–650 ms | `duration.slow` | **0.7 s** | **conflicts** — overlaps `base`, below `slow` |

The locked library already has exactly the three-tier structure the brief wants,
so this resolves without inventing a fourth set: **use `fast` / `base` / `slow`
as the three tiers.** Easing stays `ease.out = cubic-bezier(.22,1,.36,1)` for
entrances and `ease.inOut = cubic-bezier(.65,0,.35,1)` for bidirectional states.
Existing stagger conventions — cards `var(--i) * 90ms`, chips `var(--i) * 140ms`
— carry over, which also satisfies §20's stagger discipline by default.

If the intent is genuinely to make the whole system quicker, that is a change to
the locked library and belongs in its own PR with its own review — not a
homepage that quietly runs at different speeds from every other page.

The brief's "prefer spring for layout, controlled ease for content reveal" is
compatible and adopted: springs for `layout`/`layoutId` movement only.

## Section map

Duration column uses locked tokens. "Once" means `IntersectionObserver` +
disconnect, per `useCountUp`'s existing pattern.

### 1. Hero — evidence becomes a decision

- **Information problem** — "evidence-to-capital intelligence platform" is
  abstract. A visitor cannot picture what EcoIQ *does* to an input.
- **Motion** — one element transforms through four states via `layoutId`:
  `Evidence` → splits to `Risk` + `Readiness` → converges to `Capital` →
  resolves to `Proceed with conditions`. Not four cards fading in; the *same*
  node changing, so the transformation is the message.
- **Learns** — EcoIQ consumes evidence and emits a decision.
- **Duration** — 4 stages × `base`, ~4.5 s total. Settles and stops. No loop.
- **Interaction** — inert during the sequence; page remains scrollable and the
  CTA is clickable throughout. Sequence never blocks input.
- **Reduced motion** — renders the final state immediately: the full pipeline
  with all four labels visible. The meaning is in the labels, never in the
  movement.
- **Mobile** — vertical stack, no horizontal travel, 3 stages (Risk/Readiness
  combine), ~3 s.

### 2. Headline

- **Problem** — a long proposition read at once is read as marketing.
- **Motion** — two word-groups: **From evidence** → **to investment-ready
  decisions**, then supporting line, then CTA. Three steps, `base`, `ease.out`.
- **Learns** — the shape of the proposition before its detail.
- **Duration** — ~1.2 s to headline complete, CTA by ~2 s.
- **Reduced motion** — all present immediately.
- **Mobile** — identical; text reveal costs nothing.

### 3. Intent selector — one panel, many products

- **Problem** — visitors do not know which EcoIQ product answers their goal.
- **Motion** — six goals; the adjacent panel morphs via `AnimatePresence` +
  shared `layoutId`. "Assess a company" → Review panel; "Screen investments" →
  Intelligence panel. The panel *is* the same object, re-forming.
- **Learns** — the mapping from *my goal* to *EcoIQ's product*, by doing.
- **Duration** — `base` for the morph, `fast` for chip state.
- **Interaction** — radio-group semantics, arrow-key navigable, focus-visible,
  works on touch. **Each option is also a real link**, so it functions with JS
  disabled (§5's "work without JavaScript where practical").
- **Reduced motion** — panel swaps instantly, no cross-fade.
- **Mobile** — chips wrap to two rows; panel below rather than beside.

### 4. Product cards — three concepts, depth on demand

- **Problem** — 17 capabilities presented at once is the current page's failure.
- **Motion** — three cards show name/audience/outcome only. On hover, focus or
  tap, internal capabilities stagger in (`var(--i) * 90ms`, `fast`).
- **Learns** — there are three products, each with depth, without meeting all
  eighteen capability names at once.
- **Interaction** — **focus and tap both expand**, not hover alone (§18).
- **Reduced motion** — capabilities appear instantly on the same triggers.
- **Mobile** — tap to expand; one open at a time.

### 5. Decision brief — one assessment, several perspectives

- **Problem** — buyers cannot picture the deliverable.
- **Motion** — on first entry: decision status, then score counts up via the
  existing `useCountUp`, then confidence, gaps, pathways, actions. Then tabs
  (Risk / Evidence / Capital / Actions) re-weight the *same* brief with shared
  layout — the selected dimension grows, others recede.
- **Learns** — one assessment carries several decision perspectives; and
  concretely, what £4,900 buys.
- **Duration** — entry ~2.5 s; tab change `base`.
- **Interaction** — real tabs: `role="tablist"`, arrow keys, `aria-selected`.
- **Reduced motion** — final values immediately; tabs switch without motion.
- **Mobile** — tabs scroll horizontally; sequence shortened to 3 steps.
- **Data** — synthetic throughout, labelled `ILLUSTRATIVE SAMPLE`.

### 6. Why this score?

- **Problem** — a composite score is unfalsifiable unless decomposed.
- **Motion** — `71` splits via `layoutId` into five weighted components, each
  bar counting up. Returns to summary on the same control.
- **Learns** — the score is built from named, inspectable parts.
- **Duration** — `base` for the split, count-ups ~800 ms.
- **Interaction** — a real `<button>` with `aria-expanded`. Not a modal.
- **Reduced motion** — components render expanded, no bar animation.
- **Mobile** — components stack; bars full width.

### 7. Evidence → decision pipeline (the one sticky section)

- **Problem** — "AI-assisted, analyst-reviewed" is a claim, not an explanation.
- **Motion** — sticky visual on the left, stage copy on the right. Scrolling
  advances Evidence → Engines → Specialist AI → Challenge → Analyst → Brief.
  Each stage connects to the previous with an SVG path drawn at `slow`.
- **Learns** — the actual path from document to decision, and where the human is.
- **Duration** — ~12 s at normal scroll speed. **No scroll-jacking** — the page
  scrolls normally and the visual tracks progress.
- **Interaction** — stage labels are clickable jumps.
- **Reduced motion** — becomes a static numbered diagram, all stages visible,
  no stickiness.
- **Mobile** — **sticky is dropped entirely**; stages become a vertical list.
- **Note** — this is the *only* sticky storytelling section (§17).

### 8. AI agents — orchestration, not a roster

- **Problem** — twelve agent cards is the current hero's mistake.
- **Motion** — Evidence node → four representative specialists activate in
  stagger → signals return → verification compares → one decision consolidates.
  "See all agents" expands the full set via `AnimatePresence`.
- **Learns** — agents are a mechanism inside one decision, not the product.
- **Duration** — ~3 s, once.
- **Reduced motion** — static orchestration diagram.
- **Mobile** — two specialists shown, rest behind the expander.

### 9. Capital pathway

- **Problem** — the commercial value of a Review is not obvious.
- **Motion** — readiness `58` counts up to `67` as a gap is shown being closed,
  then an indicative pathway appears.
- **Learns** — closing evidence gaps changes financing readiness.
- **Duration** — ~2 s.
- **Claims** — labelled **Illustrative · Potential · Not guaranteed**, adjacent
  to the number, not in a footnote.
- **Reduced motion** — both values shown side by side with the delta.

### 10. Commercial ladder

- **Problem** — price increases look arbitrary without scope changes.
- **Motion** — starts at Review only; each subsequent tier reveals on scroll,
  and the *scope line* changes with it (1 company → portfolio → live scope →
  organisation-wide → continuous).
- **Learns** — price tracks scope.
- **Duration** — `base` per tier.
- **Reduced motion** — full ladder as a table.
- **Blocked** — see "Open questions" below. Not implementable as specified.

### 11. Before → after

- **Problem** — the pain is familiar but unnamed.
- **Motion** — scattered artefacts (300-page report, PDFs, spreadsheets)
  converge into one brief.
- **Learns** — EcoIQ's output replaces a pile of inputs.
- **Duration** — `slow`, once.
- **Reduced motion** — two labelled columns, before and after.

### 12. Outcomes as a sequence

- **Problem** — four cards read as unrelated features.
- **Motion** — Risk → Opportunity → Capital → Next step, each activating in
  turn with the previous dimmed but present.
- **Learns** — these are stages of one reasoning chain.
- **Duration** — `base`, stagger `var(--i) * 90ms`.
- **Reduced motion** — all four visible, connected by static arrows.

### 13. Role switch (Company / Investor / Government)

- **Problem** — one page serving three audiences usually means three times the
  copy.
- **Motion** — role chips re-write hero support line, recommended product and
  final CTA via text transition. **DOM is not rebuilt** (§13).
- **Learns** — EcoIQ applies to their specific seat.
- **Persistence** — `sessionStorage` only, a single enum value. No PII, no
  cookie, nothing that reaches analytics as an identifier.
- **Reduced motion** — instant text swap.
- **Mobile** — kept; it is cheap and high value.

### 14. Khalifah Eco Tours — data to place

- **Problem** — the section risks reading as a travel agency bolted on.
- **Motion** — a project node from the intelligence layer morphs into a place:
  location, ecosystem, people, stewardship action. Category chips change scene.
- **Learns** — the tours are the physical end of the same evidence chain.
- **Duration** — `base` per category change.
- **Reduced motion** — static category panels.
- **Blocked** — CTA wording depends on whether tours are operational. See below.

### 15. Khalifah framework

- **Problem** — the stewardship layer must be present without becoming the first
  thing an institutional buyer must absorb.
- **Motion** — `KHALIFAH · Stewardship` reveals a five-link chain: Principle →
  Evidence → Decision → Action → Accountability, using a restrained geometric
  transition.
- **Learns** — stewardship is methodological, not decorative.
- **Depth** — "Explore methodology" links out; no KPI dump inline.
- **Reduced motion** — static chain.

### 16. Section progress

- **Problem** — a long institutional page loses orientation.
- **Motion** — small desktop indicator: 01 Understand … 05 Experience.
- **Reduced motion** — static current-stage label.
- **Mobile** — **removed**.

## Performance constraints

The locked library states a **60-particle budget, allocated once in a fixed pool
and mutated in place**. Nothing here adds particles. Animation is confined to
`transform` and `opacity`; `layout` animation is used only where an element
genuinely moves between positions (hero pipeline, score split, intent panel).
No `width`/`height`/`top`/`left` animation. Below-the-fold islands lazy-mount.

## Not built, and why

- **Per-component `useReducedMotion()`** — `MotionProvider` already applies
  `reducedMotion="user"` globally. Adding local checks would duplicate it.
- **New duration tokens** — the locked library's `fast`/`base`/`slow` cover all
  three tiers the brief describes.
- **A second sticky section** — §17 permits one; §7 is it.
- **Map functionality for Eco Tours** — explicitly out of scope in the brief.

## Open questions blocking implementation

Three, all commercial rather than technical.

1. **Is "From £4,900 / 5 working days" approved to publish?** A price and a
   delivery SLA on the live homepage are commitments.
2. **The two briefs give different ladders.** The first says *Institutional
   Pilot from £25k*; this one says *£15k Diagnostic → £75k Pilot → Deployment →
   Annual Licence*. These cannot both be right, and section 10 teaches the
   ladder — it cannot be built on a figure that may be wrong.
3. **Are Khalifah Eco Tours operational?** The brief itself says to label them
   "Explore concept / Register interest" if not. `/khalifa-tours/` exists as a
   page; whether tours run is a matter of fact I cannot verify from the codebase.

Sections 1–9 and 11–16 do not depend on these answers. Section 10 does, and the
Eco Tours CTA in section 14 does.
