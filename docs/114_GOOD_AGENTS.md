# 114 Good Agents

## Why this doc exists

Before writing any code for this feature, a full repository audit was run
(see `docs/GOOD_AGENTS_PROGRESS.md` for the complete area-by-area map). It
found **three separate, non-cross-referenced "114 principles" datasets**
already in this repo, none of them scholar-reviewed, none of them agreeing
with each other:

1. `core/esg_principles_data.py` — `PRINCIPLES`, 114 dicts. Public,
   English-only, powers `/governance-principles/`. Its Arabic/Surah
   derivation is documented separately in
   `docs/governance-principles-surah-map.md`, marked **INTERNAL ONLY — not
   for public distribution**.
2. `core/views.py`'s hardcoded `_SURAHS` list (114 entries), powering
   `/tazkiyah-114/` and `/surah-map/`.
3. `content/tazkiyah114/surah_seeds.json` (114 entries), each carrying
   `scholar_review_status: scholar_review_pending` — i.e. explicitly none
   of these 114 are scholar-reviewed yet either.

**Decision: `core/esg_principles_data.PRINCIPLES` is the canonical source**
for `good_agents.models.GoodAgentDefinition.principle_id` — it is the only
one of the three that is public, English, DB-independent, and does not
carry an unresolved review-status field that would make "canonical" a
misleading claim. This decision was confirmed with the user rather than
made unilaterally, given all three disagree.

The other two datasets are **not modified, removed, or merged** by this
work — they remain exactly as they were. A future decision to reconcile
all three into one canonical, scholar-reviewed principle store is
out of scope here and would need its own ADR and human sign-off (see
Phase 23 / `docs/GOOD_AGENT_SAFETY.md`).

## What a GoodAgentDefinition is

One canonical principle, re-expressed as a specialised lens for
opportunity discovery:

```python
class GoodAgentDefinition(models.Model):
    principle_id            # 1-114, from core.esg_principles_data.PRINCIPLES
    name                     # from the canonical source, never invented
    category                 # from the canonical source
    arabic_name              # optional; if set, arabic_name_review_status
                             # auto-defaults to 'needs_scholar_review'
    mission                  # the canonical "question" field
    domains                  # list[str] — used by Layer 1 deterministic filter
    signal_types             # list[str] keywords — used by Layer 1
    search_questions          # list[str] — what this lens should ask
    evidence_requirements     # list[str] — what evidence this lens needs
    risk_flags                # list[str] — known failure modes for this lens
    default_priority          # tie-break ordering
```

Only 6 of the 114 have a row today (seeded by
`good_agents/management/commands/seed_good_agent_definitions.py`), chosen
for relevance to the first vertical-slice demo (energy poverty /
coal-to-clean-heating): Protection of Vulnerable Groups (#4), Ecological
Stewardship & Land Ethics (#9), Visible Consequences & Accountability
Culture (#19), Illumination & Energy Transition (#34), Kneeling &
Equitable Access (#45), The Sun & Energy as Shared Resource (#91). Adding
more is a data task (extend `SEED_LENSES` in that command), not a code
change — the framework already supports all 114.

## Never fabricated

No Arabic/Surah name is presented anywhere in this app's UI or API as
verified religious authority. `arabic_name_review_status` exists precisely
so a future scholar-review pass has somewhere real to record its
conclusion, rather than the app silently asserting one.
