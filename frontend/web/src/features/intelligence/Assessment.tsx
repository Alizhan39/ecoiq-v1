import type { CompanyDetail } from '@/types/evidence';
import { confidenceLabel, isPublished, isSignalClear } from '@/types/evidence';

/**
 * The decision view for one organisation.
 *
 * Ordered the way a decision is actually made: what is the evidence, how good
 * is it, what are the risks, what can be concluded, and what is missing.
 *
 * The score comes LAST, not first. It is the output of everything above it,
 * and leading with it invites the reader to skip the part that says whether to
 * trust it.
 */
export function Assessment({ company }: { company: CompanyDetail }) {
  const published = isPublished(company);

  return (
    <div className="assessment">
      <header className="assessment__head">
        <h1>{company.name}</h1>
        <p className="state__detail">
          {company.sector} · {company.country}
        </p>
      </header>

      <section aria-labelledby="evidence-step">
        <h2 id="evidence-step">1 · Evidence</h2>
        <dl className="evidence">
          <div className="evidence__item">
            <dt>Coverage</dt>
            <dd>{company.evidence_coverage}%</dd>
          </div>
          <div className="evidence__item">
            <dt>Confidence</dt>
            <dd>{confidenceLabel(company.confidence)}</dd>
          </div>
        </dl>
        <p className="state__detail">
          Coverage is how much of the assessment is supported. Confidence is how
          good that support is. They are separate, and they do not move together.
        </p>
      </section>

      <section aria-labelledby="risks-step">
        <h2 id="risks-step">2 · Material risks</h2>
        {company.harm_signals.length === 0 ? (
          <p className="state__detail">No risk signals recorded.</p>
        ) : (
          <ul className="signals">
            {company.harm_signals.map((signal) => {
              const unassessed = signal.status === 'insufficient_evidence';
              return (
                <li key={signal.id} className="signal">
                  <span className={`signal__dot signal__dot--${signal.status}`} />
                  <div>
                    <strong>{signal.label}</strong>{' '}
                    <span className="signal__status">
                      {/* An unassessed signal must never read as an all-clear:
                          "we did not check" and "we checked and it is fine"
                          are different findings. */}
                      {unassessed
                        ? 'Not assessed'
                        : isSignalClear(signal)
                          ? 'Clear'
                          : signal.status.replace(/_/g, ' ')}
                    </span>
                    <p className="state__detail">{signal.detail}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section aria-labelledby="decision-step">
        <h2 id="decision-step">3 · Decision assessment</h2>
        {published ? (
          <div className="score score--published">
            <span className="score__value">{company.ecoiq_score.toFixed(1)}</span>
            <span className="score__scale">/100 EcoIQ score</span>
          </div>
        ) : (
          <div className="score score--withheld">
            <p className="score__pending">Insufficient evidence</p>
            <p className="score__note">{company.evidence_note}</p>
          </div>
        )}
      </section>

      {!published ? (
        <section aria-labelledby="gaps-step">
          <h2 id="gaps-step">4 · What would change this</h2>
          <p className="prose">
            An assessment is published when every material input it weighs is
            supported by defensible evidence. This organisation is at{' '}
            <strong>{company.evidence_coverage}%</strong> coverage.
          </p>
          <p className="state__detail">
            Seeded and legacy values never count toward coverage, however many
            of them exist.
          </p>
        </section>
      ) : null}
    </div>
  );
}
