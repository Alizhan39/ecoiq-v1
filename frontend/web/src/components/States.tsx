import type { ReactNode } from 'react';

export function Loading({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="state state--loading" role="status" aria-live="polite">
      {label}…
    </div>
  );
}

/**
 * An error state that says what failed.
 *
 * Never a silent empty list: a failed request and an empty result are different
 * facts, and showing the second for the first is the UI equivalent of
 * substituting a zero.
 */
/**
 * Two things were wrong with printing `error.message` at a reader.
 *
 * It is the internal request line — production showed
 * "GET /api/v2/companies/?page=1 failed with 429" on the organisations page —
 * which tells a visitor nothing and exposes the call shape.
 *
 * And it treated every failure as the same kind. A rate limit is not a broken
 * page: the data is fine and the reader is asked to wait, which is a different
 * sentence from "this could not be loaded".
 */
function describe(error: Error): { headline: string; detail: string } {
  const status = (error as { status?: number }).status;
  if (status === 429) {
    return {
      headline: 'Too many requests from this connection.',
      detail: 'Nothing is wrong with the data. Wait a moment and reload — the '
        + 'limit resets on its own.',
    };
  }
  if (status === 403) {
    return {
      headline: 'This is not available to view.',
      detail: 'It may require sign-in, or it may not be published.',
    };
  }
  if (status === 404) {
    return {
      headline: 'This is not on record.',
      detail: 'The address may be out of date.',
    };
  }
  if (status !== undefined && status >= 500) {
    return {
      headline: 'EcoIQ could not answer just now.',
      detail: 'The failure is on our side, not in the evidence. Reloading '
        + 'usually works.',
    };
  }
  return {
    headline: 'Could not load this section.',
    detail: 'The connection may have dropped. Reloading usually works.',
  };
}

export function ErrorState({ error }: { error: Error }) {
  const { headline, detail } = describe(error);
  return (
    <div className="state state--error" role="alert">
      <p>{headline}</p>
      <p className="state__detail">{detail}</p>
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="state state--empty">{children}</div>;
}
