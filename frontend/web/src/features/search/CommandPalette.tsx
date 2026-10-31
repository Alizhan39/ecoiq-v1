import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listCompanies } from '@/api/companies';
import { fetchPrincipleRegistry } from '@/api/principles';
import type { CompanySummary } from '@/types/evidence';
import type { Principle } from '@/types/principles';

/**
 * Jump to an organisation or a principle from anywhere.
 *
 * WHY THE TWO SOURCES ARE FETCHED DIFFERENTLY
 * -------------------------------------------
 * The 114 principles are static framework text, identical for every reader, so
 * they are fetched once on first open and filtered in the browser — a keystroke
 * should not become a request for a list that cannot change.
 *
 * Organisations are hundreds of rows and the server already knows how to search
 * them, so `?q=` does that work, debounced. Filtering them client-side would
 * mean shipping the directory to every visitor for a feature most never open.
 *
 * WHAT IT DELIBERATELY DOES NOT SEARCH
 * ------------------------------------
 * Evidence and findings. Both are real things a researcher would want to search
 * and neither is searchable honestly yet: evidence text is third-party excerpt
 * whose licensing this surface has not settled, and a finding is only meaningful
 * beside the evidence that produced it. A palette that returned half a finding
 * would invite exactly the out-of-context reading the investigation page exists
 * to prevent.
 *
 * NO RESULTS IS AN ANSWER
 * -----------------------
 * An empty result says so plainly rather than showing nothing. With most
 * organisations holding no evidence today, "found nothing" is a common and
 * honest outcome, not an error state.
 */

const DEBOUNCE_MS = 200;

interface Result {
  key: string;
  kind: 'principle' | 'organisation';
  label: string;
  detail: string;
  to: string;
}

/**
 * Matches at the START of a word, not anywhere in the string.
 *
 * A plain substring search makes "iron" match "env-iron-mental", which put
 * principle #51 above #57 "Iron & Infrastructure Responsibility" — the one the
 * reader was obviously looking for. Anchoring to a word boundary keeps the
 * useful half of substring matching ("steward" still finds "stewardship")
 * without the mid-word noise.
 */
function matchesWord(haystack: string, query: string): boolean {
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(`\\b${escaped}`, 'i').test(haystack);
}

function principleResults(principles: Principle[], query: string): Result[] {
  const q = query.trim();
  if (!q) return [];
  return principles
    .filter((p) => matchesWord(p.title, q)
      || matchesWord(p.question, q)
      || String(p.kpi_id) === q)
    // Title matches first: someone typing a principle's name wants that
    // principle, not one whose question happens to mention the word.
    .sort((a, b) => Number(matchesWord(b.title, q)) - Number(matchesWord(a.title, q)))
    .slice(0, 6)
    .map((p) => ({
      key: `principle-${p.kpi_id}`,
      kind: 'principle' as const,
      label: `#${p.kpi_id} ${p.title}`,
      detail: p.question,
      to: `/principles/${p.kpi_id}/`,
    }));
}

function organisationResults(companies: CompanySummary[]): Result[] {
  return companies.slice(0, 6).map((c) => ({
    key: `company-${c.slug}`,
    kind: 'organisation' as const,
    label: c.name,
    // Never the score. The directory withholds it for most organisations and a
    // palette is not the place to leak what the page will not show.
    detail: [c.sector, c.country].filter(Boolean).join(' · '),
    to: `/companies/${c.slug}/`,
  }));
}

export function CommandPalette() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [principles, setPrinciples] = useState<Principle[]>([]);
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const restoreTo = useRef<HTMLElement | null>(null);

  const close = useCallback(() => {
    setOpen(false);
    setQuery('');
    setCompanies([]);
    setActive(0);
    // Returning focus to whatever opened it is what makes this usable without
    // a mouse; without it, closing drops the caret at the top of the document.
    restoreTo.current?.focus();
  }, []);

  // Cmd/Ctrl+K from anywhere. Registered on the document because the point is
  // that it works wherever the reader happens to be.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        restoreTo.current = document.activeElement as HTMLElement;
        setOpen((was) => !was);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  // Fetched once, on first open. A palette nobody opens costs nothing.
  useEffect(() => {
    if (!open || principles.length > 0) return undefined;
    const controller = new AbortController();
    fetchPrincipleRegistry(controller.signal)
      .then((registry) => setPrinciples(registry.principles))
      .catch(() => { /* the palette still searches organisations */ });
    return () => controller.abort();
  }, [open, principles.length]);

  useEffect(() => {
    if (!open || query.trim().length < 2) { setCompanies([]); return undefined; }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      listCompanies({ q: query.trim() }, controller.signal)
        .then((page) => setCompanies(page.results))
        .catch(() => { /* principles still resolve */ });
    }, DEBOUNCE_MS);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [open, query]);

  const results = useMemo(
    () => [...principleResults(principles, query), ...organisationResults(companies)],
    [principles, companies, query],
  );

  useEffect(() => { setActive(0); }, [results.length]);

  const go = useCallback((result: Result) => {
    close();
    navigate(result.to);
  }, [close, navigate]);

  if (!open) return null;

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Escape') { event.preventDefault(); close(); return; }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActive((i) => (results.length ? (i + 1) % results.length : 0));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActive((i) => (results.length ? (i - 1 + results.length) % results.length : 0));
    } else if (event.key === 'Enter' && results[active]) {
      event.preventDefault();
      go(results[active]);
    }
  };

  const activeId = results[active] ? `palette-${results[active].key}` : undefined;

  return (
    <div className="palette" role="presentation" onClick={close}>
      <div
        className="palette__panel"
        role="dialog"
        aria-modal="true"
        aria-label="Search EcoIQ"
        onClick={(event) => event.stopPropagation()}
      >
        <input
          ref={inputRef}
          className="palette__input"
          type="text"
          role="combobox"
          aria-expanded="true"
          aria-controls="palette-results"
          aria-activedescendant={activeId}
          aria-autocomplete="list"
          placeholder="Search organisations and principles"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={onKeyDown}
        />

        <ul className="palette__results" id="palette-results" role="listbox"
            aria-label="Results">
          {results.map((result, index) => (
            <li
              key={result.key}
              id={`palette-${result.key}`}
              role="option"
              aria-selected={index === active}
              className={index === active
                ? 'palette__result palette__result--active' : 'palette__result'}
              onMouseEnter={() => setActive(index)}
              onClick={() => go(result)}
            >
              <span className="palette__kind">{result.kind}</span>
              <span className="palette__label">{result.label}</span>
              <span className="palette__detail">{result.detail}</span>
            </li>
          ))}
        </ul>

        {query.trim().length >= 2 && results.length === 0 ? (
          <p className="palette__empty" role="status">
            Nothing matches &ldquo;{query.trim()}&rdquo;. The palette searches
            organisations and the 114 principles — not evidence or findings,
            which are only meaningful beside the investigation that produced
            them.
          </p>
        ) : null}

        {query.trim().length < 2 ? (
          <p className="palette__hint">
            Type to search {principles.length || 114} principles and every
            organisation on record. <kbd>Esc</kbd> to close.
          </p>
        ) : null}
      </div>
    </div>
  );
}
