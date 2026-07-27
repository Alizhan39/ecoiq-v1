# Independent Evidence Agent — Evaluation Criteria

Pass requires insufficient_evidence whenever verified is False and evidence_score is below 40.

Every test case in `test_cases.json` must produce the `expected_output`
fields shown; any mismatch is a failing eval, not a matter of degree.
