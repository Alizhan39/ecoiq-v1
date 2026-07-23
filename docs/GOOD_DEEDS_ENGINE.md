# Good Deeds Engine

`good_agents/services/good_deeds_engine.py` converts a qualified
`GoodOpportunity` into concrete next-step `GoodDeedAction` rows, each
tagged with an autonomy class.

## Autonomy classes

| Class | Meaning | Enforcement |
|---|---|---|
| GREEN | Safe autonomous preparation | No human gate required; can move straight to `completed`. |
| YELLOW | Human approval required before any external action | `GoodDeedAction.clean()` raises `ValidationError` if `status='completed'` and `human_approved` is not `True`. |
| RED | Capital/legal/contractual/physical execution | **Structurally unreachable.** No action type in `GoodDeedAction.ACTION_TYPE_CHOICES` maps to RED (`RED_ACTION_TYPES` is an empty frozenset) — see below for why. |

```python
GREEN_ACTION_TYPES = {
    'research', 'verify', 'analyse', 'compare', 'find_resource', 'find_funding',
    'find_partner', 'draft', 'recommend', 'prepare_application', 'prepare_policy_brief',
    'prepare_pilot', 'prepare_investment_memo', 'monitor',
}
YELLOW_ACTION_TYPES = {'match', 'connect', 'alert'}
RED_ACTION_TYPES = frozenset()
```

## Why RED is empty today

The Phase 0 repository audit (`docs/GOOD_AGENTS_PROGRESS.md`, area 11 —
Execution) found that this codebase has **no real execution/action-taking
layer at all**: the existing capital pipeline stops at
`CapitalAllocationDecision.approval_status='approved'`, and a human later
manually types in what happened via
`capital_guardian.services.execution_monitoring.record_monitoring_outcome`.
There is no code path anywhere in this repo that moves money, signs an
agreement, or executes physical works.

Rather than inventing a fake RED action type with no real execution behind
it, `GoodDeedAction`'s 17 action types were all classified GREEN or YELLOW,
and `RED_ACTION_TYPES` was left empty with a structural guarantee
(`GoodDeedAction.clean()` raises `ValidationError` unconditionally if
`autonomy_class == 'red'`) so that if a future PR adds a genuine execution
action type, it cannot silently default to GREEN/YELLOW — it must be
explicitly added to `RED_ACTION_TYPES` and will be rejected by `clean()`
until real execution + a dedicated approval workflow exists for it.

## Lifecycle

```python
propose_default_actions(opportunity)   # creates GREEN + (if zero_capital_possible) YELLOW rows
approve_action(action)                 # GREEN -> 'approved'; YELLOW -> human_approved=True, 'approved'; RED -> 'blocked'
complete_action(action, output_summary)  # raises ValueError if YELLOW/RED and not human_approved
```

Status DONE / PARTIAL / TODO:

- **DONE**: autonomy classification, structural RED block, action proposal
  from opportunity status, approval/completion lifecycle, tests.
- **TODO**: no code in this repo actually performs GREEN actions (e.g. no
  automated "research" web search) — `complete_action` only records that a
  human/process did the work and summarises it. Wiring GREEN actions to a
  real automated research/draft agent is future work.
