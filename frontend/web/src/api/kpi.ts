import { api } from './client';
import type { KpiInvestigation } from '@/types/kpi';

/**
 * One organisation against one principle.
 *
 * Separate from `companies.ts` because it answers a different question: the
 * company endpoints summarise standing, this returns a full evidence chain for
 * a single KPI.
 */
export function fetchKpiInvestigation(
  slug: string, kpiId: number, signal?: AbortSignal,
): Promise<KpiInvestigation> {
  return api.get<KpiInvestigation>(`/companies/${slug}/kpis/${kpiId}/`, signal);
}
