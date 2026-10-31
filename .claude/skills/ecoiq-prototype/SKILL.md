---
name: ecoiq-prototype
description: Build a throwaway, self-contained HTML/React prototype to explore an EcoIQ idea before committing to it — dashboards, calculators, scenario simulators, evidence graphs, KPI explorers, project-finance tools, Decision-to-Impact visualisations. Use when the goal is to see and react to a shape quickly. Not for anything that will ship: production work goes through Django templates plus the React islands in frontend/app.
---

# EcoIQ prototypes

A prototype exists to answer "is this the right shape?" and then to be
deleted. The moment it needs real auth, real permissions, or real evidence,
it stops being a prototype.

## Build it with the artifacts toolchain, not in the repo

Use the `anthropic-skills:web-artifacts-builder` skill for anything with
state, routing, or multiple components; a single-file HTML/SVG artifact for
anything simpler. Both are already available in this environment — no
install, no dependency added to EcoIQ.

Prototype files live in the session scratchpad, **not** in `frontend/app/`,
`templates/`, or `static/`. A prototype committed to the repo becomes
someone's production dependency within a week.

## Non-negotiables even for a throwaway

1. **Synthetic data only, and labelled as such.** Put a visible "Illustrative
   data — not EcoIQ output" marker in the UI itself, not just in the chat.
   Screenshots outlive their context and get pasted into decks.
2. **No real credentials, API keys, or `.env` values.** Ever, including
   read-only keys.
3. **No production endpoint calls.** A prototype must not hit the live API,
   a real database, or Stripe — not even in test mode.
4. **Do not reproduce a real company's score.** A plausible-looking EcoIQ
   score for a named real company is a fabricated assessment the moment
   anyone screenshots it. Use invented company names.
5. **Reuse the real palette** from `frontend/app/src/design/tokens.ts` so the
   prototype reads as EcoIQ (see `ecoiq-brand`) — but do not invent new
   tokens that then get back-ported.
6. **Accessibility is not deferred.** Keyboard reachable, visible focus,
   reduced-motion respected. Retrofitting is how it never happens.

## Promotion path — what changes when it ships

A prototype is a specification, not a starting codebase. Rebuilding is
expected. When promoting:

| Prototype does | Production must |
|---|---|
| Holds data in component state | Read through a Django view/serializer |
| Shows everything to everyone | Enforce `api/permissions.py` classes and tier/scope checks |
| Invents numbers | Terminate in a real evidence row or a deterministic formula in `ethics/` |
| Shows confidence as a nice bar | Carry real `confidence_tier` / `review_tier` — see `ecoiq-evidence-audit` |
| Displays an impact claim | Pass all six links in `ecoiq-impact-claims` |
| Ships as one HTML file | Become a Django template plus a React island in `frontend/app/src`, built to `static/dist/` |

**A prototype never becomes the production path by being deployed.** If
someone asks to "just point it at the real API", that is the rebuild, and it
goes through `ecoiq-security-review` and `ecoiq-release-gate`.

## Good candidates

Scenario simulators and calculators (fast feedback on input/output shape),
evidence graphs (hard to judge from a description), KPI explorers (density
and filtering decisions), Decision-to-Impact visualisations — noting that per
`ecoiq-khalifah-loop` several loop stages are scaffolds today, so a full-loop
visualisation is showing an intended architecture, and must say so.
