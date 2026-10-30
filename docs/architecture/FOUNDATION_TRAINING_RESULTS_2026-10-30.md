# Foundation training — reproducible synthetic result, 2026-10-30

**Source:** [GitHub Actions run #41135654886](https://github.com/Alizhan39/ecoiq-v1/actions/runs/41135654886), Python 3.11.16, sklearn pinned development dependencies.

This is actual **offline RandomForestClassifier training on generated synthetic data**. It is NOT real-company training, external validation, religious knowledge model, or a permission to publish an EcoIQ score.

## Dataset and split
- Deterministic seed: `20261030`.
- 14 existing EcoIQ OS domains, 48 synthetic sites/domain, 3 periods/site.
- **2,016 rows, 672 independent site groups**.
- 504 sites in group training, **168 never-seen sites** in test, no repeated site across train/test.
- Separately: all synthetic construction sites held out from the domain-generalisation model.
- Synthetic simulated event prevalence: **33.88%**.
- Training input SHA-256: `9bd779183bc169a4277b098de31805de45fdca49820600b32b6d1c14371a63dc`.
- The experiment uses 20/33 artificial normalised *risk-signal features*, NOT measured 20/33 operational KPI values. Missing is represented distinctly from measured zero.

## Held-out measurements

| Measurement (site-group holdout) | Initial 20 | Expanded 33 | Majority-class baseline |
|---|---:|---:|---:|
| Balanced accuracy | **0.7563** | 0.7505 | 0.5000 |
| Precision for synthetic event | **0.7785** | 0.7667 | 0 |
| Recall for synthetic event | **0.6170** | 0.6117 | 0 |
| True positive | 116 | 115 | 0 |
| False positive | 33 | 35 | 0 |
| False negative | 72 | 73 | 188 |
| True negative | 283 | 281 | 316 |

**Interpretation:** Initial 20 synthetic features perform **slightly better**
on this one seeded split. More features did not automatically improve the
classifier, and differences are not statistically established. There are
still **72 missed simulated events out of 188 positives** in the 20-feature
group holdout, which would be unacceptable for many critical real-world
decisions without a domain-specific safety assessment.

## Synthetic construction domain excluded from training

| Measurement | Initial 20 | Expanded 33 |
|---|---:|---:|
| Balanced accuracy | 0.7241 | 0.7222 |
| Recall | 0.5370 | 0.5556 |
| False negatives | 25 | 24 |
| False positives | 8 | 10 |

Neither model establishes transfer to a real construction site.
This out-of-domain check is synthetic, not independent real evidence.

## Conclusions and next gates

1. **Retain 20 as the candidate pilot feature budget** until independent real data justifies additional indicators. This is a research recommendation, not a definitive statistical winner.
2. Do not infer that a KPI necessarily represents a principled moral state, serious harm, avoidable waste, injustice or Shariah conformance.
3. The proposed 33 × 114 = 3,762 combinations remain **UNREVIEWED** with no verse mapping or theological labels. The 99 Names inventory is metadata only.
4. Next iteration requires documented KPI formulas, industry baselines, scoped and lawful source data, time-forward tests, fairness/missing-data assessment, cost-sensitive thresholds and false-negative analysis.
5. Existing OS flow/evidence/Mizan/Islah kernel and independent human approval stay authoritative. Do not deploy this classifier or use it to automatically change business processes.

**Technical gates:** eight foundation unit tests passed, 19 existing OS/knowledge tests passed, no model artifact saved, no external API calls. Full repository Django CI is a separate gate and must also pass before merge.
