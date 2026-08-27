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

/** A company with nothing investigated. The honest default for a fixture. */
const NO_PRINCIPLES = {
  company: { slug: 'acme', name: 'Acme', sector: 'Energy' },
  summary: {
    total: 114, assessed: 0, not_assessed: 114, assessed_pct: 0,
    counts: { not_assessed: 114 }, pending_review_total: 0,
  },
  categories: [],
  principles: [],
};

/**
 * Dispatches on URL rather than answering every call with one payload.
 *
 * The page reads two endpoints — the assessment, and the 114 principle states
 * — and a stub that returns the assessment body for both would hand the
 * principle code a shape it never receives in production. A test that passes
 * against an impossible response is not testing anything.
 */
function mock(payload: unknown, principles: unknown = NO_PRINCIPLES) {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => Promise.resolve({
    ok: true,
    status: 200,
    json: async () => (String(url).endsWith('/principles/') ? principles : payload),
  })));
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

describe('the stewardship principles doorway', () => {
  const investigated = (over: Record<string, unknown> = {}) => ({
    ...NO_PRINCIPLES,
    summary: { ...NO_PRINCIPLES.summary, assessed: 2, not_assessed: 112, assessed_pct: 1.8 },
    principles: [
      {
        kpi_id: 14, title: 'Water Stewardship', category: 'earth',
        tagline: 't', question: 'q', metrics: [], principle_statement: '',
        state: 'conflict', state_label: 'CONFLICTS',
        counts: {
          total: 2, confirmed: 2, supports: 0, conflicts: 2, context: 0,
          insufficient_to_conclude: 0, excluded_from_assessment: 0,
        },
        pending_review_count: 0, remediation_step_count: 0,
        has_material_conflict: false, is_demo: false, last_assessed_at: null,
        ...over,
      },
      {
        kpi_id: 114, title: 'Consumer Protection & Anti-Manipulation',
        category: 'community', tagline: 't', question: 'q', metrics: [],
        principle_statement: '', state: 'insufficient_evidence',
        state_label: 'INSUFFICIENT EVIDENCE',
        counts: {
          total: 0, confirmed: 0, supports: 0, conflicts: 0, context: 0,
          insufficient_to_conclude: 0, excluded_from_assessment: 0,
        },
        pending_review_count: 0, remediation_step_count: 0,
        has_material_conflict: false, is_demo: false, last_assessed_at: null,
      },
    ],
  });

  beforeEach(() => vi.unstubAllGlobals());

  it('is no longer hard-coded to principle 114', async () => {
    mock(PUBLISHED, investigated());
    show();
    expect(await screen.findByText('#14')).toBeInTheDocument();
    expect(screen.getByText('Water Stewardship')).toBeInTheDocument();
  });

  it('links each principle to its own investigation', async () => {
    mock(PUBLISHED, investigated());
    show();
    const link = await screen.findByRole('link', {
      name: /Investigate principle 14, Water Stewardship/i,
    });
    expect(link).toHaveAttribute('href', '/companies/acme/kpis/14/');
  });

  it('says nobody has looked rather than hiding the section', async () => {
    /**
     * A missing section reads as "nothing to say here". The true statement is
     * "nobody has investigated this organisation yet", which is about EcoIQ.
     */
    mock(PUBLISHED, NO_PRINCIPLES);
    show();
    expect(await screen.findByText(/None of the 114 principles has been investigated/i))
      .toBeInTheDocument();
  });

  it('reports how much of the framework is still unlooked-at', async () => {
    mock(PUBLISHED, investigated());
    show();
    expect(await screen.findByText(/2 of 114 principles investigated/i))
      .toBeInTheDocument();
    expect(screen.getByText(/112 not yet looked at/i)).toBeInTheDocument();
  });

  it('flags a material regulatory conflict, and only when confirmed', async () => {
    mock(PUBLISHED, investigated({ has_material_conflict: true }));
    show();
    expect(await screen.findByText(/Material regulatory conflict/i))
      .toBeInTheDocument();
  });

  it('shows remediation beside a finding, never instead of it', async () => {
    mock(PUBLISHED, investigated({ remediation_step_count: 3 }));
    show();
    expect(await screen.findByText(/Remediation recorded/i)).toBeInTheDocument();
    // The conflict is still the verdict.
    expect(screen.getByText('CONFLICTS')).toBeInTheDocument();
  });

  it('renders no numeric score for any principle', async () => {
    mock(PUBLISHED, investigated());
    const { container } = show();
    await screen.findByText('#14');
    const list = container.querySelector('.kpi-preview__list');
    expect(list?.textContent).not.toMatch(/\d+\s*\/\s*100/);
    expect(list?.textContent).not.toMatch(/score/i);
  });
});
