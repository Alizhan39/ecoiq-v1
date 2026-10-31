import { DEMONSTRATION_BADGE, DEMONSTRATION_NOTICE } from './demoData';

/**
 * The label that must never be more than a screen away from the numbers.
 *
 * Rendered as a `role="note"` region rather than a styled paragraph so it is
 * announced as an aside rather than read as part of the surrounding data, and
 * placed ABOVE the figures it qualifies — a disclaimer under a dashboard is
 * read after the reader has already believed the dashboard.
 */
export function DemonstrationNotice({ compact = false }: { compact?: boolean }) {
  return (
    <aside
      className={compact ? 'psnotice psnotice--compact' : 'psnotice'}
      role="note"
      aria-label="Demonstration data notice"
    >
      <p className="psnotice__badge">{DEMONSTRATION_BADGE}</p>
      <p className="psnotice__body">{DEMONSTRATION_NOTICE}</p>
    </aside>
  );
}
