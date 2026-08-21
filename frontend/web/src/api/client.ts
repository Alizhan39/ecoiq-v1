/**
 * The single API client.
 *
 * Every network call goes through here so that error handling, CSRF and the
 * base URL are decided once. Components never call `fetch` directly.
 */

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly url: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Same-origin by default.
 *
 * The deployment target is `ecoiq.uk` serving the app and `/api/*` from one
 * origin, which keeps Django's session cookie and CSRF working unchanged. A
 * separate api.ecoiq.uk would mean CORS and cross-site cookies for no benefit.
 */
const BASE = '/api/v2';

/** Django's CSRF cookie. Required for unsafe methods, absent for reads. */
function csrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match?.[1] ?? null;
}

const UNSAFE = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

export interface RequestOptions {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
}

export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const method = options.method ?? 'GET';
  const url = `${BASE}${path}`;

  const headers: Record<string, string> = { Accept: 'application/json' };
  if (options.body !== undefined) headers['Content-Type'] = 'application/json';

  if (UNSAFE.has(method)) {
    const token = csrfToken();
    // Deliberately not thrown on: a missing cookie is a legitimate anonymous
    // state, and Django will reject the request with a clear 403 which is more
    // useful than a client-side guess about why.
    if (token) headers['X-CSRFToken'] = token;
  }

  const response = await fetch(url, {
    method,
    headers,
    // Session auth. Django stays the authentication authority; the SPA does
    // not implement or store credentials of its own.
    credentials: 'same-origin',
    ...(options.body !== undefined
      ? { body: JSON.stringify(options.body) }
      : {}),
    ...(options.signal ? { signal: options.signal } : {}),
  });

  if (!response.ok) {
    throw new ApiError(
      `${method} ${url} failed with ${response.status}`,
      response.status,
      url,
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) =>
    request<T>(path, signal ? { signal } : {}),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body }),
};
