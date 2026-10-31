import { getLeaderboard } from '@/api/companies';
import { useApi } from '@/hooks/useApi';
import { EmptyState, ErrorState, Loading } from '@/components/States';
import { publishableScore } from '@/types/evidence';

/**
 * League.
 *
 * NOT PRIMARY NAVIGATION, DELIBERATELY
 * ------------------------------------
 * A ranking is the most confident statement a system like this can make, and
 * EcoIQ currently cannot make it about anybody. Putting a league table in the
 * primary nav would say the product is a ranking; it is an evidence layer that
 * can produce a ranking once the evidence exists.
 *
 * The old server-rendered league leaked what this page must not. Its charts
 * embedded fifteen companies' scores, five pillar values each and eight sector
 * averages as inline JSON while the API correctly reported
 * INSUFFICIENT_EVIDENCE for all of them — the visible table was gated and the
 * chart payload was not. There are no charts here, and every number that
 * reaches this component has already been through the same publication gate
 * the API applies.
 */
export default function League() {
  const state = useApi(getLeaderboard, []);

  if (state.status === 'loading') return <Loading label="Loading standings" />;
  if (state.status === 'error') return <ErrorState error={state.error} />;

  const {
    count, withheld_insufficient_evidence: withheld, leaderboard,
    evidence_note: note,
  } = state.data;

  return (
    <div>
      <header className="prose">
        <h1>League</h1>
        <p>
          Comparative standings across tracked organisations. A rank appears
          only where the underlying score is itself publishable — ranking an
          organisation EcoIQ cannot score would assert precisely what the score
          is withholding.
        </p>
      </header>

      {count === 0 ? (
        <EmptyState>
          {/* The backend's wording, not this component's. See the
              `evidence_note` note in types/evidence.ts. */}
          <p>{note?.headline ?? 'No organisation currently qualifies for a rank.'}</p>
          {note ? <p className="state__detail">{note.detail}</p> : null}
          <p className="state__detail">
            {withheld > 0
              ? `${withheld} organisations are tracked. This is the system `
                + 'withholding a comparison it cannot support, not an absence '
                + 'of data.'
              : 'No organisations are tracked yet.'}
          </p>
          <p className="state__detail">
            {/* Plain anchor: /companies/ is served by Django, not by this
                app. A <Link> would render a React page on click and a Django
                page on refresh. */}
            <a href="/companies/">
              What EcoIQ records about each organisation
            </a>
          </p>
        </EmptyState>
      ) : (
        <>
          <p className="state__detail">
            {count} ranked · {withheld} withheld for insufficient evidence
          </p>
          <table className="league-table">
            <caption className="visually-hidden">
              Ranked organisations by EcoIQ score
            </caption>
            <thead>
              <tr>
                <th scope="col">Rank</th>
                <th scope="col">Organisation</th>
                <th scope="col">Sector</th>
                <th scope="col">Score</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.map((company) => {
                const score = publishableScore(company);
                return (
                  <tr key={company.slug}>
                    <td>{company.rank === null ? '—' : company.rank}</td>
                    <td>
                      <a href={`/companies/${company.slug}/`}>
                        {company.name}
                      </a>
                    </td>
                    <td>{company.sector || '—'}</td>
                    {/* `score` is null unless the API published it. There is
                        no fallback here on purpose — a dash is the truthful
                        rendering of an unpublished score. */}
                    <td>{score === null ? '—' : score}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
