# EcoIQ AI Agent Training Index

This is the master file for EcoIQ's operational AI agent training packs. It
explains how the agents work together, the recommended execution order, what
each agent produces, which downstream agent/module consumes that output, how
Amanah Autopilot supervises the whole workflow, and how this can be demoed to
Microsoft, investors and industrial clients.

EcoIQ is a multi-agent industrial climate intelligence platform. It is **not**
just ESG reporting — it connects company evidence, industrial assets,
modernisation playbooks, finance readiness, and measurable impact for
industrial companies, investors, sovereign funds and public-sector partners
across energy, oil and gas, mining, metals, uranium, heating and boilers,
agriculture, food processing, manufacturing, utilities, and public
infrastructure.

## Scope of this index

This session focused on 10 of EcoIQ's 14 AI agent categories — the ones that
carry the core evidence → impact → decision pipeline:

1. Research Agent
2. Document Reader Agent
3. Photo / Visual Evidence Agent
4. Asset Passport Agent
5. Industrial Playbook Matching Agent
6. Finance Modelling Agent
7. MRV Agent
8. Governance Agent
9. Report Generator Agent
10. Amanah Autopilot Supervisor

The remaining 4 (Supplier/Funding Match Agent, Customer Success Agent, Sales
CRM Agent, Analytics Agent) already have a lighter-weight training summary in
the **Agent Training & Evaluation Lab** platform page
(`/agent-training-evaluation-lab/`, backed by `agent_training_evaluation_lab/`
in this repo) and are not duplicated here — this index and the 10 packs above
are the deeper, implementation-ready file-based counterpart for the core
pipeline agents.

## Recommended agent execution order

```
1. Research Agent
      ↓ public evidence summary
2. Document Reader Agent   (+ 3. Photo / Visual Evidence Agent, in parallel)
      ↓ extracted document facts / visual observations
4. Asset Passport Agent
      ↓ structured asset record
5. Industrial Playbook Matching Agent
      ↓ matched playbook, quick wins, deep upgrades, MRV metrics
6. Finance Modelling Agent
      ↓ draft finance memo (estimated, not guaranteed)
7. MRV Agent
      ↓ MRV stage, estimated vs verified impact, badge recommendation
8. Governance Agent
      ↓ review packet, reviewer type, approval status, blockers
9. Report Generator Agent
      ↓ investor memo / board pack / public summary / country brief

                    Amanah Autopilot Supervisor
        (runs overnight, across steps 1–9, every night)
```

## What each agent produces and who consumes it

| # | Agent | Produces | Consumed by |
|---|---|---|---|
| 1 | Research Agent | Source-linked public evidence summary | Asset Passport Agent, Governance Agent, Report Generator Agent |
| 2 | Document Reader Agent | Structured extracted facts from bills/reports/quotes | Asset Passport Agent, Finance Modelling Agent, MRV Agent |
| 3 | Photo / Visual Evidence Agent | Labelled visual hypotheses ("needs verification") | Asset Passport Agent, Industrial Playbook Matching Agent, Governance Agent |
| 4 | Asset Passport Agent | One structured, evidence-linked asset record | Industrial Playbook Matching Agent, Finance Modelling Agent, MRV Agent |
| 5 | Industrial Playbook Matching Agent | Best-fit playbook, quick wins, deep upgrades, MRV metrics | Finance Modelling Agent, Supplier & Funding Marketplace, Impact MRV Layer |
| 6 | Finance Modelling Agent | Draft CAPEX/OPEX model, funding gap (estimated) | Institutional Finance Engine, Governance Agent, Report Generator Agent |
| 7 | MRV Agent | MRV stage, estimated vs verified impact, badge recommendation | Certification & Trust Badge Engine, Public Trust & Impact Portal, Governance Agent |
| 8 | Governance Agent | Review packet, reviewer type, approval status, blockers | Report Generator Agent, Certification & Trust Badge Engine |
| 9 | Report Generator Agent | Investor memo / board pack / public summary / country brief | Executive Briefing & Board Pack Generator, Public Trust & Impact Portal |
| 10 | Amanah Autopilot Supervisor | Morning briefing, missing-evidence alerts, approval queue | Command Centre, Governance & Expert Review Board, AI Agent Operations Console |

## How Amanah Autopilot supervises the whole workflow

Amanah Autopilot Supervisor does not sit inside the linear pipeline — it runs
**overnight, across every agent's output**, checking for:

- Projects missing baseline data or after-data (Document Reader Agent / MRV Agent gaps)
- Estimated claims at risk of being shown as verified (Finance Modelling Agent / MRV Agent)
- Projects close to MRV Verified or Finance Ready (ready for a human decision)
- Public summaries blocked by missing consent (Governance Agent / Report Generator Agent)
- Unresolved No Harm alerts across any agent

It never resolves any of these itself — every finding becomes an item in the
human approval queue. This is the platform-wide safety net: no matter which
agent produced a gap, Amanah Autopilot makes sure a human sees it the next
morning.

## Shared safety principles across every agent

All 10 packs share these non-negotiable rules (see each agent's
`safety_rules.md` for the specific version):

- Never invent a missing figure — mark it missing and say so
- Never present an estimate as verified
- Never claim independent certification (Microsoft, Shariah, or otherwise)
  without a primary source or qualified reviewer
- Every high-impact output (finance, MRV, public reporting, supplier
  recommendation) requires human approval
- Maqasid/Mizan is ethical decision-support, never a fatwa
- Visual findings are hypotheses, not engineering conclusions
- No agent may independently approve, publish, or issue a badge — that stays
  with Governance Agent's human reviewer and the Certification & Trust Badge
  Engine

## How this can be demoed to Microsoft, investors, and industrial clients

### To Microsoft / enterprise ecosystem partners

Walk the pipeline end-to-end using the **Frontend Implementation Roadmap**'s
Microsoft Partner Demo Flow (`/frontend-implementation-roadmap/`): Command
Centre → Country Atlas → Asset Passport → evidence panel → Knowledge Graph
trace → Finance Ready badge → send approval to Teams → Power BI dashboard
concept → export evidence pack to SharePoint → Public Trust summary. Use
"designed to integrate with Microsoft ecosystem" wording throughout — never
"Microsoft certified" or "official partner" language, since no such
certification/partnership has been obtained.

### To investors

Show one real asset moving through the pipeline: Research Agent's cautious
public evidence → Document Reader Agent's exact bill extraction → Asset
Passport's evidence-linked record → Industrial Playbook Matching's quick-win
recommendation → Finance Modelling's estimated (not guaranteed) payback →
MRV Agent's honest "MRV In Review" status → Governance Agent's review packet
→ Report Generator's investor memo, every claim linked back to its evidence.
The story is not "AI says this project is great" — it's "here is exactly
what is known, what is missing, and what a human still needs to decide."

### To industrial clients (energy, mining, manufacturing, utilities, agriculture)

Lead with Document Reader Agent and Photo/Visual Evidence Agent — the two
agents that directly reduce the paperwork and inspection burden clients feel
today — then show how that evidence flows automatically into an Asset
Passport, a matched playbook, and (eventually) a finance-ready business case,
without ever pretending a human engineer's or financial reviewer's sign-off
is no longer needed.

## Related platform pages and repo locations

| Concept | Platform page | Repo location |
|---|---|---|
| Agent training method (all 14 categories) | `/agent-training-evaluation-lab/` | `agent_training_evaluation_lab/` |
| Document Reader Agent (deep dive) | `/document-reader-agent-training-pack/` | `document_reader_agent_training_pack/`, `ai_agents/document_reader_agent/` |
| MRV Agent (deep dive) | `/mrv-agent-training-pack/` | `mrv_agent_training_pack/`, `ai_agents/mrv_agent/` |
| Frontend delivery plan / Microsoft demo flow | `/frontend-implementation-roadmap/` | `frontend_implementation_roadmap/` |
| Trust badges (MRV Verified, Finance Ready, etc.) | `/certification-trust-badge-engine/` | `certification_trust_badge_engine/` |
| Knowledge Graph evidence nodes | `/knowledge-graph-relationship-map/` | `knowledge_graph_relationship_map/` |

## Implementation status

These 10 folders are **training packs** — system prompts, schemas, safety
rules and test cases ready for an agent runtime (LangGraph, Semantic Kernel,
Azure AI Agent Framework, Celery tasks, or similar). They are not yet wired
to a live LLM orchestration layer in this repo. Core Django product logic was
not changed to produce this index or the training packs.
