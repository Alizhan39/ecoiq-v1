import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import FormulaFlow from './FormulaFlow';
import { getFormulaFlow, previewFormulaSequence } from '@/api/formulaFlow';

vi.mock('@/api/formulaFlow', () => ({
  getFormulaFlow: vi.fn(),
  previewFormulaSequence: vi.fn(),
}));

vi.mock('@xyflow/react', () => ({
  ReactFlow: ({ nodes, onNodeClick }: {
    nodes: Array<{ id: string; data: { label: string } }>;
    onNodeClick: (event: unknown, node: { id: string }) => void;
  }) => (
    <div data-testid="reactflow">
      {nodes.map((node) => (
        <button key={node.id} onClick={() => onNodeClick(null, node)}>
          {node.data.label}
        </button>
      ))}
    </div>
  ),
  Controls: () => null,
  Background: () => null,
}));

const DATA = {
  project_slug: 'pilot',
  mode: 'candidate_preview' as const,
  execution_enabled: false as const,
  can_preview_calculate: true,
  formula_count: 2,
  formulas: [
    { key: 'revenue', title: 'Reported revenue', expression: 'reported_revenue',
      output_unit: 'GBP', required_inputs: [{ key: 'reported_revenue', unit: 'GBP' }],
      validation_status: 'PROVISIONAL_FORMULA_REQUIRES_DOMAIN_REVIEW',
      interpretation_limit: 'Source unverified', production_approved: false as const },
    { key: 'gross_margin', title: 'Gross margin',
      expression: '(revenue - cost_of_goods_sold) / revenue * 100', output_unit: '%',
      required_inputs: [{ key: 'revenue', unit: 'GBP' }, { key: 'cost_of_goods_sold', unit: 'GBP' }],
      validation_status: 'PROVISIONAL_FORMULA_REQUIRES_DOMAIN_REVIEW',
      interpretation_limit: 'Scope unverified', production_approved: false as const },
  ],
  nodes: [
    { id: 'revenue', type: 'default' as const, position: { x: 0, y: 0 },
      data: { key: 'revenue', label: 'Reported revenue', ordinal: 1,
        expression: 'reported_revenue', unit: 'GBP',
        validation_status: 'PROVISIONAL_FORMULA_REQUIRES_DOMAIN_REVIEW' } },
    { id: 'gross_margin', type: 'default' as const, position: { x: 290, y: 0 },
      data: { key: 'gross_margin', label: 'Gross margin', ordinal: 2,
        expression: '(revenue - cost_of_goods_sold) / revenue * 100', unit: '%',
        validation_status: 'PROVISIONAL_FORMULA_REQUIRES_DOMAIN_REVIEW' } },
  ],
  edges: [{ id: 'step_1', source: 'revenue', target: 'gross_margin',
    type: 'smoothstep' as const, animated: false as const }],
};

function page() {
  return render(<MemoryRouter initialEntries={['/business-os/formulas/pilot/flow']}>
    <Routes>
      <Route path="/business-os/formulas/:projectSlug/flow" element={<FormulaFlow />} />
    </Routes>
  </MemoryRouter>);
}

beforeEach(() => {
  vi.mocked(getFormulaFlow).mockReset().mockResolvedValue(DATA);
  vi.mocked(previewFormulaSequence).mockReset().mockResolvedValue({
    project_slug: 'pilot', period: '2026-10', mode: 'candidate_preview',
    execution_enabled: false, automated_publication: false,
    review_required: true, source_ids_verified: false, model_called: false,
    results: [
      { sequence: 1, formula_key: 'revenue', status: 'REPORTED_NOT_VERIFIED',
        value_decimal: '150.25', unit: 'GBP' },
      { sequence: 2, formula_key: 'gross_margin', status: 'NOT_SUPPLIED',
        value_decimal: null, unit: '%' },
    ],
  });
});

describe('project-scoped React Flow formula preview', () => {
  it('renders a text alternative, formula inputs and project-specific data', async () => {
    page();
    expect(await screen.findByTestId('reactflow')).toBeInTheDocument();
    expect(screen.getByText(/not independently verified/i)).toBeInTheDocument();
    expect(screen.getByLabelText('reported_revenue (GBP)')).toBeInTheDocument();
    expect(screen.getByText(/Accessible step-by-step list/)).toBeInTheDocument();
    expect(getFormulaFlow).toHaveBeenCalledWith('pilot', expect.anything());
  });

  it('prevents premature submissions and submits only typed source values', async () => {
    const user = userEvent.setup();
    page();
    await screen.findByTestId('reactflow');
    await user.click(screen.getByRole('button', { name: /run deterministic preview/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/reporting month/i);
    fireEvent.change(screen.getByLabelText(/Reporting period/), { target: { value: '2026-10' } });
    await user.type(screen.getByLabelText('reported_revenue (GBP)'), '150.25');
    await user.type(screen.getByLabelText('Source ID (unverified)'), 'source-1');
    await user.click(screen.getByRole('button', { name: /run deterministic preview/i }));
    await waitFor(() => expect(previewFormulaSequence).toHaveBeenCalledWith(
      'pilot', '2026-10',
      { revenue: { reported_revenue: { value: '150.25', source_ref: 'source-1' } } },
    ));
    expect(await screen.findByText(/Server-side preview/)).toBeInTheDocument();
    expect(screen.getByText('REPORTED_NOT_VERIFIED')).toBeInTheDocument();
  });

  it('prevents viewer-only accounts from running calculations', async () => {
    vi.mocked(getFormulaFlow).mockResolvedValue({
      ...DATA, can_preview_calculate: false,
    });
    page();
    const button = await screen.findByRole('button', { name: /run deterministic preview/i });
    expect(button).toBeDisabled();
    expect(screen.getByText(/role permits viewing/i)).toBeInTheDocument();
  });
});
