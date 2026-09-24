# Governed routing and one durable risk workflow

This increment builds on PR #337's source snapshots. It implements an internal
API workflow; it does not deploy a worker, send messages, connect external
systems, or replace the existing scoring/model engines.

## Shared audit

`AgentRun.observatory_session` joins routing to the existing AI Observatory.
Project runs retain the initiating actor, source snapshot IDs and hashes,
chosen route, route reason, estimated cost, physical model attempts and actual
provider token usage. Background analysis passes the citations it actually
placed in the prompt to this boundary. Sources and permissions are checked
again before a scoped model call; changed/expired sources are refused.

Routing estimates are explicitly estimates. Actual billed USD is **unknown**
unless a future billing integration supplies it. Failed calls may lack usage;
missing usage is NULL, not zero. The workflow below makes no model calls.
The token/call recorder remains best-effort telemetry, with its existing error
logging. Durable workflow events use the strict `record_event` helper in the
same transaction as the business transition; they cannot silently disappear.
This is not a cryptographically immutable audit store.

Scoped model runs claim execution once. Repeated completed/blocked/review-needed
executions do not invoke a provider again. A process killed during a provider
request leaves a `running` record: investigate provider billing/outcome before
an explicit new run. Exactly-once external inference is not claimed. Legacy
unscoped executions retain compatibility and are not retrofitted with a guessed
project or actor.

## Implemented workflow

1. Reuse `detect_red_flags` to detect a paid capital movement without evidence.
2. Create one durable `RiskFollowUp` task and internal document request, keyed
   to that project's risk. Repeated starts return the same task, including its
   final outcome; reopening a finished case is a future explicit operation.
3. Accept a current project EvidenceMemory record attached to the exact capital
   movement. Keep a versioned citation; an unrelated or inaccessible source is
   rejected. This uses the existing evidence store, not another upload system.
4. Automatically refresh the deterministic risks and recalculate the existing
   Capital Protection Score after document submission. Store its components
   and a digest binding the result to the source/trigger/document revision.
5. Wait for another project reviewer to approve or reject that exact version
   with a rationale. A changed source, stale score, revoked role, wrong digest,
   or self-approval is refused. Approval never verifies the document, authorises
   payment, or asserts that a score increase proves a risk was eliminated.

Analysts/managers start, submit and resume; reviewers/managers review; project
readers inspect. Staff retain their established project permissions, but cannot
self-approve a task they started or supplied evidence for.

The modelled task is the document request. `document_requested` means it is
available inside the project API; `sent_externally=false` is explicit. There
are no email/Slack notifications in this increment.

## API

Session authentication and normal CSRF protection apply. Obtain the CSRF cookie
through the existing session endpoint; do not bypass it. The server derives the
actor from the authenticated session and the project from the permitted slug.

| Endpoint | Operation |
|---|---|
| `GET /api/v2/projects/{slug}/risk-workflows/` | List up to 100 project tasks |
| `POST` to the same URL | `{"rule_key":"evidence_missing_123"}`; detect and start |
| `GET /api/v2/projects/{slug}/risk-workflows/{id}/` | State, source, score, review and shared trace |
| `POST` to task URL | `{"action":"document","memory_id":456}`; submit and automatically advance |
| `POST` to task URL | `{"action":"resume"}`; resume a ready/failed local step |
| `POST` to task URL | `{"action":"recalculate"}`; refresh changed scoring inputs |
| `POST` to task URL | `{"action":"review","decision":"approved","assessment_digest":"<returned digest>","notes":"<review rationale>"}`; `rejected` is also supported |
| `GET /api/v2/projects/{slug}/audit/{session_id}/` | Project-scoped shared audit trace |

Source snapshots and derived score/trace are withheld on source-access revocation.
Every review records actor, time, rationale, decision and exact assessment digest.
The API is the usable interface in this increment; no new frontend screen is
claimed. Existing UI work remains in PR #337.

## Failure and recovery

Database transactions, project/task row locks and unique event keys prevent
duplicate local transitions. A failed scoring step rolls back its partial work,
records an error **type** (never secret-bearing exception text), and remains
resumable. Three total scoring attempts are allowed. Exhaustion requires an
operator investigation; repeated document submission cannot reset the budget.

If a process stops after the document commit and before scoring, POST `resume`
uses the persisted `ready` task. If it stops inside the scoring transaction,
the database rolls that transaction back. If the response is lost after commit,
a replay returns the already persisted result and does not create another
request/review. Unchanged explicit recalculation is also a no-op.

Source corrections invalidate the old pending assessment and require a new
review. A reviewer cannot approve against stale project scoring outputs. The
digest binds the outputs used for review; it is not a snapshot of every unrelated
project table or a claim of global serialisability against legacy writers.

SQLite tests verify repeat delivery, saved-state recovery, fault injection,
bounded retries, CSRF, project roles, stale sources/assessments, no self-review
and audit rollback. PostgreSQL concurrent-worker testing remains a release
gate before enabling background parallel workers. No such workers are enabled
by this change.

## Release and next stage

Apply the additive migrations for `ai_observatory`, `agent_runtime_model_router`
and `capital_guardian`, after PR #337. No production migration/deployment is
performed by this PR. Old AgentRun rows are not assigned invented sessions.

External connectors and religious corpora follow the contract in
`KNOWLEDGE_AND_CONNECTOR_GATES.md`; they are not live integrations yet.
