import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import Labs from './Labs';

const mod = (over: Record<string, unknown>) => ({
  key: 'k', name: 'A Module', kind: 'AI_AGENT', status: 'EXPERIMENTAL',
  evaluation: 'NOT YET MEASURED', basis: 'a stated reason', ...over,
});

function mock(modules: unknown[]) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true, status: 200, json: async () => ({ counters: [], modules }),
  }));
}

beforeEach(() => vi.restoreAllMocks());

describe('Labs groups by what can honestly be claimed', () => {
  it('shows an experimental module under Experimental', async () => {
    mock([mod({ key: 'a', name: 'Experiment One' })]);
    render(<Labs />);

    expect(await screen.findByText('Experiment One')).toBeInTheDocument();
    expect(screen.getAllByText('Experimental').length).toBeGreaterThan(0);
  });

  it('keeps production modules off the page', async () => {
    mock([mod({ key: 'p', name: 'Production Thing', status: 'PRODUCTION' })]);
    render(<Labs />);

    // They are the product, not a lab.
    expect(await screen.findByText(/1 modules are in production/)).toBeInTheDocument();
    expect(screen.queryByText('Production Thing')).toBeNull();
  });

  it('shows the registry basis rather than page copy', async () => {
    mock([mod({ basis: 'no production consumer yet' })]);
    render(<Labs />);

    // A status without a stated reason is an assertion.
    expect(await screen.findByText('no production consumer yet')).toBeInTheDocument();
  });

  it('reports an unevaluated module as not yet measured', async () => {
    mock([mod({})]);
    render(<Labs />);

    expect(await screen.findByText(/not yet measured/i)).toBeInTheDocument();
  });

  it('never renders an unmeasured evaluation as a number', async () => {
    mock([mod({})]);
    const { container } = render(<Labs />);
    await screen.findByText(/not yet measured/i);

    expect(container.textContent).not.toMatch(/Evaluation:\s*0%/);
  });

  it('does not give experimental modules production styling', async () => {
    mock([mod({})]);
    const { container } = render(<Labs />);
    await screen.findByText('A Module');

    expect(container.querySelector('.status-badge--production')).toBeNull();
  });
});
