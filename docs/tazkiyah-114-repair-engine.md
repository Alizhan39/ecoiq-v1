# Tazkiyah 114 — Qur'an Repair Engine

> Concise architecture note for the **Qur'an Repair Engine** — the transformation core of
> Tazkiyah 114. It turns a real-life struggle into one small, doable repair action.
>
> All interpretive content is **reflection inspired by Qur'anic themes** — never tafsir, fatwa,
> therapy, or diagnosis. Dua lines are **prompts**, not narrated du'as unless sourced. Nothing
> interpretive ships without scholar review (and wellbeing review where sensitive). See the
> [safety principles](tazkiyah-114-safety-principles.md).

---

## 1. What it is

A repeatable **repair journey**, not a reader. The user starts at a named struggle and is walked
to one concrete change:

```
Struggle → Heart Wound → Qur'anic Theme → Surah Pathway → Reflection → Dua → One Action → 7-Day Tracking
```

## 2. The 8-step engine flow

| Step | What happens | Safety frame |
|---|---|---|
| 1 · Choose your struggle | Pick a named struggle (or describe one) | — |
| 2 · Name the hidden wound / false belief | Surface the heart-wound + the lie underneath | "a reflection, not a diagnosis" |
| 3 · Qur'anic reflection | Theme-based reflection | "inspired by Qur'anic themes" |
| 4 · Surah pathway + ayah references | 2–4 surahs, key ayahs with **translation source** | citations shown |
| 5 · Reflection questions | 2–4 honest questions to sit with | — |
| 6 · One repair action for today | A single, small, doable action | transformation over reading |
| 7 · Make dua | A dua **prompt** in the user's own words | not a narrated du'a unless sourced |
| 8 · Track 7 days | Daily check-in: read / reflect / act / dua / journal | streak = *practice done*, never shaming |

## 3. Modules (lenses on the same engine)

Each module reframes the engine for a context, and each carries a `scholar_review_status` and a
`safety_note`:

1. **Sin Cycle Breaker** — trigger → desire → sin → guilt → despair → repeat ⟶ awareness → tawbah → boundary → replacement → hope → consistency.
2. **Shaytan's Whisper vs Qur'an's Truth** — paired cards: whisper · Qur'anic truth · reflection · repair · dua prompt.
3. **The Lie I Believe** — false belief → Qur'anic correction · pathway · question · action · dua · 7-day practice.
4. **Qur'anic Decision Compass** *(non-fatwa)* — reflection questions only; routes rulings to scholars.
5. **Character Defect Repair** — pride→humility, envy→contentment, anger→restraint, etc.
6. **Relationship Repair** — with explicit boundaries + safety; patience is never acceptance of abuse.
7. **Rizq Anxiety Pathway** — rizq is written, effort still required; tawakkul ≠ laziness; halal effort is worship.
8. **Women's Heart Pathways** — dignity- and worth-before-Allah centred, non-stereotypical.
9. **Youth Mode** — modern, gentle, non-shaming.
10. **Founder / Leader Mode** — power without arrogance, money without corruption, amanah, shura.
11. **Daily Life Sunnah Integration** — micro-moments (before work, before posting, after a mistake…).
12. **30-Day Heart Reset** — flagship guided program (read → reflect → act → dua → journal).

## 4. Content model (every pathway)

```yaml
pathway:
  title:
  user_struggle:
  heart_wound:
  false_belief:
  quranic_theme:           # themes addressed — NOT a verdict
  surah_pathways: []       # [{ num, name, why }]
  ayah_references: []      # [{ ref, translation, source }]  # source REQUIRED before publish
  reflection_text:
  reflection_questions: []
  repair_action:           # ONE small action for today
  dua_prompt:              # in the user's own words; not a narrated du'a unless sourced
  journal_prompt:
  seven_day_practice: []
  opposite_virtue:         # for character/defect pathways
  boundary_note:           # for relationship/abuse-adjacent pathways
  safety_note:
  scholar_review_status:   # author_draft | source_added | needs_scholar_review |
                           # scholar_reviewed | sensitive_review_required
  sources: []              # translation/tafsir refs + license state
  last_updated:
```

## 5. Trust & safety (non-negotiable)

- Framing is always *"Qur'anic reflection" / "inspired by Qur'anic themes"* — never "means exactly…".
- Not a fatwa, therapy, diagnosis, or official tafsir. Permanent trust note on every page.
- No interpretive content ships without scholar review; status label + sources are mandatory.
- High-sensitivity modules (Sin Cycle, grief, abuse-adjacent relationships, money desperation,
  self-worth collapse) require scholar **and** wellbeing review and route to professional/emergency help.
- Relationship content never counsels staying in abuse; boundaries + safety routing always present.
- Privacy-first journaling; anti-addiction by design (no vanity metrics, no infinite scroll, no shaming).

## 6. Sample pathways (drafts — pending scholar review)

Fully-populated example pathways for **Jealousy → Contentment**, **Repeated Sin → Breaking the
Cycle**, and **Rizq Anxiety → Trusting the Provider** are maintained as seed content for the build.
Each fills every field in the content model above, with cited ayah references and a
`scholar_review_status` of `draft_reflection` (or `sensitive_review_required` where applicable).

---

## Related documents

- [Documentation index](README.md)
- [Architecture brief](tazkiyah-114-architecture.md)
- [Transformation Operating System](tazkiyah-114-transformation-operating-system.md)
- [Modules 31–60](tazkiyah-114-modules-31-60.md)
- [Safety principles](tazkiyah-114-safety-principles.md)
- [Implementation roadmap](tazkiyah-114-implementation-roadmap.md)

*Last updated: 2026-06-20.*
