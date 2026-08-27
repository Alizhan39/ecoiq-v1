import { PipelineCanvas } from './PipelineCanvas';

/**
 * How EcoIQ works — the pipeline that actually runs.
 *
 * The six stages below are implemented end to end. The wider loop is shown
 * separately and labelled as direction, because presenting an unimplemented
 * stage beside an implemented one in the same styling is how a roadmap becomes
 * a claim.
 */
const PIPELINE = [
  { step: 'Evidence', detail: 'A source, and what it supports.' },
  { step: 'Assessment', detail: 'Material inputs, scored.' },
  { step: 'Provenance', detail: 'Where each value came from, recorded.' },
  { step: 'Coverage', detail: 'How much of the assessment is supported.' },
  { step: 'Confidence', detail: 'How good that support is.' },
  { step: 'Decision', detail: 'Published only when the evidence carries it.' },
] as const;

/** Stages the platform is being built toward. Not running today. */
const DIRECTION = [
  'Observe', 'Understand', 'Generate', 'Simulate', 'Optimise',
  'Finance', 'Execute', 'Verify', 'Measure', 'Learn',
] as const;

export function HowItWorks() {
  return (
    <section aria-labelledby="how">
      <h2 id="how">How it works</h2>

      {/*
        The list is the primary and the canvas is decoration behind it: every
        stage drawn is an <li> here, so a screen reader, a crawler and anyone
        with JavaScript off lose nothing. See PipelineCanvas for why the
        drawing stops most of its particles short of Decision.
      */}
      <div className="pipeline-wrap">
        <PipelineCanvas stages={PIPELINE.length} />
        <ol className="pipeline">
          {PIPELINE.map((stage) => (
            <li key={stage.step}>
              <strong>{stage.step}</strong>
              <span>{stage.detail}</span>
            </li>
          ))}
        </ol>
      </div>
      <p className="pipeline__note">
        Most evidence does not carry a publishable conclusion. That is the
        normal outcome, not a failure of the pipeline.
      </p>

      <div className="direction">
        <h3>
          Where the platform is going{' '}
          <span className="status-badge status-badge--experimental">
            In development
          </span>
        </h3>
        <p className="prose">
          EcoIQ is being built toward a full decision-to-impact loop across
          physical systems. These stages are <strong>not running today</strong>;
          the six above are.
        </p>
        <p className="direction__stages">{DIRECTION.join(' · ')}</p>
      </div>
    </section>
  );
}
