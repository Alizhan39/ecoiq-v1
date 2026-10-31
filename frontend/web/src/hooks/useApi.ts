import { useEffect, useState } from 'react';
import { ApiError } from '@/api/client';

export type AsyncState<T> =
  | { status: 'loading' }
  | { status: 'error'; error: ApiError | Error }
  | { status: 'ready'; data: T };

/**
 * Fetch-on-mount with abort, as a discriminated union.
 *
 * A union rather than `{data, loading, error}` on purpose: the latter lets a
 * component render `data` while it is still undefined, which is how loading
 * states end up showing zeros.
 */
export function useApi<T>(
  load: (signal: AbortSignal) => Promise<T>,
  deps: readonly unknown[] = [],
): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ status: 'loading' });

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: 'loading' });

    load(controller.signal)
      .then((data) => setState({ status: 'ready', data }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setState({
          status: 'error',
          error: error instanceof Error ? error : new Error(String(error)),
        });
      });

    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
