import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Projects from './Projects';
import { quantity } from '@/types/projects';

function mock(payload: Record<string, unknown>) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    // `concepts` defaults to empty so a test that is not about concepts does
    // not have to mention them, but every test CAN set it.
    json: async () => ({ concepts: [], ...payload }),
  }));
}

function show() {
  return render(<MemoryRouter><Projects /></MemoryRouter>);
}

const project = (over: Record<string, unknown> = {}) => ({
  slug: '1', name: 'A Project', project_type: 'renewable', status: 'completed',
  location: 'Almaty', description: '', company: 'Co', verified: false,
  investment_usd: null, co2_reduction_tonnes: null, households_helped: null,
  ...over,
});

const concept = (over: Record<string, unknown> = {}) => ({
  slug: 'almaty-clean-air', name: 'Almaty Clean Air Pilot',
  tagline: 'Replacing coal heating.', status_key: 'design',
  status: 'In Design', location: 'Almaty, Kazakhstan', sector: 'Air Quality',
  timeline_label: '2025–2026 (indicative)', overview: '', problem: '',
  solution: '', expected_impact: [], kpis: [], timeline_phases: [],
  partnership_opportunities: [], funding_amount: '£15,000',
  funding_label: 'pilot (indicative)', funding_note: '',
  ...over,
});

beforeEach(() => vi.restoreAllMocks());

describe('an empty estate', () => {
  it('says there are none rather than showing demo rows', async () => {
    mock({ count: 0, verified_count: 0, results: [] });
    show();

    expect(await screen.findByText(/No projects are on record yet/i))
      .toBeInTheDocument();
  });

  it('explains what would put one here', async () => {
    mock({ count: 0, verified_count: 0, results: [] });
    show();

    expect(await screen.findByText(/problem statement, a\s+baseline/i))
      .toBeInTheDocument();
  });
});

describe('quantities', () => {
  it('renders an unrecorded quantity as an em dash', () => {
    expect(quantity(null)).toBe('—');
  });

  it('renders a real zero as zero', () => {
    expect(quantity(0)).toBe('0');
  });

  it('does not confuse the two', () => {
    expect(quantity(null)).not.toBe(quantity(0));
  });

  it('shows an em dash for a project with no recorded figures', async () => {
    mock({ count: 1, verified_count: 0, results: [project()] });
    show();

    expect(await screen.findByText('A Project')).toBeInTheDocument();
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  });
});

describe('verification', () => {
  it('marks an unverified project as not verified', async () => {
    mock({ count: 1, verified_count: 0, results: [project()] });
    show();

    // Complete and unverified is a real state — it must not read as checked.
    expect(await screen.findByText('Not verified')).toBeInTheDocument();
  });

  it('marks a verified project', async () => {
    mock({ count: 1, verified_count: 1, results: [project({ verified: true })] });
    show();

    expect(await screen.findByText('Independently verified')).toBeInTheDocument();
  });

  it('reports verified count beside the total', async () => {
    mock({ count: 3, verified_count: 1, results: [project()] });
    show();

    expect(await screen.findByText(/3 on record · 1 independently verified/))
      .toBeInTheDocument();
  });
});

describe('programme concepts', () => {
  it('are shown, so real intentions are not deleted by a migration', async () => {
    mock({ count: 0, verified_count: 0, results: [], concepts: [concept()] });
    show();

    expect(await screen.findByText('Almaty Clean Air Pilot'))
      .toBeInTheDocument();
  });

  it('never count as recorded projects', async () => {
    mock({ count: 0, verified_count: 0, results: [], concepts: [concept()] });
    show();

    // Five ideas must not become "five projects". The empty state for RECORDED
    // projects still shows, even though the page has content on it.
    expect(await screen.findByText(/No projects are on record yet/i))
      .toBeInTheDocument();
  });

  it('are labelled as concepts, not as delivered work', async () => {
    mock({ count: 0, verified_count: 0, results: [], concepts: [concept()] });
    show();

    expect(await screen.findByText(/Concept · In Design/)).toBeInTheDocument();
    expect(screen.getByText(/None of it has been implemented/i))
      .toBeInTheDocument();
  });

  it('sit under their own heading, separate from recorded projects', async () => {
    mock({ count: 0, verified_count: 0, results: [], concepts: [concept()] });
    show();

    expect(await screen.findByRole('heading', { name: 'Programme concepts' }))
      .toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Recorded projects' }))
      .toBeInTheDocument();
  });
});
