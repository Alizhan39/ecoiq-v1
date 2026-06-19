# Tazkiyah 114 — The Surah Map · Product Architecture

> **Status:** Concept + working prototype. This document is the product brief for
> *Tazkiyah 114 / The Surah Map* — a Qur'an-inspired reflection and action platform.
> It records the vision, the current prototype scope, and — most importantly — the
> **trust, scholarship, and safety rules** that any future build must honour.
>
> **Nothing in this document authorises shipping interpretive content without scholar
> review.** See [Launch gates](#launch-gates) and
> [What must not be added before scholar review](#what-must-not-be-added-before-scholar-review).

---

## 1. Product vision

**"Don't only finish a surah. Let the surah repair something in you."**

Tazkiyah 114 turns the Qur'an from something you *read* into something you *live*. It maps
**114 Surahs → 114 life pathways**, walking a person from a real, named struggle to a verse,
a reflection, one concrete action, a dua, and a journal note — then tracking that growth over
time.

It is **not** a Qur'an translation site. It sits, deliberately, at the intersection of four things:

- **Qur'anic guidance** — themes and reflection, never invented tafsir.
- **Emotional healing** — gentle, non-clinical, never a replacement for therapy.
- **Habit formation** — one small action beats passive reading.
- **A trustworthy scholarship layer** — every interpretive claim is labelled and reviewable.

**North-star metric:** *actions completed per active user per week* — transformation, not
time-on-app. The product deliberately rejects engagement-maximising patterns (infinite scroll,
vanity likes, streak-shaming, public worship comparison).

**One-line positioning:** *A Qur'an-inspired reflection and action companion for the heart —
serious about scholarship, gentle with people.*

---

## 2. Core UX flow

The spine of the entire product is one flow:

```
Choose your struggle
   → receive a Qur'anic pathway
      → read an ayah
         → reflect (one honest question)
            → take one action ("what does this ayah ask of me today?")
               → make a dua
                  → journal one note
                     → track your tazkiyah over time
```

**Five pillars** mirror this flow: **1) Choose Your Struggle · 2) Find Your Surah Pathway ·
3) Reflect on the Ayah · 4) Take One Action · 5) Track Your Tazkiyah.**

Supporting flows:

- **Crisis flow** (fast, ≤30s to relief): pick an acute state → one ayah to hold → one
  reflection → one action in the next 10 minutes → one dua → a reminder of Allah's mercy →
  clear safety exits.
- **Habit flow** (daily return): open "Today" → one ayah, one reflection, one action, one dua,
  one journal line. Streak counts the *practice done*, never just *opening the app*; missed days
  are never punished.
- **Depth flow**: a recurring struggle → a Nafs Pattern → a 7-Day Repair Plan → the opposite
  virtue to build.
- **Heart Mirror** (guided self-reflection): "What is your heart asking for right now?" → a
  mapped pathway, framed explicitly as *"a guided reflection based on what you selected"* —
  never predictive, mystical, or fortune-telling.

---

## 3. Current prototype scope

A working single-page prototype exists in the EcoIQ Django project (route
`/tazkiyah-114/`, alias `/surah-map/`; template `templates/tazkiyah.html`, view
`core.views.tazkiyah`). It is the public teaser and the MVP shell.

**In the prototype today:**

- Hero + the five-pillar framing and gentle disclaimer.
- **Choose Your Struggle** — 12 struggles, each mapped to a pathway + surahs (interactive).
- **Qur'an Pathways** — 10 pathways with an animated path-draw map.
- **The 114 Surah Map** — all 114 surahs, searchable/filterable; ~15 curated "deep" cards.
- **Surah life maps** — curated featured cards (theme, what it repairs, situations, key ayahs,
  reflection questions, action, dua, modern application, common mistake).
- **Qur'an Repair Engine** — symptom → one ayah, one repair (interactive).
- **Life Crisis Mode** — calm anchor + explicit emergency-help disclaimer.
- **Nafs Patterns** — three Qur'anic states of the self (classical lens).
- **99 Names Pathways** — a curated set matched to struggles.
- **7-Day Repair Plans** — tabbed weekly journeys.
- **Heart Reflection Tool** — gentle Q&A → suggested pathway.
- **Daily Tazkiyah Tracker** — Read → Reflect → Act → Dua → Repeat (browser localStorage + streak).
- **Scholar Review Status** — a transparency table.

**Prototype constraints (intentional):**

- All copy is framed as *"reflection inspired by Qur'anic themes"* — never authoritative tafsir.
- Detailed reflections are **drafts, marked scholar-review pending**.
- ~15 surahs have full cards; the remaining surahs carry a short theme only.
- Ayah numbering follows the standard (Hafs) count; translations are paraphrase and **must be
  cited** before any production launch.
- All styling/JS is scoped under `.tz`; no other EcoIQ pages are affected.

This document does not change the prototype. Building the full product (below) is future work.

---

## 4. Trust & scholar-review principles

The product earns trust through **radical transparency about what is and isn't reviewed**.

- **Reflection, not tafsir.** We say *"reflection inspired by Qur'anic themes"*, never *"this
  surah means exactly…"*. Authoritative meaning belongs to qualified scholarship.
- **No fatwas, no diagnoses, no spiritual promises.** The product never issues rulings, never
  diagnoses mental illness, and never promises a specific outcome.
- **Every interpretive unit is labelled.** Each card/page/pathway carries a content-status label
  and (once added) its translation/tafsir sources, reviewer, and last-updated date.
- **Sources are cited.** Qur'an translation and tafsir references are attributed; nothing
  interpretive ships unattributed.
- **A review pipeline gates publication** (see workflow below).

**Content status labels**

| Label | Meaning |
|---|---|
| `Draft Reflection` | Authored, not yet sourced or reviewed. |
| `Source Added` | Translation/tafsir references attached; awaiting scholar. |
| `Needs Scholar Review` | In the scholar queue. |
| `Scholar Reviewed` | Approved by a qualified reviewer (name/date/confidence optional). |
| `Sensitive Topic — Review Required` | High-sensitivity; requires scholar **and** wellbeing review before publishing. |

**Scholar review workflow**

```
Author drafts            → Draft Reflection
  add translation/tafsir  → Source Added
  submit                  → Needs Scholar Review   (scholar queue)
  scholar approves        → Scholar Reviewed        (publishable)
   ↘ if sensitive topic   → Sensitive Topic — Review Required
                             (scholar + wellbeing reviewer, BOTH required)
Any change to an ayah/translation/source re-opens review.
```

Roles: **Author · Source-checker · Scholar · Wellbeing reviewer · Editor.** A public
"Content Status" view should list what is reviewed versus pending.

**Potential reference sources to integrate later** (licensing must be cleared first):
Tafsir Ibn Kathir, Tafsir as-Sa'di, Tafsir al-Jalalayn, The Clear Quran, Sahih International.
Treat each `SourceRef` with a license state: `owned | licensed | permission_pending | public_domain`.
Do not ship full translation/tafsir text until licensing/permission is confirmed.

---

## 5. Content safety rules

These are non-negotiable and must be enforced in code (e.g. lint/CI), not left to discipline.

1. **Status badge + sources are mandatory** on every interpretive component. Unlabelled
   interpretive content must fail CI.
2. **Humble framing only** — "reflection inspired by Qur'anic themes"; never "means exactly".
3. **No fatwas, no medical/clinical claims, no diagnosis, no predictions.**
4. **Permanent trust note** on every page:
   > "This platform is for Qur'anic reflection and personal growth. It does not replace qualified
   > scholars, tafsir study, therapy, medical support, legal advice, or fatwa. Where interpretation
   > is provided, it should be reviewed by qualified Islamic knowledge holders."
5. **Crisis / grief / "about to sin" / money-desperation content** is high-sensitivity: it must
   route to professionals and emergency services, must carry the disclaimer
   *"This is not a fatwa, not therapy, and not a diagnosis. It is a guided Qur'anic reflection
   tool,"* and must pass wellbeing review.
6. **Privacy first.** Journaling is private and local-first; no selling data; clear export and
   delete. Cloud sync is opt-in only.
7. **Anti-addiction by design.** No infinite scroll, no follower counts, no vanity likes, no
   public worship comparison, no shaming on missed days.
8. **Copyright discipline.** No full tafsir/translation text until licensed; attribute and verify
   even public-domain sources.
9. **Gentle language for pain.** The "Dark Night of the Soul" pathway must not promise instant
   relief or imply punishment; it offers companionship, sabr, dua, and small next steps only.

---

## 6. MVP roadmap

| Phase | Goal | Ships |
|---|---|---|
| **0 · Teaser (done)** | Validate the concept publicly | The Django `/tazkiyah-114/` prototype page. |
| **1 · MVP** | Prove the *spine* loop end-to-end | Choose Your Struggle · 114 Surah Map · Surah page (Level 1 + curated 2/3) · Ayah-to-Action engine · Daily Tazkiyah Companion · Life Crisis Mode (core states) · Heart Journal (local-first) · 3–4 7-Day Plans · static Pathway Map · **full trust + status labels** · manual scholar queue. |
| **2 · Depth** | Make it complete and sticky | All Nafs Patterns · all 7-Day Plans · 99 Names expansion · Prophetic Character Builder · Real-Life Roles · Family Mode · Money/Rizq Repair · interactive Pathway Map ("wow" visual) · accounts + cloud sync · journal insights · scholar review CMS · Do/Don't shareable cards. |
| **3 · Scale (careful)** | Reach and assist, safely | Bounded AI Reflection Companion · safe Community / "Muslim benefit feed" · Dark Night of the Soul pathway (high-sensitivity) · notifications · localisation · audio/full-tafsir (licensing permitting). |

**MVP rule of thumb:** ship the spine (struggle → ayah → action → dua → journal → track) with
hand-authored, clearly-labelled content for ~15 surahs and the 12 struggles. Everything else is
depth added once the loop is proven.

---

## 7. Future feature layers

Grouped by the layer they add. None are MVP.

- **Reflection depth:** One-Surah-Three-Levels (Understand / Reflect / Live) for all 114;
  Heart Mirror; Prophetic Character Builder; Nafs Patterns (full set).
- **Life-context layers:** Qur'an for Real-Life Roles (parent, founder, student, grieving…);
  Money / Rizq / Rizq-fear repair (ethical wealth, Maqasid al-Shariah, stewardship);
  Family Mode (today's family ayah, child question, bedtime dua, character of the week).
- **Action & habit:** Ayah-to-Action engine; 7-Day Repair Plans (all nine); Daily Tazkiyah
  Companion; Heart Journal insights (recurring struggles, surahs studied, actions completed,
  duas, gratitude, nafs patterns, traits developing).
- **The signature visual:** the interactive Pathway Map —
  *Heart Wounds → Qur'anic Pathways → Surahs → Ayahs → Actions → Character change.*
- **Sharing:** Do/Don't life-correction cards as beautiful, non-vanity shareable content.
- **High-care:** Dark Night of the Soul pathway (Phase 3, highest sensitivity).
- **Community (Phase 3, safe-by-design):** anonymous reflections, family circles, halaqa groups,
  scholar-reviewed reminders, 7-day group challenges, private accountability partners, "I
  benefited from this" instead of likes, **no follower counts by default.**
- **AI Reflection Companion (Phase 3, strictly bounded):**
  - *May:* help find a pathway from a selected struggle; suggest reflection questions; convert
    ayah themes into small actions; privately summarise journal patterns; recommend 7-day plans;
    remind users to seek a scholar / therapist / professional when needed.
  - *Must not:* issue fatwas; claim to speak for Allah; give definitive tafsir unless sourced and
    reviewed; diagnose mental illness; replace therapy; make spiritual promises.

---

## 8. Launch gates

A phase may not ship until **all** of its gates pass.

**Phase 1 (MVP) gates**

- The spine flow works end-to-end (struggle → ayah → action → dua → journal → track).
- The first ~20 content cards are at least `Source Added`.
- The **Trust Note and status labels are present and non-removable** (enforced in CI).
- **Life Crisis Mode** content has passed a wellbeing-aware review and carries the standard
  disclaimer + emergency routing.
- Journal data is private and local-first with working export/delete.
- No fatwas, diagnoses, predictions, or unlabelled interpretive content anywhere.

**Phase 2 gates**

- Every published interpretive page is `Scholar Reviewed` (or clearly labelled otherwise).
- Scholar review CMS workflow is operational with named reviewers and last-updated dates.
- All licensed translation/tafsir text has confirmed licensing.

**Phase 3 gates**

- AI Companion passes red-team testing against every "must not" rule before exposure to users.
- Community features pass a safety/moderation and anti-addiction design review.
- Dark Night pathway passes scholar + wellbeing review and routes clearly to professional help.

---

## 9. What must NOT be added before scholar review

The following are **blocked** until qualified scholarly (and, where noted, wellbeing) review:

- **Definitive tafsir or "this ayah means X" statements.** Only labelled reflection is permitted
  pre-review.
- **Any fatwa, ruling, or fiqh guidance.** Route these needs to qualified scholars instead.
- **Full tafsir/translation text** (Ibn Kathir, as-Sa'di, Jalalayn, Clear Quran, Sahih
  International, etc.) — blocked until **licensing/permission is confirmed**.
- **High-sensitivity content** — "about to sin", suicide-adjacent crisis, deep grief, the Dark
  Night pathway, money desperation — blocked until scholar **and** wellbeing review.
- **99 Names pages presented as authoritative** — the curated set must be reviewed before being
  treated as more than reflection.
- **The AI Reflection Companion** — do not expose to users until the trust layer, content corpus,
  and guardrails are mature and red-teamed (Phase 3).
- **Any predictive, mystical, "energy", or fortune-telling framing** — permanently prohibited,
  not merely deferred. The Heart Mirror must always read as *"a guided reflection based on what
  you selected."*

Promote content from *draft* to *public-authoritative* only by moving it through the
[scholar review workflow](#4-trust--scholar-review-principles).

---

*Last updated: 2026-06-19 · Status of this document: living brief, pending scholar advisory input.*
