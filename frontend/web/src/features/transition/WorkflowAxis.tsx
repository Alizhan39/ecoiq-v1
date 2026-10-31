/**
 * WorkflowAxis — what EcoIQ does, beside what happens to the plant.
 *
 * TWO AXES, VISIBLY DIFFERENT
 * ---------------------------
 * The plant transformation and this workflow are not the same timeline, and
 * the layout has to say so. ENGINEER is drawn as a container holding the four
 * physical interventions; the other six stages hold nothing, because they have
 * no physical stage. A reader who takes this for a single seven-step sequence
 * has been misled by the design, not by the words.
 *
 * The active stage correlates with the plant — scroll into ELECTRIFY and
 * ENGINEER lights up — but correlation is all it is. SIMULATE, FINANCE and
 * EXECUTE never light up, because nothing in the drawing corresponds to them.
 *
 * STATUS IS NOT DECORATION
 * ------------------------
 * Every stage carries a status from platform_registry's vocabulary and the
 * basis it rests on. The basis is shown, not hidden behind a tooltip: a status
 * a reader cannot check is the thing this codebase keeps having to remove.
 */
import type { StageKey } from './model/stages';
import { STAGES } from './model/stages';
import {
  STATUS_MEANING, WORKFLOW, WORKFLOW_DISCLAIMER, type WorkflowStage,
} from './domain/capabilities';

export interface WorkflowAxisProps {
  /** The physical stage currently shown, so the active step can correlate. */
  physicalStage: StageKey;
  headingId?: string;
}

export function WorkflowAxis({
  physicalStage, headingId = 'itworkflow-heading',
}: WorkflowAxisProps) {
  return (
    <section className="itworkflow" aria-labelledby={headingId}>
      <h2 id={headingId}>How EcoIQ works</h2>
      <p className="itworkflow__lede">
        The sequence above is what happens to the plant. This is what EcoIQ
        does around it — a different axis, on a different timeline.
      </p>
      <p className="itworkflow__disclaimer">{WORKFLOW_DISCLAIMER}</p>

      <ol className="itworkflow__list">
        {WORKFLOW.map((stage) => (
          <WorkflowStep
            key={stage.key}
            stage={stage}
            active={stage.activeDuringPhysical.includes(physicalStage)}
            physicalStage={physicalStage}
          />
        ))}
      </ol>
    </section>
  );
}

function WorkflowStep({ stage, active, physicalStage }: {
  stage: WorkflowStage; active: boolean; physicalStage: StageKey;
}) {
  const contained = stage.containsPhysicalStages
    .map((key) => STAGES.find((s) => s.key === key)!)
    .filter(Boolean);

  return (
    <li
      className={[
        'itworkflow__step',
        `is-${stage.status.toLowerCase()}`,
        active ? 'is-active' : '',
      ].filter(Boolean).join(' ')}
      aria-current={active ? 'step' : undefined}
    >
      <div className="itworkflow__head">
        <h3>{stage.label}</h3>
        <span className={`itworkflow__status is-${stage.status.toLowerCase()}`}>
          {stage.status}
        </span>
      </div>
      <p className="itworkflow__summary">{stage.summary}</p>

      {contained.length > 0 ? (
        <div className="itworkflow__contains">
          <h4>Physical interventions inside this stage</h4>
          {/*
            Nested list, not siblings of the seven. These are classes of
            physical change that all happen within ENGINEER — rendering them
            at the same level would recreate the single-sequence error the
            whole two-axis layout exists to avoid.
          */}
          <ul>
            {contained.map((s) => (
              <li
                key={s.key}
                className={s.key === physicalStage ? 'is-current' : ''}
                aria-current={s.key === physicalStage ? 'true' : undefined}
              >
                {s.label}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <details className="itworkflow__basis">
        <summary>{STATUS_MEANING[stage.status]}</summary>
        <p>{stage.basis}</p>
      </details>
    </li>
  );
}
