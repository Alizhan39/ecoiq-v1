/**
 * SystemStatePanel — what the plant IS, at this scroll position.
 *
 * Qualitative, deliberately. The state functions produce values in [0,1] and
 * none of them reaches the reader as a number: "Combustion → Electrified" is
 * true and unmistakable, where "82%" beside an industrial schematic reads as a
 * meter and survives a screenshot with the caption stripped off.
 *
 * Emissions is the one row with no transition, because there isn't one to
 * report. See EMISSIONS_STATE.
 */
import { DEBUG_STATE_LABEL, EMISSIONS_STATE, systemStateAt } from './semantic/systemState';
import { STATE_FUNCTIONS } from './model/state';

export interface SystemStatePanelProps {
  progress: number;
  /** Shows the raw model fractions, explicitly labelled. Off by default. */
  debug?: boolean;
}

export function SystemStatePanel({ progress, debug = false }: SystemStatePanelProps) {
  const readings = systemStateAt(progress);

  return (
    <section className="itstate" aria-labelledby="itstate-heading">
      <h2 id="itstate-heading">System state</h2>

      <dl className="itstate__list">
        {readings.map((r) => (
          <div
            key={r.key}
            className={`itstate__row ${r.complete ? 'is-complete' : ''}`}
          >
            <dt>{r.label}</dt>
            <dd>
              <ol className="itstate__track">
                {r.states.map((state, i) => (
                  <li
                    key={state}
                    className={[
                      'itstate__step',
                      i < r.index ? 'is-past' : '',
                      i === r.index ? 'is-now' : '',
                    ].filter(Boolean).join(' ')}
                    aria-current={i === r.index ? 'true' : undefined}
                  >
                    {state}
                  </li>
                ))}
              </ol>
            </dd>
          </div>
        ))}

        {/*
          Emissions has no track, because it does not move. Rendering it as a
          row that never advances would read as "not yet"; rendering it with
          its explanation says what is actually the case.
        */}
        <div className="itstate__row itstate__row--unknown">
          <dt>{EMISSIONS_STATE.label}</dt>
          <dd>
            <strong>{EMISSIONS_STATE.state}</strong>
            <p className="itstate__note">{EMISSIONS_STATE.explanation}</p>
          </dd>
        </div>
      </dl>

      {debug ? (
        <details className="itstate__debug">
          <summary>{DEBUG_STATE_LABEL}</summary>
          <p className="itstate__note">{DEBUG_STATE_LABEL}</p>
          <table>
            <thead>
              <tr><th scope="col">Function</th><th scope="col">Value</th></tr>
            </thead>
            <tbody>
              {STATE_FUNCTIONS.map((spec) => (
                <tr key={spec.key}>
                  <th scope="row">{spec.key}</th>
                  <td>{spec.fn(progress).toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      ) : null}
    </section>
  );
}
