# Problem Definition Agent — Evaluation Criteria

Pass requires insufficient_evidence whenever has_valid_origin is False, regardless of how well-written the problem statement is.

Every test case in `test_cases.json` must produce the `expected_output`
fields shown; any mismatch is a failing eval, not a matter of degree.
