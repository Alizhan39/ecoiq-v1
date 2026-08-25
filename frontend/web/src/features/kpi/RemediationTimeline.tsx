import type { RemediationStep } from '@/types/kpi';

/**
 * finding → response → change → regulatory response → residual concern.
 *
 * REMEDIATION DOES NOT CANCEL A FINDING
 * -------------------------------------
 * This is rendered as a separate timeline, below the assessment, and it is not
 * counted toward the verdict — deliberately. If remediation offset conflicting
 * evidence, an organisation could resolve a problem and watch the historical
 * finding disappear from its own record. What happened and what was done about
 * it are two dimensions, and both stay visible.
 *
 * `verification` is shown on every step because "we changed it" is a claim
 * until someone independent agrees.
 */
export function RemediationTimeline({ steps }: { steps: RemediationStep[] }) {
  if (!steps.length) return null;

  return (
    <section className="remediation" aria-labelledby="remediation-heading">
      <h2 id="remediation-heading">Remediation</h2>
      <p className="remediation__note">
        Tracked separately from the assessment. Remediation does not retire the
        finding it responds to.
      </p>
      <ol className="remediation__list">
        {steps.map((s) => (
          <li key={s.position} className={`remediation__step remediation__step--${s.kind}`}>
            <div className="remediation__marker" aria-hidden="true" />
            <div className="remediation__content">
              <p className="remediation__kind">{s.kind_label}</p>
              <p className="remediation__summary">{s.summary}</p>
              {s.detail ? <p className="remediation__detail">{s.detail}</p> : null}
              <p className="remediation__meta">
                <span className={`kpi-chip kpi-chip--verify-${s.verification}`}>
                  {s.verification_label}
                </span>
                {s.occurred_on ? <span className="remediation__date">{s.occurred_on}</span> : null}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
