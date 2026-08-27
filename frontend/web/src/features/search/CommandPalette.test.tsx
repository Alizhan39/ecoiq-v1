import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CommandPalette } from './CommandPalette';

vi.mock('@/api/principles', () => ({ fetchPrincipleRegistry: vi.fn() }));
vi.mock('@/api/companies', () => ({ listCompanies: vi.fn() }));
import { listCompanies } from '@/api/companies';
import { fetchPrincipleRegistry } from '@/api/principles';

const REGISTRY = {
  total: 114,
  categories: [],
  principles: [
    {
      kpi_id: 57, title: 'Iron & Infrastructure Responsibility', category: 'earth',
      tagline: 't', question: 'Does infrastructure investment account for impact?',
      metrics: [], principle_statement: '',
    },
    {
      kpi_id: 114, title: 'Consumer Protection & Anti-Manipulation', category: 'social',
      tagline: 't', question: 'Does it protect informed choice?',
      metrics: [], principle_statement: '',
    },
  ],
};

const COMPANIES = {
  count: 1, next: null, previous: null,
  results: [{
    slug: 'walmart', name: 'Walmart', sector: 'retail', country: 'United States',
    is_public: true, verified: false, ecoiq_score: null, score_status: 'INSUFFICIENT_EVIDENCE',
  }],
};

function show() {
  vi.mocked(fetchPrincipleRegistry).mockResolvedValue(REGISTRY as never);
  vi.mocked(listCompanies).mockResolvedValue(COMPANIES as never);
  return render(<MemoryRouter><CommandPalette /></MemoryRouter>);
}

async function open() {
  await userEvent.keyboard('{Control>}k{/Control}');
  return screen.findByRole('dialog', { name: /Search EcoIQ/i });
}

beforeEach(() => vi.clearAllMocks());

describe('the command palette', () => {
  it('is closed until asked for', () => {
    show();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('opens on ctrl+k and takes focus', async () => {
    show();
    await open();
    expect(screen.getByRole('combobox')).toHaveFocus();
  });

  it('closes on escape', async () => {
    show();
    await open();
    await userEvent.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('finds a principle by title', async () => {
    show();
    await open();
    await userEvent.type(screen.getByRole('combobox'), 'infrastructure');
    expect(await screen.findByText(/#57 Iron & Infrastructure Responsibility/))
      .toBeInTheDocument();
  });

  it('does not match mid-word', async () => {
    /**
     * Found in browser verification: searching "iron" returned #51 Scattering
     * Winds above #57 Iron & Infrastructure, because its question contains
     * "env-iron-mental". Anchoring to a word boundary keeps "steward" ->
     * "stewardship" working without that noise.
     */
    show();
    await open();
    await userEvent.type(screen.getByRole('combobox'), 'iron');
    const options = await screen.findAllByRole('option');
    expect(options).toHaveLength(1);
    expect(options[0]).toHaveTextContent(/#57 Iron & Infrastructure/);
  });

  it('still matches the start of a longer word', async () => {
    show();
    await open();
    await userEvent.type(screen.getByRole('combobox'), 'manipul');
    expect(await screen.findByText(/#114 Consumer Protection/)).toBeInTheDocument();
  });

  it('finds a principle by its number', async () => {
    show();
    await open();
    await userEvent.type(screen.getByRole('combobox'), '114');
    expect(await screen.findByText(/#114 Consumer Protection/)).toBeInTheDocument();
  });

  it('finds an organisation through the server, debounced', async () => {
    show();
    await open();
    await userEvent.type(screen.getByRole('combobox'), 'walmart');
    expect(await screen.findByText('Walmart')).toBeInTheDocument();
    await waitFor(() => expect(listCompanies).toHaveBeenCalled());
  });

  it('never shows a score beside an organisation', async () => {
    /**
     * The directory withholds the composite for most organisations. A palette
     * is not the place to leak what the page itself will not show.
     */
    show();
    await open();
    await userEvent.type(screen.getByRole('combobox'), 'walmart');
    await screen.findByText('Walmart');
    const option = screen.getByRole('option', { name: /Walmart/ });
    expect(option.textContent).not.toMatch(/\d+\s*\/\s*100|score/i);
  });

  it('says plainly when nothing matches', async () => {
    vi.mocked(fetchPrincipleRegistry).mockResolvedValue(REGISTRY as never);
    vi.mocked(listCompanies).mockResolvedValue(
      { count: 0, next: null, previous: null, results: [] } as never);
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);
    await open();
    await userEvent.type(screen.getByRole('combobox'), 'zzzznothing');
    expect(await screen.findByText(/Nothing matches/i)).toBeInTheDocument();
  });

  it('says what it does not search, and why', async () => {
    vi.mocked(fetchPrincipleRegistry).mockResolvedValue(REGISTRY as never);
    vi.mocked(listCompanies).mockResolvedValue(
      { count: 0, next: null, previous: null, results: [] } as never);
    render(<MemoryRouter><CommandPalette /></MemoryRouter>);
    await open();
    await userEvent.type(screen.getByRole('combobox'), 'zzzznothing');
    expect(await screen.findByText(/not evidence or findings/i)).toBeInTheDocument();
  });

  it('is navigable by keyboard alone', async () => {
    show();
    await open();
    await userEvent.type(screen.getByRole('combobox'), 'a');
    await screen.findByRole('option', { name: /Iron & Infrastructure/ });
    const first = screen.getAllByRole('option')[0];
    expect(first).toHaveAttribute('aria-selected', 'true');
    await userEvent.keyboard('{ArrowDown}');
    expect(screen.getAllByRole('option')[1]).toHaveAttribute('aria-selected', 'true');
  });

  it('points the combobox at the active option for a screen reader', async () => {
    show();
    await open();
    await userEvent.type(screen.getByRole('combobox'), 'infrastructure');
    await screen.findByRole('option', { name: /Iron & Infrastructure/ });
    expect(screen.getByRole('combobox'))
      .toHaveAttribute('aria-activedescendant', 'palette-principle-57');
  });
});
