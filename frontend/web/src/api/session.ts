import { api } from './client';
import type { Identity } from '@/types/session';

/**
 * Who am I — and, as a side effect, set the CSRF cookie.
 *
 * Anonymous is a successful answer (`authenticated: false`, HTTP 200), not an
 * error. The public product is anonymous by default, and treating that as a
 * failure would make every first page load look broken.
 */
export function getSession(signal?: AbortSignal): Promise<Identity> {
  return api.get<Identity>('/session/', signal);
}

export function signIn(username: string, password: string): Promise<Identity> {
  return api.post<Identity>('/session/sign-in/', { username, password });
}

export function signOut(): Promise<Identity> {
  return api.post<Identity>('/session/sign-out/', {});
}
