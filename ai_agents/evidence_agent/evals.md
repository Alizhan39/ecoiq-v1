# Evidence Agent — Evaluation Criteria

Pass requires flagging missing_data whenever confidence is non-null and evidence_reference_count is 0.

Every test case in `test_cases.json` must produce the `expected_output`
fields shown; any mismatch is a failing eval, not a matter of degree.
