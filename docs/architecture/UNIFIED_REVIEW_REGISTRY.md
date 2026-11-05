# Unified EcoIQ review inventory

`ecoiq_os/review_registry.py` is a typed index over existing source-of-truth
catalogues. It adds identity, content fingerprints, relationship validation and
bounded inspection; it does not copy their definitions into another catalogue.
The initial verified inventory has **4,191 typed entries**, not 4,191 approved
principles or working analytical checks:

| Kind | Current entries | Meaning |
| --- | ---: | --- |
| Operational principle | 114 | Existing operational questions; not assessed here |
| Candidate KPI | 33 | Candidate questions; 20 are initial priorities |
| Formula candidate | 20 | Existing expressions and units, separate from KPI identity |
| Knowledge definition | 25 | Core/environmental drafts, deduplicated by ID |
| Governance domain | 12 | Research taxonomy with contextual KPI links |
| Reform capability | 12 | Research specifications, not deployed engines |
| Surah reference | 114 | Metadata/navigation, not reviewed interpretation |
| Divine-name reference | 99 | One attributed enumeration, pending review |
| KPI/surah review pair | 3,762 | Existing 33 × 114 UNREVIEWED work items |

Runtime counts come from source records, not this table. The code does not
invent 99 × 114 or other products to reach a target above 10,000. Additional
real catalogues can be indexed after identifying their canonical source,
stable identity and review semantics. This does not claim to inventory the
complete universe of EcoIQ knowledge.

## Identity and provenance

Namespaces distinguish unlike objects: `principle:001`, `kpi:revenue`,
`formula:revenue`, `surah:001`, `review-kpi-surah:revenue:001`, and
`name:<enumeration>:<name-key>`. An ordinal is not a universal name identifier.
IDs stay stable when content changes; `content_sha256` changes instead.

Every entry retains its source file/key, review status, content fingerprint
and related IDs. Formula records point to candidate KPIs; domain/capability
links reference actual formulas. KPI/surah work items reuse the existing
`foundation_catalog.review_queue_page` and reference both parent records.
Duplicate IDs, conflicting reused definitions and dangling links fail closed.
A code-file reference locates a catalogue definition; it does not verify a
business measurement or religious assertion. No source text or review receipt
is fabricated.

## Inspection and runtime integration

The read-only management command is an operator interface, not a public API:

```bash
DEBUG=True python manage.py review_registry_inventory
DEBUG=True python manage.py review_registry_inventory --entries \
  --kind kpi_surah_review_pair --start 3700 --limit 62
```

`registry_page` permits at most 100 entries. Empty tail pages have no next
cursor. No database writes or network/model calls are made.

The grounded investigation report includes the index's counts and fingerprint
under `extended_registry`; `inventory_sha256` also binds that fingerprint.
All entries participate, including the 13 additional candidate KPIs,
references and pending review matrix absent from the initial detailed lists.
Thousands of records are not appended to every response or provider prompt.

All entries retain `source_verified=False` and `decision_ready=False`.
Inventory coverage does not establish applicability, measured compliance,
source authentication, scholarly approval, a score or a legal verdict. Existing
human/source/knowledge/publication gates remain authoritative. Other AI entry
points remain outside this first grounded-service integration.

## Verification

```bash
DEBUG=True python manage.py test ecoiq_os.tests_review_registry \
  ecoiq_os.tests_principle_review ecoiq_os.tests_grounded_ai \
  api.tests_v2_decision_islah api.tests_os_pilot_journey --noinput
```

Tests traverse every page and relationship, check boundary pages, source
content drift, stable IDs, bad bounds, duplicate/dangling references, operator
output and final AI report fingerprint propagation. They do not treat index
traversal as an assessment of real-world compliance.
