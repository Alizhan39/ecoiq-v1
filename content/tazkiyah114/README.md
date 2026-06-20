# Tazkiyah 114 — Seed Content

Seed/structured content for the **Tazkiyah 114 / Surah Map** product concept.

> ⚠️ **This is not public, authoritative content.**
>
> These files exist **for product structure only** — to shape data models, components, and review
> tooling. They are **reflection inspired by Qur'anic themes**, not tafsir, not a fatwa, not therapy,
> and not a diagnosis.
>
> **Before any public use, every record requires:** a verified Qur'an translation source, tafsir
> references, source checks, and qualified **scholar review** (plus **wellbeing review** for
> sensitive content). Nothing here is `approved_for_public`.

## Files

| File | Purpose | Status |
|---|---|---|
| `surah_seeds.json` | All 114 surahs (1–114) as Surah-Card seed records (schema-aligned). | `draft_reflection` — all pending scholar review |
| `moduleSeeds.ts` | Seed concepts for modules 31–60. | `draft_reflection` |

## Schema

Field definitions follow [`docs/tazkiyah-114-content-schema.md`](../../docs/tazkiyah-114-content-schema.md)
(the **Surah Card** entity). Each record carries the review/status fields
(`content_status`, `source_status`, `translation_status`, `tafsir_status`,
`scholar_review_status`, `wellbeing_review_required`, `sensitivity_level`, `reviewed_by`,
`last_reviewed_at`, `notes`).

## Review workflow (summary)

```
draft_reflection → source_needed → translation_pending → tafsir_pending
→ scholar_review_pending → (wellbeing_review_required if sensitive)
→ approved_for_preview → approved_for_public
```

A record may only be shown publicly once it reaches `approved_for_public` through the review
workflow. The current seed is at most preview material, clearly labelled and not scholar-approved.

## Validation

`surah_seeds.json` is guarded by a lightweight validator so future edits cannot silently break
the 114-surah structure. It checks: valid JSON; exactly 114 records; contiguous and unique
numbers 1–114; the identical 18-field schema/order on every record; every record marked
`draft_reflection` / `translation_pending` / `scholar_review_pending`; `_meta.authoritative = false`;
`_meta.scope` covering all 114 surahs; and a humble safety note on every record. It exits non-zero
on any failure.

```bash
# Run the validator directly
python manage.py validate_tazkiyah114_seeds

# Or as part of the test suite (CI guardrail)
python manage.py test core.tests_tazkiyah_seeds
```

Validation logic: `core/management/commands/validate_tazkiyah114_seeds.py`
(reused by `core/tests_tazkiyah_seeds.py`).

## Safety notes

- Themes are intentionally **short and cautious**; no detailed tafsir, no invented interpretation.
- Translations are paraphrase placeholders (`translation_pending`) until a cited, licensed source
  is attached.
- Revelation-type classifications are the commonly cited ones; some are disputed and must be
  verified in review (see per-record `notes`).
- Any change to a translation, source, or sensitive wording reopens review.

See also: [`docs/tazkiyah-114-safety-principles.md`](../../docs/tazkiyah-114-safety-principles.md)
and the [documentation index](../../docs/README.md).

*Last updated: 2026-06-20.*
