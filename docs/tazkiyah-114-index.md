# Tazkiyah 114 — Documentation Index

**Tazkiyah 114 / The Surah Map** — a Qur'an-inspired reflection and action platform that helps
people move from a real-life struggle to Qur'anic guidance, reflection, action, dua, journaling,
and long-term tazkiyah. **114 Surahs → 114 life pathways.**

> All interpretive content is *reflection inspired by Qur'anic themes* — never tafsir, fatwa,
> therapy, or diagnosis. Nothing interpretive publishes without scholar review.

## Documents

| Document | What it covers |
|---|---|
| [Architecture brief](tazkiyah-114-architecture.md) | Product vision, core UX flow, current prototype scope, trust & scholar-review principles, MVP roadmap, launch gates. |
| [Transformation Operating System](tazkiyah-114-transformation-operating-system.md) | Full architecture: Surah Map · Struggle Finder · Repair Engine · Daily Mizan · Scholar Review Layer · Community Layer. |
| [Modules 31–60](tazkiyah-114-modules-31-60.md) | Structured product concepts for modules 31–60. |
| [Safety & Trust Principles](tazkiyah-114-safety-principles.md) | Binding safety, trust, and anti-vanity rules. |
| [Implementation Roadmap](tazkiyah-114-implementation-roadmap.md) | Phases 1–6 with gates. |

## Scholar review workflow

Defined in the
[Transformation OS → Scholar Review Layer](tazkiyah-114-transformation-operating-system.md#e-scholar-review-layer)
and summarised in the [Safety Principles](tazkiyah-114-safety-principles.md#7-content-status-labels):

```
author_draft → source_added → needs_scholar_review → scholar_reviewed → publishable
```

Sensitive topics require **scholar + wellbeing reviewer**. Any change to an ayah, translation,
source, or sensitive wording **reopens review**.

## Seed content

- `content/tazkiyah114/moduleSeeds.ts` — seed-ready structured content for modules 31–60.

## Current prototype

A working single-page prototype lives in the EcoIQ Django project at `/tazkiyah-114/`
(alias `/surah-map/`). This documentation set defines the full product it can grow into.

*Last updated: 2026-06-19.*
