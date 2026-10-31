import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Home from './Home';

function mockStats(counters: unknown[]) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true, status: 200,
    json: async () => ({ counters, modules: [] }),
  }));
}

const counter = (key: string, value: number | null, is_proof = true) => ({
  key, label: key, value, derivation: 'derived', is_proof,
});

function renderHome() {
  return render(<MemoryRouter><Home /></MemoryRouter>);
}

beforeEach(() => {
  vi.restoreAllMocks();
  mockStats([]);
});

describe('positioning', () => {
  it('leads with current capability, not future capability', async () => {
    renderHome();

    expect(screen.getByRole('heading', { level: 1 }).textContent)
      .toMatch(/evidence you can inspect/i);
  });

  it('separates what it does today from where it is going', async () => {
    renderHome();

    expect(screen.getByText(/Today\s+the platform does the part below/i))
      .toBeInTheDocument();
  });

  it('does not claim system optimisation is live', async () => {
    const { container } = renderHome();
    const text = container.textContent ?? '';

    expect(text).not.toMatch(/real-time optimisation/i);
    expect(text).not.toMatch(/enterprise[- ]ready/i);
    expect(text).not.toMatch(/agents working continuously/i);
  });
});

describe('unsupported proof is never invented', () => {
  it('omits a proof counter that is zero', async () => {
    mockStats([counter('companies_published', 0)]);
    renderHome();

    // "0 published assessments" is accurate and proves nothing.
    expect(await screen.findByRole('heading', { name: /what sits behind/i }))
      .toBeInTheDocument();
    expect(screen.queryByText('0')).toBeNull();
  });

  it('omits a proof counter that is null', async () => {
    mockStats([counter('projects_verified', null)]);
    renderHome();

    expect(screen.queryByText('—')).toBeNull();
  });

  it('shows a proof counter that is real', async () => {
    mockStats([counter('companies_published', 12)]);
    renderHome();

    expect(await screen.findByText('12')).toBeInTheDocument();
  });

  it('never shows a non-proof counter', async () => {
    mockStats([counter('companies_total', 467, false)]);
    renderHome();

    // A row count is not proof of anything about the product.
    expect(screen.queryByText('467')).toBeNull();
  });

  it('shows the derivation beside a figure it does show', async () => {
    mockStats([counter('evidenced_metrics', 340)]);
    renderHome();

    expect(await screen.findByText('derived')).toBeInTheDocument();
  });
});

describe('the forbidden claims', () => {
  it('never states an agent count', async () => {
    const { container } = renderHome();

    expect(container.textContent).not.toMatch(/33 (operational )?agents/i);
  });

  it('never states an analysed-company count', async () => {
    const { container } = renderHome();

    expect(container.textContent).not.toMatch(/\d+ analysed companies/i);
  });
});

describe('how it works', () => {
  it('shows the six stages that actually run', async () => {
    renderHome();

    for (const stage of ['Evidence', 'Assessment', 'Provenance', 'Coverage',
                         'Confidence', 'Decision']) {
      expect(screen.getAllByText(stage).length).toBeGreaterThan(0);
    }
  });

  it('marks the wider loop as not running today', async () => {
    renderHome();

    expect(screen.getByText(/not running today/i)).toBeInTheDocument();
  });

  it('labels the direction section as in development', async () => {
    renderHome();

    expect(screen.getByText('In development')).toBeInTheDocument();
  });
});

describe('system verticals', () => {
  it('lists the four directions', async () => {
    renderHome();

    for (const name of ['Energy', 'Transport & Aviation', 'Cities & Buildings',
                        'Nature & Resources']) {
      expect(screen.getByText(new RegExp(name.replace('&', '&')))).toBeInTheDocument();
    }
  });

  it('marks every vertical as planned', async () => {
    renderHome();

    expect(screen.getAllByText('Planned')).toHaveLength(4);
  });

  it('offers no analyse affordance for an unbuilt vertical', async () => {
    renderHome();

    // A button that cannot do the thing it names is worse than no button.
    expect(screen.queryByRole('button', { name: /analyse/i })).toBeNull();
    expect(screen.queryByRole('link', { name: /analyse energy/i })).toBeNull();
  });

  it('says they are not available yet', async () => {
    renderHome();

    expect(screen.getByText(/Not available yet/i)).toBeInTheDocument();
  });
});

describe('pathways', () => {
  it('points at the real product surfaces', async () => {
    renderHome();

    expect(screen.getByRole('link', { name: /company & investment/i }))
      .toHaveAttribute('href', '/intelligence');
    expect(screen.getByRole('link', { name: 'Projects' }))
      .toHaveAttribute('href', '/projects');
  });
});
