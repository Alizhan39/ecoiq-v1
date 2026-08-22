import { api } from './client';
import type {
  CompanyDetail,
  CompanySummary,
  Leaderboard,
  Paginated,
} from '@/types/evidence';

export function listCompanies(
  signal?: AbortSignal,
): Promise<Paginated<CompanySummary>> {
  return api.get<Paginated<CompanySummary>>('/companies/', signal);
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
