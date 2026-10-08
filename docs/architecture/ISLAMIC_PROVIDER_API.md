# Sajda / Azan.kz and neural source retrieval

## Implemented integration and access boundary

`islamic_knowledge` is a Django app with a passage table, operator import commands,
an editorial admin workflow and read-only JSON endpoints. It extends the reference
and review contracts introduced in the wisdom/justice increment.

On 2026-10-07, official public pages confirmed Quran/names content but no public
content API documentation was found for either provider. This is an integration
adapter for **agreed normalised JSON feeds or authorised exports**, not a claim
that a guessed private endpoint works. No provider text or translation is bundled
or silently scraped. Unconfigured feeds explicitly report `awaiting_agreed_feed`.

| Provider | Official entry point | Data integration |
| --- | --- | --- |
| Sajda | [App](https://sajda.com/en), [name-list explanation](https://faq.sajda.app/en/question/113) | `SAJDA_KNOWLEDGE_FEED_URL` or authorised export |
| Azan.kz | [Portal](https://azan.kz/), [99-name course](https://azan.kz/durus/dars/99-imyon-Allaha-97) | `AZAN_KZ_KNOWLEDGE_FEED_URL` or authorised export |

Feed URLs must use HTTPS on the selected provider's declared hosts. Requests have
connect/read timeouts, refuse redirects, require JSON and read at most 2 MiB.
No server-side endpoint accepts a caller-supplied remote URL. Native provider
formats require a documented mapping once access is agreed; until then the
adapter consumes the schema below. The sources endpoint exposes configuration
status, not feed URLs or credentials.

The catalogue still contains 114 surah metadata entries and one attributed,
unreviewed 99-name enumeration. These are reference indexes sourced as recorded
in their JSON files, **not downloaded Sajda/Azan.kz texts**. Imported name passages
must preserve a provider enumeration identifier and explicitly map to a known
name key. Provider ordinals are never mapped automatically: Sajda explains that
lists differ, and the Azan.kz course has its own lesson ordering.

## JSON API

| GET endpoint | Response |
| --- | --- |
| `/api/islamic/sources/` | Providers, official links, explicit feed access status |
| `/api/islamic/surahs/` | All 114 metadata entries; no translation or tafsir |
| `/api/islamic/names/` | All 99 identifiers, source enumeration and pending scholar review |
| `/api/islamic/passages/` | Published exact source passages with attribution/version/digest |
| `/api/islamic/search/?q=...` | Neural cosine ranking of published indexed passages with citations |
| `/api/islamic/search/?q=...&mode=hybrid` | Neural + Unicode word retrieval, reciprocal rank fusion, explicit lexical degradation |

Passage listing supports `provider`, `language`, `surah`, `name`, `limit` (1–50)
and `offset` (0–10000). Search supports `provider`, `language` and `limit` (1–20).
Invalid inputs return 400. All endpoints reject writes. Search is throttled
through the existing trusted-origin limiter (anonymous 5/min, authenticated
10/min, including staff), sharing its configured cache infrastructure.

Disabled/unavailable neural execution returns 503 without switching to a lexical
method and labelling it neural. An enabled search with no indexed published
sources returns an empty list. Similarity is not calibrated confidence, evidence
of correctness or a religious ruling. Sources must be reviewed and cited before
content appears; editorial publication does not create a scholar review receipt,
prove authentication or clear `assess_definition`/OS gates.

### Hybrid retrieval (2026-10-08)

`mode=hybrid` reuses the pinned multilingual encoder and adds exact Unicode word
matching over published passages. Both retrieve up to 20 candidates; reciprocal
rank fusion sums `1 / (60 + rank)` per list and deduplicates by passage ID and
source digest. Equal scores use provider/external ID order. This avoids combining
cosine and lexical values as though they shared a meaningful scale. See the
[original RRF paper](https://doi.org/10.1145/1571941.1572114). No improvement on a
religious corpus is claimed before an evaluated query set exists.

Example for an imported, published Kazakh corpus:

```bash
curl --get 'https://ecoiq.uk/api/islamic/search/' \
  --data-urlencode 'q=Таза су' --data 'mode=hybrid&language=kk&limit=5'
```

This is the API contract; the example does not claim a deployed/live feed.
`method` is `hybrid_rrf` when neural contributions remain, otherwise
`lexical_overlap`. `neural_status` explicitly reports `used`, `disabled`,
`unavailable` or `no_results`. An unavailable/disabled encoder gives a 200 lexical
result with `model: null`; the default neural-only endpoint still gives 503.
An empty match returns an empty list. Invalid inputs give 400, and a corpus
beyond the 10,000-passage lexical capacity gives 503 without truncating it.
Modes share the same throttle; switching modes does not reset the request budget.

Each result preserves the exact passage, source URL, digest, rights and
attribution, plus `matched_by`, `fusion_score`, `lexical_match` (fraction of query
words present) and nullable neural `similarity`. Neither score is confidence or
a religious ruling. Queries require 1–32 distinct searchable words within the
existing 1,000-character bound; neural execution retains its token-window check.
Words are case-folded/NFKC-normalised; combining marks are removed to support
Arabic queries with or without harakat. Kazakh letters are retained. There is
no stemming or lexical translation. The lexical scan streams passages without
loading stored vectors; final fusion rechecks publication and source/embedding
digests after both searches. No external LLM, API key or new runtime dependency
is introduced.

## Import and editorial publication

The operator runs:

```bash
python manage.py migrate
python manage.py sync_islamic_provider --provider azan_kz --file authorised-export.json
# Or use an agreed feed configured on the server:
python manage.py sync_islamic_provider --provider sajda
```

The export schema is shown with **placeholders**, not source content:

```json
{
  "schema_version": 1,
  "provider": "azan_kz",
  "passages": [{
    "external_id": "<stable provider passage ID>",
    "source_url": "https://azan.kz/durus/dars/99-imyon-Allaha-97",
    "kind": "tafsir",
    "work": "<source work title>",
    "edition": "<source edition>",
    "source_version": "<provider content version>",
    "language": "ru",
    "attribution": "<actual author or translator>",
    "passage": "<exact authorised source passage>",
    "rights": "permission_pending",
    "rights_evidence": ""
  }]
}
```

For Quran/translation passages, include valid `surah` and `ayah_start`, optionally
`ayah_end`; Hafs boundaries are checked. For a divine-name passage, include
`name_key` and the provider's `enumeration`. Text is bounded to 4,000 characters;
an export contains 1–1,000 passages and duplicate IDs are rejected.

The whole export is validated before any write, then imported atomically by
`(provider, external_id)`. Imports cannot provide review fields, revocation or
vectors. Unchanged imports preserve review/index state; source edits invalidate
both. No absent export record is implicitly deleted or withdrawn.

In Django admin, an editor with change permission records licence/permission
evidence, checks the exact passage/source and uses **Publish selected passages
after editorial source/rights review**. Pending rights, withdrawn content or stale
digests cannot publish. The review records user and time against a digest of text
**and all attribution/reference/version/rights metadata**. Deleting the reviewer
also hides the publication. Source changes require a new editorial review.

This workflow is a passage publication boundary; authenticated scholarly review
and canonical full-text verification for OS principle bindings remain separate
work. The API exposes no approval or religious-verification claims.

## Neural encoder and operation

The model is
[`paraphrase-multilingual-MiniLM-L12-v2`](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
at revision `bf3bf13ab40c3157080a7ab344c831b9ad18b5eb`, using 384-dimensional CPU
vectors. The source model card lists 50 languages and Apache 2.0. Language codes
in the source API are metadata; this does not promise evaluated neural quality
for every language, including Kazakh. A domain/language evaluation is still needed.

The encoder is optional and OFF by default. Install separately with the CPU
wheel, keeping it out of the default Django dependencies:

```bash
pip install 'torch==2.14.1' --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-neural.txt
export ISLAMIC_NEURAL_CACHE_DIR=/path/to/model-cache
python manage.py prepare_islamic_encoder --download
export ISLAMIC_NEURAL_SEARCH_ENABLED=true
python manage.py embed_islamic_passages
python scripts/benchmarks/islamic_neural_smoke.py
```

Weight preparation is the explicit network step. Requests load cached pinned
weights only, with remote code disabled and safetensors required. An encoder is
cached per process; embeddings are computed in batches of 16, checked for finite
values and normalised. Inputs beyond the model's 128-token window are rejected,
so long source text is not silently truncated. Import shorter exact passages
with their original locators instead. Query text is limited to 1,000 characters
and must also fit the token window.

Vectors store the model revision and source digest. Indexing/search ignore stale,
unreviewed or revoked data, and writes/results recheck digests to detect concurrent
edits/withdrawals. Existing Evidence Memory lexical vectors are untouched, so
incompatible 256-dimensional hashing and 384-dimensional neural embeddings are
never compared.

Phase 1 streams exact cosine ranking for up to 10,000 indexed passages, holding
only top K. Larger corpora explicitly require a vector index; no silent corpus
truncation. Model weights consume hundreds of MB, so provision CPU/RAM and the
cache before enabling. No Render plan or production environment is changed by
this increment.

## Validation

Regression tests use synthetic non-religious texts/vectors to check import,
review invalidation, access status, Quran locators, enumeration identity, API
filters/pagination, rate limiting, ranking ties, stale vectors, concurrent
withdrawals, encoder shape/normalisation and refused truncation.

The real pinned model was also downloaded and run with `HF_HUB_OFFLINE=1` and
`TRANSFORMERS_OFFLINE=1` on Python 3.12.14, using the versions pinned in
`requirements-neural.txt` (CPU torch). Four authored English/Russian/Arabic/control
sentences produced finite unit vectors of shape `(4, 384)`. Observed English–Russian
cosine was 0.9516, English–Arabic 0.7881 and an unrelated control 0.1371. This is an
execution smoke, not a provider-corpus or religious retrieval-quality evaluation.

An opt-in live test also passed with the real offline encoder: authorised synthetic
fixtures → editorial publication → batched indexing → Django search on English,
Russian and Arabic queries. It checks execution and source citations, not ranking
quality on religious material. Run it with the prepared cache and optional extra:

The hybrid increment adds synthetic regressions for fusion/deduplication,
Russian/Kazakh/Arabic/English word matching, filters, model failure, shared
throttles, capacity bounds and edits/withdrawals during ranking. The opt-in live
test now exercises both neural-only and hybrid paths with authored English,
Russian, Arabic and Kazakh fixtures. These check execution, not language/domain
retrieval quality.

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ISLAMIC_NEURAL_LIVE_TEST=1 \
  DEBUG=True python manage.py test islamic_knowledge.test_neural_live --noinput
```

```bash
DEBUG=True python manage.py test islamic_knowledge ecoiq_os \
  mizan.test_system_balance platform_registry api.tests_v2_platform --noinput
ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
```

Activation still requires agreed provider access/exports, rights review, source
publication, optional dependency/weight preparation and indexing. These are
reported explicitly rather than presenting empty or unconfigured integrations as
live provider content.
