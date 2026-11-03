import { api } from './client';
import type { FormulaCandidate, FormulaResult } from './formulaFlow';

export interface ProcessFormulaParameter {
  key: string;
  unit: string;
  used_by: string[];
}

export interface ProcessFormulaContext {
  project_slug: string;
  process_analysis_id: number;
  case_id: string;
  domain: string;
  process_name: string;
  period: string;
  mode: 'process_formula_review';
  production_approved: false;
}

export interface ProcessFormulaContract extends ProcessFormulaContext {
  formulas: FormulaCandidate[];
  parameters: ProcessFormulaParameter[];
  can_preview_calculate: boolean;
  source_measurements_stored_in_process_analysis: false;
}

export interface ProcessFormulaResult extends FormulaResult {
  missing_inputs: string[];
}

export interface ProcessFormulaReport extends ProcessFormulaContext {
  formula_count: 20;
  all_formulas_visited: true;
  counts: {
    reported_not_verified: number;
    needs_measurements: number;
    blocked: number;
  };
  results: ProcessFormulaResult[];
  automated_publication: false;
  review_required: true;
  source_identifiers_verified: false;
  model_called: false;
}

export type ProcessMeasure = {
  value: string;
  unit: string;
  source_ref: string;
};

const path = (slug: string, runId: number) =>
  `/projects/${encodeURIComponent(slug)}/process-analyses/${runId}/formula-review/`;

export const getProcessFormulaContract = (slug: string, runId: number) =>
  api.get<ProcessFormulaContract>(path(slug, runId));

export const previewProcessFormulas = (
  slug: string, runId: number, measurements: Record<string, ProcessMeasure>,
) => api.post<ProcessFormulaReport>(path(slug, runId), { measurements });
