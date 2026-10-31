import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import type { CompanyPrinciple, CompanyPrincipleMatrix } from '@/types/principles';

/**
 * One organisation against all 114, as a matrix.
 *
 * NOT A HEATMAP
 * -------------
 * Every cell carries its principle number as text and its state as a label in
 * the accessible name. Colour is a second channel, never the only one — a
 * reader who cannot distinguish hues must still be able to tell a conflict
 * from an unassessed principle, and on this product that is not a nicety:
 * "insufficient evidence" and "concern" are opposite claims and must never
 * differ only by shade.
 *
 * WHY NOT-YET-INVESTIGATED IS THE DEFAULT AND STAYS VISIBLE
 * --------------------------------------------------------
 * Most cells are `not_assessed` for most organisations today, and the matrix
 * shows all 114 rather than only the interesting ones. Hiding them would make
 * a nearly-empty assessment look complete, which is the single failure this
 * product exists to avoid. The count above the grid says so in words.
 *
 * COMPOSED, NOT ENUMERATED
 * ------------------------
 * A cell's meaning is its state PLUS the orthogonal facts the API reports
 * beside it — evidence awaiting review, remediation recorded, a conflict
 * resting on a final regulatory finding. The server does not flatten those
 * into a fourth status vocabulary and neither does this.
 */

const STATE_LABEL: Record<string, string> = {
  strong_support: 'Substantiated support',
  support: 'Support',
  mixed: 'Mixed evidence',
  mixed_material_conflict: 'Mixed — material conflict',
  conflict: 'Substantiated concern',
  neutral_or_no_material_link: 'No material link',
  insufficient_evidence: 'Insufficient evidence',
  not_assessed: 'Not yet investigated',
};

/** Short glyph for the cell face. Never the only carrier of meaning. */
const STATE_GLYPH: Record<string, string> = {
  strong_support: '++',
  support: '+',
  mixed: '±',
  mixed_material_conflict: '±!',
  conflict: '−',
  neutral_or_no_material_link: '·',
  insufficient_evidence: '?',
  not_assessed: '',
};

type Filter = 'all' | 'investigated' | 'evidence' | 'concern' | 'review';

const FILTERS: { key: Filter; label: string; hint: string }[] = [
  { key: 'all', label: 'All 114', hint: 'Every principle, investigated or not' },
  { key: 'investigated', label: 'Investigated', hint: 'Someone has looked' },
  { key: 'evidence', label: 'Has evidence', hint: 'Evidence on file, counted or not' },
  { key: 'concern', label: 'Concern or conflict', hint: 'Evidence points against' },
  { key: 'review', label: 'Awaiting review', hint: 'Evidence that counts toward nothing yet' },
];

function matches(principle: CompanyPrinciple, filter: Filter): boolean {
  switch (filter) {
    case 'investigated':
      return principle.state !== 'not_assessed';
    case 'evidence':
      return principle.counts.total > 0;
    case 'concern':
      return principle.state === 'conflict'
        || principle.state === 'mixed'
        || principle.state === 'mixed_material_conflict';
    case 'review':
      return principle.pending_review_count > 0;
    default:
      return true;
  }
}

export function PrincipleMatrix(
  { matrix, slug }: { matrix: CompanyPrincipleMatrix; slug: string },
) {
  const [filter, setFilter] = useState<Filter>('all');
  const [selected, setSelected] = useState<CompanyPrinciple | null>(null);

  const shown = useMemo(
    () => matrix.principles.filter((p) => matches(p, filter)),
    [matrix.principles, filter],
  );

  const { summary } = matrix;

  return (
    <section aria-labelledby="principle-matrix" className="matrix">
      <h2 id="principle-matrix">All {summary.total} principles</h2>
      <p className="matrix__lede">
        {summary.assessed === 0 ? (
          <>
            None of the {summary.total} principles has been investigated for
            this organisation yet. Every cell below is unassessed — a statement
            about EcoIQ&rsquo;s coverage, not a finding about the organisation.
          </>
        ) : (
          <>
            {summary.assessed} of {summary.total} principles investigated.
            The remaining {summary.not_assessed} have not been looked at, and
            are shown rather than hidden.
          </>
        )}
      </p>
      {summary.pending_review_total > 0 ? (
        <p className="matrix__pending">
          {summary.pending_review_total} evidence item
          {summary.pending_review_total === 1 ? '' : 's'} awaiting review.
          Recorded, visible, and counting toward no verdict until reviewed.
        </p>
      ) : null}

      <div className="filters" role="group" aria-label="Filter principles">
        {FILTERS.map((f) => {
          const count = matrix.principles.filter((p) => matches(p, f.key)).length;
          return (
            <button
              key={f.key}
              type="button"
              className={filter === f.key ? 'chip chip--on' : 'chip'}
              aria-pressed={filter === f.key}
              title={f.hint}
              onClick={() => setFilter(f.key)}
            >
              {f.label} <span className="chip__count">{count}</span>
            </button>
          );
        })}
      </div>

      {shown.length === 0 ? (
        <p className="matrix__empty">
          No principle matches this filter for this organisation.
        </p>
      ) : (
        <ul className="matrix__grid">
          {shown.map((principle) => (
            <li key={principle.kpi_id}>
              <button
                type="button"
                className={`matrix__cell matrix__cell--${principle.state}`}
                aria-pressed={selected?.kpi_id === principle.kpi_id}
                onClick={() => setSelected(
                  selected?.kpi_id === principle.kpi_id ? null : principle,
                )}
              >
                <span className="matrix__num" aria-hidden="true">
                  {principle.kpi_id}
                </span>
                <span className="matrix__glyph" aria-hidden="true">
                  {STATE_GLYPH[principle.state] ?? ''}
                </span>
                <span className="visually-hidden">
                  Principle {principle.kpi_id}, {principle.title}:{' '}
                  {STATE_LABEL[principle.state] ?? principle.state_label}
                  {principle.has_material_conflict
                    ? ', material regulatory conflict' : ''}
                  {principle.remediation_step_count > 0
                    ? ', remediation recorded' : ''}
                  {principle.pending_review_count > 0
                    ? `, ${principle.pending_review_count} item(s) awaiting review` : ''}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {selected ? <MatrixDetail principle={selected} slug={slug} /> : null}
    </section>
  );
}

function MatrixDetail(
  { principle, slug }: { principle: CompanyPrinciple; slug: string },
) {
  const { counts } = principle;
  return (
    <aside className="matrix__detail" aria-live="polite">
      <p className="matrix__detail-eyebrow">
        Principle #{principle.kpi_id}
      </p>
      <h3>{principle.title}</h3>
      <p className="matrix__detail-question">{principle.question}</p>

      <p className="matrix__detail-state">
        <span className={`kpi-chip kpi-chip--status matrix__state--${principle.state}`}>
          {STATE_LABEL[principle.state] ?? principle.state_label}
        </span>
        {principle.has_material_conflict ? (
          <span className="kpi-chip kpi-chip--conflicts">
            Material regulatory conflict
          </span>
        ) : null}
        {principle.remediation_step_count > 0 ? (
          <span className="kpi-chip kpi-chip--context">
            {principle.remediation_step_count} remediation step
            {principle.remediation_step_count === 1 ? '' : 's'} recorded
          </span>
        ) : null}
        {principle.is_demo ? (
          <span className="kpi-chip kpi-chip--excluded">Demonstration data</span>
        ) : null}
      </p>

      {counts.total === 0 ? (
        <p className="matrix__detail-empty">
          No evidence has been linked to this principle for this organisation.
          That is why it is unassessed.
        </p>
      ) : (
        <dl className="matrix__counts">
          <div><dt>Counted</dt><dd>{counts.confirmed}</dd></div>
          <div><dt>Supports</dt><dd>{counts.supports}</dd></div>
          <div><dt>Conflicts</dt><dd>{counts.conflicts}</dd></div>
          <div><dt>Context</dt><dd>{counts.context}</dd></div>
          <div>
            <dt>Recorded, not counted</dt>
            <dd>{counts.excluded_from_assessment}</dd>
          </div>
        </dl>
      )}

      <p className="matrix__detail-links">
        <Link to={`/companies/${slug}/kpis/${principle.kpi_id}/`}>
          Open the investigation
        </Link>
        {' · '}
        <Link to={`/principles/${principle.kpi_id}/`}>
          What this principle asks
        </Link>
      </p>
    </aside>
  );
}
