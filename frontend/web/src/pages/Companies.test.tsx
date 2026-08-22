import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Companies from './Companies';

const company = (over: Record<string, unknown> = {}) => ({
  slug: 'acme', name: 'Acme', sector: 'Energy', country: 'UK',
  is_public: true, verified: false, ecoiq_score: null,
  score_status: 'INSUFFICIENT_EVIDENCE', evidence_coverage: 0,
  confidence: 'INSUFFICIENT_EVIDENCE', rank: null, url: '',
  ...over,
});

function mock(payload: Record<string, unknown>) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true, status: 200,
    json: async () => ({ count: 1, next: null, previous: null, results: [], ...payload }),
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

beforeEach(() => vi.restoreAllMocks());

describe('the directory withholds what the old one leaked', () => {
  it('shows no score for an unassessed organisation', async () => {
    mock({ results: [company()] });
    render(<Companies />);

    expect(await screen.findByText('Evidence assessment pending'))
      .toBeInTheDocument();
  });

  it('renders no rank at all', async () => {
    // Not "null-safe" — absent. A rank beside a withheld score would be the
    // comparative claim the score is refusing to make.
    mock({ results: [company({ rank: 4 })] });
    const { container } = render(<Companies />);
    await screen.findByText('Acme');

    expect(container.textContent).not.toMatch(/#\d/);
    expect(container.querySelector('.rank')).toBeNull();
  });

  it('requests no score ordering and no tier filter', async () => {
    // The page it replaces ordered by -ecoiq_total_score and filtered on
    // moral_label. Both publish the withheld number.
    const fetchMock = mock({ results: [company()] });
    render(<Companies />);
    await screen.findByText('Acme');

    const url = fetchMock.mock.calls[0]![0] as string;
    for (const forbidden of ['ordering', 'sort', 'label', 'min_score',
      'max_score', 'moral']) {
      expect(url).not.toContain(forbidden);
    }
  });

  it('shows a published score when the evidence carries one', async () => {
    mock({
      results: [company({
        ecoiq_score: 76.4, score_status: 'PUBLISHED',
        evidence_coverage: 100, confidence: 'HIGH',
      })],
    });
    render(<Companies />);

    expect(await screen.findByText('76.4')).toBeInTheDocument();
  });

  it('reports coverage and confidence separately', async () => {
    mock({ results: [company({ evidence_coverage: 40, confidence: 'HIGH' })] });
    render(<Companies />);

    expect(await screen.findByText('40%')).toBeInTheDocument();
    expect(screen.getByText('High')).toBeInTheDocument();
  });
});

describe('search and paging', () => {
  it('sends the search term to the API', async () => {
    const fetchMock = mock({ results: [company()] });
    render(<Companies />);
    await screen.findByText('Acme');

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/Search by name/i), 'northwind');
    await user.click(screen.getByRole('button', { name: 'Search' }));

    await waitFor(() => {
      const urls = fetchMock.mock.calls.map((c) => c[0] as string);
      expect(urls.some((u) => u.includes('q=northwind'))).toBe(true);
    });
  });

  it('does not render the whole estate into one page', async () => {
    // The server-rendered directory emitted all 467 cards — 822 kB.
    mock({ count: 467, next: '?page=2', results: [company()] });
    render(<Companies />);

    expect(await screen.findByRole('button', { name: /Next/ })).toBeEnabled();
  });

  it('disables paging at the ends', async () => {
    mock({ count: 1, next: null, previous: null, results: [company()] });
    render(<Companies />);
    await screen.findByText('Acme');

    expect(screen.getByRole('button', { name: /Previous/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Next/ })).toBeDisabled();
  });

  it('says an empty search is a search result, not an empty estate', async () => {
    mock({ count: 467, results: [] });
    render(<Companies />);

    expect(await screen.findByText(/No organisation matches that search/i))
      .toBeInTheDocument();
    expect(screen.getByText(/467 organisations/)).toBeInTheDocument();
  });

  it('links to the company page with a plain anchor', async () => {
    // /companies/<slug>/ is still server-rendered; a client-side Link would
    // render one thing on click and another on refresh.
    mock({ results: [company()] });
    render(<Companies />);

    expect(await screen.findByRole('link', { name: 'Acme' }))
      .toHaveAttribute('href', '/companies/acme/');
  });
});
