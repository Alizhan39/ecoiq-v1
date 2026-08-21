import { Link } from 'react-router-dom';
import { listCompanies } from '@/api/companies';
import { useApi } from '@/hooks/useApi';
import { EmptyState, ErrorState, Loading } from '@/components/States';
import { EvidenceSummary, RankDisplay, ScoreDisplay } from '@/components/EvidenceState';

/**
 * Organisations.
 *
 * Companies are no longer the primary product, and ranking is deliberately not
 * the hero. The list leads with evidence state, because for almost every
 * organisation that is the entire truthful answer.
 */
export default function Companies() {
  const state = useApi(listCompanies, []);

  if (state.status === 'loading') return <Loading label="Loading organisations" />;
  if (state.status === 'error') return <ErrorState error={state.error} />;

  const { results } = state.data;
  if (results.length === 0) {
    return <EmptyState>No organisations to show.</EmptyState>;
  }

  return (
    <div>
      <h1>Organisations</h1>
      <ul className="grid">
        {results.map((company) => (
          <li className="card" key={company.slug}>
            <Link to={`/companies/${company.slug}`}>{company.name}</Link>
            <ScoreDisplay company={company} />
            <EvidenceSummary
              coverage={company.evidence_coverage}
              confidence={company.confidence}
            />
            {/* Never derived from list position. */}
            <RankDisplay rank={company.rank} />
          </li>
        ))}
      </ul>
    </div>
  );
}
