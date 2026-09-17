# Project access and execution context

`gold_intelligence.access` is the authority for project grants. Retrieval also
applies `evidence_memory.services.retrieval_policy` to each evidence record.
Company/country identifiers select relevant records; they never grant access.

| Active project role | Read evidence/results | Run analysis | Share evidence | Approve/reject decisions |
|---|---|---|---|---|
| Viewer | Yes | No | No | No |
| Analyst | Yes | Yes | No | No |
| Reviewer | Yes | No | No | Yes |
| Manager | Yes | Yes | Yes | Yes |

Active staff retain their existing cross-project authority. A role applies to
one project and requires an active account and active membership. Manager does
not grant staff status or permission to assign memberships. Only administrators
with Django model permissions can edit memberships in Django admin. Sharing
still requires the evidence's existing verification and visibility conditions.

## Identity and results

Decision Studio takes the actor from `request.user` and validates the selected
project against analysis grants. Suggested questions use the same selected
project. Follow-up questions inherit the parent's project and cannot switch it.
Reading a saved answer requires both its existing ownership rule and a current
project read grant; membership alone does not reveal another member's questions.
The form retains deterministic execution and its existing rate limit.

LangGraph and queued tasks accept server-supplied `requesting_user_id` and
`project_id`; they reload account and membership before execution. LangGraph
rechecks at every node and clears sensitive state if the grant is revoked.
Absent context preserves legacy memory-free execution. Partial, malformed or
revoked context fails closed. Retry arguments preserve both identifiers.

New DecisionQuery, OrchestrationRun and AgentRun records store a protected
project FK. Project results require a current read grant, and project agent
runs are excluded from shared workbench summaries and unscoped Council cases.
Idempotent agent reuse is project-scoped. Deleting a project with saved runs or
answers is blocked instead of making those records unscoped.

## Rollout and limits

Apply the four additive schema migrations with the normal release procedure,
then explicitly assign memberships in Django admin. There is no automatic
membership grant or production migration execution in this change. Deactivating
a membership revokes subsequent reads, searches and executions.

Existing unscoped runs keep their legacy visibility. Before rollout, review
historical agent runs produced with private context under PR #335 and assign
their verified project ownership; historical Council copies require a separate
review. Project ownership cannot safely be inferred from a company or country.
This change does not introduce organization-wide tenancy for all legacy apps.

Project directories, evidence pages, analysis, evidence sharing and the human
decision gate use the new grants. Other write stages (including document intake)
retain existing staff restrictions. Legacy capital decisions use project names;
ambiguous duplicate project names fail closed for approval and loss lookups.
A future FK migration can replace those legacy name associations.
