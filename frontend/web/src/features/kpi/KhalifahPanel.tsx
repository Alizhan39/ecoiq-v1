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
 *
 * EVERY SENTENCE COMES FROM THIS PRINCIPLE
 * ----------------------------------------
 * The falsification criteria and the strengthening list were once written for
 * principle #114 and rendered for whatever principle was open. That was
 * invisible while #114 was the only one the product linked to; once the matrix
 * made all 114 reachable, Walmart against "Time Risk & Transition Urgency" was
 * being advised to "keep security warnings proportionate to actual risk" —
 * App Store guidance, on a principle about the pace of transition.
 *
 * So nothing here is written per principle any more. The indicators come from
 * `stewardship_principle.metrics`, which is the canonical registry's own
 * statement of what evidence against this principle consists of, and the rest
 * is derived from counts and evidence fields in the payload. A sentence this
 * panel cannot ground in the principle it is describing is one it does not
 * say.
 */
export function KhalifahPanel({ inv }: { inv: KpiInvestigation }) {
  const [open, setOpen] = useState<'why' | 'challenge' | 'improve' | 'audit' | null>('why');
  const { counts, assessment } = inv;
  const established = inv.evidence.filter(isEstablishedFinding)
    .filter((e) => e.counts_toward_assessment);
  // The canonical registry's own statement of what evidence against THIS
  // principle consists of. Never a list written for a different one.
  const indicators = inv.stewardship_principle.metrics;

  return (
    <section className="khalifah" aria-labelledby="khalifah-heading">
      <div className="khalifah__head">
        <h2 id="khalifah-heading">Khalifah</h2>
        <p className="khalifah__sub">Evidence analyst</p>
      </div>

      {inv.presentation?.is_demonstration ? (
        <p className="khalifah__demo" role="note">
          Explaining a worked example. The evidence below is demonstration data
          held separately from reviewed production evidence, so nothing here is
          an EcoIQ finding about this organisation.
        </p>
      ) : null}

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
          ['improve', 'What would strengthen this?'],
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
            {indicators[0] ? (
              <li>
                Independent measurement of {indicators[0]} contradicts what the
                current evidence shows.
              </li>
            ) : null}
            {counts.excluded_from_assessment > 0 ? (
              <li>
                The {counts.excluded_from_assessment} item
                {counts.excluded_from_assessment === 1 ? '' : 's'} currently
                excluded {counts.excluded_from_assessment === 1 ? 'is' : 'are'}
                {' '}reviewed and confirmed, changing the balance of what counts.
              </li>
            ) : (
              <li>
                Evidence not yet linked to this principle is found and
                confirmed, changing the balance of what counts.
              </li>
            )}
          </ul>
        </div>
      ) : null}

      {open === 'improve' ? (
        <div className="khalifah__body">
          <p className="khalifah__label">
            What evidence would make this assessment firmer — not advice to the
            organisation, and not a finding about it.
          </p>
          {indicators.length > 0 ? (
            <>
              <p>
                EcoIQ assesses this principle against the following indicators.
                Evidence bearing on any of them, from a source that can be
                checked, would strengthen what can be concluded here.
              </p>
              <ul>
                {indicators.map((indicator) => <li key={indicator}>{indicator}</li>)}
              </ul>
            </>
          ) : (
            <p>
              The registry records no measurable indicators for this principle,
              so there is nothing specific to name here. That is a gap in the
              framework rather than in this organisation&rsquo;s disclosure.
            </p>
          )}
          {counts.confirmed > 0 && counts.supports > 0 && counts.conflicts === 0 ? (
            <p>
              Nothing currently conflicts. A conclusion resting only on evidence
              that agrees is weaker than one that survived disagreement, so
              evidence pointing the other way would firm this up rather than
              undermine it.
            </p>
          ) : null}
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
