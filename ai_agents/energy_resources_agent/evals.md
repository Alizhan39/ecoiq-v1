# Energy and Resources Agent — Evaluation Criteria

Pass requires flagging missing_data whenever an impact figure has no corresponding baseline ResourceFlow on the same twin.

Every test case in `test_cases.json` must produce the `expected_output`
fields shown; any mismatch is a failing eval, not a matter of degree.
