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
export function ErrorState({ error }: { error: Error }) {
  return (
    <div className="state state--error" role="alert">
      <p>Could not load this section.</p>
      <p className="state__detail">{error.message}</p>
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="state state--empty">{children}</div>;
}
