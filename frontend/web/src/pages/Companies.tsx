import { useCallback, useMemo, useState } from 'react';
import { listCompanies } from '@/api/companies';
import type { CompanyQuery } from '@/api/companies';
import { useApi } from '@/hooks/useApi';
import { EmptyState, ErrorState, Loading } from '@/components/States';
import { EvidenceSummary, ScoreDisplay } from '@/components/EvidenceState';

/**
 * The company directory.
 *
 * WHAT THIS DELIBERATELY DOES NOT DO
 * ----------------------------------
 * The server-rendered directory it replaces ordered all 467 cards by
 * `-ecoiq_total_score` and offered a filter over `moral_label`, the tier
 * derived from that score. Both publish a withheld number: ordering lets you
 * read a company's standing off its position, and the tier filter lets you
 * select on it. Neither showed a digit, and both were a ranking.
 *
 * This page orders by name — the order /api/v2/companies/ returns — and offers
 * no tier filter and no score sort. There is no arrangement of these cards
 * from which a withheld score can be inferred.
 *
 * It also does not render 467 cards into one 822 kB document. The API has
 * paginated all along; the old page simply never asked.
 *
 * RANK IS ABSENT ENTIRELY
 * -----------------------
 * Not "null-safe" — absent. A directory is not a leaderboard, and a rank shown
 * beside a card whose score is withheld would be the comparative claim the
 * score is refusing to make. /league/ is where ranking lives, and it publishes
 * nothing today either.
 */
export default function Companies() {
  const [query, setQuery] = useState<CompanyQuery>({});
  const [draft, setDraft] = useState('');

  const load = useCallback(
    (signal: AbortSignal) => listCompanies(query, signal),
    [query],
  );
  const state = useApi(load, [query]);

  const sectors = useMemo(
    () =>
      state.status === 'ready'
        ? [...new Set(state.data.results.map((c) => c.sector).filter(Boolean))].sort()
        : [],
    [state],
  );

  function search(event: React.FormEvent) {
    event.preventDefault();
    setQuery((current) => ({ ...current, q: draft.trim(), page: 1 }));
  }

  return (
    <div>
      <header className="prose">
        <h1>Organisations</h1>
        <p>
          What EcoIQ records about each organisation, and how much of it is
          supported. An assessment appears only where the evidence carries one.
        </p>
      </header>

      <form className="filters" onSubmit={search} role="search">
        <label className="field__label" htmlFor="company-search">
          Search by name
        </label>
        <div className="filters__row">
          <input
            id="company-search"
            className="field__input"
            type="search"
            value={draft}
            placeholder="Organisation name"
            onChange={(event) => setDraft(event.target.value)}
          />
          <button type="submit" className="cta">Search</button>
        </div>

        {sectors.length > 1 ? (
          <div className="filters__row">
            <label className="field__label" htmlFor="sector-filter">Sector</label>
            <select
              id="sector-filter"
              className="field__input"
              value={query.sector ?? ''}
              onChange={(event) =>
                setQuery((current) => ({
                  ...current, sector: event.target.value, page: 1,
                }))
              }
            >
              <option value="">All sectors</option>
              {sectors.map((sector) => (
                <option key={sector} value={sector}>{sector}</option>
              ))}
            </select>
          </div>
        ) : null}
      </form>

      <Results state={state} query={query} onPage={(page) =>
        setQuery((current) => ({ ...current, page }))} />
    </div>
  );
}


function Results({
  state, query, onPage,
}: {
  state: ReturnType<typeof useApi<Awaited<ReturnType<typeof listCompanies>>>>;
  query: CompanyQuery;
  onPage: (page: number) => void;
}) {
  if (state.status === 'loading') return <Loading label="Loading organisations" />;
  if (state.status === 'error') return <ErrorState error={state.error} />;

  const { count, results, next, previous } = state.data;
  const page = query.page ?? 1;

  if (results.length === 0) {
    return (
      <EmptyState>
        <p>No organisation matches that search.</p>
        <p className="state__detail">
          This is a search result, not a statement about the estate — EcoIQ
          tracks {count === 0 ? 'organisations' : `${count} organisations`} in
          total.
        </p>
      </EmptyState>
    );
  }

  return (
    <>
      <p className="state__detail">
        {count} organisation{count === 1 ? '' : 's'}
        {query.q ? ` matching “${query.q}”` : ''}
        {query.sector ? ` in ${query.sector}` : ''}
      </p>

      <ul className="grid">
        {results.map((company) => (
          <li className="card" key={company.slug}>
            <h2 className="card__title">
              {/* Plain anchor: the company page is server-rendered. */}
              <a href={`/companies/${company.slug}/`}>{company.name}</a>
            </h2>
            <p className="state__detail">
              {[company.sector, company.country].filter(Boolean).join(' · ') || '—'}
            </p>
            <ScoreDisplay company={company} />
            <EvidenceSummary
              coverage={company.evidence_coverage}
              confidence={company.confidence}
            />
          </li>
        ))}
      </ul>

      <nav className="pager" aria-label="Pagination">
        <button
          type="button" className="pager__button"
          disabled={!previous} onClick={() => onPage(page - 1)}
        >
          ← Previous
        </button>
        <span className="pager__position">Page {page}</span>
        <button
          type="button" className="pager__button"
          disabled={!next} onClick={() => onPage(page + 1)}
        >
          Next →
        </button>
      </nav>
    </>
  );
}
