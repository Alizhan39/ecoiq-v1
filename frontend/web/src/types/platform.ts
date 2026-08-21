/**
 * Platform counters, from the single source of truth.
 *
 * `value` is `number | null`. Null means "no meaningful figure" and must render
 * as an em dash — never as 0. A zero is a measurement; null is the absence of
 * one, and conflating them is the defect this whole programme removed from the
 * backend.
 */
export interface PlatformCounter {
  key: string;
  label: string;
  value: number | null;
  /** One line a reader could verify. Never a marketing sentence. */
  derivation: string;
  /** True when this figure may be presented as product proof. */
  is_proof: boolean;
}

export interface PlatformStats {
  counters: PlatformCounter[];
  modules: ModuleSummary[];
}

export type ModuleStatus =
  | 'PRODUCTION'
  | 'BETA'
  | 'EXPERIMENTAL'
  | 'PLANNED'
  | 'SPECIFICATION';

export interface ModuleSummary {
  key: string;
  name: string;
  kind: string;
  status: ModuleStatus;
  /** 'NOT YET MEASURED' is a valid, honest value. Never render it as 0%. */
  evaluation: string;
  /** Why this status. A status without a basis is an assertion. */
  basis: string;
}

/** Renders a counter. The one place null-vs-zero is decided. */
export function counterDisplay(counter: PlatformCounter): string {
  return counter.value === null ? '—' : counter.value.toLocaleString();
}

export const NOT_MEASURED = 'NOT YET MEASURED';

export function isEvaluated(module: ModuleSummary): boolean {
  return module.evaluation !== NOT_MEASURED;
}
