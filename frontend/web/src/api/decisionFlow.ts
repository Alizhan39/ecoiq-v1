import { api } from './client';

/**
 * Backend-owned React Flow-shaped graph contract.
 *
 * This is the transport layer only: the interactive React Flow editor is NOT
 * installed yet. The server owns the order, access gate and review step.
 * Never infer workflow-execution capability from a rendered edge.
 */
export type DecisionNodeKind =
  | 'question'
  | 'access_check'
  | 'evidence_retrieval'
  | 'ai_gateway'
  | 'schema_validation'
  | 'human_review'
  | 'reviewed_result';

export interface DecisionFlowNode {
  id: string;
  type: 'default';
  position: { x: number; y: number };
  data: { kind: DecisionNodeKind; label: string; description: string };
}

export interface DecisionFlowEdge {
  id: string;
  source: string;
  target: string;
  type: 'smoothstep';
  animated: false;
}

export interface DecisionFlowPreview {
  mode: 'preview';
  execution_enabled: false;
  nodes: DecisionFlowNode[];
  edges: DecisionFlowEdge[];
}

/** Staff-only endpoint. A 403 is expected for ordinary users. */
export const getDecisionFlowPreview = (signal?: AbortSignal) =>
  api.get<DecisionFlowPreview>('/decision-flow/preview/', signal);
