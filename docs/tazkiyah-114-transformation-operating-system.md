# Tazkiyah 114 — Transformation Operating System

> **Status:** Product architecture (concept). Living document, pending scholar advisory input.
>
> Tazkiyah 114 / The Surah Map is **not** a Qur'an translation website. It is a guided
> *transformation operating system*: a person starts from real-life pain and is walked through a
> repeatable repair journey toward one small, doable change.
>
> Everything interpretive here is **reflection inspired by Qur'anic themes** — never tafsir,
> fatwa, therapy, or diagnosis. See
> [`tazkiyah-114-safety-principles.md`](tazkiyah-114-safety-principles.md) and the
> [scholar review layer](#e-scholar-review-layer). No interpretive content ships without review.

**The core loop, in one line:**

```
Pain → Qur'anic mirror → Heart diagnosis → Ayah reflection → Dua → Action → Habit tracker → Review
```

---

## A. Surah Map

114 Surahs presented as **114 life pathways**. Each pathway is a structured object that connects a
surah's theme to a lived struggle and a concrete next step.

Each Surah pathway connects:

| Field | Meaning |
|---|---|
| **Surah theme** | The pathway's central theme (reflection, not a verdict on the surah). |
| **Life struggle** | The real-world pain this pathway speaks to. |
| **Heart disease / virtue** | The disease it helps repair and/or the virtue it builds. |
| **Ayah reflection** | A short, humble reflection anchored in key ayahs (with cited translation). |
| **Practical action** | One small action for today. |
| **Dua prompt** | A dua *prompt* in the user's own words — **not** a narrated dua unless sourced. |
| **Tracker habit** | The habit to track across 7 days. |
| **Review status** | `author_draft → source_added → needs_scholar_review → scholar_reviewed`. |

**Design notes**
- ~15 surahs ship as fully-authored "deep" pathways at MVP; the rest appear with a short theme
  and are clearly marked *scholar-review pending*.
- Ayah numbering follows the standard (Hafs) count. Translations are paraphrase **until cited**.
- A surah may belong to multiple pathways (e.g. Yusuf → patience, hope, betrayal-recovery).

---

## B. Struggle Finder

The primary on-ramp. The user starts from **pain**, not from knowing which surah to read. The
finder maps a struggle to one or more Surah pathways.

**Categories**

- **Emotional states** — anxiety, sadness, loneliness, numbness, fear, restlessness.
- **Sins and repentance** — repeated sin, shame, guilt, "too late" despair.
- **Salah struggles** — missing prayers, distraction, heaviness, consistency.
- **Family and marriage** — conflict, distance, resentment, communication, patience.
- **Parenting** — overwhelm, anger, guilt, raising character, presence.
- **Grief and loss** — bereavement, miscarriage, divorce, lost dreams.
- **Money and rizq** — fear of poverty, debt, haram temptation, comparison.
- **Social media / digital nafs** — comparison, addiction, validation-seeking, wasted time.
- **Time** — procrastination, heedlessness, busyness without barakah.
- **Speech** — backbiting, harshness, lying, complaining, silence against injustice.
- **Body** — neglect, abuse, shame, gratitude for health (non-medical).
- **Leadership / power** — arrogance, corruption-temptation, amanah, shura.
- **Decision making** — fear-driven choices, paralysis, istikhara, seeking counsel.

Each struggle resolves to: **recommended pathway → first ayah → one reflection question →
"begin a 7-day repair."**

---

## C. Repair Engine

The repeatable engine behind every pathway and module.

```
1. Pain            — name the struggle in plain language
2. Qur'anic mirror — the engine reflects the pain back through a Qur'anic theme
3. Heart diagnosis — surface the likely heart-wound / false belief (reflection, not diagnosis)
4. Ayah reflection — 1–3 key ayahs (cited) + a short, humble reflection
5. Dua             — a dua prompt in the user's own words
6. Action          — ONE small repair action for today
7. Habit tracker   — track read / reflect / act / dua / journal across 7 days
8. Review          — content is labelled and flows through scholar review before publish
```

**Principles**
- One action beats passive reading; the engine always ends in a doable step.
- The tracker counts *practice done*, never *app opened*; missed days are never shamed.
- The engine never issues a ruling, a diagnosis, or a promise of outcome.

---

## D. Daily Mizan

A daily two-part reflection practice (a "balance" check). Gentle, private, journal-backed.

**Morning**
- **Intention** — what am I doing today for Allah?
- **Weakness to guard** — which slip am I most likely to make today?
- **Name of Allah to remember** — one Name to carry through the day (e.g. As-Sabur, Ar-Razzaq).
- **One action** — one concrete good deed I commit to.

**Evening**
- Where did I obey Allah today?
- Where did I slip?
- Who did I hurt?
- What blessing did I ignore?
- What do I ask forgiveness for?
- What do I thank Allah for?

**Notes**
- The evening review is **muhasabah-style self-reflection**, framed gently — never spiritual
  shame or scorekeeping. Toxic positivity and harsh self-judgment are both out of place here.
- Entries are private and local-first. Over time (Phase 3) the journal surfaces patterns
  (recurring slips, blessings noticed, Names returned to) — privately, never publicly.

---

## E. Scholar Review Layer

No interpretive content is published without review. The workflow is explicit and auditable.

```
author_draft → source_added → needs_scholar_review → scholar_reviewed → publishable
```

- **Sensitive topics** (sin/addiction/despair, grief, abuse-adjacent relationships, money
  desperation, body/health, self-worth collapse) additionally require a **wellbeing reviewer** —
  scholar **and** wellbeing reviewer, both, before publish.
- **Any change** to an ayah, translation, source, or sensitive wording **reopens review**.
- Every page renders its status, sources, reviewer (optional), and last-updated date.
- A public **Content Status** view lists what is reviewed versus pending.
- Reference sources (e.g. Tafsir Ibn Kathir, Tafsir as-Sa'di, Tafsir al-Jalalayn, The Clear
  Quran, Sahih International) are integrated **only after licensing/permission is cleared**.

Roles: **Author · Source-checker · Scholar · Wellbeing reviewer · Editor.**

---

## F. Community Layer — safe-by-design

**This is not "Instagram for Muslims."** It deliberately avoids vanity metrics, public worship
comparison, follower obsession, arguments, and infinite scroll.

**Features (Phase 5)**
- Anonymous reflections
- Family circles
- Sisters circles
- Youth circles
- Founders circles
- Grief circles
- 7-day group challenges
- Private accountability partners
- **"I benefited from this"** instead of likes
- **No follower count by default**

**Design rules**
- No public ranking of worship; no leaderboards of ibadah.
- No infinite scroll; circles are small, bounded, and purpose-led.
- Moderation and a wellbeing escalation path are prerequisites, not afterthoughts.
- Default to privacy and anonymity; identity and visibility are opt-in.

---

## Related documents

- [Architecture brief](tazkiyah-114-architecture.md)
- [Modules 31–60](tazkiyah-114-modules-31-60.md)
- [Safety principles](tazkiyah-114-safety-principles.md)
- [Implementation roadmap](tazkiyah-114-implementation-roadmap.md)
- Seed content: `content/tazkiyah114/moduleSeeds.ts`

*Last updated: 2026-06-19.*
