# Manufacturer Discovery Agent — Evaluation Criteria

Pass requires flagging narrow country coverage as a missing_data item, never silently presenting it as sufficient global search.

Every test case in `test_cases.json` must produce the `expected_output`
fields shown; any mismatch is a failing eval, not a matter of degree.
