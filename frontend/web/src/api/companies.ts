import { api } from './client';
import type {
  CompanyDetail,
  CompanySummary,
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
