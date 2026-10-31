/**
 * TransitionNarrative — the modernisation sequence as accessible content.
 *
 * WHY THIS IS NOT A CAPTION
 * -------------------------
 * The industrial scene is no longer decoration. It carries the primary product
 * explanation, so the information it conveys has to exist outside the canvas —
 * not summarised for a screen reader, but present as content, from the same
 * source the drawing renders.
 *
 * That is the pattern EvidenceGraph established on the investigation page: the
 * SVG is aria-hidden precisely BECAUSE a real list of the same facts sits
 * beside it. A reader who cannot see the picture is not told what the picture
 * looks like; they are given the thing it depicts.
 *
 * It renders every step at every scroll position, marking which have been
 * reached, because the argument is the sequence. Revealing steps as they
 * scroll would make the reading order depend on the scroll position, and a
 * screen-reader user does not scroll to read.
 */
import type { NarrativeStep } from './narrative';
import {
  NARRATIVE_DISCLAIMER, lossSummaries, narrativeAt, scenarioSummary,
} from './narrative';
import { FULL_MODERNISATION } from '../model/plant';

export interface TransitionNarrativeProps {
  /** Scroll progress, 0 to 1. Clamped downstream. */
  progress: number;
  /** Heading id, so a wrapping section can be labelled by it. */
  headingId?: string;
}

export function TransitionNarrative({
  progress, headingId = 'industrial-transition-heading',
}: TransitionNarrativeProps) {
  const steps = narrativeAt(progress);
  const losses = lossSummaries();
  const scenario = scenarioSummary(FULL_MODERNISATION);

  return (
    <section className="transition-narrative" aria-labelledby={headingId}>
      <h2 id={headingId}>Industrial modernisation, step by step</h2>

      {/*
        First, not last. A reader meets the disclaimer before the content it
        qualifies, rather than discovering after the fact that none of it
        describes a real plant.
      */}
      <p className="transition-narrative__disclaimer">{NARRATIVE_DISCLAIMER}</p>

      <ol className="transition-narrative__steps">
        {steps.map((step) => (
          <NarrativeStepItem key={step.key} step={step} />
        ))}
      </ol>

      <h3>What a diagnosis looks for</h3>
      {/*
        Its own scroll container. Four columns do not fit a 390px viewport, and
        a table that widens the PAGE makes every other element on it scroll
        sideways too. Wide content scrolls inside itself.
      */}
      <div className="transition-narrative__scroll">
      <table className="transition-narrative__losses">
        <caption>
          Loss categories, and what EcoIQ holds about each. Every magnitude is
          unknown: naming a loss is not the same as having measured it.
        </caption>
        <thead>
          <tr>
            <th scope="col">Loss</th>
            <th scope="col">Category</th>
            <th scope="col">Magnitude</th>
            <th scope="col">Evidence</th>
          </tr>
        </thead>
        <tbody>
          {losses.map((loss) => (
            <tr key={loss.label}>
              <th scope="row">{loss.label}</th>
              <td>{loss.category}</td>
              <td>{loss.magnitude}</td>
              <td>{loss.evidenced ? 'Recorded' : 'None recorded'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>

      <h3>Outcome</h3>
      <p>{scenario.outcomeNote}</p>
      <p>{scenario.verification}</p>
    </section>
  );
}

function NarrativeStepItem({ step }: { step: NarrativeStep }) {
  return (
    <li
      className={[
        'transition-narrative__step',
        step.reached ? 'is-reached' : '',
        step.current ? 'is-current' : '',
      ].filter(Boolean).join(' ')}
      // Marks the step a sighted reader is looking at, without hiding the
      // others from anyone.
      aria-current={step.current ? 'step' : undefined}
    >
      <h3>{step.label}</h3>
      <p>{step.meaning}</p>

      {step.changes.length > 0 ? (
        <>
          <h4>What changes physically</h4>
          <ul>
            {step.changes.map((change) => <li key={change}>{change}</li>)}
          </ul>
        </>
      ) : null}

      {step.addresses.length > 0 ? (
        <>
          <h4>Losses this addresses</h4>
          <ul>
            {step.addresses.map((loss) => (
              <li key={loss.id}>{loss.label}</li>
            ))}
          </ul>
        </>
      ) : null}
    </li>
  );
}
