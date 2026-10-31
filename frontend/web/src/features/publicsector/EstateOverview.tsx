import { ESTATE, FLAGGED_ASSETS, portfolioTotals } from './demoData';
import { poundsToM, poundsExact, tonnes } from './economics';

/**
 * The four figures, then the sentence that turns them into work.
 *
 * The saving headline is DERIVED — `portfolioTotals().annualSaving` is the sum
 * of the seventeen flagged assets, not a constant. So is the count. A headline
 * that is not the sum of the rows beneath it is the failure mode this whole
 * demonstration is arguing against, and it would be absurd to commit it here.
 */
export function EstateOverview({ headingId }: { headingId: string }) {
  const totals = portfolioTotals();

  return (
    <section className="psestate" aria-labelledby={headingId}>
      <h3 id={headingId} className="visually-hidden">
        Estate overview
      </h3>

      <dl className="psestate__figures">
        <div className="psfigure">
          <dt>Buildings</dt>
          <dd>{ESTATE.buildings.value}</dd>
        </div>
        <div className="psfigure">
          <dt>Annual energy spend</dt>
          <dd>{poundsToM(ESTATE.annualEnergySpend.value)}</dd>
        </div>
        <div className="psfigure">
          <dt>Annual emissions</dt>
          <dd>
            {tonnes(ESTATE.annualEmissions.value)}
            {' '}
            <span className="psfigure__unit">tCO₂e</span>
          </dd>
        </div>
        <div className="psfigure psfigure--accent">
          <dt>Identified annual saving opportunity</dt>
          <dd>{poundsExact(totals.annualSaving)}</dd>
        </div>
      </dl>

      <p className="psestate__callout">
        <strong>
          {totals.assetCount} assets require attention
        </strong>{' '}
        — {totals.assetCount} of {ESTATE.buildings.value} buildings are
        consuming materially more than their own baseline predicts.
      </p>
      <p className="psestate__derivation">
        The saving figure is the sum of the {FLAGGED_ASSETS.length} assets
        listed below, and the payback on each is its capital requirement
        divided by its annual saving. Nothing on this page is a headline
        written separately from the rows beneath it.
      </p>
    </section>
  );
}
