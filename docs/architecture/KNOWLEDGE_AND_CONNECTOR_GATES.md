# Next stage: external systems and specialised knowledge

The internal risk workflow is the first integration boundary. No connector or
Quran/tafsir corpus is enabled by the current PR. These are implementation and
acceptance requirements for the next increment, not claims of certification.

## External adapters

Start with one read-only source selected for an actual project. Record its
owner, permitted projects, allowed operations, authentication reference, usage
rights, version, retrieval time and content hash. Store credentials only in the
existing secret configuration, never in prompts, source metadata or audit logs.

Each adapter needs explicit timeout, rate-limit handling, response-size limits,
source ACL enforcement and provenance mapping into the current evidence store.
Retrieved content is untrusted data and cannot authorise tools or override the
user's instructions. Use existing outbound URL/SSRF controls. Test unavailability,
malformed data, replay, revoked access and changed source versions before rollout.

Outbound actions additionally need a durable outbox linked to the analysis
session, an idempotency key accepted by the destination, recorded human approval
for the exact action payload, bounded retries/backoff, and reconciliation of
unknown outcomes. Never translate a timeout into an automatic duplicate payment,
message or irreversible write. Internal `document_requested` events must not be
relabelled as externally delivered.

## Quran, translations and tafsir are distinct source types

Preserve separate records for source text, translation, commentary and EcoIQ's
derived interpretation. A translation or model-generated explanation must never
be labelled as the original Arabic text or a scholar's quotation.

| Record | Required provenance before use |
|---|---|
| Quran text | Approved publisher/corpus identity, edition/reading metadata, surah and ayah locator, exact Arabic text, canonical reference, content version/hash, independent reference check |
| Translation | Translator, language, edition, rights, exact passage, linked ayah range, version/hash |
| Tafsir | Author, work, edition, volume/page or stable entry ID, passage, linked ayah range, source URL, rights, version/hash |
| Interpretation | Referenced passages and editions, scope/context, author or model/run ID, uncertainty/disagreement, named qualified reviewer, rationale and review time |

Source admission and interpretation approval are separate gates. Check every
locator against the selected authoritative edition; do not assume a URL or hash
proves authenticity. The expert review must cover the actual interpretation,
not merely confirm that a quoted verse exists. Corrections, disputes or edition
changes invalidate dependent pending approvals and require review again.

Build a separately reviewed evaluation set before semantic retrieval is enabled:
exact reference lookup, ambiguous paraphrases, translation differences, different
commentaries, missing answers and adversarial instructions inside documents.
Keep legitimate scholarly disagreement visible. When sources/review are missing,
return insufficient evidence and a request for expert review.

No automatic fatwas, Shariah certification or invented verse references. AI may
retrieve and propose an interpretation for review; it cannot stand in for the
qualified human reviewer. Agree the corpus editions, rights and reviewer roster
before ingestion. Existing experimental principle mappings are not automatically
promoted to an approved religious corpus.
