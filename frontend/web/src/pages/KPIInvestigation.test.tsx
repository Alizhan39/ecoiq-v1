import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import KPIInvestigation from './KPIInvestigation';
import type { KpiInvestigation as Investigation } from '@/types/kpi';

vi.mock('@/api/kpi', () => ({ fetchKpiInvestigation: vi.fn() }));
import { fetchKpiInvestigation } from '@/api/kpi';

const base: Investigation = {
  company: { slug: 'testco', name: 'Testco', sector: 'technology' },
  stewardship_principle: {
    kpi_id: 114, title: 'Consumer Protection & Anti-Manipulation',
    tagline: 'tagline', question: 'Does it protect informed choice?',
    category: 'social', principle_statement: 'statement', metrics: [],
  },
  assessment: {
    verdict: 'mixed_material_conflict', verdict_label: 'MIXED — MATERIAL CONFLICT',
    confidence: 'VERY_HIGH', confidence_reasons: ['A final regulatory finding is present.'],
    rationale: 'Both hold.', is_demo: true, last_assessed_at: null,
  },
  counts: {
    total: 2, confirmed: 2, supports: 1, conflicts: 1, context: 0,
    excluded_from_assessment: 0, remediation_steps: 1,
  },
  evidence: [
    {
      id: 1, title: 'Platform tracking permission', relation: 'supports',
      legal_status: 'company_policy', legal_status_strength: 1,
      source_authority: 'Testco', source_url: 'https://example.org/a',
      source_type: 'manual', date_collected: '2026-01-01', review_tier: 'human_reviewed',
      verification_status: 'verified', review_state: 'confirmed',
      counts_toward_assessment: true, match_basis: '', is_demo: true, excerpt: 'Body A',
    },
    {
      id: 2, title: 'Regulator decision on steering', relation: 'conflicts',
      legal_status: 'final_regulatory_finding', legal_status_strength: 4,
      source_authority: 'Regulator', source_url: 'https://example.org/b',
      source_type: 'manual', date_collected: '2026-02-01',
      review_tier: 'independently_verified', verification_status: 'verified',
      review_state: 'confirmed', counts_toward_assessment: true, match_basis: '',
      is_demo: true, excerpt: 'Body B',
    },
  ],
  remediation: [{
    position: 1, kind: 'residual_concern', kind_label: 'Residual Concern',
    summary: 'Still under scrutiny', detail: '', occurred_on: null,
    verification: 'claimed', verification_label: 'Claimed by Organisation',
    evidence_id: null,
  }],
};

function renderPage(data: Investigation, entry = '/companies/testco/kpis/114') {
  vi.mocked(fetchKpiInvestigation).mockResolvedValue(data);
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/companies/:slug/kpis/:kpiId" element={<KPIInvestigation />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => vi.clearAllMocks());

describe('KPI investigation', () => {
  it('leads with the question and the verdict, not a score', async () => {
    renderPage(base);
    expect(await screen.findByText('Consumer Protection & Anti-Manipulation'))
      .toBeInTheDocument();
    expect(screen.getByText('Does it protect informed choice?')).toBeInTheDocument();
    // The verdict appears in the header, on the principle node and in the
    // Khalifah panel — deliberately. Assert it is present, not that it is unique.
    expect(screen.getAllByText('MIXED — MATERIAL CONFLICT').length)
      .toBeGreaterThan(0);
    expect(screen.queryByText(/\/100/)).not.toBeInTheDocument();
  });

  it('states relation in text, never colour alone', async () => {
    renderPage(base);
    await screen.findByText('Consumer Protection & Anti-Manipulation');
    expect(screen.getAllByText('Supports').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Conflicts').length).toBeGreaterThan(0);
  });

  it('distinguishes a final finding from a company policy in words', async () => {
    renderPage(base);
    await screen.findByText('Consumer Protection & Anti-Manipulation');
    expect(screen.getAllByText('Final regulatory finding').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Company policy').length).toBeGreaterThan(0);
  });

  it('never presents a preliminary finding as concluded', async () => {
    const prelim = structuredClone(base);
    prelim.evidence[1]!.legal_status = 'preliminary_regulatory_finding';
    renderPage(prelim);
    await screen.findByText('Consumer Protection & Anti-Manipulation');
    await userEvent.click(screen.getByRole('button', { name: /Regulator decision/ }));
    expect(await screen.findByText(/Preliminary\./)).toBeInTheDocument();
    expect(screen.queryByText('Final regulatory finding')).not.toBeInTheDocument();
  });

  it('opens the evidence chain as five distinct steps', async () => {
    renderPage(base);
    await screen.findByText('Consumer Protection & Anti-Manipulation');
    await userEvent.click(screen.getByRole('button', { name: /Regulator decision/ }));
    for (const step of ['Source', 'Evidence', 'Claim', 'Provenance']) {
      expect(await screen.findByRole('heading', { name: step })).toBeInTheDocument();
    }
    expect(screen.getByText(/Interpretation/)).toBeInTheDocument();
  });

  it('shows insufficient evidence rather than a zero', async () => {
    const empty = structuredClone(base);
    empty.assessment.verdict = 'insufficient_evidence';
    empty.assessment.verdict_label = 'INSUFFICIENT EVIDENCE';
    empty.evidence = []; empty.remediation = [];
    empty.counts = { ...empty.counts, total: 0, confirmed: 0, supports: 0, conflicts: 0 };
    renderPage(empty);
    expect(await screen.findByRole('heading', { name: 'Insufficient evidence' }))
      .toBeInTheDocument();
    expect(screen.getByText(/not a finding in the organisation's favour/))
      .toBeInTheDocument();
    expect(screen.queryByText(/^0$/)).not.toBeInTheDocument();
  });

  it('marks evidence that does not count, without hiding it', async () => {
    const excluded = structuredClone(base);
    excluded.evidence[1]!.counts_toward_assessment = false;
    excluded.evidence[1]!.review_state = 'proposed';
    excluded.counts.excluded_from_assessment = 1;
    renderPage(excluded);
    await screen.findByText('Consumer Protection & Anti-Manipulation');
    expect(screen.getByRole('button', { name: /Regulator decision/ })).toBeInTheDocument();
    expect(screen.getAllByText('Excluded from assessment').length).toBeGreaterThan(0);
  });

  it('declares a demonstration corpus', async () => {
    renderPage(base);
    expect(await screen.findByText(/Demonstration corpus/)).toBeInTheDocument();
  });

  it('shows remediation separately and says it does not retire the finding', async () => {
    renderPage(base);
    await screen.findByText('Consumer Protection & Anti-Manipulation');
    expect(screen.getByRole('heading', { name: 'Remediation' })).toBeInTheDocument();
    expect(screen.getByText(/does not retire the finding/)).toBeInTheDocument();
  });

  it('can be challenged, and says what would change the conclusion', async () => {
    renderPage(base);
    await screen.findByText('Consumer Protection & Anti-Manipulation');
    await userEvent.click(screen.getByRole('button', { name: /Challenge this conclusion/ }));
    expect(await screen.findByText(/overturned/)).toBeInTheDocument();
  });

  it('exposes an audit trail of how the assessment was produced', async () => {
    renderPage(base);
    await screen.findByText('Consumer Protection & Anti-Manipulation');
    await userEvent.click(screen.getByRole('button', { name: /How was this produced/ }));
    expect(await screen.findByText(/2 confirmed and counted/)).toBeInTheDocument();
    expect(screen.getByText(/not asserted, and not model-generated/)).toBeInTheDocument();
  });

  it('renders no sacred-source material', async () => {
    const { container } = renderPage(base);
    await screen.findByText('Consumer Protection & Anti-Manipulation');
    const html = container.innerHTML;
    for (const term of ['Surah', 'surah', 'An-Nas', 'ayah', 'Qur', 'Arabic']) {
      expect(html).not.toContain(term);
    }
  });

  it('names who is affected', async () => {
    renderPage(base);
    expect(await screen.findByRole('heading', { name: 'Whose choice is affected' }))
      .toBeInTheDocument();
  });
});


describe('the selected evidence item lives in the URL', () => {
  /**
   * An investigation is a thing people send each other — "look at this source"
   * is the point of the page. A selection held only in component state cannot
   * be linked to, bookmarked, or reopened after a refresh.
   */

  it('opens the drawer for the evidence item named in the query string', async () => {
    // Queried by the drawer's own accessible name: the title also appears on
    // the graph node behind it, so a bare text match finds two elements and
    // proves nothing about which one opened.
    renderPage(base, '/companies/testco/kpis/114?evidence=2');
    expect(await screen.findByRole('complementary', {
      name: 'Evidence: Regulator decision on steering',
    })).toBeInTheDocument();
  });

  it('ignores an evidence id this investigation does not contain', async () => {
    /** A stale link shows the investigation, not a failure. */
    renderPage(base, '/companies/testco/kpis/114?evidence=9999');
    expect(await screen.findByText('Consumer Protection & Anti-Manipulation'))
      .toBeInTheDocument();
    expect(screen.getByText(/Select any evidence item/i)).toBeInTheDocument();
  });

  it('ignores a non-numeric evidence id', async () => {
    renderPage(base, '/companies/testco/kpis/114?evidence=drop-table');
    expect(await screen.findByText(/Select any evidence item/i)).toBeInTheDocument();
  });

  it('closing the drawer clears the selection', async () => {
    renderPage(base, '/companies/testco/kpis/114?evidence=1');
    const drawer = await screen.findByRole('complementary', {
      name: 'Evidence: Platform tracking permission',
    });
    await userEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(drawer).not.toBeInTheDocument();
    expect(await screen.findByText(/Select any evidence item/i)).toBeInTheDocument();
  });

  it('selecting a different item swaps the drawer', async () => {
    renderPage(base, '/companies/testco/kpis/114?evidence=1');
    await screen.findByRole('complementary', {
      name: 'Evidence: Platform tracking permission',
    });
    await userEvent.click(screen.getByRole('button', {
      name: /Regulator decision on steering/i,
    }));
    expect(await screen.findByRole('complementary', {
      name: 'Evidence: Regulator decision on steering',
    })).toBeInTheDocument();
  });

  it('shows the hint rather than a drawer when nothing is selected', async () => {
    renderPage(base);
    expect(await screen.findByText(/Select any evidence item/i)).toBeInTheDocument();
  });
});
