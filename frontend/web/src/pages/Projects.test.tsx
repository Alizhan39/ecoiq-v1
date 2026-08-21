import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import Projects from './Projects';
import { quantity } from '@/types/projects';

function mock(payload: unknown) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true, status: 200, json: async () => payload,
  }));
}

const project = (over: Record<string, unknown> = {}) => ({
  slug: '1', name: 'A Project', project_type: 'renewable', status: 'completed',
  location: 'Almaty', description: '', company: 'Co', verified: false,
  investment_usd: null, co2_reduction_tonnes: null, households_helped: null,
  ...over,
});

beforeEach(() => vi.restoreAllMocks());

describe('an empty estate', () => {
  it('says there are none rather than showing demo rows', async () => {
    mock({ count: 0, verified_count: 0, results: [] });
    render(<Projects />);

    expect(await screen.findByText(/No projects are on record yet/i))
      .toBeInTheDocument();
  });

  it('explains what would put one here', async () => {
    mock({ count: 0, verified_count: 0, results: [] });
    render(<Projects />);

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
    render(<Projects />);

    expect(await screen.findByText('A Project')).toBeInTheDocument();
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  });
});

describe('verification', () => {
  it('marks an unverified project as not verified', async () => {
    mock({ count: 1, verified_count: 0, results: [project()] });
    render(<Projects />);

    // Complete and unverified is a real state — it must not read as checked.
    expect(await screen.findByText('Not verified')).toBeInTheDocument();
  });

  it('marks a verified project', async () => {
    mock({ count: 1, verified_count: 1, results: [project({ verified: true })] });
    render(<Projects />);

    expect(await screen.findByText('Independently verified')).toBeInTheDocument();
  });

  it('reports verified count beside the total', async () => {
    mock({ count: 3, verified_count: 1, results: [project()] });
    render(<Projects />);

    expect(await screen.findByText(/3 on record · 1 independently verified/))
      .toBeInTheDocument();
  });
});
