import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import Principles from './Principles';
import PrincipleDetail from './PrincipleDetail';

const REGISTRY = {
  total: 114,
  categories: [
    { key: 'governance', label: 'Governance & Leadership', principle_count: 2 },
    { key: 'earth', label: 'Stewardship of Earth & Resources', principle_count: 1 },
  ],
  principles: [
    {
      kpi_id: 1, title: 'Guidance & Purpose', category: 'governance',
      tagline: 'Does this organisation know where it is going?',
      question: 'Is there a clear, accountable purpose statement?',
      metrics: ['mission alignment score'], principle_statement: 'Organisations without purpose drift.',
    },
    {
      kpi_id: 36, title: 'Core Commitment', category: 'governance',
      tagline: 'What is the irreducible core commitment?',
      question: 'Is there an explicit, binding commitment?',
      metrics: [], principle_statement: '',
    },
    {
      kpi_id: 57, title: 'Iron & Infrastructure Responsibility', category: 'earth',
      tagline: 'Is infrastructure built responsibly?',
      question: 'Are infrastructure decisions accountable?',
      metrics: ['asset lifecycle disclosure'], principle_statement: '',
    },
  ],
};

function mock(payload: unknown = REGISTRY) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true, status: 200, json: async () => payload,
  }));
}

function showList() {
  return render(<MemoryRouter><Principles /></MemoryRouter>);
}

function showDetail(id: string) {
  return render(
    <MemoryRouter initialEntries={[`/principles/${id}`]}>
      <Routes>
        <Route path="/principles/:kpiId" element={<PrincipleDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => vi.unstubAllGlobals());

describe('the principle registry', () => {
  it('leads with the question, not the title alone', async () => {
    mock();
    showList();
    expect(await screen.findByText('Is there a clear, accountable purpose statement?'))
      .toBeInTheDocument();
  });

  it('groups principles by their canonical domain', async () => {
    mock();
    showList();
    expect(await screen.findByRole('heading', { name: /Governance & Leadership/ }))
      .toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Stewardship of Earth/ }))
      .toBeInTheDocument();
  });

  it('filters to one domain without hiding the total', async () => {
    mock();
    showList();
    await screen.findByText('Guidance & Purpose');
    await userEvent.click(screen.getByRole('button', { name: /Governance & Leadership/ }));
    expect(screen.queryByRole('heading', { name: /Stewardship of Earth/ }))
      .not.toBeInTheDocument();
    expect(screen.getByText('Guidance & Purpose')).toBeInTheDocument();
  });

  it('carries no organisation, evidence or verdict', async () => {
    /**
     * This page describes the method. A framework page that quietly showed how
     * organisations scored would be a league table in methodology clothing.
     */
    mock();
    const { container } = showList();
    await screen.findByText('Guidance & Purpose');
    expect(container.textContent).not.toMatch(/verdict|confirmed evidence|score of/i);
  });

  it('links each principle to its own page', async () => {
    mock();
    showList();
    const link = await screen.findByRole('link', { name: /Read principle 57/i });
    expect(link).toHaveAttribute('href', '/principles/57/');
  });
});

describe('a single principle', () => {
  it('shows the question as the headline claim', async () => {
    mock();
    showDetail('1');
    expect(await screen.findByRole('heading', { name: /Guidance & Purpose/ }))
      .toBeInTheDocument();
    expect(screen.getByText('Is there a clear, accountable purpose statement?'))
      .toBeInTheDocument();
  });

  it('says indicators are not a checklist', async () => {
    mock();
    showDetail('1');
    expect(await screen.findByText(/not a checklist, and not a score/i))
      .toBeInTheDocument();
  });

  it('omits the indicators section when there are none', async () => {
    mock();
    showDetail('36');
    await screen.findByRole('heading', { name: /Core Commitment/ });
    expect(screen.queryByRole('heading', { name: 'Indicators' }))
      .not.toBeInTheDocument();
  });

  it('says a principle does not exist rather than rendering an empty one', async () => {
    /**
     * An id outside 1-114 is not a principle awaiting evidence. A page that
     * looked merely unassessed would misstate the size of the framework.
     */
    mock();
    showDetail('999');
    expect(await screen.findByRole('heading', { name: /No such principle/i }))
      .toBeInTheDocument();
  });

  it('shows no organisation standing', async () => {
    /**
     * Asserted on the absence of an organisation and of counted evidence, not
     * on the words "supports" or "conflicts": the page explains what those
     * mean, and a substring search would fail on the framework's own
     * vocabulary being defined.
     */
    mock();
    const { container } = showDetail('1');
    await screen.findByRole('heading', { name: /Guidance & Purpose/ });
    const text = container.textContent ?? '';
    expect(text).not.toMatch(/\bAcme\b|\bApple\b|Organisations assessed/i);
    expect(text).not.toMatch(/\d+ confirmed|\d+ of 114|assessed for this/i);
  });
});
