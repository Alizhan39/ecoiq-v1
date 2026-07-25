# Actionable Public-Need Discovery (PR13)

## What this adds

PR12 proved that EcoIQ must not contact an information publisher merely
because its feed generated a signal — all ten real `GoodOpportunity`
rows at the time were USGS earthquake events, and USGS's real role for
any single event is `source_of_information`, never a legitimate
outreach recipient. That finding surfaced the real bottleneck: it was
never outreach infrastructure. It was signal quality and actionability.

PR13 adds `public_need_discovery`, a bounded, evidence-driven layer that
sits between discovery (`good_agents.GoodOpportunity`, already
evidence-gated) and `outreach_readiness` (PR12's governance layer for
actually contacting a real organisation). It answers one question PR12
assumes has already been answered: **is this genuinely an actionable
need, and who really has the remit to act on it?** — never "is this
worth telling someone about?" (discovery's job) and never "is this safe
to email?" (`outreach_readiness`'s job).

## An important event is not automatically an actionable EcoIQ opportunity

A `GoodOpportunity` passing the existing evidence gate means the
underlying signal is credible and interesting. It does not mean a real
organisation has a real, evidenced remit to act on it, that a
legitimate small action exists, or that outreach — as opposed to an
existing official process — is even the correct next step.
`PilotCandidateAssessment.actionability_state` (`informational_only`,
`potentially_actionable`, `actionable_needs_review`, `actionable`,
`wrong_recipient`, `no_responsible_body_identified`, `no_clear_action`,
`insufficient_evidence`, `sensitive_review_required`) makes this
distinction explicit and separately tracked from
`GoodOpportunity.status`.

## An evidence publisher is not automatically the responsible recipient

The same discipline PR12 built, applied one stage earlier.
`ORGANISATION_ROLE_CHOICES` deliberately separates `evidence_publisher`
and `jurisdiction_authority` from the five roles that actually justify
progressing a candidate — `responsible_authority`,
`potential_implementer`, `funder`, `resource_provider`, `referral_body`
(`ROLES_THAT_JUSTIFY_ACTIONABILITY`). `services.roles.record_role()`
lets a real organisation hold several of these roles simultaneously —
each an independent `CandidateOrganisationRole` row with its own
evidence reference and human confirmation — never collapsed into one
field. `services.actionability.evaluate_candidate()` will not recommend
`actionable` while every *confirmed* role is `evidence_publisher`/
`jurisdiction_authority` alone; it recommends `wrong_recipient` instead.

## When an official public process exists, EcoIQ should prefer that process over unsolicited outreach

`PilotCandidateAssessment.use_official_process` +
`official_process_type` (`general_contact`, `official_application`,
`consultation_submission`, `incident_report`, `referral_form`,
`grant_application`, `data_request`, `procurement_portal`,
`public_feedback`) let a reviewer record that the correct action is
already an existing process — a live example from this PR's real demo:
Barrow Borough Council's real, currently-solicited Local Plan
consultation. `services.qualification.promote_to_outreach_readiness()`
structurally refuses to promote a candidate marked
`use_official_process=True` — `QualificationNotAllowedError` is raised,
not silently ignored — so an actionable candidate whose correct path is
"submit evidence to the consultation" can never accidentally become an
unsolicited email instead.

## Jurisdiction resolution

Jurisdiction is free-text everywhere else in this repository
(`capability_graph.Organisation.jurisdiction`,
`outreach_readiness.OutreachCandidateAssessment.jurisdiction`) — this PR
does not introduce a competing structured model.
`services.jurisdiction.resolve_jurisdiction()` is a deterministic
lookup: prefer the opportunity's own real `region` field, fall back to
the originating signal's `region`, fall back to a fixed
`PUBLISHER_TO_JURISDICTION` table of real, known publishers (mirroring
`good_agents.services.responsible_party.PUBLISHER_TO_PARTY_TYPE`'s
existing discipline), and otherwise return the honest sentinel
`NO_JURISDICTION` rather than a guess parsed from free text.

## Responsible-body evidence

Every `CandidateOrganisationRole` carries an `evidence_reference` (a
soft pointer, e.g. `capability_graph.OrganisationCapability:12`, or a
real source URL) and a `rationale` — never a role inferred from an
organisation's name or sector alone.
`services.roles.suggest_roles_from_capability_graph()` only ever
*suggests* roles (created `confirmed=False`) by reading real, existing
`capability_graph.OrganisationCapability` edges through a fixed,
deterministic `capability → role` table
(`_CAPABILITY_TO_ROLE` — e.g. `regulate`/`respond_to_emergency` →
`responsible_authority`, `fund`/`grant` → `funder`); a human must still
call `record_role(..., confirmed=True)` before that suggestion counts
toward actionability.

## Small action and value-to-recipient

`services.small_action.record_small_action()` requires a real,
non-empty `description` — `SmallActionNotAllowedError` blocks a generic
"solve this problem" ask structurally, not by convention.
`SMALL_ACTION_TYPE_CHOICES` mirrors this PR's own worked examples
(submit evidence to a consultation, ask for the correct referral route,
clarify programme eligibility, surface a matching public grant, request
a missing public dataset, notify a data inconsistency, refer to an
existing programme, connect a resource to a need).

## Sensitivity handling

The same ten-category vocabulary PR12 uses
(`SENSITIVITY_CATEGORY_CHOICES`), applied one stage earlier so a
sensitive case can be flagged before any organisation is even
approached about it in the outreach layer.
`services.sensitivity.record_sensitivity_review(...,
outreach_inappropriate=True)` forces `actionability_state =
'sensitive_review_required'` — the exact `EVIDENCE_VALID_BUT_
OUTREACH_INAPPROPRIATE` distinction: evidence importance is never
confused with permission to progress.
`services.sensitivity.suggest_sensitivity_categories()` is a
deterministic keyword pass over the opportunity's own real title/
problem text — a starting point for a human reviewer, never itself a
decision.

## Discovery-qualified vs actionability-qualified vs outreach-suitable

Three separate, real booleans on `PilotCandidateAssessment` — never
collapsed into one flag. `discovery_qualified` reports the real,
already-happened evidence-gate outcome (`evaluate_cluster`).
`actionability_qualified` reflects whether `actionability_state` is
currently `actionable`/`actionable_needs_review`. `outreach_suitable`
is set only by a real, successful `promote_to_outreach_readiness()`
call — never inferred merely from `actionability_qualified`, since
outreach suitability additionally requires PR12's own suitability
review to genuinely pass, which promotion never fast-tracks.

## Human review

Every write in `public_need_discovery` requires a real actor — jurisdiction
resolution is the sole read-only exception (it is a deterministic
computation over already-public facts, not a judgement call).
`set_actionability_state()`, `record_role(..., confirmed=True)`,
`record_small_action()`, `record_official_process()`,
`record_sensitivity_review()`, and `promote_to_outreach_readiness()` all
raise a `NotAllowedError` subclass when `actor` is `None`. No function
in this app ever sets `actionability_state = 'actionable'`
automatically from a high match score — `evaluate_candidate()` only
ever returns a *recommendation* a human reviewer sees and may accept.

## Promotion never bypasses `outreach_readiness`'s own governance

`promote_to_outreach_readiness()` pre-fills a fresh
`outreach_readiness.OutreachCandidateAssessment` — `recipient_role`,
`organisation`, and a real call to PR12's own
`record_recipient_responsibility_test()` — using only this candidate's
own human-*confirmed* justifying role. It never touches
`suitability_state`; a promoted candidate starts, honestly, at
`not_ready`, and the same human actor (or another reviewer) must still
walk PR12's full suitability review, sensitivity gate, minimum viable
ask, route, message, risk checklist, dry run, and Founder Send Review
from scratch, through PR12's own unmodified code.

## Two new real providers

`good_agents/services/provider_adapters.py` (extended, not duplicated)
gains `fetch_govuk_consultations` (the same real, already-allowlisted
GOV.UK Search API, restricted to open consultations) and
`fetch_data_gov_uk_datasets` (the real, standard `data.gov.uk` CKAN
`package_search` API — a genuinely new domain, requiring a new
allowlist entry). Both reuse `safe_http.safe_fetch()` unmodified. A
real bug in that shared SSRF-hardened redirect handler
(`httpx.URL(...).join(...).human_repr()` — not a real method on the
installed `httpx` version) was found and fixed
(`str(httpx.URL(...).join(...))`) while live-testing the new
`data.gov.uk` adapter, whose real redirect chain
(`data.gov.uk` → `www.data.gov.uk` → `ckan.publishing.service.gov.uk`,
all genuine `.gov.uk`/GDS infrastructure) exercised a path the original
three adapters never had.

## Provider observability

`ProviderRunMetrics` — one row per `(SignalProvider, GoodDiscoveryRun)`,
never overwritten — reuses `GoodDiscoveryRun` as the real run anchor
(no second run/session concept) and the real `WorldSignal.provider` FK
to attribute qualitative funnel counts (informational-only,
potentially-actionable, actionability-qualified, rejected, missing
jurisdiction, missing responsible body, official routes found) back to
the exact provider that supplied each opportunity's lead signal.

## Do not send anything

This PR discovers and qualifies. It performs no external action: no
provider added here writes anywhere but `WorldSignal`/`GoodOpportunity`
via the existing, unchanged discovery pipeline; no view imports
`safe_fetch`, `httpx`, or `send_mail` (enforced by a regression test);
`promote_to_outreach_readiness()` never sets `outreach_readiness`'s
`suitability_state`, drafts a message, or records a founder decision.

## Disclaimers

**"An important event is not automatically an actionable EcoIQ
opportunity."**

**"An evidence publisher is not automatically the responsible
recipient."**

**"When an official public process exists, EcoIQ should prefer that
process over unsolicited outreach."**
