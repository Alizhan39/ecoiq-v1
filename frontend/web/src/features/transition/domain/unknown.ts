/**
 * unknown — the difference between "zero" and "we have not measured this".
 *
 * WHY THIS FILE EXISTS BEFORE ANY OF THE OTHERS
 * ---------------------------------------------
 * Every type in this domain has a slot for a number EcoIQ does not yet have:
 * capex, annual savings, payback, emissions avoided. The failure mode for a
 * model like this is not being wrong about those numbers — it is DEFAULTING
 * them, so a facility nobody has surveyed reports £0 capex and 0 t CO2e
 * avoided, and a reader takes silence for a measurement.
 *
 * The backend already learned this the hard way. `core/unknown.py` exists
 * because `profile.controversy_risk_score or 0` told readers that an
 * unassessed organisation was "within acceptable range", and
 * `public_benefit_score or 50` rewrote a genuine measured 0.0 into an average
 * — so the company with the worst real score was the one guaranteed not to be
 * flagged. Same discipline, same reasoning, on this side of the wire.
 *
 * The rule is one line: an absent measurement is `null`, and `null` never
 * silently becomes a number.
 */

/** A quantity that may not have been measured. `null` means UNKNOWN. */
export type Measured<T> = T | null;

/** A number with the unit it is measured in, or nothing at all. */
export interface Quantity {
  value: number;
  /** Free-form on purpose — this model does not own a unit registry yet. */
  unit: string;
  /**
   * Where the number came from. A quantity with no basis is not a measurement,
   * and the type makes you say which it is.
   */
  basis: QuantityBasis;
}

export type QuantityBasis =
  /** Measured at the facility. The only basis that may be reported as fact. */
  | 'measured'
  /** Derived from measured quantities by a documented calculation. */
  | 'derived'
  /** A stated assumption in a scenario. Never a finding. */
  | 'assumed'
  /** A figure for illustration only. Must never leave the prototype. */
  | 'illustrative';

/** The bases a caller may present to a reader as a fact about a facility. */
export const REPORTABLE_BASES: readonly QuantityBasis[] = ['measured', 'derived'];

export function isReportable(q: Measured<Quantity>): boolean {
  return q !== null && REPORTABLE_BASES.includes(q.basis);
}

/**
 * An unknown quantity. Named rather than writing `null` inline so a reader
 * grepping for what is not yet known finds every one of them.
 */
export const UNKNOWN = null;

/**
 * Every economic and environmental figure this model will eventually carry.
 *
 * ALL OPTIONAL, ALL UNKNOWN BY DEFAULT
 * The shape exists now so that when real facility data arrives it has
 * somewhere to go without a schema change. Nothing in the prototype populates
 * any of it. A scenario that has not been costed reports null, and the
 * semantic layer renders an em dash rather than a zero.
 */
export interface EconomicOutcome {
  capex: Measured<Quantity>;
  opexBefore: Measured<Quantity>;
  opexAfter: Measured<Quantity>;
  annualSavings: Measured<Quantity>;
  paybackYears: Measured<Quantity>;
  npv: Measured<Quantity>;
  irr: Measured<Quantity>;
}

export interface ResourceOutcome {
  energySaved: Measured<Quantity>;
  waterSaved: Measured<Quantity>;
  wasteRecovered: Measured<Quantity>;
  emissionsAvoided: Measured<Quantity>;
}

/** Both halves, all unknown. The only outcome the prototype ever constructs. */
export function unknownOutcome(): EconomicOutcome & ResourceOutcome {
  return {
    capex: UNKNOWN,
    opexBefore: UNKNOWN,
    opexAfter: UNKNOWN,
    annualSavings: UNKNOWN,
    paybackYears: UNKNOWN,
    npv: UNKNOWN,
    irr: UNKNOWN,
    energySaved: UNKNOWN,
    waterSaved: UNKNOWN,
    wasteRecovered: UNKNOWN,
    emissionsAvoided: UNKNOWN,
  };
}

/** Is any figure in an outcome actually known? */
export function hasAnyMeasurement(
  outcome: Partial<EconomicOutcome & ResourceOutcome>,
): boolean {
  return Object.values(outcome).some((q) => q !== null && q !== undefined);
}

/**
 * How a reader should see a quantity. Never "0" for an absent one.
 *
 * The em dash is the convention `api/v2_platform.py` already documents for a
 * null counter: "a zero is a measurement and null is the absence of one".
 */
export function displayQuantity(q: Measured<Quantity>): string {
  if (q === null) return '—';
  const suffix = q.basis === 'measured' || q.basis === 'derived'
    ? '' : ` (${q.basis})`;
  return `${q.value} ${q.unit}${suffix}`;
}
