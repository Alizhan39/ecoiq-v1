/**
 * narrative — the transition as content, independent of any drawing.
 *
 * This module imports nothing from the view layer and knows nothing about
 * SVG, canvas, coordinates or opacity. It produces the information the picture
 * conveys, so a reader who cannot see the picture is not reading a description
 * of it — they are reading the same source the picture is drawn from.
 *
 * That is the pattern EvidenceGraph already uses on the investigation page:
 * "the same graph, as content. Not a summary of the picture — the picture is a
 * rendering of this." The canvas may be aria-hidden precisely because this
 * exists.
 *
 * WHAT IT REFUSES TO SAY
 * ----------------------
 * No percentages. The state functions produce numbers in [0,1] that describe a
 * model, and rendering "82% heat recovered" beside an industrial diagram is
 * indistinguishable from a measurement. So the narrative reports a stage, what
 * physically changed at it, and the direction of the change — and where a
 * figure would go, it reports that no figure exists.
 */
import type { LossPoint } from '../domain/entities';
import { INTERVENTIONS, describeDelta } from '../domain/interventions';
import type { InterventionType } from '../domain/interventions';
import type { Scenario } from '../domain/scenario';
import { hasQuantifiedOutcome } from '../domain/scenario';
import { displayQuantity } from '../domain/unknown';
import { LOSSES } from '../model/plant';
import type { Stage, StageKey } from '../model/stages';
import { STAGES, stageAt, stageReached } from '../model/stages';

/** Which interventions belong to which narrative stage. */
const STAGE_INTERVENTIONS: Partial<Record<StageKey, InterventionType[]>> = {
  retrofit: ['VARIABLE_SPEED_DRIVE'],
  electrify: ['PROCESS_ELECTRIFICATION'],
  recover: ['HEAT_RECOVERY', 'STORAGE'],
  circularise: ['WATER_REUSE', 'MATERIAL_RECOVERY'],
  optimise: ['PROCESS_OPTIMISATION'],
};

export interface NarrativeStep {
  key: StageKey;
  label: string;
  meaning: string;
  /** Has the scroll reached this step? */
  reached: boolean;
  /** Is this the step the reader is currently in? */
  current: boolean;
  /** The physical changes this step makes, from the intervention deltas. */
  changes: string[];
  /** Losses this step addresses, by their conceptual category. */
  addresses: LossPoint[];
}

/**
 * The whole narrative at a given scroll position.
 *
 * Every step is always present — a reader is never shown a partial list,
 * because the argument is the sequence, not whichever part has scrolled into
 * view. `reached` and `current` say where they are in it.
 */
export function narrativeAt(progress: number): NarrativeStep[] {
  const here: Stage = stageAt(progress);
  return STAGES.map((stage) => {
    const types = STAGE_INTERVENTIONS[stage.key] ?? [];
    const changes = types.flatMap((t) => describeDelta(INTERVENTIONS[t].delta));
    const lossTypes = new Set(types.flatMap((t) => INTERVENTIONS[t].addresses));
    return {
      key: stage.key,
      label: stage.label,
      meaning: stage.meaning,
      reached: stageReached(progress, stage.key),
      current: stage.key === here.key,
      changes,
      addresses: LOSSES.filter((l) => lossTypes.has(l.type)),
    };
  });
}

/** What a diagnosis found, as content. Categories, never magnitudes. */
export interface LossSummary {
  label: string;
  category: string;
  /** Always "—" in the prototype. The slot exists; the number does not. */
  magnitude: string;
  /** Whether anything supports this loss being real. */
  evidenced: boolean;
}

export function lossSummaries(): LossSummary[] {
  return LOSSES.map((l) => ({
    label: l.label,
    category: l.type,
    magnitude: displayQuantity(l.magnitude),
    evidenced: l.evidenceIds.length > 0,
  }));
}

/**
 * A scenario as content, including what is NOT known about it.
 *
 * `quantified` is false for every scenario this prototype builds, and the
 * caller is expected to render the outcome section as unavailable rather than
 * as zeros. Returning the flag rather than hiding the section keeps the
 * absence visible: "not costed" is information, and omitting it silently would
 * let a reader assume it had been.
 */
export interface ScenarioSummary {
  id: string;
  label: string;
  interventions: { label: string; summary: string; changes: string[] }[];
  expected: { lossType: string; direction: string; rationale: string }[];
  quantified: boolean;
  outcomeNote: string;
  verification: string;
}

export function scenarioSummary(scenario: Scenario): ScenarioSummary {
  return {
    id: scenario.id,
    label: scenario.label,
    interventions: scenario.interventions.map((t) => ({
      label: INTERVENTIONS[t].label,
      summary: INTERVENTIONS[t].summary,
      changes: describeDelta(INTERVENTIONS[t].delta),
    })),
    expected: scenario.outcome.expected.map((e) => ({
      lossType: e.lossType,
      direction: e.direction,
      rationale: e.rationale,
    })),
    quantified: hasQuantifiedOutcome(scenario),
    outcomeNote: hasQuantifiedOutcome(scenario)
      ? 'Outcome figures are present.'
      : 'No capital cost, saving, payback or emissions figure exists for this '
        + 'scenario. EcoIQ holds no facility data behind this illustration, so '
        + 'these are unknown rather than zero.',
    verification: verificationSentence(scenario),
  };
}

function verificationSentence(scenario: Scenario): string {
  switch (scenario.outcome.verification.state) {
    case 'VERIFIED':
      return 'Measured after implementation, and the outcome matches what was expected.';
    case 'DIVERGED':
      return 'Measured after implementation, and the outcome differs from what was expected.';
    case 'AWAITING_MEASUREMENT':
      return 'Implemented. Measurement has not yet been collected.';
    case 'NOT_VERIFIED':
    default:
      return 'Not verified. Nothing has been implemented or measured — this is '
        + 'a description of a sequence, not a record of one that happened.';
  }
}

/**
 * The sentence that must accompany the illustration wherever it appears.
 *
 * Not optional, and not a footnote the caller may skip: the semantic layer
 * exports it so a page rendering the narrative has already imported the reason
 * the narrative is not a case study.
 */
export const NARRATIVE_DISCLAIMER =
  'This is an illustration of how an industrial modernisation sequence works. '
  + 'It describes no specific facility, contains no measured data, and asserts '
  + 'nothing about any organisation.';
