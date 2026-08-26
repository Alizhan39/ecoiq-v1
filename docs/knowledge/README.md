# EcoIQ knowledge workspace

A project-local, plain-Markdown knowledge base for the thinking behind EcoIQ:
architecture decisions, Khalifah Engine documentation, the 33 KPI × 114 surah
research, evidence and provenance methodology, regulations, pilots, customer
discovery, and climate / transition-finance research.

**Obsidian is optional and is not part of the runtime.** These are ordinary
`.md` files, readable and editable with anything. Obsidian adds backlinks and
graph view if you open the folder as a vault; nothing here depends on it, and
nothing about EcoIQ's architecture changes if you never do. Wikilink syntax
guidance comes from the installed `obsidian-markdown` skill.

## Layout

```
docs/knowledge/
├── README.md          ← this file (tracked)
├── templates/         ← the five note types (tracked)
└── vault/             ← authored notes (gitignored except .gitkeep)
```

`vault/` is gitignored on purpose. It accumulates customer discovery notes,
pilot hypotheses and half-formed research — material that has not been
through the evidence boundary and should not sit in the repository's history.
Promote a note into `docs/` once it is a settled project fact.

## Hard rules

1. **No secrets.** No API keys, credentials, connection strings or `.env`
   content. Ever.
2. **No production data.** Do not copy database rows here. A note *references*
   a record by id; it never duplicates it. The database is the source of
   truth, and a stale copy in a note is a provenance hazard.
3. **No customer-identifying or personal data** without a specific approved
   reason. Prefer "a UK water utility" over a named contact.
4. **No Qur'anic or Arabic terminology on anything customer-facing.** Internal
   notes may use it; the moment content moves toward a public surface it uses
   the English principle names in
   [`docs/governance-principles-surah-map.md`](../governance-principles-surah-map.md).
5. **A note is never evidence.** Nothing here is a verified record. Promotion
   runs through `ecoiq-research-ingest` and the evidence models, with a named
   human reviewer.

## The four layers — keep them apart

The single most valuable thing this workspace does is refuse to blur these.
Most bad analysis is an interpretation wearing a claim's clothes.

| Layer | Is | Never |
|---|---|---|
| **Source** | A document that exists, with an origin, date and hash | A summary of it |
| **Claim** | A specific assertion a source makes | Your reading of what it implies |
| **Evidence** | A claim connected to an EcoIQ record, with confidence and review state | A claim you find convincing |
| **Interpretation** | What you think it means | A fact |
| **Decision** | What was decided, by whom, when, and what would reverse it | A discussion |

Each layer links down to the one it rests on. An interpretation with no claim
beneath it, or a claim with no source, is the defect this structure exists to
make visible.

## Stable IDs

Every note carries an `id` that never changes, even if the title or filename
does. Links use the id, so renaming never breaks a reference.

| Type | Prefix | Example |
|---|---|---|
| Evidence note | `EV-` | `EV-2026-0041` |
| Regulatory finding | `REG-` | `REG-UK-CSRD-0007` |
| KPI definition | `KPI-` | `KPI-033-water-intensity` |
| Pilot hypothesis | `PILOT-` | `PILOT-KZ-2026-002` |
| Architecture decision | `ADR-` | `ADR-0014` |

Jurisdiction codes match the platform's four markets: `UK`, `KZ`, `SA`, `TR`.

## Templates

| Template | Use for |
|---|---|
| [evidence-note.md](templates/evidence-note.md) | A source and the claims drawn from it |
| [regulatory-finding.md](templates/regulatory-finding.md) | A compliance or jurisdiction position |
| [kpi-definition.md](templates/kpi-definition.md) | What a KPI means and how it is computed |
| [pilot-hypothesis.md](templates/pilot-hypothesis.md) | A falsifiable pilot claim |
| [architecture-decision-record.md](templates/architecture-decision-record.md) | A decision with consequences |

Copy a template into `vault/`, rename it to its id, fill the frontmatter.
Leave a field as `unknown` rather than guessing — an honest gap is data.

## Activating Obsidian (optional, manual)

Obsidian is not installed by this repository and is not required. To use it:
install Obsidian, then **Open folder as vault** → `docs/knowledge/`. Nothing
else to configure. See [`../ai-tooling/MANUAL_ACTIONS.md`](../ai-tooling/MANUAL_ACTIONS.md).
