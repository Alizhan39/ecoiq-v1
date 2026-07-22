# Funding Matcher

`good_agents.services.funding_matcher.suggest_funding_matches` is
deliberately the most conservative service in PR3.

## Why

No real grant/investor/philanthropy database exists anywhere in this repo
(confirmed during the PR3 Phase 0 verification — only finance-scoped
opportunity models exist elsewhere, none of them a funder directory). A
"funding matcher" with no real funder data behind it can only ever suggest
*categories* worth a human researching, never assert a verified match.

## What it actually does

For each relevant funder type (filtered by `FUNDER_TYPE_RELEVANT_THEMES` —
e.g. `green_finance` only suggested for energy/environment/climate/
biodiversity/waste-themed opportunities, never irrelevantly spammed onto
every opportunity), creates a `FundingMatch` starting at
`'potentially_relevant'`.

**Structural guarantee, not just a service default**: `FundingMatch.save()`
itself forces `eligibility_status='requires_sharia_review'` whenever
`funder_type` is `waqf` or `islamic_finance` and someone tries to set
`'eligible'` — this cannot be bypassed by calling the model directly,
only by a real, separate Sharia-review process this PR does not implement
(see `docs/GOOD_AGENT_SAFETY.md`). This system **never** determines Sharia
compliance itself.

## Status: DONE (architecture + honest defaults) / MISSING (real funder data)

- **DONE**: theme-filtered suggestion, Sharia-sensitive routing (enforced
  at the model layer), idempotent per (opportunity, funder_type), tested.
- **MISSING**: no real funder directory, no real eligibility-criteria
  matching — every `FundingMatch` created today says so explicitly in its
  `notes` field ("No real funder database is connected yet").
