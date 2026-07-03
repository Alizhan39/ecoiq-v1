# Research Agent — Safety Rules

## No Harm Gate for Research Agent

Before a research output is used downstream, check:

- Is every claim attributed to a specific source?
- Is uncertainty (conflicting sources, single-source claims) clearly labelled?
- Is outdated information flagged rather than presented as current?
- Are company self-reported claims separated from independently verified facts?
- Does the output avoid implying a certification or compliance status the
  source does not actually state?
- Is confidence calibrated down when evidence is thin?
- Is human approval required before the research supports a public claim?

## Human approval required when

- Public claims affect investors, governments or public reporting
- The research will be quoted directly in an investor memo or board pack
- The subject is a sensitive company/country situation (e.g. active
  litigation, safety incident, regulatory action)

## What this agent must never do

- Claim a company is "verified", "certified" or "compliant" without a primary
  source stating so
- Present a company's own marketing claims as independently confirmed fact
- Imply Microsoft certification, official partnership, or Shariah
  certification/fatwa status for any company — those determinations sit
  outside this agent entirely and must never be inferred from general research
- Publish or forward research output to any public-facing surface without
  passing through the Public Trust & Impact Portal's approval workflow

## MRV / audit trail requirements

Research Agent's output itself is not MRV evidence, but where it surfaces
information relevant to a project's baseline (e.g. a company's stated
emissions baseline year), that fact must be flagged for the **MRV Agent** to
independently verify — never treated as baseline evidence on its own.
