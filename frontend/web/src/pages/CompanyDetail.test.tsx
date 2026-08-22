import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import CompanyDetail from './CompanyDetail';

const WITHHELD = {
  slug: 'acme', name: 'Acme', sector: 'Energy', country: 'UK',
  score_status: 'INSUFFICIENT_EVIDENCE', ecoiq_score: null,
  evidence_coverage: 0, confidence: 'INSUFFICIENT_EVIDENCE',
  evidence_note: { headline: 'Evidence assessment pending', detail: 'Not enough evidence.' },
  evidence_gaps: { covered: 0, required: 16, missing: ['a', 'b'], unevidenced: [], reasons: ['no evidence'] },
};

const PUBLISHED = {
  ...WITHHELD,
  score_status: 'PUBLISHED', ecoiq_score: 76.4, evidence_coverage: 100,
  confidence: 'HIGH', evidence_note: undefined,
  evidence_gaps: { covered: 16, required: 16, missing: [], unevidenced: [], reasons: [] },
  material_evidence: [
    { key: 'public_benefit_score', label: 'Public benefit', value: 70 },
    { key: 'harm_penalty', label: 'Harm penalty', value: null },
  ],
  decision_risks: {
    integrity: { score: 68, risk_level: 'moderate', verdict: 'proceed', evidence_status: 'sufficient', red_line_breached: false },
    controversies: [],
  },
  ethics: {
    net_ethical_impact: 55, transition_stewardship: 60, regenerative_value: 40,
    total_benefit_score: 70, total_harm_score: 15, key_harms: ['Flaring'],
    key_benefits: [], next_best_actions: [], engine_confidence: 'medium',
    analyst_reviewed: false, formula_version: 'v3',
  },
  financing_readiness: {
    readiness: 62, tier: 'developing', evidence_completeness: 80,
    dimensions: {}, missing_requirements: ['Audited emissions'], next_actions: [],
    engine_confidence: 'medium', analyst_reviewed: false,
  },
  shariah: {
    disclaimer: 'A named, versioned business-activity and financial-ratio eligibility screen. Not a religious ruling, a fatwa, or a certification.',
    methodology: 'AAOIFI-like v2', overall_result: 'eligible',
    business_activity_result: 'pass', business_activity_reason: '',
    financial_ratio_result: 'pass', data_completeness_pct: 90,
    review_status: 'system_checked', screened_at: null,
  },
};

function mock(payload: unknown) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true, status: 200, json: async () => payload,
  }));
}

function show() {
  return render(
    <MemoryRouter initialEntries={['/companies/acme']}>
      <Routes><Route path="/companies/:slug" element={<CompanyDetail />} /></Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => vi.restoreAllMocks());

describe('an organisation with no publishable assessment', () => {
  it('shows the pending state, not a score', async () => {
    mock(WITHHELD);
    show();
    expect(await screen.findByText('Evidence assessment pending')).toBeInTheDocument();
  });

  it('renders no panel at all', async () => {
    // Absent, not empty. An empty ethics panel beside a real one is still a
    // statement about the organisation.
    mock(WITHHELD);
    show();
    await screen.findByText('Evidence assessment pending');

    for (const heading of ['Material evidence', 'Decision risks',
      'Ethics and governance', 'Financing readiness',
      'Shariah eligibility screen']) {
      expect(screen.queryByRole('heading', { name: heading })).toBeNull();
    }
  });

  it('still shows the gaps, which is the actionable part', async () => {
    mock(WITHHELD);
    show();
    expect(await screen.findByText(/0 of 16 material inputs/)).toBeInTheDocument();
  });

  it('shows no number that could be read as a score', async () => {
    mock(WITHHELD);
    const { container } = show();
    await screen.findByText('Evidence assessment pending');
    expect(container.textContent).not.toMatch(/\b\d{1,3}\.\d\b/);
  });
});

describe('a published organisation', () => {
  it('shows the score', async () => {
    mock(PUBLISHED);
    show();
    expect(await screen.findByText('76.4')).toBeInTheDocument();
  });

  it('puts evidence before conclusion', async () => {
    mock(PUBLISHED);
    const { container } = show();
    await screen.findByRole('heading', { name: 'Material evidence' });

    const order = [...container.querySelectorAll('h2')].map((h) => h.textContent);
    expect(order.indexOf('Material evidence'))
      .toBeLessThan(order.indexOf('Ethics and governance'));
    expect(order.indexOf('Evidence gaps'))
      .toBeLessThan(order.indexOf('Provenance and methodology'));
  });

  it('renders an unassessed pillar as an em dash, never zero', async () => {
    mock(PUBLISHED);
    show();
    await screen.findByRole('heading', { name: 'Material evidence' });

    const harm = screen.getByText('Harm penalty').closest('div');
    expect(harm?.textContent).toContain('—');
    expect(harm?.textContent).not.toContain('0.0');
  });

  it('renders the Shariah disclaimer with the result', async () => {
    mock(PUBLISHED);
    const { container } = show();
    await screen.findByRole('heading', { name: 'Shariah eligibility screen' });

    const section = container.querySelector('section[aria-labelledby="shariah"]');
    expect(section?.textContent).toMatch(/not a religious ruling/i);
    // In the same section as the verdict, not elsewhere on the page.
    expect(section?.textContent).toContain('eligible');
  });

  it('says financing readiness is not a recommendation', async () => {
    mock(PUBLISHED);
    show();
    expect(await screen.findByText(/not a recommendation of any particular instrument/i))
      .toBeInTheDocument();
  });

  it('does not claim an absence of controversies is a clean finding', async () => {
    mock(PUBLISHED);
    show();
    expect(await screen.findByText(/not a finding that none exist/i))
      .toBeInTheDocument();
  });

  it('renders none of the retired panels', async () => {
    mock(PUBLISHED);
    const { container } = show();
    await screen.findByRole('heading', { name: 'Material evidence' });

    for (const gone of [/matched financing pathways/i, /data status/i,
      /watchlist/i, /share price/i]) {
      expect(container.textContent).not.toMatch(gone);
    }
  });
});
