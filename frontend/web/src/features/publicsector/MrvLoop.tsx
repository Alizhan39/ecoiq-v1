import { MRV_OUTCOME, MRV_STAGES } from './demoData';
import { percent, poundsExact, variancePercent } from './economics';

/**
 * Baseline → Intervention → Measurement → Normalisation → Actual → Variance →
 * Verified outcome.
 *
 * The variance is COMPUTED from the forecast and the verified figure beside
 * it, not written down. A measurement section that hard-codes its own variance
 * is a contradiction in terms, and it would be the single most embarrassing
 * line on the page to be caught with.
 *
 * The vocabulary is the public-facing reading of the eight-step workflow in
 * impact_mrv_layer — the same sequence, named the way a finance officer asks
 * for it. Nothing internal is replaced or weakened by stating it this way.
 */
export function MrvLoop({ headingId }: { headingId: string }) {
  const forecast = MRV_OUTCOME.forecastAnnualSaving.value;
  const verified = MRV_OUTCOME.verifiedAnnualSaving.value;
  const variance = variancePercent(verified, forecast);

  return (
    <section className="psmrv" aria-labelledby={headingId}>
      <h3 id={headingId}>Measurement and verification</h3>
      <p className="psmrv__lede">
        A saving is not delivered when a recommendation is approved. It is
        delivered when a measurement period ends and the evidence supports the
        number.
      </p>

      <ol className="psmrv__stages">
        {MRV_STAGES.map((stage, index) => (
          <li className="psmrv__stage" key={stage.key}>
            <span className="psmrv__step">
              {String(index + 1).padStart(2, '0')}
            </span>
            <h4>{stage.label}</h4>
            <p>{stage.detail}</p>
          </li>
        ))}
      </ol>

      <div className="psmrv__outcome">
        <h4>Verified outcome — Leisure Centre boiler upgrade</h4>
        <dl className="psmrv__figures">
          <div className="psfigure psfigure--small">
            <dt>Forecast annual saving</dt>
            <dd>{poundsExact(forecast)}</dd>
          </div>
          <div className="psfigure psfigure--small psfigure--accent">
            <dt>Verified annual saving</dt>
            <dd>{poundsExact(verified)}</dd>
          </div>
          <div className="psfigure psfigure--small">
            <dt>Variance to forecast</dt>
            <dd>{percent(variance)}</dd>
          </div>
          <div className="psfigure psfigure--small">
            <dt>Measurement period</dt>
            <dd>{MRV_OUTCOME.measurementPeriod}</dd>
          </div>
          <div className="psfigure psfigure--small">
            <dt>Evidence status</dt>
            <dd>
              <span className="pschip pschip--status-verified">
                {MRV_OUTCOME.evidenceStatus}
              </span>
            </dd>
          </div>
        </dl>
        <p className="psmrv__caveat">{MRV_OUTCOME.caveat}</p>
      </div>
    </section>
  );
}
