# Release verification: interactive Lab and ML candidates

Baseline: PRs #346 and #347, merged through `9df74705a8bacb9ae3b6ea5f99c972f038f6a15e`.
Do not infer production readiness from merge, synthetic metrics, or check counts.
AR and ML activation are separate decisions. Record evidence against the exact
release SHA; previous-commit checks do not certify a new deployment.

## Implemented safeguards

- The training CLI requires candidate output by default, rejects candidate/apply
  and candidate/legacy combinations before querying data, and requires the
  explicit `--allow-legacy-write` override for legacy replacement or DB apply.
  It is an operational guard, not a quality approval system or atomic promotion.
- Viewer failures restore focus to retry if the removed viewer held focus, while
  retaining the text controls. Import failures preserve keyboard recovery too.
- The Chromium browser workflow exercises compiled assets at 375 px with a local
  API fixture. Its screenshots and traces are review evidence, not hardware proof.

## Open release gates

All rows below remain OPEN until the indicated evidence is attached. Assign an
owner when scheduling a run; no owner, approval or result is assumed here.
P0 blocks the affected capability. P1 is required before production-ready claims.

| Priority / scope | Procedure and reason | Pass evidence |
| --- | --- | --- |
| P0 ML dataset | Restore authorized DB access, approve provenance, labels and dataset version; technical completeness cannot establish truth. | Dataset version and approval reference; candidate reports for real-data runs, feature/input/artifact hashes and runtime versions. Do not commit raw confidential data. |
| P0 ML external evaluation | Freeze an untouched external set; separate related companies and time; predeclare acceptable scoring error and baseline improvement. Existing EcoIQ targets do not independently validate the score formula. | Sample counts, split rules, MAE and baseline on identical rows, sector errors, exclusions, uncertainty and reviewer acceptance. Ten rows is not a production sample-size justification. |
| P0 ML runtime | Check reviewed candidate reload/predict in the actual deployment image; prior local `_loss` import failure is unresolved for deployment compatibility. | Exact Python/sklearn/numpy/joblib versions, trusted artifact hashes, expected vs actual predictions on reviewed probes; no pickle import workaround. |
| P0 ML activation / rollback | Preserve incumbent artifacts and public scores while testing; rehearse version selection and rollback in staging. CLI legacy writes are still not an atomic multi-model promotion. | Before/after artifact hashes and score checks; staging activation/rollback log; explicit review of any scheduler invoking legacy writes. |
| P0 ML decision use | Anomaly counts and cluster names do not prove wrongdoing or useful classification. | Reviewed labels, accepted false-positive/false-negative criteria and cluster stability review; otherwise keep `NOT_MEASURED` and experimental/non-decision use. |
| P0 AR permission / lifecycle | Actual Android Chrome and iOS Safari over HTTPS: allow, refuse, cancel, exit, return, repeat; camera must not start on page entry. | Device/OS/browser versions and recording: text UI survives, no repeated unsolicited prompts, retry works and native handoff returns cleanly. |
| P1 AR placement | Test claimed WebXR/Scene Viewer/Quick Look paths; generated USDZ is not validated by GLB parsing. | Model placement and interaction recording on each supported path; accessible text remains authoritative when native hotspots are absent; no measured-scale claims. |
| P1 layout / keyboard | Inspect 375 px screenshots and navigate using Tab/Shift+Tab/Enter, including catalogue links and viewer controls, loading, failure and retry. | No clipped controls or unintended overflow; visible logical focus, no traps; record human visual inspection separately from automated assertions. |
| P1 fallback | Block JS chunk, GLB, and network; test unsupported AR/WebGL on real browsers; restore network and retry. | Text remains usable; errors are understandable; recovery succeeds without stale disabled controls. |
| P1 language | Fluent KK and AR reviewers inspect labels, errors, demo disclaimers, RTL, numbers and long strings on narrow screens. | Reviewer/date and corrected strings; automated `lang` / `dir` assertions are not translation approval. |
| P1 deployed assets / speed | Check release SHA, HTTPS route/API/static files, deferred viewer network request and realistic mobile network/device performance. | No stale asset 404s; viewer requested only after Load; measured timings against an agreed device budget (300 kB gzip is not a speed measurement). |

## Conditional gates

Real customer models require organization/publication authorization, upload
format/size validation and evidence permission checks. Never expose private R2
URLs or add arbitrary remote fetching to the anonymous demo endpoint.

Neural search training is outside the company training command. Before changing
the pinned encoder, obtain licensed query/passage relevance labels, independent
train/validation/test partitions and EN/RU/KK/AR comparison to the existing
encoder, with citation/source review.

## Evidence record template

- Gate and release SHA:
- Date, operator/reviewer:
- Environment or device / OS / browser versions:
- Dataset/artifact version, if applicable (no secrets or raw personal data):
- Procedure and expected result:
- Actual result and evidence link:
- PASS / FAIL / BLOCKED, issue and next action:

A blocked run stays BLOCKED. Synthetic fixture training must never be labelled
real-data training. Screenshots cannot certify camera permission or native AR.

## Follow-up local verification (2026-10-09)

- Python 3.12: combined ML, interactive API and SPA suite: **269 passed**.
- Frontend: **564 passed** across 41 files; ESLint and TypeScript/build passed.
- Six Playwright browser cases are discoverable. Local Chromium installation
  failed because the download returned truncated ZIP archives, so browser layout,
  real GLB rendering and screenshot review remain **BLOCKED locally**, not passed.
- No approved real-data training, external model validation, deployment-runtime
  certification, fluent-speaker sign-off or physical AR test was performed.
- This local Python runtime does not replace CI's pinned 3.11.16 validation.
