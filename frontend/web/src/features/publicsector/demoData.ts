/**
 * demoData — the London Borough Sustainability Command Centre dataset.
 *
 * ════════════════════════════════════════════════════════════════════════════
 *  FICTITIOUS DEMONSTRATION DATASET.
 *
 *  There is no borough. There is no client. Nothing here was measured,
 *  supplied by a public body, or derived from one. Every figure was written
 *  to make the decision flow legible, and none of it describes a real estate,
 *  a real asset, a real saving or a real verification.
 *
 *  EcoIQ has delivered no public-sector engagement. If this dataset is ever
 *  mistaken for a case study, that is the failure this header exists to
 *  prevent.
 * ════════════════════════════════════════════════════════════════════════════
 *
 * WHY EVERY QUANTITY CARRIES A BASIS
 * ----------------------------------
 * The `Quantity`/`basis` primitive from features/transition/domain/unknown is
 * reused rather than reinvented, and every quantity in this file is
 * `illustrative`. That is enforced by demoData.test.ts, which walks the whole
 * dataset: a figure added here without a basis, or with `measured`, fails the
 * suite. Labelling is a property of the data, not a promise the page makes.
 *
 * WHY THE ASSETS ARE NAMED "School A" AND NOT "Meadowbank Primary"
 * ---------------------------------------------------------------
 * An invented school name is indistinguishable from a real one, and there is a
 * real school behind almost any plausible name. Role labels cannot be mistaken
 * for an identifiable building, which is exactly the property this dataset
 * needs.
 *
 * WHAT IS DELIBERATELY NOT HERE
 * -----------------------------
 * Payback, portfolio totals and variance. Those are DERIVED in economics.ts
 * from the inputs below, so the demo cannot show a payback that disagrees with
 * the capex and saving printed beside it.
 */
import type { Quantity } from '@/features/transition/domain/unknown';

/**
 * The label. One string, used by every surface that shows this data, so a
 * page cannot display the dataset without displaying its status.
 */
export const DEMONSTRATION_NOTICE =
  'Fictitious demonstration dataset. The borough, its estate and every figure '
  + 'shown are illustrative — no real organisation, asset, saving or client '
  + 'outcome is described.';

/** Short form, for a badge beside a figure. */
export const DEMONSTRATION_BADGE = 'Demonstration data';

/** Every money quantity is in whole pounds; every emission quantity in tCO₂e. */
function money(pounds: number): Quantity {
  return { value: pounds, unit: 'GBP', basis: 'illustrative' };
}

function emissions(tco2e: number): Quantity {
  return { value: tco2e, unit: 'tCO2e', basis: 'illustrative' };
}

function count(units: number, unit: string): Quantity {
  return { value: units, unit, basis: 'illustrative' };
}

// ── The estate ───────────────────────────────────────────────────────────────

export interface EstateSummary {
  buildings: Quantity;
  annualEnergySpend: Quantity;
  annualEmissions: Quantity;
}

/**
 * The four figures a procurement reader sees first.
 *
 * `identifiedAnnualSaving` is NOT here. It is the sum of the flagged assets
 * below, computed by portfolioTotals(), because a headline saving that is not
 * the sum of its parts is the single most common way a dashboard becomes
 * untrue.
 */
export const ESTATE: EstateSummary = {
  buildings: count(127, 'buildings'),
  annualEnergySpend: money(8_400_000),
  annualEmissions: emissions(14_820),
};

// ── Flagged assets ───────────────────────────────────────────────────────────

export type AssetProblem =
  | 'HVAC inefficiency'
  | 'Boiler / heating system inefficiency'
  | 'Lighting inefficiency'
  | 'Heating controls and schedule mismatch'
  | 'Building fabric losses'
  | 'Communal heating inefficiency'
  | 'Hot water system inefficiency'
  | 'Compressed air losses'
  | 'Motor and drive losses';

export interface FlaggedAsset {
  id: string;
  /** A role label, never an identifiable building. See the header. */
  name: string;
  category: string;
  problem: AssetProblem;
  capex: Quantity;
  annualSaving: Quantity;
  emissionsReduction: Quantity;
  /** Ranking is by payback, computed — this is only the display order seed. */
  priority: number;
}

/**
 * Seventeen assets, because the headline says seventeen require attention.
 *
 * All seventeen are listed rather than three-plus-a-number: the £740,000
 * headline is the SUM of this list, asserted by demoData.test.ts. A portfolio
 * figure with no portfolio behind it is a magic number, and this page exists
 * to argue against exactly that habit.
 */
export const FLAGGED_ASSETS: FlaggedAsset[] = [
  {
    id: 'leisure-centre',
    name: 'Leisure Centre',
    category: 'Leisure',
    problem: 'Boiler / heating system inefficiency',
    capex: money(110_000),
    annualSaving: money(79_000),
    emissionsReduction: emissions(220),
    priority: 1,
  },
  {
    id: 'school-a',
    name: 'School A',
    category: 'Education',
    problem: 'HVAC inefficiency',
    capex: money(42_000),
    annualSaving: money(31_000),
    emissionsReduction: emissions(84),
    priority: 2,
  },
  {
    id: 'council-office',
    name: 'Council Office',
    category: 'Corporate estate',
    problem: 'Lighting inefficiency',
    capex: money(18_000),
    annualSaving: money(16_000),
    emissionsReduction: emissions(31),
    priority: 3,
  },
  {
    id: 'street-lighting-zone-3',
    name: 'Street Lighting — Zone 3',
    category: 'Infrastructure',
    problem: 'Lighting inefficiency',
    capex: money(265_000),
    annualSaving: money(180_000),
    emissionsReduction: emissions(261),
    priority: 4,
  },
  {
    id: 'housing-block-a',
    name: 'Housing Block A',
    category: 'Housing',
    problem: 'Communal heating inefficiency',
    capex: money(118_000),
    annualSaving: money(75_000),
    emissionsReduction: emissions(205),
    priority: 5,
  },
  {
    id: 'housing-block-b',
    name: 'Housing Block B',
    category: 'Housing',
    problem: 'Communal heating inefficiency',
    capex: money(88_000),
    annualSaving: money(54_000),
    emissionsReduction: emissions(149),
    priority: 6,
  },
  {
    id: 'museum-archive',
    name: 'Museum & Archive',
    category: 'Culture',
    problem: 'HVAC inefficiency',
    capex: money(86_000),
    annualSaving: money(52_000),
    emissionsReduction: emissions(118),
    priority: 7,
  },
  {
    id: 'school-c',
    name: 'School C',
    category: 'Education',
    problem: 'Building fabric losses',
    capex: money(78_000),
    annualSaving: money(43_000),
    emissionsReduction: emissions(118),
    priority: 8,
  },
  {
    id: 'care-home-a',
    name: 'Care Home A',
    category: 'Adult social care',
    problem: 'Hot water system inefficiency',
    capex: money(52_000),
    annualSaving: money(38_000),
    emissionsReduction: emissions(101),
    priority: 9,
  },
  {
    id: 'sports-hall',
    name: 'Sports Hall',
    category: 'Leisure',
    problem: 'HVAC inefficiency',
    capex: money(44_000),
    annualSaving: money(33_000),
    emissionsReduction: emissions(88),
    priority: 10,
  },
  {
    id: 'depot-workshop',
    name: 'Depot & Fleet Workshop',
    category: 'Operations',
    problem: 'Compressed air losses',
    capex: money(38_000),
    annualSaving: money(29_000),
    emissionsReduction: emissions(61),
    priority: 11,
  },
  {
    id: 'waste-transfer-station',
    name: 'Waste Transfer Station',
    category: 'Operations',
    problem: 'Motor and drive losses',
    capex: money(33_000),
    annualSaving: money(25_000),
    emissionsReduction: emissions(52),
    priority: 12,
  },
  {
    id: 'civic-theatre',
    name: 'Civic Theatre',
    category: 'Culture',
    problem: 'HVAC inefficiency',
    capex: money(29_000),
    annualSaving: money(24_000),
    emissionsReduction: emissions(51),
    priority: 13,
  },
  {
    id: 'school-b',
    name: 'School B',
    category: 'Education',
    problem: 'Heating controls and schedule mismatch',
    capex: money(26_000),
    annualSaving: money(22_000),
    emissionsReduction: emissions(58),
    priority: 14,
  },
  {
    id: 'library-a',
    name: 'Library A',
    category: 'Culture',
    problem: 'Lighting inefficiency',
    capex: money(21_000),
    annualSaving: money(18_000),
    emissionsReduction: emissions(34),
    priority: 15,
  },
  {
    id: 'community-centre',
    name: 'Community Centre',
    category: 'Community',
    problem: 'Heating controls and schedule mismatch',
    capex: money(14_000),
    annualSaving: money(12_000),
    emissionsReduction: emissions(26),
    priority: 16,
  },
  {
    id: 'registry-office',
    name: 'Registry Office',
    category: 'Corporate estate',
    problem: 'Lighting inefficiency',
    capex: money(11_000),
    annualSaving: money(9_000),
    emissionsReduction: emissions(18),
    priority: 17,
  },
];

// ── Priority 01: the Leisure Centre, in depth ────────────────────────────────

export interface EnergyAnomaly {
  assetId: string;
  fuel: string;
  /** Percentage above the weather-normalised baseline. */
  deviationPercent: Quantity;
  excessAnnualCost: Quantity;
  /** Candidate causes. Ranked by nothing — they are candidates, not findings. */
  candidateCauses: string[];
  detectedBy: string;
}

export const LEISURE_CENTRE_ANOMALY: EnergyAnomaly = {
  assetId: 'leisure-centre',
  fuel: 'Gas',
  deviationPercent: { value: 31, unit: '%', basis: 'illustrative' },
  excessAnnualCost: money(96_000),
  candidateCauses: [
    'Boiler inefficiency',
    'Poor controls',
    'Heating schedule mismatch',
    'Building fabric losses',
  ],
  detectedBy:
    'Consumption compared against a weather-normalised baseline built from '
    + 'the site’s own prior-year meter data and degree-day data for the '
    + 'period.',
};

export interface InterventionOption {
  id: string;
  label: string;
  /** What it physically changes, in one line. */
  effect: string;
  capex: Quantity;
  annualSaving: Quantity;
  emissionsReduction: Quantity;
}

/**
 * The comparison a capital decision actually turns on.
 *
 * The boiler-upgrade row is the SAME capex and saving as the Leisure Centre
 * entry in FLAGGED_ASSETS, asserted by test — the portfolio view and the
 * drill-down must not disagree about the same intervention.
 */
export const LEISURE_CENTRE_INTERVENTIONS: InterventionOption[] = [
  {
    id: 'controls-optimisation',
    label: 'Controls optimisation',
    effect:
      'Re-sequence plant, correct setpoints and align the heating schedule to '
      + 'actual occupancy. Changes how the existing equipment runs, not what '
      + 'it is.',
    capex: money(18_000),
    annualSaving: money(27_000),
    emissionsReduction: emissions(71),
  },
  {
    id: 'boiler-upgrade',
    label: 'Boiler upgrade',
    effect:
      'Replace the heat-raising plant with a higher-efficiency unit, keeping '
      + 'the distribution system.',
    capex: money(110_000),
    annualSaving: money(79_000),
    emissionsReduction: emissions(220),
  },
  {
    id: 'heat-pump-transition',
    label: 'Heat-pump transition',
    effect:
      'Retire fired heat entirely and move the load to electricity, which '
      + 'changes the fuel as well as the efficiency.',
    capex: money(410_000),
    annualSaving: money(118_000),
    emissionsReduction: emissions(381),
  },
];

/**
 * The sequence EcoIQ would put in front of a decision-maker.
 *
 * Phrased as a proposal throughout. EcoIQ proposes; a person decides. The
 * approval gate below is not decoration on top of an automated action — it is
 * the point at which anything happens at all.
 */
export const LEISURE_CENTRE_RECOMMENDATION = {
  sequence: [
    'Controls optimisation',
    'Boiler upgrade',
    'Evaluate heat-pump transition at the next capital cycle',
  ],
  reasoning:
    'Controls optimisation returns capital fastest and reduces the load the '
    + 'later plant has to meet, so sizing it first avoids buying capacity the '
    + 'building no longer needs. The heat-pump transition carries the largest '
    + 'emissions reduction and the longest payback, which makes it a capital-'
    + 'cycle decision rather than an in-year one.',
  status: 'Needs human approval',
} as const;

// ── Evidence ────────────────────────────────────────────────────────────────

export type EvidenceConfidence = 'High' | 'Medium' | 'Low';
export type EvidenceStatus = 'Verified' | 'Recorded' | 'Modelled' | 'Outstanding';

export interface EvidenceItem {
  id: string;
  type: string;
  source: string;
  /** ISO date. Fixed values — this dataset is deterministic. */
  date: string;
  confidence: EvidenceConfidence;
  methodology: string;
  status: EvidenceStatus;
}

/**
 * What the recommendation rests on, item by item.
 *
 * Two of these are deliberately not "Verified". A demonstration evidence
 * panel in which everything is green teaches a buyer the wrong thing about
 * what EcoIQ does — the product's whole argument is that it shows you the
 * weak links rather than averaging them away.
 */
export const LEISURE_CENTRE_EVIDENCE: EvidenceItem[] = [
  {
    id: 'ev-bills',
    type: 'Energy bills',
    source: 'Supplier invoices, 24 months',
    date: '2026-07-31',
    confidence: 'High',
    methodology: 'Invoiced consumption and cost, reconciled to meter reads.',
    status: 'Verified',
  },
  {
    id: 'ev-meter',
    type: 'Meter readings',
    source: 'Half-hourly gas and electricity meters',
    date: '2026-07-31',
    confidence: 'High',
    methodology: 'Half-hourly interval data, gap-checked against invoiced totals.',
    status: 'Verified',
  },
  {
    id: 'ev-attributes',
    type: 'Building attributes',
    source: 'Estate asset register',
    date: '2026-05-14',
    confidence: 'Medium',
    methodology: 'Floor area, construction period, plant inventory and pool volume.',
    status: 'Recorded',
  },
  {
    id: 'ev-baseline',
    type: 'Weather-normalised baseline',
    source: 'Derived from meter data and degree-day data',
    date: '2026-08-02',
    confidence: 'High',
    methodology:
      'Regression of consumption on heating degree days for the site, fitted '
      + 'on the prior year and applied to the current period.',
    status: 'Modelled',
  },
  {
    id: 'ev-tariff',
    type: 'Tariff data',
    source: 'Contracted supply rates',
    date: '2026-04-01',
    confidence: 'High',
    methodology: 'Unit rate and standing charge for the contracted period.',
    status: 'Verified',
  },
  {
    id: 'ev-maintenance',
    type: 'Maintenance history',
    source: 'Facilities management records',
    date: '2026-06-20',
    confidence: 'Low',
    methodology:
      'Service and fault records for the heating plant. Records are '
      + 'incomplete before 2024, which is why confidence is low rather than '
      + 'assumed.',
    status: 'Outstanding',
  },
  {
    id: 'ev-factors',
    type: 'Emission factors',
    source: 'Published national conversion factors for the reporting year',
    date: '2026-06-01',
    confidence: 'High',
    methodology: 'Applied to metered fuel and electricity consumption.',
    status: 'Verified',
  },
];

// ── Human approval ──────────────────────────────────────────────────────────

export const APPROVAL_ACTIONS = [
  {
    id: 'approve',
    label: 'Approve',
    consequence:
      'The intervention enters delivery tracking, and the measurement period '
      + 'that will test it starts from the commissioning date.',
  },
  {
    id: 'reject',
    label: 'Reject',
    consequence:
      'The recommendation is closed with the reason recorded against it. The '
      + 'underlying anomaly stays open, because rejecting a proposal does not '
      + 'resolve the thing that produced it.',
  },
  {
    id: 'request-analysis',
    label: 'Request further analysis',
    consequence:
      'The recommendation returns for more work, with the evidence gap named. '
      + 'Here that would be the incomplete maintenance history.',
  },
] as const;

// ── MRV ─────────────────────────────────────────────────────────────────────

export interface MrvStage {
  key: string;
  label: string;
  detail: string;
}

/**
 * The measurement loop, in the buyer's vocabulary.
 *
 * This is a public-facing simplification of the eight-step workflow in
 * impact_mrv_layer/views.py (Measure Baseline → … → Generate Report), not a
 * competing definition of it. The internal workflow is unchanged; this names
 * the same sequence in the seven steps a finance officer asks about.
 */
export const MRV_STAGES: MrvStage[] = [
  {
    key: 'baseline',
    label: 'Baseline',
    detail:
      'Consumption, cost and emissions before the change, weather-normalised '
      + 'so a mild winter cannot be mistaken for a saving.',
  },
  {
    key: 'intervention',
    label: 'Intervention',
    detail: 'What was installed, when it was commissioned, and at what cost.',
  },
  {
    key: 'measurement',
    label: 'Measurement period',
    detail:
      'Twelve months of post-commissioning meter data, so a full heating '
      + 'season is inside the window.',
  },
  {
    key: 'normalisation',
    label: 'Normalisation',
    detail:
      'The baseline is adjusted to the weather and occupancy actually '
      + 'experienced, so the comparison is like for like.',
  },
  {
    key: 'actual',
    label: 'Actual saving',
    detail: 'Normalised baseline minus measured consumption, priced at the '
      + 'tariff in force.',
  },
  {
    key: 'variance',
    label: 'Variance',
    detail:
      'Actual against forecast. Reported signed, because a shortfall and an '
      + 'overshoot are not the same result.',
  },
  {
    key: 'verified',
    label: 'Verified outcome',
    detail:
      'The saving with its evidence chain attached, at the confidence that '
      + 'chain supports.',
  },
];

/**
 * The closing figures.
 *
 * `variance` is absent on purpose — it is computed from these two by
 * economics.variancePercent, so the demo cannot print a variance that
 * disagrees with the numbers above it.
 */
export const MRV_OUTCOME = {
  forecastAnnualSaving: money(79_000),
  verifiedAnnualSaving: money(76_420),
  measurementPeriod: '12 months from commissioning',
  evidenceStatus: 'VERIFIED' as const,
  /**
   * NO FIGURE IN THIS SENTENCE.
   *
   * It said "here it was 3.3% optimistic" until a sweep of the diff caught
   * it: that is the variance, restated by hand, in the one file whose whole
   * argument is that derived numbers are derived. Change the verified saving
   * and the prose would have gone on claiming 3.3% next to a computed figure
   * that said something else. The variance is rendered beside this line by
   * economics.variancePercent; the sentence explains what it means.
   */
  caveat:
    'A verified outcome states what the evidence supports, not that the '
    + 'forecast was right. Here the forecast was optimistic, and the record '
    + 'says so rather than quietly restating the forecast as the result.',
};

// ── Portfolio arithmetic ────────────────────────────────────────────────────

export interface PortfolioTotals {
  assetCount: number;
  capex: number;
  annualSaving: number;
  emissionsReduction: number;
}

/** Totals derived from FLAGGED_ASSETS. Never typed as constants anywhere. */
export function portfolioTotals(
  assets: FlaggedAsset[] = FLAGGED_ASSETS,
): PortfolioTotals {
  return assets.reduce<PortfolioTotals>(
    (acc, asset) => ({
      assetCount: acc.assetCount + 1,
      capex: acc.capex + asset.capex.value,
      annualSaving: acc.annualSaving + asset.annualSaving.value,
      emissionsReduction: acc.emissionsReduction + asset.emissionsReduction.value,
    }),
    { assetCount: 0, capex: 0, annualSaving: 0, emissionsReduction: 0 },
  );
}

/** One asset by id, or null. Null rather than a throw: a bad id in a URL is a
 *  404, and the page decides that, not this module. */
export function assetById(id: string): FlaggedAsset | null {
  return FLAGGED_ASSETS.find((asset) => asset.id === id) ?? null;
}
