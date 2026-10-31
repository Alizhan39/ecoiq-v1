# Frontend API Contract

**The contract React consumes.** Backend is the source of truth; React presents
it. No scoring, eligibility, coverage or confidence logic is reimplemented on
the client.

Captured empirically from the running API, not transcribed from serializer
code.

---

## The rule that governs everything below

> **A missing value is `null`. It is never `0`, never `50`, never a substitute.**

Any of these in frontend code is a defect:

```ts
score ?? 0          // ✗
score || 0          // ✗
score ?? 50         // ✗
rank || 0           // ✗
confidence ?? "MEDIUM"   // ✗
coverage || 0       // ✗ — see the note on coverage below
```

The correct shape is always a branch on `score_status`, never a coalesce on the
number.

---

## `GET /api/v2/companies/`

Paginated list. Each result:

```json
{
  "slug": "example-co",
  "name": "Example Co",
  "sector": "other",
  "country": "UK",
  "is_public": false,
  "verified": false,
  "ecoiq_score": null,
  "score_status": "INSUFFICIENT_EVIDENCE",
  "evidence_coverage": 0,
  "confidence": "INSUFFICIENT_EVIDENCE",
  "rank": null,
  "url": "https://ecoiq.uk/api/v2/companies/example-co/"
}
```

## `GET /api/v2/companies/:slug/`

```
city · confidence · country · description · ecoiq_score · evidence_coverage
evidence_note · harm_signals · is_public · logo_url · name · score_status
sector · slug · verified · website
```

---

## Field semantics

### `score_status` — authoritative

| value | meaning |
|---|---|
| `PUBLISHED` | the score may be displayed |
| `PROVISIONAL` | defined, reachable, **currently produced by nothing** |
| `INSUFFICIENT_EVIDENCE` | the score must not be displayed |

**This field, not the score, decides what the UI renders.** `PROVISIONAL` exists
in the contract today so the client is built for a three-state world before the
threshold that produces the third state is chosen. Handle it; do not assume it
is unreachable forever.

### `ecoiq_score` — `number | null`

`null` whenever `score_status !== "PUBLISHED"`. The API never emits a
placeholder.

A **`0.0` is a real, publishable score** — a company genuinely assessed at zero.
It is not "missing". Code that treats `0` as falsy will misreport it, which is
the exact bug this programme spent a migration removing from the backend.

```ts
// ✓
if (company.score_status === "PUBLISHED" && company.ecoiq_score !== null) {
  render(company.ecoiq_score);   // 0.0 renders as 0.0
} else {
  renderEvidencePending(company.evidence_note);
}
```

### `evidence_coverage` — `number` (0–100 integer)

Weighted share of the 16 material inputs with defensible provenance. **Always
present, never null** — zero coverage is a real measurement ("we checked, and
nothing is evidenced"), not an absence.

Whole percent only. Do not render decimals; the denominator is 16 and greater
precision would be invented.

Pair it with its two halves when explaining: *"78% — 11 of 16 material inputs
supported."*

### `confidence` — string enum

`HIGH` · `MEDIUM` · `LOW` · `INSUFFICIENT_EVIDENCE`

**Not a number, and never rendered as one.** The inputs are categorical, and a
percentage would manufacture precision the data cannot support.

**Independent of coverage.** They do not track each other and must not be
combined into a single indicator:

- 100% coverage from unverified press releases → complete, and **weak**
- 40% coverage from independently verified audits → incomplete, and **strong**

Two separate elements in the UI. Never an average.

### `rank` — `number | null`

`null` when the score is not publishable. **Never compute a rank client-side.**
A rank is a comparative claim; deriving one from a sorted list would assert
exactly what the backend is withholding.

Sorting a list for display is fine. Numbering it is not.

### `evidence_note` — string (detail only)

Plain-English explanation of why a score is withheld. Render it instead of the
score, not alongside a placeholder.

### `harm_signals` — array (detail only)

```json
{ "id": "pollution", "label": "Pollution Severity",
  "status": "clear", "penalty": 0, "detail": "…" }
```

`status` may be `insufficient_evidence`, which is **not** `clear`. A signal that
could not be assessed must not render as an all-clear.

---

## Provenance summary

There is **no** `provenance` key on the v2 company payload today, and the
frontend must not assume one. Provenance is exposed through its summary
projections — `evidence_coverage`, `confidence`, `evidence_note` — not as a
graph.

A deeper "why this result?" view would need a dedicated endpoint. It does not
exist yet; do not build UI that assumes it does.

**Never dump raw provenance rows at a user.**

---

## TypeScript types

```ts
export type ScoreStatus =
  | "PUBLISHED"
  | "PROVISIONAL"
  | "INSUFFICIENT_EVIDENCE";

export type Confidence =
  | "HIGH"
  | "MEDIUM"
  | "LOW"
  | "INSUFFICIENT_EVIDENCE";

export interface CompanySummary {
  slug: string;
  name: string;
  sector: string;
  country: string;
  is_public: boolean;
  verified: boolean;
  /** null unless score_status === "PUBLISHED". 0 is a valid score. */
  ecoiq_score: number | null;
  score_status: ScoreStatus;
  /** 0–100 integer. Always present; 0 is a measurement, not an absence. */
  evidence_coverage: number;
  confidence: Confidence;
  /** null when the score is not publishable. Never derive one. */
  rank: number | null;
  url: string;
}
```

`strictNullChecks` must be on. It is what makes the compiler enforce this
contract rather than leaving it to review.

---

## Financing claims

Company-specific financial claims are eligibility-gated server-side. If the
backend returns none, the company does not qualify to be shown any — the
frontend must not synthesise an "indicative" alternative.

---

## API v1

Legacy, unchanged, not for new frontend work. Its keys are preserved for
existing consumers; `ecoiq_score` there is now `null` rather than a substituted
number.

**React uses v2 exclusively.**

---

## What the frontend must never do

1. Coalesce a null score to any number
2. Render `confidence` as a percentage
3. Combine coverage and confidence into one indicator
4. Compute a rank
5. Treat `0` as missing
6. Treat `insufficient_evidence` as `clear`
7. Reimplement eligibility, coverage or scoring
8. Assume a provenance graph endpoint exists
