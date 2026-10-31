import { useState } from 'react';
import type { CompanySummary } from '@/types/evidence';

/**
 * Choose an organisation to assess.
 *
 * Filtering is client-side over the loaded page, which is honest about what it
 * is: a way to find something in a list you already have, not a search over the
 * whole estate. A box that looked like search but only matched one page would
 * be worse than no box.
 */
export function Picker({
  companies,
  onSelect,
  selected,
}: {
  companies: CompanySummary[];
  onSelect: (slug: string) => void;
  selected: string | null;
}) {
  const [query, setQuery] = useState('');
  const term = query.trim().toLowerCase();
  const shown = term
    ? companies.filter((c) => c.name.toLowerCase().includes(term))
    : companies;

  return (
    <div className="picker">
      <label className="picker__label" htmlFor="picker-search">
        Find an organisation
      </label>
      <input
        id="picker-search"
        type="search"
        className="picker__input"
        value={query}
        placeholder="Filter this page…"
        onChange={(event) => setQuery(event.target.value)}
      />

      {shown.length === 0 ? (
        <p className="state__detail">Nothing on this page matches “{query}”.</p>
      ) : (
        <ul className="picker__list">
          {shown.map((company) => (
            <li key={company.slug}>
              <button
                type="button"
                className={
                  company.slug === selected
                    ? 'picker__item picker__item--active'
                    : 'picker__item'
                }
                aria-current={company.slug === selected}
                onClick={() => onSelect(company.slug)}
              >
                <span>{company.name}</span>
                {/* Evidence state, not the score. The list is for choosing
                    something to look at, and a score here would rank a set
                    that is mostly unpublishable. */}
                <span className="picker__coverage">
                  {company.evidence_coverage}% evidence
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
