/**
 * Projects.
 *
 * Every quantity is nullable. A project with no recorded CO2 figure has no
 * recorded figure — it did not reduce zero tonnes, and the difference is the
 * whole point.
 */
export interface Project {
  slug: string;
  name: string;
  project_type: string;
  status: string;
  location: string;
  description: string;
  company: string;
  /** Complete and unverified is a real state. Do not infer one from the other. */
  verified: boolean;
  investment_usd: number | null;
  co2_reduction_tonnes: number | null;
  households_helped: number | null;
}

export interface ProjectList {
  count: number;
  /** Carried beside `count` because "12 projects" and "12 projects, 0
   *  independently verified" are very different statements. */
  verified_count: number;
  results: Project[];
}

/** A quantity, or an em dash. Never a substituted zero. */
export function quantity(value: number | null, unit = ''): string {
  if (value === null) return '—';
  return unit ? `${value.toLocaleString()} ${unit}` : value.toLocaleString();
}
