# Document Reader Agent — Evaluation Metrics

Field extraction accuracy, missing field detection, unit preservation
accuracy, document type classification accuracy, table extraction quality,
PII detection rate, unsupported claim rate, human approval trigger accuracy,
JSON/schema validity, reviewer acceptance rate.

## Pass/fail criteria

A golden test case passes when: document type is correctly classified, all
expected fields are extracted or correctly marked missing, units/currency are
preserved exactly, evidence quality matches the rubric in `outputs.md`, and no
invented value appears anywhere in the output.
