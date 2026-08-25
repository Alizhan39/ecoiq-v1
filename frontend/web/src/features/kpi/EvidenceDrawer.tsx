import type { KpiEvidence, StewardshipPrinciple } from '@/types/kpi';
import { LEGAL_STATUS_LABEL, RELATION_LABEL, isEstablishedFinding } from '@/types/kpi';

/**
 * One evidence item, opened.
 *
 * THE CHAIN IS THE POINT (§11)
 * ----------------------------
 * Source, evidence, claim, interpretation and KPI relation are rendered as five
 * distinct steps because they are five distinct things, and collapsing them is
 * how "a regulator published a decision" silently becomes "the company is bad".
 * A reader can disagree with the interpretation while accepting the evidence,
 * and the layout has to make that possible.
 *
 * The interpretation step is labelled as EcoIQ's, not the source's. That
 * distinction is the difference between reporting and asserting.
 */
export function EvidenceDrawer({
  evidence, principle, onClose,
}: {
  evidence: KpiEvidence;
  principle: StewardshipPrinciple;
  onClose: () => void;
}) {
  const established = isEstablishedFinding(evidence);

  return (
    <aside className="kpi-drawer" aria-label={`Evidence: ${evidence.title}`}>
      <div className="kpi-drawer__top">
        <div className="kpi-drawer__chips">
          <span className={`kpi-chip kpi-chip--${evidence.relation}`}>
            {RELATION_LABEL[evidence.relation]}
          </span>
          <span className={`kpi-chip kpi-chip--status${established ? ' is-established' : ''}`}>
            {LEGAL_STATUS_LABEL[evidence.legal_status]}
          </span>
          {!evidence.counts_toward_assessment ? (
            <span className="kpi-chip kpi-chip--excluded">Excluded from assessment</span>
          ) : null}
        </div>
        <button type="button" className="kpi-drawer__close" onClick={onClose}>
          Close<span className="visually-hidden"> evidence detail</span>
        </button>
      </div>

      <h2 className="kpi-drawer__title">{evidence.title}</h2>

      {/* §5: a preliminary finding must never read like a concluded one. */}
      {evidence.legal_status === 'preliminary_regulatory_finding' ? (
        <p className="kpi-drawer__caution" role="note">
          Preliminary. A regulator has set out a provisional position. It is not a
          concluded finding and must not be read as one.
        </p>
      ) : null}

      <ol className="kpi-chain">
        <li>
          <h3>Source</h3>
          <p>{evidence.source_authority || 'Unattributed'}</p>
        </li>
        <li>
          <h3>Evidence</h3>
          <p>{evidence.excerpt || 'Full text withheld — see the source record.'}</p>
        </li>
        <li>
          <h3>Claim</h3>
          <p>{claimFor(evidence)}</p>
        </li>
        <li>
          <h3>Interpretation <span className="kpi-chain__whose">EcoIQ</span></h3>
          <p>{interpretationFor(evidence, principle)}</p>
        </li>
        <li>
          <h3>Relation to principle #{principle.kpi_id}</h3>
          <p>{RELATION_LABEL[evidence.relation]}</p>
        </li>
      </ol>

      <SourceProvenance evidence={evidence} />
    </aside>
  );
}

/**
 * Forensic detail (§25). Deliberately dull: dates, tiers, states and a link.
 * Nothing here is interpreted — it is the paper trail.
 */
export function SourceProvenance({ evidence }: { evidence: KpiEvidence }) {
  return (
    <section className="kpi-provenance">
      <h3>Provenance</h3>
      <dl>
        <div><dt>Authority</dt><dd>{evidence.source_authority || '—'}</dd></div>
        <div><dt>Evidentiary standing</dt>
          <dd>{LEGAL_STATUS_LABEL[evidence.legal_status]}</dd></div>
        <div><dt>Collected</dt><dd>{evidence.date_collected ?? '—'}</dd></div>
        <div><dt>Review tier</dt><dd>{evidence.review_tier.replace(/_/g, ' ')}</dd></div>
        <div><dt>Verification</dt><dd>{evidence.verification_status}</dd></div>
        <div><dt>Review state</dt><dd>{evidence.review_state.replace(/_/g, ' ')}</dd></div>
        <div><dt>Counts toward assessment</dt>
          <dd>{evidence.counts_toward_assessment ? 'Yes' : 'No — not confirmed'}</dd></div>
        {evidence.match_basis ? (
          <div><dt>Match basis</dt><dd>{evidence.match_basis}</dd></div>
        ) : null}
        {evidence.is_demo ? (
          <div><dt>Corpus</dt><dd>Demonstration — not independently verified</dd></div>
        ) : null}
      </dl>
      {evidence.source_url ? (
        <a className="kpi-provenance__link" href={evidence.source_url}
           target="_blank" rel="noopener noreferrer">
          View source<span className="visually-hidden"> (opens in a new tab)</span>
        </a>
      ) : null}
    </section>
  );
}

/**
 * Deterministic, structured, derived from fields — never generated prose.
 * A sentence assembled from `relation` and `legal_status` can be wrong, but it
 * cannot hallucinate a fact that is not in the record.
 */
function claimFor(e: KpiEvidence): string {
  if (e.relation === 'conflicts') {
    return isEstablishedFinding(e)
      ? 'An authority concluded that the organisation\'s own rules or design constrained informed choice.'
      : 'The record indicates the organisation\'s rules or design may constrain informed choice.';
  }
  if (e.relation === 'supports') {
    return 'The record describes a control that reduces the scope for others to manipulate users.';
  }
  if (e.relation === 'context') {
    return 'The record describes surrounding circumstances without concluding either way.';
  }
  return 'The record discusses the principle but does not settle it.';
}

function interpretationFor(e: KpiEvidence, p: StewardshipPrinciple): string {
  if (e.relation === 'conflicts') {
    return `Weighed against "${p.title}", this counts against the organisation: the principle `
      + 'asks whether people are protected from manipulation even where a practice is lawful, '
      + 'so lawfulness does not settle it.';
  }
  if (e.relation === 'supports') {
    return `Weighed against "${p.title}", this counts in the organisation's favour — it removes `
      + 'a manipulation route that would otherwise be available to third parties.';
  }
  return 'Recorded for completeness. It informs the picture without moving the verdict.';
}
