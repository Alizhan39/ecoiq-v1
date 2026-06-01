# EcoIQ Capital Integrity Score — Reference Document

**Version: 1.0 — June 2026**
**Audience: Internal methodology, investor briefings, API documentation**

---

## What Is the Capital Integrity Score?

The Capital Integrity Score (CIS) answers a question that standard ESG ratings do not:

> *Is this capital likely to create real public benefit — or is it structured to extract value, generate reputational optics, or obscure a weak underlying project?*

Climate finance is growing rapidly. Green bonds, sustainability-linked loans, transition finance, and blended capital instruments are increasingly common. But not all of them deliver on their stated purpose. Greenwashing, vague use-of-proceeds frameworks, opaque procurement structures, and absent impact measurement are widespread problems.

The Capital Integrity Score evaluates a financing instrument, project, or transaction across seven dimensions to produce a single integrity assessment: **Weak**, **Moderate**, **Strong**, or **High Integrity**.

It is designed for:
- Development banks evaluating project finance proposals
- ESG teams assessing bond or fund eligibility
- Responsible investors conducting pre-investment due diligence
- Ethical finance institutions screening for genuine impact
- Government agencies allocating climate transition capital

---

## Seven Dimensions

### 1. Use of Proceeds Clarity (weight: 20%)
*Is it unambiguous what the capital will be used for?*

High-integrity capital has a specific, documented, contractually ring-fenced use of proceeds. Vague commitments ("general sustainability purposes"), broad sector labels without project-level detail, and absence of reporting frameworks are integrity risks.

**What we assess:**
- Specificity of use-of-proceeds documentation
- Presence of a defined exclusion list
- Commitment to annual impact reporting
- Third-party second opinion or certification

### 2. Public Benefit Potential (weight: 20%)
*Does the stated use have genuine potential to create public value?*

Renewable energy, nature-based solutions, energy efficiency, and community infrastructure score high. Refinancing existing fossil fuel assets labelled as "transition", extractive industry expansion with green labels, and financial instruments with no traceable project-level benefit score low.

**What we assess:**
- Project type and sector alignment
- Direct community beneficiaries
- National or regional development contribution
- Additionality (would the project happen without this capital?)

### 3. Greenwashing Risk (weight: 20%)
*Are there red flags suggesting the environmental or social label does not match the substance?*

This dimension is inverted: a high score means low greenwashing risk. Red flags include: no third-party verification, fossil fuel projects labelled "transition" without a credible phase-out plan, vague impact claims without baseline data, and mismatched instrument labels.

**What we assess:**
- Verification and certification status
- Label–substance alignment (green bond for a gas pipeline = high risk)
- Presence of quantified baselines and targets
- Track record of issuer/borrower on previous commitments

### 4. Ownership and Procurement Transparency (weight: 15%)
*Is the ownership structure clear? Is procurement competitive and fair?*

Capital that flows through opaque ownership structures, related-party procurement, or jurisdictions with poor beneficial ownership registries is at elevated risk of rent extraction, corruption, and reputational harm.

**What we assess:**
- Beneficial ownership disclosure
- Procurement framework (IFC, EBRD, national standards, or none)
- Related-party transaction disclosure
- Regulatory compliance history of the issuer/borrower

### 5. Community and Social Impact (weight: 10%)
*Will affected communities benefit? Were they consulted?*

Communities near industrial or infrastructure projects are frequently the least represented in capital allocation decisions and the most exposed to negative impacts. High-integrity capital structures community consultation and benefit-sharing as a condition, not a courtesy.

**What we assess:**
- Community consultation (FPIC-aligned where applicable)
- Direct community benefit mechanisms
- Local employment and procurement commitments
- Grievance and remedy mechanisms

### 6. Measurable Emissions or Resilience Impact (weight: 10%)
*Are there quantified, verifiable climate or resilience targets?*

High-integrity climate capital has a credible theory of change backed by numbers: tonnes of CO₂ avoided, MWh of renewable capacity added, hectares of habitat restored, or populations gaining climate resilience. Absent metrics are a structural integrity failure.

**What we assess:**
- Specific, time-bound emission reduction or resilience targets
- Baseline year and measurement methodology
- Independent impact verification plan
- Alignment with Paris Agreement or national NDCs

### 7. Ethical Finance Compatibility (weight: 5%)
*Does the instrument align with principles of justice, harm avoidance, and stewardship?*

This dimension assesses compatibility with ethical and responsible capital frameworks, including development finance standards, ESG principles, and long-horizon stewardship criteria.

**What we assess:**
- Sector exclusions (tobacco, weapons, extractive harm, prohibited industries)
- Alignment with harm avoidance requirements
- Transparency and accountability mechanisms
- Stewardship orientation of the issuer

---

## Scoring Formula

```
CIS = (proceeds_clarity    × 0.20)
    + (public_benefit      × 0.20)
    + (greenwashing_risk   × 0.20)   ← inverted: high score = low risk
    + (ownership_transp    × 0.15)
    + (community_impact    × 0.10)
    + (measurable_impact   × 0.10)
    + (ethical_compat      × 0.05)
```

All dimensions are scored 0–100. Final CIS is 0–100.

---

## Label Tiers

| Label | CIS Range | Meaning |
|-------|-----------|---------|
| **High Integrity** | 80 – 100 | Strong across all dimensions. Suitable for responsible finance consideration subject to verification. |
| **Strong** | 65 – 79 | Solid profile with minor gaps. Conditions may apply for full labelling. |
| **Moderate** | 45 – 64 | Partial integrity. Specific remediation required before responsible finance eligibility. |
| **Weak** | 0 – 44 | Material integrity failures. Capital at risk of greenwashing, rent extraction, or reputational harm. Not suitable for responsible finance labelling. |

---

## Red Flags (Automatic)

Regardless of final score, the following conditions always generate a red flag:

- No use of proceeds specificity ("general corporate purposes")
- No third-party verification for instruments labelled "green" or "sustainable"
- Fossil fuel extraction projects labelled as "transition" without a credible phase-out commitment
- Beneficial ownership not disclosed
- No impact measurement plan or baseline data
- Instrument type does not match project type (e.g. green bond for non-green asset)
- Sector excluded by major ethical finance frameworks (weapons, tobacco, significant gambling, harmful extractives)

---

## Positive Indicators

The following features actively reduce risk and improve score:

- CBI certification or equivalent second-party opinion
- Specific, quantified impact targets with baseline years
- Community consultation documentation (FPIC-aligned)
- IFC/EBRD/ADB procurement framework applied
- Impact reporting commitment (annual, independent)
- Open ownership structure in a well-regulated jurisdiction
- Additionality clearly demonstrated
- Gender inclusion and local employment commitments

---

## Ethical and Responsible Finance Compatibility

### For Ethical Finance Institutions

The Capital Integrity Score is designed to align with responsible capital frameworks that require:

| CIS Dimension | Ethical Finance Principle |
|---------------|--------------------------|
| Use of Proceeds Clarity | Certainty of purpose — capital must serve a clearly defined, beneficial function |
| Public Benefit Potential | Maslaha (public interest) — capital must create genuine societal good |
| Greenwashing Risk (low) | Truthfulness — claims about the instrument must be substantiated |
| Ownership Transparency | Amanah (trustworthiness) — structures must be transparent and free from concealed interests |
| Community Impact | Adl (justice) — affected communities must benefit equitably |
| Measurable Impact | Evidence-based accountability — outcomes must be verifiable |
| Ethical Compatibility | Harm avoidance — proceeds must not fund excluded activities |

> **Internal note**: The above table uses accessible English equivalents of the underlying principles. When briefing Islamic finance institutions internally, the full Maqasid al-Shariah mapping is in `docs/mizan-engine.md`. Do NOT publish this table in public API responses or marketing materials.

### Sukuk and Islamic Finance Instruments

The Capital Integrity Score is particularly applicable to sukuk and other Islamic finance instruments because:

1. Sukuk are inherently asset-backed — the "use of proceeds" clarity requirement directly mirrors the sukuk structure requirement that proceeds fund a specific, identifiable asset or project.
2. Shariah screening excludes sectors with high CIS greenwashing risk (alcohol, tobacco, weapons, speculation).
3. The community and social impact dimension maps to the Islamic requirement that capital serve genuine human welfare (maslaha ammah).
4. Transparency requirements mirror amanah (trustworthiness) as a foundational principle.

A high CIS score is not a substitute for formal Shariah compliance review, but it provides a strong structural signal that an instrument is likely to be compatible with the spirit of responsible Islamic capital allocation.

**Public-facing language for Islamic finance audiences:**
> "EcoIQ's Capital Integrity Score evaluates whether climate capital is transparent, beneficial, and free from greenwashing — criteria that align with the foundational requirements of ethical and responsible finance, including Shariah-compliant investment screening."

---

## Integration With EcoIQ Mizan Engine

The Capital Integrity Score uses several of the same underlying metrics as the Mizan Engine but applies them specifically to capital instruments rather than company operating profiles:

| CIS Dimension | Mizan Engine Equivalent |
|---------------|------------------------|
| Public benefit potential | `public_benefit_score` |
| Community and social impact | `justice_distribution_score` |
| Ownership transparency | `transparency_accountability_score` |
| Greenwashing risk | `harm_reduction_score` + `evidence_confidence_score` |
| Ethical compatibility | `stewardship_score` |

When an `existing_ecoiq_profile` (company slug) is provided as input, the CIS uses the company's Mizan score to calibrate the issuer/borrower credibility adjustment.

---

## ML Integration Roadmap

The current implementation is rule-based and transparent. ML integration will follow the same pattern as the Mizan Engine:

```python
# ML-HOOK: replace rule-based dimension formulas with:
#   from joblib import load
#   clf = load('ml/models/capital_integrity_clf.joblib')
#   fv  = capital_integrity_feature_vector(inp)
#   scores = clf.predict([list(fv.values())])[0]  # 7 dimension scores
```

Training data requirements:
- Historical green bond and sustainability-linked loan outcomes with verified impact reports
- Greenwashing enforcement cases (SEC, FCA, BaFin) labelled with structural red flags
- ICMA GBP and CBI certification data with issuer characteristics
- Development bank (IFC, EBRD, ADB) project finance outcomes

---

## Output Fields

Every CIS evaluation returns:

| Field | Type | Description |
|-------|------|-------------|
| `capital_integrity_score` | float 0–100 | Weighted composite |
| `label` | str | `high-integrity` / `strong` / `moderate` / `weak` |
| `dimension_scores` | dict | All 7 dimension scores |
| `red_flags` | list[str] | Structural integrity failures |
| `positive_indicators` | list[str] | Integrity-positive features |
| `investor_note` | str | Narrative summary for investors |
| `islamic_finance_note` | str | Ethical/responsible finance compatibility |
| `due_diligence_required` | list[str] | Specific verification items |
| `recommended_next_actions` | list[str] | Actionable improvement steps |
| `confidence` | str | `model-estimate` (always, for CIS) |
| `methodology` | str | Engine version reference |

---

*Internal use. Contains methodology details and internal terminology not for public reproduction.*
*Last updated: June 2026.*
