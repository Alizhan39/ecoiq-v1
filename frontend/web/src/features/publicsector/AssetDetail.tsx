import { useEffect, useRef } from 'react';
import {
  LEISURE_CENTRE_ANOMALY,
  LEISURE_CENTRE_INTERVENTIONS,
  LEISURE_CENTRE_RECOMMENDATION,
  type FlaggedAsset,
} from './demoData';
import {
  paybackYears, percent, poundsExact, poundsToK, tonnes, years,
} from './economics';

/**
 * One asset, opened.
 *
 * TWO DEPTHS, AND WHY THE SHALLOW ONE SAYS SO
 * -------------------------------------------
 * The Leisure Centre carries the full drill-down: the anomaly, the candidate
 * causes, the option comparison and the recommended sequence. The other
 * sixteen carry the figures and a line stating that the deeper analysis is
 * illustrated on the priority asset.
 *
 * The alternative — generating a plausible-looking anomaly and a three-option
 * comparison for all seventeen — would have produced sixteen more sets of
 * invented numbers to make the demo look deeper than it is. A demonstration
 * that says "this one is worked through, the others are not" is more use to a
 * buyer than one that hides where the work stops.
 */
export function AssetDetail({ asset }: { asset: FlaggedAsset }) {
  const headingRef = useRef<HTMLHeadingElement>(null);

  // Move focus to the heading when the selection changes. Without it, a
  // keyboard user activates a row and the detail appears somewhere below their
  // focus ring, which they have no way of knowing.
  useEffect(() => {
    headingRef.current?.focus();
  }, [asset.id]);

  const isPriority = asset.id === LEISURE_CENTRE_ANOMALY.assetId;

  return (
    <section className="psdetail" aria-labelledby="psdetail-heading">
      <p className="psdetail__eyebrow">
        Priority {String(asset.priority).padStart(2, '0')}
      </p>
      <h3 id="psdetail-heading" ref={headingRef} tabIndex={-1}>
        {asset.name}
      </h3>

      <dl className="psdetail__figures">
        <div className="psfigure psfigure--small">
          <dt>Problem</dt>
          <dd>{asset.problem}</dd>
        </div>
        <div className="psfigure psfigure--small">
          <dt>CAPEX</dt>
          <dd>{poundsToK(asset.capex.value)}</dd>
        </div>
        <div className="psfigure psfigure--small">
          <dt>Annual saving</dt>
          <dd>{poundsToK(asset.annualSaving.value)}</dd>
        </div>
        <div className="psfigure psfigure--small">
          <dt>CO₂ reduction</dt>
          <dd>{tonnes(asset.emissionsReduction.value)} tCO₂e</dd>
        </div>
        <div className="psfigure psfigure--small">
          <dt>Payback</dt>
          <dd>
            {years(paybackYears(asset.capex.value, asset.annualSaving.value))}
          </dd>
        </div>
      </dl>

      {isPriority ? <LeisureCentreAnalysis /> : (
        <p className="psdetail__shallow">
          The full analysis — anomaly detection against a weather-normalised
          baseline, candidate causes, and a costed comparison of interventions
          — is worked through on the Leisure Centre. It has not been invented
          for this asset, and a demonstration that filled the gap with
          plausible numbers would be teaching you the wrong thing about how
          EcoIQ works.
        </p>
      )}
    </section>
  );
}

/** The deep drill-down: anomaly, causes, options, recommendation. */
function LeisureCentreAnalysis() {
  const anomaly = LEISURE_CENTRE_ANOMALY;

  return (
    <>
      <section className="psanomaly" aria-labelledby="psanomaly-heading">
        <h4 id="psanomaly-heading">Energy anomaly detected</h4>
        <dl className="psanomaly__figures">
          <div className="psfigure psfigure--small">
            <dt>{anomaly.fuel} consumption</dt>
            <dd className="is-adverse">
              {percent(anomaly.deviationPercent.value)} versus expected baseline
            </dd>
          </div>
          <div className="psfigure psfigure--small">
            <dt>Estimated excess annual cost</dt>
            <dd className="is-adverse">
              {poundsExact(anomaly.excessAnnualCost.value)}
            </dd>
          </div>
        </dl>
        <p className="psanomaly__method">{anomaly.detectedBy}</p>

        <h5 className="psanomaly__causes-heading">Possible causes</h5>
        <ul className="pschips">
          {anomaly.candidateCauses.map((cause) => (
            <li key={cause}>{cause}</li>
          ))}
        </ul>
        <p className="psanomaly__note">
          Candidates, not findings. Establishing which of these is responsible
          is survey work, and EcoIQ does not resolve it from meter data alone.
        </p>
      </section>

      <section className="pscompare" aria-labelledby="pscompare-heading">
        <h4 id="pscompare-heading">Intervention comparison</h4>
        <div className="psassets__scroll">
          <table className="pstable">
            <caption className="visually-hidden">
              Interventions compared on capital requirement, annual saving,
              carbon reduction and payback.
            </caption>
            <thead>
              <tr>
                <th scope="col">Intervention</th>
                <th scope="col" className="pstable__num">CAPEX</th>
                <th scope="col" className="pstable__num">Annual saving</th>
                <th scope="col" className="pstable__num">CO₂ reduction</th>
                <th scope="col" className="pstable__num">Payback</th>
              </tr>
            </thead>
            <tbody>
              {LEISURE_CENTRE_INTERVENTIONS.map((option) => (
                <tr key={option.id}>
                  <th scope="row">
                    {option.label}
                    <span className="pstable__sub">{option.effect}</span>
                  </th>
                  <td className="pstable__num">{poundsToK(option.capex.value)}</td>
                  <td className="pstable__num">
                    {poundsToK(option.annualSaving.value)}
                  </td>
                  <td className="pstable__num">
                    {tonnes(option.emissionsReduction.value)} t
                  </td>
                  <td className="pstable__num">
                    {years(paybackYears(
                      option.capex.value, option.annualSaving.value))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="psrecommend">
          <h5>Suggested sequence</h5>
          <ol className="psrecommend__sequence">
            {LEISURE_CENTRE_RECOMMENDATION.sequence.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          <p className="psrecommend__why">
            {LEISURE_CENTRE_RECOMMENDATION.reasoning}
          </p>
          <p className="psrecommend__gate">
            <strong>AI-assisted decision support.</strong> This is a proposal
            put in front of a person. EcoIQ does not procure, commit capital,
            instruct a contractor or change a building system. Nothing below
            this point happens without the approval on this page.
          </p>
        </div>
      </section>
    </>
  );
}
