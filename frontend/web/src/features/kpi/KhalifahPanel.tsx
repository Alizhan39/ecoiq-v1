import { useState } from 'react';
import type { KpiInvestigation } from '@/types/kpi';
import { CONFIDENCE_LABEL, isEstablishedFinding } from '@/types/kpi';

/**
 * The analyst panel: what was found, why, and what would change it.
 *
 * DETERMINISTIC BY CONSTRUCTION
 * -----------------------------
 * Every sentence here is assembled from counts and field values already in the
 * payload. There is no model call, and that is a design decision rather than a
 * limitation: an assessment that cites evidence must not be narrated by
 * something capable of inventing a citation. When this is eventually connected
 * to the AI gateway, the gateway's job will be phrasing — never the finding.
 *
 * "Challenge this conclusion" (§14) is the panel's most important control. A
 * system that states what would falsify it is auditable; one that only asserts
 * is not.
 */
export function KhalifahPanel({ inv }: { inv: KpiInvestigation }) {
  const [open, setOpen] = useState<'why' | 'challenge' | 'improve' | 'audit' | null>('why');
  const { counts, assessment } = inv;
  const established = inv.evidence.filter(isEstablishedFinding)
    .filter((e) => e.counts_toward_assessment);

  return (
    <section className="khalifah" aria-labelledby="khalifah-heading">
      <div className="khalifah__head">
        <h2 id="khalifah-heading">Khalifah</h2>
        <p className="khalifah__sub">Evidence analyst</p>
      </div>

      <p className="khalifah__lede">
        {counts.confirmed === 0
          ? 'No confirmed evidence is linked to this principle, so no assessment has been made.'
          : `${counts.confirmed} confirmed item${counts.confirmed === 1 ? '' : 's'}: `
            + `${counts.supports} supporting, ${counts.conflicts} conflicting`
            + `${counts.context ? `, ${counts.context} contextual` : ''}.`}
      </p>

      <dl className="khalifah__verdict">
        <div><dt>Assessment</dt><dd>{assessment.verdict_label}</dd></div>
        <div><dt>Confidence</dt><dd>{CONFIDENCE_LABEL[assessment.confidence]}</dd></div>
      </dl>

      <nav className="khalifah__actions" aria-label="Interrogate this assessment">
        {([
          ['why', 'Why this assessment?'],
          ['challenge', 'Challenge this conclusion'],
          ['improve', 'What would improve this?'],
          ['audit', 'How was this produced?'],
        ] as const).map(([key, label]) => (
          <button
            key={key} type="button"
            className={`khalifah__action${open === key ? ' is-open' : ''}`}
            aria-expanded={open === key}
            onClick={() => setOpen(open === key ? null : key)}
          >
            {label}
          </button>
        ))}
      </nav>

      {open === 'why' ? (
        <div className="khalifah__body">
          <p>{assessment.rationale || 'No rationale recorded.'}</p>
          <h3>Confidence rests on</h3>
          <ul>
            {assessment.confidence_reasons.map((r) => <li key={r}>{r}</li>)}
          </ul>
        </div>
      ) : null}

      {open === 'challenge' ? (
        <div className="khalifah__body">
          <p>
            This assessment would weaken if the following became true. Each is
            checkable, which is the point — a conclusion nobody can falsify is not
            a finding.
          </p>
          <ul>
            {established[0] ? (
              <>
                <li>
                  The finding by {established[0].source_authority} is overturned,
                  annulled on appeal, or formally superseded.
                </li>
                <li>
                  A regulator confirms the remediation closed the restriction, rather
                  than the organisation asserting it.
                </li>
              </>
            ) : (
              <li>A regulator concludes proceedings either way, replacing
                  provisional material with a settled finding.</li>
            )}
            <li>
              Independent measurement shows alternatives are presented neutrally,
              rather than merely being permitted.
            </li>
            <li>
              Evidence currently excluded from the assessment is reviewed and
              confirmed, changing the balance of what counts.
            </li>
          </ul>
        </div>
      ) : null}

      {open === 'improve' ? (
        <div className="khalifah__body">
          <p className="khalifah__label">
            Recommendations — not findings, and not evidence of intent.
          </p>
          <ul>
            <li>Present alternatives with equivalent prominence to the default path.</li>
            <li>Keep security warnings proportionate to actual risk, so caution does
                not function as friction.</li>
            <li>Publish switching-friction measurements openly enough to be checked.</li>
            <li>Obtain independent confirmation that remediation achieved its aim.</li>
          </ul>
        </div>
      ) : null}

      {open === 'audit' ? (
        <div className="khalifah__body">
          <h3>How this assessment was produced</h3>
          <ul className="khalifah__audit">
            <li>{counts.total} evidence item{counts.total === 1 ? '' : 's'} considered</li>
            <li>{counts.confirmed} confirmed and counted</li>
            <li>{counts.excluded_from_assessment} excluded — not in a confirmed review state</li>
            <li>{counts.supports} supporting · {counts.conflicts} conflicting · {counts.context} contextual</li>
            <li>{counts.remediation_steps} remediation step{counts.remediation_steps === 1 ? '' : 's'}, tracked separately and not counted toward the verdict</li>
            <li>Verdict derived by rule from confirmed links — not asserted, and not model-generated</li>
          </ul>
        </div>
      ) : null}
    </section>
  );
}
