import { api } from './client';
import type { CompanyPrincipleMatrix, PrincipleRegistry } from '@/types/principles';

/**
 * The 114 principles EcoIQ assesses against.
 *
 * Takes no slug: this describes the method, which is the same whoever is being
 * investigated. Cacheable in a way the company matrix is not.
 */
export function fetchPrincipleRegistry(signal?: AbortSignal): Promise<PrincipleRegistry> {
  return api.get<PrincipleRegistry>('/principles/', signal);
}

/**
 * One organisation across all 114.
 *
 * Separate from `fetchKpiInvestigation`: this returns every principle's STATE
 * in one request, which is what a matrix needs. The investigation endpoint
 * returns one principle's full evidence chain, which is what a reader needs
 * after picking a cell. Serving both from one shape would make the common case
 * pay for the rare one.
 */
export function fetchCompanyPrinciples(
  slug: string, signal?: AbortSignal,
): Promise<CompanyPrincipleMatrix> {
  return api.get<CompanyPrincipleMatrix>(`/companies/${slug}/principles/`, signal);
}
