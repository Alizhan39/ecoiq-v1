import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import League from './League';

function mock(payload: Record<string, unknown>) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      evidence_note: {
        headline: 'Evidence assessment pending',
        detail: 'No organisation currently has the evidence coverage a '
          + 'published score requires, so none can be ranked.',
      },
      ...payload,
    }),
  }));
}

function show() {
  return render(<MemoryRouter><League /></MemoryRouter>);
}

const company = (over: Record<string, unknown> = {}) => ({
  slug: 'acme', name: 'Acme', sector: 'Energy', country: 'UK',
  is_public: true, verified: false, ecoiq_score: null,
  score_status: 'INSUFFICIENT_EVIDENCE', evidence_coverage: 0,
  confidence: 'INSUFFICIENT_EVIDENCE', rank: null, url: '',
  ...over,
});

beforeEach(() => vi.restoreAllMocks());

describe('a league with nothing publishable — production today', () => {
  it('renders the backend\'s explanation, not one of its own', async () => {
    // A page that writes its own sentence about withheld evidence will
    // eventually disagree with the one the company pages give.
    mock({ count: 0, withheld_insufficient_evidence: 467, leaderboard: [] });
    show();

    expect(await screen.findByText('Evidence assessment pending'))
      .toBeInTheDocument();
    expect(screen.getByText(/so none can be ranked/i)).toBeInTheDocument();
  });

  it('distinguishes "nothing qualifies" from "nothing exists"', async () => {
    mock({ count: 0, withheld_insufficient_evidence: 467, leaderboard: [] });
    show();

    // An empty list means two very different things. The page must say which.
    expect(await screen.findByText(/467 organisations are tracked/i))
      .toBeInTheDocument();
  });

  it('says so plainly when there genuinely is nothing tracked', async () => {
    mock({ count: 0, withheld_insufficient_evidence: 0, leaderboard: [] });
    show();

    expect(await screen.findByText(/No organisations are tracked yet/i))
      .toBeInTheDocument();
  });

  it('falls back to its own wording only if the API sends none', async () => {
    mock({
      count: 0, withheld_insufficient_evidence: 3, leaderboard: [],
      evidence_note: null,
    });
    show();

    expect(await screen.findByText(/No organisation currently qualifies/i))
      .toBeInTheDocument();
  });

  it('embeds no score anywhere in the document', async () => {
    // The regression this page exists to not repeat: the server-rendered
    // league gated its visible table and left fifteen companies' scores in an
    // inline chart payload.
    mock({ count: 0, withheld_insufficient_evidence: 467, leaderboard: [] });
    const { container } = show();
    await screen.findByText('Evidence assessment pending');

    expect(container.innerHTML).not.toMatch(/\d+\.\d/);
  });
});

describe('a league with publishable rows', () => {
  it('shows the rank and the score', async () => {
    mock({
      count: 1, withheld_insufficient_evidence: 3, evidence_note: null,
      leaderboard: [company({
        ecoiq_score: 76.4, score_status: 'PUBLISHED', rank: 1,
        evidence_coverage: 100, confidence: 'HIGH',
      })],
    });
    show();

    expect(await screen.findByText('76.4')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('reports how many were withheld', async () => {
    mock({
      count: 1, withheld_insufficient_evidence: 3, evidence_note: null,
      leaderboard: [company({
        ecoiq_score: 76.4, score_status: 'PUBLISHED', rank: 1,
      })],
    });
    show();

    expect(await screen.findByText(/1 ranked · 3 withheld/)).toBeInTheDocument();
  });

  it('renders an em dash, never a zero, for an unpublished score', async () => {
    // The API should not send this combination, but if it ever did, the page
    // must not invent a number to fill the cell.
    mock({
      count: 1, withheld_insufficient_evidence: 0, evidence_note: null,
      leaderboard: [company({ rank: 4 })],
    });
    show();

    expect(await screen.findByText('Acme')).toBeInTheDocument();
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });
});
