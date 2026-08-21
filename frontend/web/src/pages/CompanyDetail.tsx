import { useParams } from 'react-router-dom';
import { getCompany } from '@/api/companies';
import { useApi } from '@/hooks/useApi';
import { ErrorState, Loading } from '@/components/States';
import { EvidenceSummary, ScoreDisplay } from '@/components/EvidenceState';
import { isSignalClear } from '@/types/evidence';

/**
 * One organisation.
 *
 * Evidence status leads. When the score is withheld the page says why, in the
 * backend's own words, instead of showing a placeholder next to an explanation
 * nobody reads.
 */
export default function CompanyDetail() {
  const { slug } = useParams<{ slug: string }>();
  const state = useApi(
    (signal) => getCompany(slug ?? '', signal),
    [slug],
  );

  if (state.status === 'loading') return <Loading />;
  if (state.status === 'error') return <ErrorState error={state.error} />;

  const company = state.data;

  return (
    <article>
      <h1>{company.name}</h1>
      <p className="state__detail">
        {company.sector} · {company.country}
      </p>

      <ScoreDisplay company={company} note={company.evidence_note} />
      <EvidenceSummary
        coverage={company.evidence_coverage}
        confidence={company.confidence}
      />

      {company.harm_signals.length > 0 ? (
        <section aria-labelledby="signals">
          <h2 id="signals">Signals</h2>
          <ul>
            {company.harm_signals.map((signal) => (
              <li key={signal.id}>
                <strong>{signal.label}</strong>{' '}
                {/* insufficient_evidence is NOT clear. A check nobody ran
                    must not render as a pass. */}
                <span>
                  {isSignalClear(signal) ? 'Clear' : signal.status.replace(/_/g, ' ')}
                </span>
                <p className="state__detail">{signal.detail}</p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </article>
  );
}
