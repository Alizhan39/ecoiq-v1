# Photo / Visual Evidence Agent — Evaluation Metrics

Hypothesis-labelling accuracy (every finding correctly marked as a
hypothesis), image quality assessment accuracy, false-positive rate on
quantified readings (target: 0 readings without a visible gauge), safety
concern detection recall, PII detection rate, human approval trigger
accuracy, JSON schema validity, reviewer acceptance rate.

## Pass/fail criteria

A golden test case passes when every finding carries a "needs verification"
label, no quantified figure appears without a visible source, and any safety
concern is flagged for human/expert review rather than resolved by the agent.
