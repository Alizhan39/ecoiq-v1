import { useState } from 'react';
import { APPROVAL_ACTIONS, LEISURE_CENTRE_RECOMMENDATION } from './demoData';

/**
 * The decision gate.
 *
 * WHAT THESE BUTTONS DO, AND WHAT THEY MUST NOT LOOK LIKE THEY DO
 * ---------------------------------------------------------------
 * They set a piece of local state and describe what the choice would mean.
 * They submit nothing, reach no API and change no record — this page is a
 * demonstration and has no borough to write to.
 *
 * That could have been left implicit and it deliberately is not: a
 * demonstration whose Approve button looks like it approved something teaches
 * a buyer that EcoIQ acts on its own recommendations, which is the exact
 * opposite of the thing this section exists to establish. So the outcome
 * message names the consequence in the conditional, and says it did not
 * happen.
 */
export function ApprovalGate({ headingId }: { headingId: string }) {
  const [chosen, setChosen] = useState<string | null>(null);
  const action = APPROVAL_ACTIONS.find((candidate) => candidate.id === chosen);

  return (
    <section className="psapproval" aria-labelledby={headingId}>
      <h3 id={headingId}>Human approval required</h3>

      <p className="psapproval__status">
        <span className="psapproval__label">Recommendation status</span>
        <span className="pschip pschip--pending">
          {LEISURE_CENTRE_RECOMMENDATION.status}
        </span>
      </p>

      <p className="psapproval__lede">
        EcoIQ proposes. A person with the authority to spend decides. Nothing
        is procured, committed or instructed by the system, and no automated
        step follows an approval that a person has not seen.
      </p>

      <div className="psapproval__actions">
        {APPROVAL_ACTIONS.map((candidate) => (
          <button
            key={candidate.id}
            type="button"
            className={
              chosen === candidate.id
                ? 'psapproval__button is-chosen'
                : 'psapproval__button'
            }
            aria-pressed={chosen === candidate.id}
            onClick={() => setChosen(candidate.id)}
          >
            {candidate.label}
          </button>
        ))}
      </div>

      {/* Polite, not assertive: the reader pressed the button, so they are
          already looking at this region. */}
      <div className="psapproval__outcome" role="status" aria-live="polite">
        {action ? (
          <>
            <p>
              <strong>In a live deployment, {action.label.toLowerCase()} would:</strong>{' '}
              {action.consequence}
            </p>
            <p className="psapproval__nothing">
              Nothing was recorded. This is a demonstration page with no
              organisation behind it, and no request left your browser.
            </p>
          </>
        ) : (
          <p className="psapproval__prompt">
            Choose an action to see what it would mean. Nothing is submitted.
          </p>
        )}
      </div>
    </section>
  );
}
