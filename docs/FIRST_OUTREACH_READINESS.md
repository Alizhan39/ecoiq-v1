# First Real Outreach Readiness (PR12)

## What this adds

PR2-11 built a real, evidence-backed truth chain from signal to pilot
launchpad. Nothing in that chain, until now, asked the one question that
actually matters before contacting a real person at a real organisation:
**is this genuinely the right organisation to contact, for a legitimate
reason, through the correct route?**

PR12 adds `outreach_readiness`, a deliberately separate, stricter
governance layer sitting between "EcoIQ has a real opportunity and a
resolved organisation" and "a real message leaves this system." It
produces, at most, a founder-reviewed message ready to send — it never
sends one. `EXTERNAL_OUTREACH_ENABLED = False` in `ecoiq/settings.py`
is hardcoded, not environment-configurable, and no code path in this PR
reads it to perform a send.

## An evidence source is not automatically the organisation responsible for acting on the evidence

This is the central discipline of the whole app, and the reason it
exists as a separate model set rather than an extension of PR5's
`OutreachDraft`. `OutreachCandidateAssessment.recipient_role` forces an
explicit choice between seven real roles — `source_of_information`,
`responsible_authority`, `potential_implementer`, `funder`,
`resource_provider`, `research_body`, `referral_body` — and
`services/assessment.record_recipient_responsibility_test()` structurally
rejects (`suitability_state = 'wrong_organisation'`) any candidate whose
recipient role is `source_of_information` alone. A reviewer cannot
accidentally skip this: setting the role to `source_of_information` *is*
the rejection, not a separate step someone might forget.

This exact mechanism was run against all ten real earthquake
`GoodOpportunity` rows this repository currently holds (all sourced from
the USGS significant-earthquakes feed). Every one of them resolves, via
the existing PR5/PR7 `responsible_party.suggest_from_signal()`, to USGS —
and USGS's real, honest role for any single already-published earthquake
event is `source_of_information`: it operates the monitoring feed and
public data API the signal came from, not a disaster-response function
for individual events. All ten were therefore correctly, structurally
rejected as `wrong_organisation`, with a system recommendation of
`do_not_send` on every one. See the final report for the full walk-through.

## Preparing an outreach message does not establish a partnership, endorsement, consent, obligation, or commitment

Stated on every assessment page, the Founder Send Review page, and the
Pilot Launchpad integration. A `SUITABLE` verdict, an approved message,
a passing risk review, and a passing dry run together mean only that a
human may now consider sending something — never that anything has been
agreed, promised, or committed to.

## Recipient responsibility test

`services/assessment.record_recipient_responsibility_test()` requires
every field to be a real, checked claim, never inferred from an
organisation's name or sector: `identity_confirmed`,
`remit_confirmed_for_this_issue` (with a written `remit_rationale`),
`geographic_relevance_confirmed`, and `capability_evidence_reference` (a
soft pointer into the real Capability Graph evidence, e.g.
`capability_graph.OrganisationCapability:12` — never free-typed
evidence). `limitations` is deliberately not optional in spirit — a real
capability claim almost always has a real limit worth stating.

## Minimum viable ask

`OutreachCandidateAssessment.minimum_viable_ask` is a single free-text
field, deliberately not a menu of pre-approved requests — the discipline
is enforced by the risk checklist (`request_proportionate`,
`request_answerable`), not by constraining what a human can type.
Explicitly out of scope by the same checklist: partnership, endorsement,
funding commitment, confidential information, immediate operational
action, legal advice, religious certification, broad consultancy, or
access to victims/vulnerable people.

## Sensitivity review

`services/assessment.record_sensitivity_review()` records which of ten
real categories apply (disaster, death/injury, children, health,
war/conflict, vulnerable communities, legal disputes, religion, personal
data, emergency response) and, separately,
`evidence_valid_but_outreach_inappropriate` — the exact distinction Phase
13 requires: marking a case sensitive never itself blocks outreach; only
this second, explicit flag does, and it maps to `suitability_state =
'too_sensitive'`, a terminal state.

## Fact / inference / request / unknown

`OutreachMessageVersion` stores `fact_points`, `inference_points`,
`the_request`, and `unknowns` as four separate JSON lists — never
collapsed into one prose block. This survives verbatim into the
Assessment page, the Founder Send Review page, and the dry-run snapshot.

## Risk controls

`OutreachRiskReview` is a mandatory 15-item checklist, one per message
version (a new version always needs its own fresh review). Every field
defaults `False` — an item not explicitly reviewed never silently
"passes." `founder_approve()` (services/message.py) structurally refuses
to run unless `risk_review.all_passed` is `True`.

## Message versioning and approval invalidation

`services/message.create_message_version()` always creates the next
version number; if the prior version had reached `'approved'`, creating a
new one automatically invalidates it (`services/message.invalidate_version()`)
— an edit after approval can never leave a stale approved version
sitting alongside a newer, unreviewed one.

## Human review roles

`OutreachReviewRole` tracks who held `drafter` / `reviewer` /
`founder_approver` on a given assessment. `services/roles.role_summary()`
reports `single_reviewer_limitation: True` whenever the same real person
held more than one role — surfaced directly on both the Assessment page
and Founder Send Review, never hidden behind an implied "independently
reviewed" status that didn't happen.

## Dry run

`services/dry_run.run_dry_run()` snapshots exactly what would be sent —
recipient route, subject, body, sender identity, transport mode — and
validates it, but imports and calls no send function of any kind. A
regression test (`DryRunTests.test_dry_run_never_calls_send_mail`) mocks
`django.core.mail.send_mail` and asserts it is never touched by a dry
run.

## Transport audit

`services/dry_run.transport_audit()` reuses PR9's
`has_real_mail_transport()` (same `EMAIL_BACKEND` check, same repo — no
second transport-detection mechanism) and reports one of
`REAL_EMAIL_TRANSPORT` / `MANUAL_EMAIL` / `PUBLIC_CONTACT_FORM_MANUAL` /
`OTHER_VERIFIED_PUBLIC_CHANNEL` / `NO_TRANSPORT`. Locally, with no real
SMTP credentials configured, this is honestly `NO_TRANSPORT` /
`MANUAL_EMAIL` depending on route type — never `REAL_EMAIL_TRANSPORT`.

## External delivery switch

`ecoiq.settings.EXTERNAL_OUTREACH_ENABLED = False`, hardcoded (not read
from an environment variable) so that turning it on is a deliberate code
change for a later, separate, explicitly-reviewed PR to make — never a
deploy-time configuration someone could accidentally leave enabled. No
function in `outreach_readiness` reads this flag to perform a send; it
exists purely as the gate a future PR must add real transport behind.

## Founder approval

`services/founder_review.compute_recommendation()` is a pure, explainable
read — it may suggest `send` / `revise` / `do_not_send` with real,
listed reasons, but `services/founder_review.record_decision()` is the
only thing that makes a decision real, and it always requires an actual
human actor. There is no AI-callable path to `record_decision()` at all
— Phase 27's "AI may not approve send" is enforced by the function's
absence from any AI-facing surface, not by a runtime check that could be
bypassed. A regression test confirms the founder's real decision can
diverge from — and overrides — the system's computed recommendation.

## Duplicate / contact history

`services/duplicate_check.prior_outreach_history()` checks two real,
existing sources: PR5's `OutreachDraft` rows already marked `sent` for
the same organisation, and any prior `FounderSendDecision` with
`decision='send'` for the same organisation on a different opportunity.
No do-not-contact registry model exists yet in this PR — none has ever
been needed, since nothing has ever been sent — so this reports what
genuinely exists today rather than fabricating a history mechanism ahead
of having real data to check (see Known Limitations).
