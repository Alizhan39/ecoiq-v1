import { useCallback, useEffect, useState } from 'react';
import { getSession, signIn as apiSignIn, signOut as apiSignOut } from '@/api/session';
import { ANONYMOUS, type Identity } from '@/types/session';

/**
 * Session state for the app shell.
 *
 * Loads once on mount, which also primes the CSRF cookie before any unsafe
 * request. A failure resolves to ANONYMOUS rather than throwing: if the
 * session endpoint is unreachable the correct assumption is "not signed in",
 * and the public product still works.
 */
export function useSession() {
  const [identity, setIdentity] = useState<Identity>(ANONYMOUS);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    getSession(controller.signal)
      .then(setIdentity)
      .catch(() => setIdentity(ANONYMOUS))
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  const signIn = useCallback(async (username: string, password: string) => {
    const next = await apiSignIn(username, password);
    setIdentity(next);
    return next;
  }, []);

  const signOut = useCallback(async () => {
    // Never optimistic. The server owns the session, and showing a signed-out
    // UI over a live session is worse than a moment of latency.
    const next = await apiSignOut();
    setIdentity(next);
    return next;
  }, []);

  return { identity, loading, signIn, signOut };
}
