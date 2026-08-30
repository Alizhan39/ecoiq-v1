/**
 * economics — the derivations behind every figure the borough demo displays.
 *
 * WHY THIS FILE EXISTS AT ALL
 * ---------------------------
 * A demo is the easiest place in a product to write a number that is not the
 * result of anything. Payback "1.4 years" typed beside a £110k capex and a
 * £79k saving is not a calculation, it is a coincidence waiting to stop being
 * one — and the moment somebody edits the saving, the demo starts showing a
 * payback that contradicts its own inputs in front of a buyer.
 *
 * So the dataset in demoData.ts holds only INPUTS: capex, annual saving, CO2
 * reduction, forecast, verified. Every derived figure on the page — payback,
 * portfolio totals, variance — is computed here, from those inputs, at render
 * time. There is no second copy of any number to drift.
 *
 * NO BUSINESS LOGIC IS DUPLICATED HERE
 * ------------------------------------
 * These are arithmetic identities (capex ÷ saving; (actual − forecast) ÷
 * forecast), not EcoIQ's evidence, eligibility or scoring rules. Those live in
 * companies/eligibility.py, companies/provenance.py and the engines behind
 * them, are session-authenticated, and are not what a public demonstration
 * page is entitled to reach into.
 */

/** Simple payback in years. Null when the saving cannot produce one. */
export function paybackYears(
  capexPounds: number,
  annualSavingPounds: number,
): number | null {
  // Not `annualSaving || 0`: a zero or negative saving has no payback, and
  // rendering "0.0 years" for it would be the fastest payback on the page.
  if (annualSavingPounds <= 0) return null;
  return capexPounds / annualSavingPounds;
}

/**
 * Variance of an outcome against its forecast, as a percentage.
 *
 * Signed: under-delivery is negative. A demo that reports the absolute value
 * would show a 3.3% shortfall and a 3.3% overshoot identically, which is the
 * one distinction the whole MRV section exists to make.
 */
export function variancePercent(
  actual: number,
  forecast: number,
): number | null {
  if (forecast === 0) return null;
  return ((actual - forecast) / forecast) * 100;
}

/** £42,000 → "£42k". Whole thousands only; the inputs are all round. */
export function poundsToK(pounds: number): string {
  return `£${Math.round(pounds / 1000).toLocaleString('en-GB')}k`;
}

/** £8,400,000 → "£8.4m". For estate-scale figures. */
export function poundsToM(pounds: number): string {
  return `£${(pounds / 1_000_000).toFixed(1)}m`;
}

/** £76,420 → "£76,420". For a figure whose precision is the point. */
export function poundsExact(pounds: number): string {
  return `£${Math.round(pounds).toLocaleString('en-GB')}`;
}

/** 1.3924 → "1.4 years". Null → an em dash, never "0". */
export function years(value: number | null): string {
  return value === null ? '—' : `${value.toFixed(1)} years`;
}

/** −3.266 → "−3.3%". Uses a real minus sign, not a hyphen. */
export function percent(value: number | null): string {
  if (value === null) return '—';
  const sign = value < 0 ? '−' : '+';
  return `${sign}${Math.abs(value).toFixed(1)}%`;
}

/** 14820 → "14,820". */
export function tonnes(value: number): string {
  return value.toLocaleString('en-GB');
}
