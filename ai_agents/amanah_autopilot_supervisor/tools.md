# Amanah Autopilot Supervisor — Tools

## EcoIQ modules this agent reads from / writes to

- **Amanah Autopilot** — the platform module this agent's output populates
- **Command Centre** — morning briefing panel
- **Governance & Expert Review Board** — human approval queue
- **AI Agent Operations Console** — agent task health monitoring
- **Impact MRV Layer** — MRV status across projects
- **Certification & Trust Badge Engine** — badges affected by overnight findings

## External tool concepts (not yet wired to a live runtime)

- Overnight batch scheduler (e.g. Celery beat / cron equivalent)
- Cross-project pattern detection (portfolio-level gap clustering)

## Explicit non-tools

- No automated approval of any flagged item
- No automated public publication
- No automated badge issuance
