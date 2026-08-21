import { api } from './client';
import type { PlatformStats } from '@/types/platform';

/**
 * Platform counters and module statuses.
 *
 * The only source of any number the product shows about itself. A component
 * that wants a count asks for this; it never hard-codes one.
 */
export function getPlatformStats(signal?: AbortSignal): Promise<PlatformStats> {
  return api.get<PlatformStats>('/platform/', signal);
}
