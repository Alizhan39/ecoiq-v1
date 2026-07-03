# Research Agent — Evaluation Metrics

| Metric | What it measures |
|---|---|
| Source attribution accuracy | Every fact in `evidence_summary` maps to a real, correctly cited source |
| Missing data detection | Absent fields correctly flagged rather than guessed |
| Confidence calibration | Confidence score matches actual source strength/agreement |
| Outdated information detection | Old data correctly flagged as outdated |
| Unsupported claim rate | Rate of claims not traceable to a cited source (target: 0) |
| Certification-overclaim rate | Rate of implying certification/compliance without a primary source (target: 0) |
| Human approval trigger accuracy | Correctly flags outputs destined for public/investor/government use |
| JSON schema validity | Output always matches `outputs.md` schema |
| Reviewer acceptance rate | Proportion of outputs a human reviewer accepts without correction |

## Pass/fail criteria for a golden test case

A test case **passes** when:
1. All fields present in the schema (no silently dropped fields)
2. Every `evidence_summary` item is attributable to a `source_list` entry
3. `missing_data` and `confidence` match the expected values in `test_cases.json`
4. No invented figures, dates or certifications appear anywhere in the output

A test case **fails** if any invented fact appears, regardless of how minor.
