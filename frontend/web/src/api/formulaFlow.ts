import { api } from './client';

export interface FormulaInput {
  key: string;
  unit: string;
}
export interface FormulaCandidate {
  key: string;
  title: string;
  expression: string;
  output_unit: string;
  required_inputs: FormulaInput[];
  validation_status: string;
  interpretation_limit: string;
  production_approved: false;
}
export interface FormulaGraphNode {
  id: string;
  type: 'default';
  position: { x: number; y: number };
  data: {
    key: string;
    label: string;
    ordinal: number;
    expression: string;
    unit: string;
    validation_status: string;
  };
}
export interface FormulaGraphEdge {
  id: string;
  source: string;
  target: string;
  type: 'smoothstep';
  animated: false;
}
export interface FormulaFlow {
  project_slug: string;
  mode: 'candidate_preview';
  execution_enabled: false;
  formula_count: number;
  formulas: FormulaCandidate[];
  nodes: FormulaGraphNode[];
  edges: FormulaGraphEdge[];
}
export interface ObservationInput {
  value: string | null;
  source_ref: string;
}
export type FormulaObservations = Record<string, Record<string, ObservationInput>>;
export interface FormulaResult {
  sequence: number;
  formula_key: string;
  status: string;
  value_decimal: string | null;
  unit: string;
  expression?: string;
  period?: string;
  source_identifiers?: string[];
  review_status?: string;
  interpretation_limit?: string;
  verified_evidence?: false;
  independently_verified?: false;
  approved_for_implementation?: false;
}
export interface FormulaRun {
  project_slug: string;
  period: string;
  mode: 'candidate_preview';
  execution_enabled: false;
  automated_publication: false;
  review_required: true;
  source_ids_verified: false;
  model_called: false;
  results: FormulaResult[];
}

// All API calls go through the existing single same-origin/CSRF client.
const endpoint = (slug: string) =>
  `/projects/${encodeURIComponent(slug)}/formulas/flow/`;

export const getFormulaFlow = (slug: string, signal?: AbortSignal) =>
  api.get<FormulaFlow>(endpoint(slug), signal);

export const previewFormulaSequence = (
  slug: string, period: string, observations: FormulaObservations,
) => api.post<FormulaRun>(endpoint(slug), { period, observations });
