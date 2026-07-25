# First Legitimate Public Action (PR14)

## What this adds

PR13 proved EcoIQ can find real, actionable UK public-need candidates
with real, named, evidenced responsible bodies — a genuine improvement
over PR12's earthquake-only baseline. It did not yet decide *what to do*
about any of them. PR14 adds `public_action_preparation`: it takes ONE
real candidate PR13 already found `actionable` and prepares the exact
legitimate next action, choosing from 9 real types
(`use_official_public_process`, `submit_consultation_response`,
`request_programme_clarification`, `refer_to_existing_service`,
`request_public_data`, `surface_funding_route`,
`propose_zero_capital_connection`, `prepare_outreach`, `no_action`) —
never defaulting to email, never executing anything externally.

## An important event is not automatically an actionable EcoIQ opportunity — and being actionable is not automatically permission to act

This app deliberately reuses, never duplicates, PR13's own real
findings. `services.action_type.recommend_action_type()` reads
`public_need_discovery.PilotCandidateAssessment` and
`CandidateOrganisationRole` directly — jurisdiction, confirmed
justifying roles, and whether an official process was already found —
and only ever recommends within what those real rows support.
`ActionTypeDecision.opportunity` is a `OneToOneField` on the same
`good_agents.GoodOpportunity` every governance layer in this lineage
anchors to.

## Do not make a fuel-poverty referral without a real beneficiary

The real case this PR was built to get right. `ACTION_TYPES_REQUIRING_
REAL_BENEFICIARY = {'refer_to_existing_service'}` — `services.action_
type.record_action_type_decision()` structurally raises
`ActionTypeNotAllowedError` if `refer_to_existing_service` is selected
without both `has_real_beneficiary=True` *and* a real, non-empty
`beneficiary_basis_notes` explanation (setting the flag alone is not
enough). `recommend_action_type()` never suggests
`refer_to_existing_service` even when a `referral_body` role is
confirmed — it recommends `request_programme_clarification` instead,
with an explicit reason citing this exact rule.

Real demo: opportunity #6 ("Fuel poverty", North Yorkshire County
Council, real `referral_body` role confirmed via
`capability_graph`/PR13) was walked end-to-end. No beneficiary exists —
EcoIQ has no real resident asking for help — so the system correctly
recommended, and a human correctly selected,
`request_programme_clarification`: a real, narrow, low-risk question
("does North Yorkshire County Council operate a public fuel-poverty
referral/signposting service, and what is the correct entry point?"),
never a fabricated referral.

## Do not invent a still-open consultation

`VerifiedOfficialProcess.status` is never 'open' merely because a
reviewer selects it — `services.process_verification.record_process_
verification()` structurally overrides `status` to `'expired'` whenever
a real recorded `closing_date` has already passed, regardless of what
status value was submitted. `services.readiness.compute_action_
readiness()` returns `'blocked'` for any candidate whose verified
process is expired, and `services.founder_review.compute_recommendation()`
recommends `do_not_proceed` for it.

Real demo: two real candidates were checked against their real,
live web pages via `WebFetch`, not assumed:

- Opportunity #3, "Barrow Borough Local Plan — Preferred Options Draft"
  (Barrow Borough Council): the real `data.gov.uk` page states the
  consultation ran July-August 2015 and the Council had already moved
  to a "Publication Draft" stage by 2016 — closed for over a decade.
  Recorded `status='expired'`, `closing_date=2015-08-31`. Readiness:
  `blocked`. Founder recommendation: `do_not_proceed`.
- Opportunity #5, "Local Transport Plan Consultation 2024" (City of
  York Council): the real page states the consultation closed 4
  February 2024 — verified but not yet recorded in this PR's live
  walkthrough (left in `not_assessed` in the real demo state to show a
  genuinely untouched real candidate alongside the two fully-walked
  ones).

## Official process verification

`VerifiedOfficialProcess` records real, human-checked facts only —
process name, owning organisation, official URL, route type, opening/
closing date, eligibility, required information, submission format,
evidence allowed, acknowledgement semantics, and `checked_notes`
explaining *how* it was verified (Phase 3's own instruction: never
invent a deadline or eligibility rule). `last_checked_at`/
`last_checked_by` are always a real actor and a real timestamp.

## Evidence pack and 114-principle relevance

`services.evidence_pack.build_evidence_pack()` is a pure read
composition — real `WorldSignal` source records, PR13's jurisdiction and
confirmed roles, and `good_agents.services.pilot_launchpad.principle_
relevance()` reused directly rather than reimplemented (the same real,
persisted `AgentActivationRecord` rows PR6 already produces). Missing
evidence stays reported as missing (`what_ecoiq_does_not_know`), never
filled with invented prose.

## Content drafting is never one generic template

`services.content_draft` maps each action type to its own real content
type (`consultation_response`, `referral_brief`, `clarification_
question`, `data_request`, `connection_proposal`) — `prepare_outreach`
and `no_action` are explicitly excluded from this module entirely
(`DRAFTABLE_ACTION_TYPES`); `prepare_outreach` hands off to PR12's own
`outreach_readiness.services.message`, never a second outreach-drafting
mechanism. A referral brief with `required_fields_missing` populated
cannot be founder-approved until every field is filled (Phase 9: "do
not mark request complete merely because a text response exists").

Versioning mirrors `outreach_readiness.OutreachMessageVersion` exactly:
editing after founder approval never mutates the approved row — it
creates the next version and invalidates the old one.

## Ethics review

A stricter, action-specific checklist than PR13's upstream sensitivity
gate (which stays unmodified): vulnerability, health/financial
hardship, personal data risk, representation risk (no claimed
consensus/mandate), consent, misrouting risk, wasted-public-resources
risk, implied-authority risk. Every field defaults `False`; `all_passed`
requires every one explicitly set `True` by a real reviewer.

## The 10-state readiness ladder

`services.readiness.compute_action_readiness()` — never a stored field,
always recomputed: `not_assessed`, `needs_evidence`, `needs_process_
verification`, `needs_responsible_body`, `needs_action_definition`,
`needs_ethics_review`, `ready_for_content_review`, `ready_for_founder_
action_review`, `blocked`, `rejected`. `ready_for_founder_action_review`
is never returned unless ethics review has genuinely passed and — for
content-draftable action types — a real founder-approved draft exists.

## Founder Action Review

The one real decision this app exists to gate.
`services.founder_review.compute_recommendation()` is a pure,
deterministic read (`proceed`/`revise`/`do_not_proceed`, with real
reasons); `record_decision()` is the only way to make a choice real,
and always requires a real human actor — no `ai_generated` path exists
anywhere in this module (Phase 16's own explicit rule).

## Do not send/submit/refer/apply/contact anything

`EXTERNAL_PUBLIC_ACTIONS_ENABLED = False` is hardcoded in
`ecoiq/settings.py`; no code path in `public_action_preparation` reads
it. No view imports `safe_fetch`, `httpx`, or `send_mail` (enforced by
a regression test). Recording a `PROCEED` decision only ever writes one
`FounderActionDecision` row.

## Disclaimers

**"An important event is not automatically an actionable EcoIQ
opportunity."**

**"An evidence publisher is not automatically the responsible
recipient."**

**"A real, evidenced beneficiary is required before EcoIQ may propose a
referral — a real public need is not, by itself, a real beneficiary."**

**"A Founder Action Decision does not create a partnership, contract,
funding commitment, or obligation, and does not perform any real
external submission, referral, application, or contact."**
