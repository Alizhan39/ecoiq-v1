import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

describe('the 114 principle matrix', () => {
  const matrix = (over: Record<string, unknown> = {}) => ({
    ...NO_PRINCIPLES,
    summary: { ...NO_PRINCIPLES.summary, assessed: 1, not_assessed: 113, assessed_pct: 0.9 },
    principles: [
      {
        kpi_id: 14, title: 'Water Stewardship', category: 'earth',
        tagline: 't', question: 'Is water managed responsibly?', metrics: [],
        principle_statement: '', state: 'conflict', state_label: 'CONFLICTS',
        counts: {
          total: 2, confirmed: 2, supports: 0, conflicts: 2, context: 0,
          insufficient_to_conclude: 0, excluded_from_assessment: 0,
        },
        pending_review_count: 0, remediation_step_count: 0,
        has_material_conflict: false, is_demo: false, last_assessed_at: null,
        ...over,
      },
      ...Array.from({ length: 113 }, (_, i) => ({
        kpi_id: i + 15, title: `Principle ${i + 15}`, category: 'governance',
        tagline: 't', question: 'q', metrics: [], principle_statement: '',
        state: 'not_assessed', state_label: 'NOT ASSESSED',
        counts: {
          total: 0, confirmed: 0, supports: 0, conflicts: 0, context: 0,
          insufficient_to_conclude: 0, excluded_from_assessment: 0,
        },
        pending_review_count: 0, remediation_step_count: 0,
        has_material_conflict: false, is_demo: false, last_assessed_at: null,
      })),
    ],
  });

  beforeEach(() => vi.unstubAllGlobals());

  it('renders every principle, not only the investigated ones', async () => {
    /**
     * Hiding the unassessed would make a nearly-empty assessment look
     * complete, which is the failure this product exists to avoid.
     */
    mock(PUBLISHED, matrix());
    const { container } = show();
    await screen.findByRole('heading', { name: /All 114 principles/i });
    expect(container.querySelectorAll('.matrix__cell')).toHaveLength(114);
  });

  it('says in words how much has not been looked at', async () => {
    mock(PUBLISHED, matrix());
    show();
    expect(await screen.findByText(/1 of 114 principles investigated/i))
      .toBeInTheDocument();
    expect(screen.getByText(/113 have not been looked at/i)).toBeInTheDocument();
  });

  it('does not carry state in colour alone', async () => {
    /**
     * "Insufficient evidence" and "concern" are opposite claims. A reader who
     * cannot distinguish hues must still be able to tell them apart, so the
     * state is in every cell's accessible name.
     */
    mock(PUBLISHED, matrix());
    show();
    expect(await screen.findByRole('button', {
      name: /Principle 14, Water Stewardship: Substantiated concern/i,
    })).toBeInTheDocument();
  });

  it('opens a cell into its evidence counts and both links', async () => {
    mock(PUBLISHED, matrix());
    show();
    const cell = await screen.findByRole('button', { name: /Principle 14, Water/i });
    await userEvent.click(cell);
    expect(await screen.findByRole('heading', { name: 'Water Stewardship' }))
      .toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Open the investigation/i }))
      .toHaveAttribute('href', '/companies/acme/kpis/14/');
    expect(screen.getByRole('link', { name: /What this principle asks/i }))
      .toHaveAttribute('href', '/principles/14/');
  });

  it('explains an empty cell rather than leaving it blank', async () => {
    mock(PUBLISHED, matrix());
    show();
    // Exact name: /Principle 15,/ also matches 150-159 and the filter chips.
    await userEvent.click(await screen.findByRole('button', {
      name: 'Principle 15, Principle 15: Not yet investigated',
    }));
    expect(await screen.findByText(/No evidence has been linked to this principle/i))
      .toBeInTheDocument();
  });

  it('filters without pretending the hidden principles do not exist', async () => {
    mock(PUBLISHED, matrix());
    const { container } = show();
    await screen.findByRole('heading', { name: /All 114 principles/i });
    // Exact name: 113 cells carry "Not yet investigated" in their accessible
    // name, so a loose /Investigated/ matches the grid as well as the chip.
    await userEvent.click(screen.getByRole('button', { name: 'Investigated 1' }));
    expect(container.querySelectorAll('.matrix__cell')).toHaveLength(1);
    // The count on the "All" chip still reports the full framework.
    expect(screen.getByRole('button', { name: 'All 114 114' })).toBeInTheDocument();
  });

  it('shows remediation beside a finding, never instead of it', async () => {
    mock(PUBLISHED, matrix({ remediation_step_count: 3, has_material_conflict: true }));
    show();
    await userEvent.click(await screen.findByRole('button', { name: /Principle 14, Water/i }));
    const detail = await screen.findByRole('complementary');
    expect(detail).toHaveTextContent(/3 remediation steps recorded/i);
    // The conflict is still the verdict; remediation sits beside it.
    expect(detail).toHaveTextContent('Substantiated concern');
    expect(detail).toHaveTextContent(/Material regulatory conflict/i);
  });

  it('reports evidence awaiting review as counting toward nothing', async () => {
    mock(PUBLISHED, {
      ...matrix({ pending_review_count: 4, state: 'not_assessed' }),
      summary: { ...NO_PRINCIPLES.summary, assessed: 0, not_assessed: 114, pending_review_total: 4 },
    });
    show();
    expect(await screen.findByText(/counting toward no verdict until reviewed/i))
      .toBeInTheDocument();
  });

  it('says nobody has looked when nothing is assessed', async () => {
    mock(PUBLISHED, NO_PRINCIPLES);
    show();
    expect(await screen.findByText(/None of the 114 principles has been investigated/i))
      .toBeInTheDocument();
  });

  it('renders no numeric score for any principle', async () => {
    mock(PUBLISHED, matrix());
    const { container } = show();
    await screen.findByRole('heading', { name: /All 114 principles/i });
    const grid = container.querySelector('.matrix__grid');
    expect(grid?.textContent).not.toMatch(/\d+\s*\/\s*100|score/i);
  });
});
