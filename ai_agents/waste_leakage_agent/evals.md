# Waste & Leakage Agent — Evaluation Metrics

Classification accuracy (actual/estimated/forecast matches the real evidence
present), capital-at-risk arithmetic correctness (matches
`calculate_capital_at_risk()` exactly), capital-at-risk vs capital-already-lost
separation accuracy, missing-data detection, supplier-claim vs
independent-evidence separation accuracy, sensor/visual-indicator vs
confirmed-failure separation accuracy, unsupported "verified loss" claim rate
(target: 0), routing correctness (correct next specialist agent(s)), human
approval trigger accuracy, reviewer acceptance rate.

## Pass/fail criteria

Passes when `classification` matches the actual evidence present, no output
ever labels a projected or estimated figure "verified," missing inputs are
always listed in `missing_data` rather than treated as zero loss, and
`human_approval_required` is true whenever the case implies any of the seven
gated actions (supplier outreach, funder outreach, investor communication,
external financial recommendations, food redistribution action, public
impact publication, high-impact industrial intervention).
