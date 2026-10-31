# Context policy

How context is spent in this repository, and the one thing that is never
traded for tokens.

**The rule that outranks every budget below: never drop provenance to save
tokens.** Source identity, retrieval date, document hash, reviewer, and
confidence tier survive every summarisation, compaction and handoff. A
number that arrives without its source has not been compressed — it has been
corrupted. EcoIQ sells auditability; a cheaper answer that cannot be traced
is worth less than no answer.

The second rule: **optimise tokens-per-task, not tokens-per-request.**
Aggressive compression that forces three re-reads costs more than the
summary saved.

## Loading discipline

Skills are metadata-first: only `name` and `description` are in context until
one is invoked. That only works if descriptions are trigger-scoped, so:

1. **Route, don't survey.** [`ecoiq-engineering-os`](../../.claude/skills/ecoiq-engineering-os/SKILL.md)
   is a map. Pick the smallest set, then stop. Loading every skill is a bug
   (standing rules 3 and 4).
2. **No always-on injection.** This is why the `superpowers` SessionStart
   hook was rejected — it prepends its skill text to every session regardless
   of task. See [THIRD_PARTY_SKILLS_AUDIT.md](THIRD_PARTY_SKILLS_AUDIT.md).
3. **One authority per layer.** Overlapping skills get resolved, not stacked.
   `ecoiq-khalifah-engine` coordinates and points; it does not restate what
   the specialist skills say.
4. **Reference, don't inline.** Link to `tokens.ts`, don't paste it. Link to
   a model, don't reproduce it.

## Retrieval

- **Smallest sufficient chunk.** Read the function, not the module; the
  section, not the document. `sed -n 'A,Bp'` over `cat`.
- **Metadata travels with the chunk.** An `EvidenceMemory.text_chunk` is
  useless without `source_reference`, `date_collected`, `verification_status`
  and `confidence`. Retrieve them together or not at all.
- **Two hashes, never conflated.** `integrity_reference` hashes the *chunk*;
  a manifest's `document_sha256` hashes the *source file*. Both, labelled.
- **Absence is a result.** "No evidence record covers this" is a correct
  answer. Widening the search until something plausible appears is how
  fabrication starts.

## Caching

Cache anything, with one carve-out: **never serve a stale regulatory or live
operational answer.**

| Cacheable | Never cached |
|---|---|
| Skill and doc text | A compliance conclusion for a jurisdiction |
| Repository structure, schemas | Live KPI, emissions or price data |
| Stable reference tables | Anything with an effective date that may have passed |
| Conversation prefix | A confidence tier or review state |

Invalidate when **any** of these change: the underlying document, the
jurisdiction, the effective date, the model or model version, the calculation
or formula version, or the review state of a cited record.

## Memory separation

Three tiers. Do not let them blur.

| Tier | Holds | Authority |
|---|---|---|
| **Conversation memory** | This session's working state | None. Never cite it as a source. |
| **Project facts** | `CLAUDE.md`, skills, `docs/` | Instructional |
| **Verified records** | Database rows with a named reviewer | The only thing that may be called VERIFIED FACT |

"We established earlier that emissions were 12,400 tCO₂e" is conversation
memory. It is MODEL INFERENCE unless it resolves to a record.

## Agent handoffs

A handoff is a structured summary, never a transcript dump. It must carry:

1. Task and current state
2. Decisions made **and why**
3. Files touched, with paths
4. **Every claim with its label** (VERIFIED FACT / SOURCE-BACKED CLAIM /
   MODEL INFERENCE / ASSUMPTION / UNKNOWN / RECOMMENDATION) and its source
5. Open risks and unresolved contradictions
6. The next action

A handoff that arrives with unlabelled claims is a defect: the receiving
agent cannot tell an assumption from a fact, and will treat both as fact.

## Budgets by task type

Working targets for the *task*, not per request. Exceeding one is a signal to
re-scope or compress, not a failure.

| Task type | Target | Load | Compress when |
|---|---|---|---|
| **Quick question** | ≤ 15k | Router only; usually no skill | Never — re-scope instead |
| **Code change** | 30–80k | 1 domain skill + the files touched | Reading > 5 files to understand one change |
| **Regulatory research** | 40–120k | `ecoiq-regulatory-review` + sources | Per source, keeping all 8 metadata fields |
| **Evidence-graph analysis** | 50–150k | `ecoiq-evidence-audit` | Per record — never drop reviewer or tier |
| **Scenario modelling** | 60–150k | `ecoiq-khalifah-engine` | Per scenario, keeping assumptions and ranges |
| **Large document analysis** | 100–250k | `context-compression` | Continuously; hierarchical summaries |
| **Full release validation** | 20–40k | `ecoiq-release-gate` | Never — it is command output, keep failures verbatim |

Cross-cutting caps: no single file read past ~2k lines without a reason;
no more than 3 skills concurrently; a handoff summary ≤ 2k tokens.

## Measuring whether this works

Token count alone is the wrong metric — it rewards dropping evidence. Track:

| Metric | Target | Why |
|---|---|---|
| **Citation correctness** | 100% | Every cited record exists and says what was claimed. Non-negotiable. |
| **Retrieval precision** | ≥ 0.8 | Retrieved chunks that were actually used |
| **Provenance survival** | 100% | Claims that still carry source + date + reviewer after compression |
| **Re-fetch rate** | < 15% | How often compression forced re-reading — the real cost of over-compression |
| **Label completeness** | 100% | Substantive claims carrying exactly one epistemic label |
| Tokens per task | Trending down | **Only valid while all of the above hold** |

If tokens fall while citation correctness or provenance survival falls, the
optimisation failed. Revert it.
