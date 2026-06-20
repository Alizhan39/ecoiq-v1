# Tazkiyah 114 — Content Schema

> **Status:** Schema proposal (documentation only). Defines how Tazkiyah 114 content — Surahs,
> pathways, repair cards, crisis modes, nafs patterns, money/rizq modules, and tracker content —
> *should* be stored and reviewed before becoming live.
>
> **No database models are created here.** No live pages, routes, or navigation are changed. This
> is a future-facing schema so content can be authored, sourced, reviewed, and gated safely.
>
> Every interpretive record is **reflection inspired by Qur'anic themes** until reviewed — never
> tafsir, fatwa, therapy, or diagnosis. See [Safety rules](#8-safety-rules).

---

## Conventions

- **Type** uses simple, storage-neutral names: `string`, `text`, `int`, `enum`, `bool`,
  `string[]`, `object[]`, `datetime`. They map cleanly to JSON, Django fields, or a TS type later.
- **Required** = must be present before the record can leave `draft_reflection`.
- Every interpretive record carries review/status fields (see [Review Workflow](#7-review-workflow)).
  Shared review fields are defined once here and referenced by each entity:

| Field | Type | Notes |
|---|---|---|
| `content_status` | enum `ReviewStatus` | Overall lifecycle state (see §7). |
| `source_status` | enum | `source_needed` → `source_added`. |
| `translation_status` | enum | `translation_pending` → `translation_added`. |
| `tafsir_status` | enum | `tafsir_pending` → `tafsir_referenced`. |
| `scholar_review_status` | enum | `scholar_review_pending` → `scholar_reviewed`. |
| `wellbeing_review_required` | bool | True for sensitive content; gates publish. |
| `sensitivity_level` | enum | `standard` \| `sensitive` \| `crisis`. |
| `last_reviewed_at` | datetime | Set on each review action. |
| `reviewed_by` | string | Reviewer name/id (optional, shown when present). |
| `sources` | object[] | `{ kind: 'translation' \| 'tafsir', name, locator, license }`. |
| `version` | int | Incremented on any change; change reopens review. |

---

## 1. Surah Card

| Field | Type | Required | Notes |
|---|---|---|---|
| `surah_number` | int (1–114) | yes | Primary identity. |
| `surah_name_arabic` | string | yes | e.g. `الفاتحة`. |
| `surah_name_transliteration` | string | yes | e.g. `Al-Fatihah`. |
| `surah_name_translation` | string | yes | e.g. `The Opening`. |
| `revelation_type` | enum `meccan \| medinan` | yes | Standard classification; verify in review. |
| `short_theme` | string | yes | A brief thematic label (reflection, not a verdict). |
| `life_pathways` | string[] | no | Pathway keys this surah belongs to. |
| `repair_areas` | string[] | no | Heart wounds/virtues it speaks to. |
| `source_status` | enum | yes | See shared fields. |
| `translation_status` | enum | yes | |
| `tafsir_status` | enum | yes | |
| `scholar_review_status` | enum | yes | |
| `wellbeing_review_required` | bool | yes | Usually false for surah-level cards. |
| `content_status` | enum `ReviewStatus` | yes | |
| `last_reviewed_at` | datetime | no | |
| `reviewed_by` | string | no | |

---

## 2. Ayah Reflection Card

| Field | Type | Required | Notes |
|---|---|---|---|
| `ayah_reference` | string | yes | e.g. `Ar-Ra'd 13:28` (standard/Hafs numbering). |
| `arabic_text` | text | no | Optional; must be verified if shown. |
| `translation` | text | yes | Paraphrase until a cited source is attached. |
| `translation_source` | object | yes-before-publish | `{ name, license }` (e.g. The Clear Quran). |
| `tafsir_references` | object[] | yes-before-publish | `[{ name, locator }]`. |
| `reflection_summary` | text | yes | "Reflection inspired by Qur'anic themes." |
| `heart_wound` | string | no | The wound it speaks to. |
| `life_area` | string | no | e.g. anxiety, rizq, repentance. |
| `action_step` | string | yes | One small action. |
| `dua_prompt` | string | yes | A prompt, **not** a narrated du'a unless sourced. |
| `sensitivity_level` | enum | yes | `standard \| sensitive \| crisis`. |
| `review_status` | enum `ReviewStatus` | yes | |

---

## 3. Qur'an Repair Engine Card

| Field | Type | Required | Notes |
|---|---|---|---|
| `struggle` | string | yes | Plain-language entry ("I'm scared about money"). |
| `hidden_wound` | string | yes | The wound/false belief beneath it. |
| `quranic_theme` | string | yes | Theme addressed — not a verdict. (`qur_anic_theme`) |
| `correction` | text | yes | The gentle Qur'anic reframe. |
| `action_today` | string | yes | One small action. |
| `dua_prompt` | string | yes | In the user's own words. |
| `evening_check` | string | no | A muhasabah prompt for the evening. |
| `related_surahs` | int[] | no | Surah numbers. |
| `related_names_of_allah` | string[] | no | e.g. `Ar-Razzaq` (need source + review). |
| `safety_note` | text | yes | Routing for sensitive/crisis cases. |
| `review_status` | enum `ReviewStatus` | yes | |

---

## 4. Life Crisis Mode Card

| Field | Type | Required | Notes |
|---|---|---|---|
| `crisis_type` | string | yes | e.g. about-to-sin, grief, despair, money panic. |
| `immediate_reminder` | text | yes | One ayah/theme to hold (cited before publish). |
| `grounding_action` | string | yes | A calming, immediate step. |
| `next_10_minutes_action` | string | yes | One thing to do in the next 10 minutes. |
| `dua_prompt` | string | yes | A prompt. |
| `emergency_support_note` | text | yes | **Always present.** Routes to emergency/professional help. |
| `wellbeing_review_required` | bool | yes | **Always true** for crisis content. |
| `sensitivity_level` | enum | yes | **`crisis`** for this entity. |
| `review_status` | enum `ReviewStatus` | yes | Cannot reach `approved_for_public` without scholar + wellbeing review. |

---

## 5. Nafs Pattern

| Field | Type | Required | Notes |
|---|---|---|---|
| `pattern_name` | string | yes | e.g. `An-Nafs al-Ammarah`, or `comparison`. |
| `modern_signs` | string[] | yes | How it shows up in daily life. |
| `heart_root` | text | yes | The root it grows from. |
| `quranic_correction` | text | yes | Theme-based correction. (`qur_anic_correction`) |
| `opposite_virtue` | string | yes | The virtue to build. |
| `seven_day_plan` | string[] | no | Seven short day-steps. |
| `related_surahs` | int[] | no | |
| `related_names_of_allah` | string[] | no | Need source + review. |
| `review_status` | enum `ReviewStatus` | yes | |
| `sensitivity_level` | enum | yes | Often `sensitive` (e.g. despair). |

---

## 6. Money/Rizq Module

| Field | Type | Required | Notes |
|---|---|---|---|
| `module_name` | string | yes | e.g. `Rizq Emergency Mode`. |
| `master_category` | enum `fear \| halal \| barakah \| justice \| family \| growth` | yes | |
| `user_problem` | string | yes | The money pain. |
| `quranic_principle` | text | yes | Principle/theme (reflection). (`qur_anic_principle`) |
| `reflection_questions` | string[] | yes | |
| `action_steps` | string[] | yes | Small, doable. |
| `audit_questions` | string[] | no | For monthly muhasabah modules. |
| `professional_advice_required` | bool | yes | True for debt/crisis/legal modules. |
| `scholar_review_required` | bool | yes | True wherever riba/zakat/contracts are near. |
| `review_status` | enum `ReviewStatus` | yes | |
| `sensitivity_level` | enum | yes | |

> Money/rizq content is **not financial advice, not a fatwa, not a zakat calculator, not a riba
> ruling**, and uses **no prosperity-gospel language**. See [Safety rules](#8-safety-rules).

---

## 7. Review Workflow

`ReviewStatus` is the lifecycle enum every interpretive record moves through:

| Status | Meaning |
|---|---|
| `draft_reflection` | Authored; inspired by Qur'anic themes; not sourced/reviewed. |
| `source_needed` | Needs a verified translation source. |
| `translation_pending` | Translation not yet attached/verified. |
| `tafsir_pending` | Tafsir references not yet cited. |
| `scholar_review_pending` | In the scholar queue. |
| `wellbeing_review_required` | Sensitive/crisis content awaiting wellbeing review. |
| `approved_for_preview` | Cleared to show in the labelled preview/prototype only. |
| `approved_for_public` | Cleared for public educational use. |
| `archived` | Withdrawn / superseded; retained for history. |

**Rules**
- A record reaches `approved_for_public` only after: source added → translation added → tafsir
  referenced → scholar reviewed → (if sensitive/crisis) wellbeing reviewed.
- Crisis content (`sensitivity_level = crisis`) and sensitive content require **scholar + wellbeing**
  approval before `approved_for_public`.
- Any change to an ayah, translation, source, or sensitive wording **increments `version` and
  reopens review** (drops back to the appropriate pending state).
- The current live prototype content is at most `approved_for_preview` — clearly labelled, never
  presented as scholar-approved.

```
draft_reflection
  → source_needed → (source added)
  → translation_pending → (translation added)
  → tafsir_pending → (tafsir referenced)
  → scholar_review_pending → (scholar approves)
  → [if sensitive/crisis] wellbeing_review_required → (wellbeing approves)
  → approved_for_preview → approved_for_public
  (archived at any point; any change → back to a pending state)
```

---

## 8. Safety rules

Binding for every record and for the schema itself:

- **Not a fatwa. Not therapy. Not a diagnosis.**
- **No tafsir fabrication.** Reflections are theme-based; authoritative meaning requires cited
  sources and scholar review.
- **No prosperity-gospel language.** Never imply worship guarantees wealth.
- **No shaming poverty.** Worth before Allah is never a balance.
- **No promises of wealth for worship.**
- **Crisis content requires wellbeing review** (and scholar review) before public use.
- **Religious rulings require qualified scholars** (riba, zakat, contracts, fiqh).
- Serious debt/legal/financial or mental-health crisis routes to **professionals and emergency
  services**; the schema enforces an always-present `emergency_support_note` on crisis cards.
- Framing language: *"reflection inspired by Qur'anic themes" · "pending scholar review" ·
  "source needed" · "not fatwa / not therapy / not diagnosis."*

---

## 9. Future implementation plan

This schema is intentionally storage-neutral so it can become, in stages:

1. **JSON seed files** — author content as `content/tazkiyah114/*.json` matching these field names
   (the existing `content/tazkiyah114/moduleSeeds.ts` is the precedent). Cheap, reviewable in PRs,
   no infra. Good for the preview prototype.
2. **Django models** — promote each entity to a model (e.g. `SurahCard`, `AyahReflection`,
   `RepairCard`, `CrisisCard`, `NafsPattern`, `MoneyModule`) with the shared review fields on an
   abstract base (`ReviewableContent`). Status as a `TextChoices` enum; `version` auto-increments;
   a signal reopens review on relevant field changes.
3. **Admin review workflow** — Django admin actions + list filters by `content_status`,
   `sensitivity_level`, and `wellbeing_review_required`; per-role permissions
   (Author / Source-checker / Scholar / Wellbeing reviewer / Editor); a public "Content Status" view.
4. **Next.js content API** — a read-only API that serves **only** `approved_for_public` (or
   `approved_for_preview` behind a preview flag), so unreviewed content can never leak to users.
5. **Scholar review dashboard** — a queue UI showing pending items, sources, diffs since last
   review, reviewer assignment, confidence, and last-reviewed dates; sensitive items require the
   second (wellbeing) sign-off before they can be marked public.

**Migration note:** start at stage 1 (JSON seeds) for the preview, then introduce the
`ReviewableContent` base and models (stage 2) before any public launch — nothing reaches
`approved_for_public` outside the review workflow.

---

## Related documents

- [Documentation index](README.md)
- [Transformation Operating System → Scholar Review Layer](tazkiyah-114-transformation-operating-system.md#e-scholar-review-layer)
- [Qur'an Repair Engine](tazkiyah-114-repair-engine.md)
- [Modules 31–60](tazkiyah-114-modules-31-60.md)
- [Money & Rizq Deep System](tazkiyah-114-money-rizq-deep-system.md)
- [Safety principles](tazkiyah-114-safety-principles.md)
- Seed precedent: `content/tazkiyah114/moduleSeeds.ts`

*Last updated: 2026-06-20.*
