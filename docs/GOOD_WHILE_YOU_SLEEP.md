# Good While You Sleep

## What this is today

`GoodDiscoveryRun` (`good_agents.models.GoodDiscoveryRun`) is the
Observatory's actual unit of work. PR3 added real STAGED, CHECKPOINTED
execution (Phase 13): `current_stage` + `stage_checkpoints` record
completion of each of `fetch_signals → normalise → deduplicate → cluster →
triage → activate_agents → verify_evidence → create_candidates →
match_resources → run_better_way → rank → generate_brief`, so a second
call with the same `idempotency_key` resumes rather than redoing
already-completed stages — this is exercised directly in
`good_agents.tests.DiscoveryEngineTests.test_checkpoint_stages_recorded`
and `.test_run_is_idempotent`.

`GoodMission` (PR3) is the standing configuration a human defines once
(`name`, `geographies`, `themes`, `principle_ids`, `capital_budget_usd`,
`run_cost_budget_usd`, `risk_tolerance`, `min_confidence`,
`max_opportunities`, `schedule`, `enabled`) and re-runs — see
`seed_dogfood_mission` for an example config row.

Two ways to run a discovery pass:

```bash
# PR2's original path — a human-authored signal, unchanged:
python manage.py run_almaty_good_agent_demo

# PR3's new path — raw, unclustered, un-vetted signals in, Morning Brief out:
python manage.py run_overnight_good_discovery_demo
```

or programmatically via `good_agents.services.discovery_run.run_discovery`
(PR2, unchanged) or `good_agents.services.discovery_engine.run_global_discovery`
(PR3, new).

There is also a Celery task, `good_agents.tasks.run_good_discovery_task`,
following this repo's existing on-demand `@shared_task` pattern (see
`backend_intelligence_engine/tasks.py`) — this wraps PR2's `run_discovery`
only; `run_global_discovery` is not yet wrapped in a Celery task (its
`opportunity_builder` callback isn't JSON-serialisable across the wire —
an honest limitation, not silently worked around).

## What "Observatory" does NOT mean yet — read this before assuming otherwise

The Phase 0 audit found **zero** existing code anywhere in this repository
implementing continuous signal scanning: no Celery beat schedule, no cron
entry in `render.yaml`, no ingestion loop that watches the world and
produces `Signal` objects on its own. `amanah_autopilot/` (an existing app
literally named for "overnight checks") has no `models.py` at all — it is a
UI-copy shell, not a running process, and `render.yaml`'s Celery
worker/Redis block is commented out in production ("NOT enabled by
default... a real, additional cost decision").

This still does **not** fix that in PR3. `run_global_discovery` takes an
explicit `raw_signals` list supplied by the caller (a management command,
a test, or in future a real provider adaptor) — it does not source signals
from the internet itself. This is a deliberate scope boundary, not an
oversight:

- **DONE**: bounded/resumable/checkpointed/idempotent run tracking at
  stage granularity, cost-budget enforcement, `duplicates_removed`/
  `rejected_opportunities`/`insufficient_evidence_count` metrics (Phase 30
  false-positive control), Celery task wrapper (PR2's path only).
- **TODO**: real signal sourcing (a web/document search or ingestion feed
  that produces raw signal dicts continuously); a real
  `django-celery-beat` schedule (would also require enabling the
  commented-out Celery worker in `render.yaml` — an infrastructure/cost
  decision for a human, not something this PR does unilaterally per
  CLAUDE.md's standing rule against ad-hoc deploy-config changes); wrapping
  `run_global_discovery` itself in a Celery task (blocked on the
  `opportunity_builder` callback not being JSON-serialisable — a future PR
  would need a registry-of-named-builders pattern instead of an arbitrary
  callable).
- **BLOCKED**: true "while you sleep" execution needs the commented-out
  Celery worker turned on in production, which is a deploy/cost decision
  outside this PR's scope.

## Morning Brief (PR3 Phase 16-18)

`good_agents.services.morning_brief.build_brief(run)` assembles entirely
from `run` and its related, already-persisted rows — every number is real,
never computed ad hoc or fabricated for display. It adds **Top 3 Actions**
(`morning_brief.top_3_actions`) — an AttentionPriority ranking (urgent +
evidence-gap + high-leverage weighted) that suppresses low-value noise
rather than showing every opportunity as equally important, exactly as
Phase 18 asks. `/good-agents/morning-brief/`
(`good_agents.views.morning_brief`) renders both the original PR2 view and
the new Top 3 Actions section.
