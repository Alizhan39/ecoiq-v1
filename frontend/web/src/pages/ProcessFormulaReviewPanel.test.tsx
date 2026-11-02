import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProcessFormulaReviewPanel from './ProcessFormulaReviewPanel';
import {
  getProcessFormulaContract, previewProcessFormulas,
} from '@/api/processFormulaReview';

vi.mock('@/api/processFormulaReview', () => ({
  getProcessFormulaContract: vi.fn(),
  previewProcessFormulas: vi.fn(),
}));

const CONTRACT = {
  project_slug: 'test-project',
  process_analysis_id: 12,
  case_id: 'PROCESS-12',
  domain: 'construction',
  process_name: 'Delivery',
  period: '2026-10',
  mode: 'process_formula_review' as const,
  production_approved: false as const,
  can_preview_calculate: true,
  source_measurements_stored_in_process_analysis: false as const,
  formulas: [{
    key: 'energy_intensity', title: 'Energy intensity', expression: 'total_energy / produced_units',
    output_unit: 'kWh/unit', required_inputs: [
      { key: 'total_energy', unit: 'kWh' }, { key: 'produced_units', unit: 'unit' },
    ],
    validation_status: 'PROVISIONAL_FORMULA_REQUIRES_DOMAIN_REVIEW',
    interpretation_limit: 'Only reported measurements', production_approved: false as const,
  }],
  parameters: [{
    key: 'total_energy', unit: 'kWh', used_by: ['energy_intensity'],
  }, {
    key: 'produced_units', unit: 'unit', used_by: ['energy_intensity', 'water_intensity', 'ghg_intensity'],
  }],
};

const REPORT = {
  project_slug: 'test-project', process_analysis_id: 12,
  case_id: 'PROCESS-12', domain: 'construction', process_name: 'Delivery',
  period: '2026-10', mode: 'process_formula_review' as const,
  production_approved: false as const, formula_count: 20 as const,
  all_formulas_visited: true as const, automated_publication: false as const,
  review_required: true as const, source_identifiers_verified: false as const,
  model_called: false as const,
  counts: { reported_not_verified: 1, needs_measurements: 19, blocked: 0 },
  results: [{
    sequence: 1, formula_key: 'energy_intensity', status: 'REPORTED_NOT_VERIFIED',
    value_decimal: '50', unit: 'kWh/unit', missing_inputs: [],
  }],
};

beforeEach(() => {
  vi.mocked(getProcessFormulaContract).mockReset().mockResolvedValue(CONTRACT);
  vi.mocked(previewProcessFormulas).mockReset().mockResolvedValue(REPORT);
});

describe('ProcessFormulaReviewPanel', () => {
  it('loads a saved process and does not treat missing numbers as zero', async () => {
    const user = userEvent.setup();
    const onReport = vi.fn();
    render(<ProcessFormulaReviewPanel projectSlug="test-project" onReport={onReport} />);
    await user.click(screen.getByRole('button', { name: 'Load process' }));
    expect(screen.getByRole('alert')).toHaveTextContent(/valid positive/i);
    await user.type(screen.getByLabelText('Saved process analysis ID'), '12');
    await user.click(screen.getByRole('button', { name: 'Load process' }));
    expect(await screen.findByText(/Delivery/)).toBeInTheDocument();
    expect(getProcessFormulaContract).toHaveBeenCalledWith('test-project', 12);
    await user.click(screen.getByRole('button', { name: /Evaluate all 20/i }));
    await waitFor(() => expect(previewProcessFormulas).toHaveBeenCalledWith(
      'test-project', 12, {},
    ));
    expect(await screen.findByText(/20-KPI process coverage/)).toBeInTheDocument();
    expect(onReport).toHaveBeenCalledWith(REPORT);
  });

  it('shares one parameter and blocks half-filled source entries', async () => {
    const user = userEvent.setup();
    render(<ProcessFormulaReviewPanel projectSlug="test-project" onReport={vi.fn()} />);
    await user.type(screen.getByLabelText('Saved process analysis ID'), '12');
    await user.click(screen.getByRole('button', { name: 'Load process' }));
    await screen.findByText(/Delivery/);
    await user.click(screen.getByText(/Enter measurements/));
    fireEvent.change(screen.getByLabelText(/total_energy \(kWh\)/), {
      target: { value: '500' },
    });
    await user.click(screen.getByRole('button', { name: /Evaluate all 20/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/both value and source/i);
    expect(previewProcessFormulas).not.toHaveBeenCalled();
    fireEvent.change(screen.getAllByLabelText('Source identifier')[0]!, {
      target: { value: 'meter-1' },
    });
    fireEvent.change(screen.getByLabelText(/produced_units \(unit\)/), {
      target: { value: '10' },
    });
    fireEvent.change(screen.getAllByLabelText('Source identifier')[1]!, {
      target: { value: 'log-2' },
    });
    await user.click(screen.getByRole('button', { name: /Evaluate all 20/i }));
    await waitFor(() => expect(previewProcessFormulas).toHaveBeenCalledWith(
      'test-project', 12, {
        total_energy: { value: '500', unit: 'kWh', source_ref: 'meter-1' },
        produced_units: { value: '10', unit: 'unit', source_ref: 'log-2' },
      },
    ));
  });

  it('does not let read-only viewers calculate', async () => {
    vi.mocked(getProcessFormulaContract).mockResolvedValue({
      ...CONTRACT, can_preview_calculate: false,
    });
    const user = userEvent.setup();
    render(<ProcessFormulaReviewPanel projectSlug="test-project" onReport={vi.fn()} />);
    await user.type(screen.getByLabelText('Saved process analysis ID'), '12');
    await user.click(screen.getByRole('button', { name: 'Load process' }));
    expect(await screen.findByRole('button', { name: /Evaluate all 20/i })).toBeDisabled();
  });
});
