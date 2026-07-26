# Digital Twin Agent — Evaluation Criteria

Pass requires: every open critical/high TwinDataGap in the input is echoed in `missing_data`; `position` is never `support` when `ready_for_optimisation` is False.

Every test case in `test_cases.json` must produce the `expected_output`
fields shown; any mismatch is a failing eval, not a matter of degree.
