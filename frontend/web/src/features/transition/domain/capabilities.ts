/**
 * capabilities — what EcoIQ actually does around a physical system, and how
 * much of each part exists today.
 *
 * TWO AXES, NOT ONE
 * -----------------
 * The plant transformation (LEGACY → … → VERIFY) and this workflow are
 * different questions on different timelines. RETROFIT, ELECTRIFY, RECOVER and
 * CIRCULARISE are classes of physical intervention that all sit INSIDE
 * ENGINEER; SIMULATE, FINANCE and EXECUTE have no physical stage at all.
 * Flattening them into one list would misdescribe both — which is why
 * `containsPhysicalStages` exists rather than the two sequences being merged.
 *
 * THE VOCABULARY IS NOT NEW
 * -------------------------
 * `CapabilityStatus` mirrors platform_registry/agents.py exactly: PRODUCTION,
 * BETA, EXPERIMENTAL, PLANNED, SPECIFICATION. That module's rule applies here
 * too — "a status without a stated basis is an assertion" — so `basis` is
 * required on every stage and says what the status rests on.
 *
 * The mirroring is enforced across the language boundary by
 * `api/tests_capability_vocabulary.py`, which parses this file. Two lists of
 * status names in two languages is exactly how they drift, and this codebase
 * has already paid for that once with six stale copies of a visibility rule.
 */
import type { StageKey } from '../model/stages';

/** Mirrors platform_registry.agents. Do not add a value that is not there. */
export type CapabilityStatus =
  | 'PRODUCTION'
  | 'BETA'
  | 'EXPERIMENTAL'
  | 'PLANNED'
  | 'SPECIFICATION';

/** What a reader is told each status means, in the registry's own terms. */
export const STATUS_MEANING: Record<CapabilityStatus, string> = {
  PRODUCTION: 'Runs today on the live evidence path.',
  BETA: 'Runs today, with a narrower basis than production.',
  EXPERIMENTAL: 'Built and deterministic, but not on a production path and '
    + 'not fed by real facility data.',
  PLANNED: 'The architecture accepts it. Nothing runs yet.',
  SPECIFICATION: 'Described, and not built.',
};

export type WorkflowKey =
  | 'diagnose' | 'engineer' | 'simulate' | 'optimise'
  | 'finance' | 'execute' | 'verify';

export interface WorkflowStage {
  key: WorkflowKey;
  label: string;
  /** What EcoIQ does at this stage, for a reader. */
  summary: string;
  status: CapabilityStatus;
  /**
   * Why that status. Required, and deliberately specific: "not yet live" is a
   * mood, "every economic slot is null and no facility has been surveyed" is a
   * fact a reader can check.
   */
  basis: string;
  /**
   * Physical stages this workflow step covers. Only ENGINEER has any — the
   * containment is the whole reason the two axes are separate.
   */
  containsPhysicalStages: StageKey[];
  /** Physical stages during which this step is the active one. */
  activeDuringPhysical: StageKey[];
}

export const WORKFLOW: readonly WorkflowStage[] = [
  {
    key: 'diagnose',
    label: 'Diagnose',
    summary:
      'Map the system and identify where energy, heat, water and material are '
      + 'lost, and which losses are worth acting on.',
    status: 'EXPERIMENTAL',
    basis:
      'The loss model is built and deterministic — seven loss categories, each '
      + 'locatable on a piece of equipment or a flow. It is not fed by facility '
      + 'data: every magnitude in the model is null, because naming a loss is '
      + 'not the same as having measured one.',
    containsPhysicalStages: [],
    activeDuringPhysical: ['legacy', 'diagnose'],
  },
  {
    key: 'engineer',
    label: 'Engineer',
    summary:
      'Structure the interventions that change the plant: what equipment is '
      + 'replaced, what routes are removed, and which loops close.',
    status: 'EXPERIMENTAL',
    basis:
      'Nine intervention types, each carrying an explicit topology change '
      + 'rather than a label — the catalogue refuses an intervention that '
      + 'adds and removes nothing. Deterministic and tested. Not applied to '
      + 'any real plant.',
    containsPhysicalStages: ['retrofit', 'electrify', 'recover', 'circularise'],
    activeDuringPhysical: ['retrofit', 'electrify', 'recover', 'circularise'],
  },
  {
    key: 'simulate',
    label: 'Simulate',
    summary:
      'Compare intervention scenarios against each other before committing to '
      + 'one.',
    status: 'PLANNED',
    basis:
      'The scenario model exists and can hold several sets of interventions '
      + 'with their assumptions. Nothing simulates: comparing scenarios needs '
      + 'quantities, and every quantity in the model is unknown until a '
      + 'facility is surveyed.',
    containsPhysicalStages: [],
    activeDuringPhysical: [],
  },
  {
    key: 'optimise',
    label: 'Optimise',
    summary:
      'Select a technically and economically defensible pathway, and '
      + 'coordinate the system that results.',
    status: 'PLANNED',
    basis:
      'Selecting between pathways requires costs and measured outcomes to '
      + 'select on. Neither exists, so nothing here ranks anything — and a '
      + 'ranking built from defaults would be worse than no ranking.',
    containsPhysicalStages: [],
    activeDuringPhysical: ['optimise'],
  },
  {
    key: 'finance',
    label: 'Finance',
    summary:
      'Capital cost, operating saving, payback and funding route for the '
      + 'chosen pathway.',
    status: 'PLANNED',
    basis:
      'Every economic field — capex, opex before and after, annual saving, '
      + 'payback, NPV, IRR — exists in the model and every one of them is '
      + 'null. EcoIQ has costed nothing.',
    containsPhysicalStages: [],
    activeDuringPhysical: [],
  },
  {
    key: 'execute',
    label: 'Execute',
    summary:
      'Deliver the work: procurement, staging, commissioning, and the '
      + 'partners who do it.',
    status: 'SPECIFICATION',
    basis:
      'Described, and not built. Execution needs a real project and delivery '
      + 'partners; EcoIQ has neither, and no part of this exists in code.',
    containsPhysicalStages: [],
    activeDuringPhysical: [],
  },
  {
    key: 'verify',
    label: 'Verify',
    summary:
      'Measure what actually changed and compare it with what the scenario '
      + 'expected — including when it does not match.',
    status: 'SPECIFICATION',
    basis:
      'The verification states exist in the model, including DIVERGED, so a '
      + 'result that contradicts the expectation is sayable. Nothing can reach '
      + 'VERIFIED without metered data from a real facility, and there is none.',
    containsPhysicalStages: [],
    activeDuringPhysical: ['verify'],
  },
] as const;

/** The workflow stage a given physical stage sits under, if any. */
export function workflowForPhysical(stage: StageKey): WorkflowStage | undefined {
  return WORKFLOW.find((w) => w.activeDuringPhysical.includes(stage));
}

/**
 * Whether any stage may be described to a reader as something EcoIQ does now.
 *
 * False for every stage today. Exported so a caller that wants to write "we
 * do this" has to ask, and gets told no.
 */
export function isLiveCapability(stage: WorkflowStage): boolean {
  return stage.status === 'PRODUCTION' || stage.status === 'BETA';
}

/** The sentence the workflow section carries, because none of it is live. */
export const WORKFLOW_DISCLAIMER =
  'None of these stages runs against a real facility today. The statuses are '
  + 'the same ones the platform registry uses for every other module, and each '
  + 'one says what it rests on.';
