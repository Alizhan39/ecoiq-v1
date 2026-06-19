# Tazkiyah 114 — Implementation Roadmap

> A phased plan from documentation to a safe, premium product. Each phase has a clear gate; a
> phase does not ship until its content has moved through the
> [scholar review workflow](tazkiyah-114-transformation-operating-system.md#e-scholar-review-layer).
> Nothing interpretive publishes without review. See
> [safety principles](tazkiyah-114-safety-principles.md).

---

## Phase 1 — Documentation + seeds *(current)*

**Goal:** a complete, reviewable paper product before any new app code.

- Modules 1–60 documented (1–30 in the architecture brief + transformation OS; 31–60 in
  [modules 31–60](tazkiyah-114-modules-31-60.md)).
- Scholar review workflow defined (`author_draft → source_added → needs_scholar_review →
  scholar_reviewed → publishable`; sensitive topics require scholar + wellbeing review).
- Content model defined (Surah pathway schema; module seed schema in
  `content/tazkiyah114/moduleSeeds.ts`).
- Safety principles documented and treated as binding.

**Gate:** docs reviewed internally; seed content validated; no live app changes.

---

## Phase 2 — Static prototype

**Goal:** make the spine visible and clickable, content-first.

- Surah Map (browse/search/filter — already prototyped on `/tazkiyah-114/`).
- Struggle Finder (struggle → pathway).
- Sample pathway pages (curated, fully-authored, clearly labelled).
- Daily Mizan mockup (morning + evening).
- Repentance Room mockup (gentle stepper, sensitive-flagged).

**Gate:** trust note + status labels present and non-removable; sensitive mockups carry the
disclaimer; no user data stored server-side yet.

---

## Phase 3 — User accounts

**Goal:** make it personal and durable.

- Private journal (local-first → opt-in cloud).
- Habit tracking (read/reflect/act/dua/journal; practice streaks, no shaming).
- Saved pathways.
- Family mode (multiple profiles).

**Gate:** privacy-first data model with working export/delete; opt-in sync only.

---

## Phase 4 — Review system

**Goal:** make scholarship operational and visible.

- Scholar dashboard (review queue, approvals, reviewer name/date/confidence).
- Source checker (translation/tafsir references + license state).
- Status badges rendered on every interpretive page.
- Content versioning (any change to ayah/translation/source/sensitive wording reopens review).

**Gate:** every published interpretive page is `scholar_reviewed` (or clearly labelled otherwise);
public Content Status page live.

---

## Phase 5 — Community circles

**Goal:** safe, small, purpose-led connection — not a feed.

- Safe groups (family, sisters, youth, founders, grief).
- No vanity metrics, no follower counts, no public worship ranking, no infinite scroll.
- Accountability tools (private partners, "I benefited from this").
- Group challenges (7-day).

**Gate:** moderation + wellbeing escalation path operational; grief/abuse circles have trained
moderation; passes a safety/anti-addiction design review.

---

## Phase 6 — Premium tier

**Goal:** sustainability that funds scholarship.

- Advanced journaling insights (patterns over months).
- Family mode (expanded).
- Founder/leader pathways.
- Printable cards (Do/Don't, Whisper-vs-Truth).
- Reviewed premium programs (e.g. 30-Day Heart Reset, seasonal modes).
- **Transparent message that premium helps fund scholarship/review.**

**Gate:** all premium interpretive content is `scholar_reviewed`; the funding message is honest and
visible.

---

## Cross-phase rules

- Do not build the AI Reflection Companion or the community feed before the trust layer and content
  corpus are mature (see safety principles). Red-team the AI against every "must not" before any
  user exposure.
- Licensed translation/tafsir text (Ibn Kathir, as-Sa'di, Jalalayn, Clear Quran, Sahih
  International) is integrated only after licensing/permission is confirmed.

*Last updated: 2026-06-19.*
