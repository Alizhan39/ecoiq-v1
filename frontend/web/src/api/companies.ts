import { api } from './client';
import type { Assessment } from '@/types/assessment';
import type {
  CompanyDetail,
  CompanySummary,
  Leaderboard,
  Paginated,
} from '@/types/evidence';

/** Query for the company directory. Every field is optional. */
export interface CompanyQuery {
  q?: string;
  sector?: string;
  country?: string;
  page?: number;
}

/**
 * Deliberately NOT here: a score filter, a rank sort, or a tier filter.
 *
 * The server-rendered directory this replaces offered a `label` filter over
 * `moral_label` — a tier derived from the composite score — and ordered every
 * card by `-ecoiq_total_score`. Both publish the withheld number: one lets you
 * select on it, the other lets you read it off a card's position.
 *
 * /api/v2/companies/ orders by name and exposes no score filter, so the
 * correct client is the one that asks for nothing more.
 */
export function listCompanies(
  query: CompanyQuery = {},
  signal?: AbortSignal,
): Promise<Paginated<CompanySummary>> {
  const params = new URLSearchParams();
  if (query.q) params.set('q', query.q);
  if (query.sector) params.set('sector', query.sector);
  if (query.country) params.set('country', query.country);
  if (query.page && query.page > 1) params.set('page', String(query.page));
  const suffix = params.toString();
  return api.get<Paginated<CompanySummary>>(
    `/companies/${suffix ? `?${suffix}` : ''}`, signal);
}

export function getCompany(
  slug: string,
  signal?: AbortSignal,
): Promise<CompanyDetail> {
  return api.get<CompanyDetail>(
    `/companies/${encodeURIComponent(slug)}/`,
    signal,
  );
}

/**
 * Ranked organisations.
 *
 * The endpoint ranks only what is publishable — a leaderboard is a comparative
 * statement about every row in it, so an unevidenced organisation is withheld
 * rather than placed somewhere in the order.
 */
export function getLeaderboard(signal?: AbortSignal): Promise<Leaderboard> {
  return api.get<Leaderboard>('/leaderboard/', signal);
}

/**
 * The full assessment for one organisation.
 *
 * Separate from getCompany() because it is a different question: that one asks
 * what the directory needs, this one asks everything the page shows. Both go
 * through the same publication gate on the server.
 */
export function getAssessment(
  slug: string,
  signal?: AbortSignal,
): Promise<Assessment> {
  return api.get<Assessment>(
    `/companies/${encodeURIComponent(slug)}/assessment/`,
    signal,
  );
}
