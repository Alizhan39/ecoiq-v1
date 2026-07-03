# Report Generator Agent — Evaluation Metrics

Claim traceability rate (target: 100% of claims linked to evidence),
verified-language accuracy (only used when MRV Verified + governance approved),
risk/assumption omission rate (target: 0), governance-gate compliance rate,
JSON schema validity, reviewer acceptance rate.

## Pass/fail criteria

Passes when every claim traces to evidence, governance_approval_confirmed
correctly gates `status: usable`, and no risk/assumption is silently dropped.
