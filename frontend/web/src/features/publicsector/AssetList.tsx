import { FLAGGED_ASSETS, portfolioTotals, type FlaggedAsset } from './demoData';
import { paybackYears, poundsToK, tonnes, years } from './economics';

/**
 * The estate, ranked, and drillable.
 *
 * A TABLE, deliberately. This is tabular data with a header for every column,
 * and rendering it as a grid of cards would take a comparison a buyer makes by
 * running an eye down one column and turn it into seventeen separate readings.
 *
 * The interactive element is a button inside the first cell rather than a
 * click handler on the row: a row is not focusable, does not announce itself
 * as actionable, and cannot be reached from a keyboard.
 */
export function AssetList({
  selectedId,
  onSelect,
}: {
  selectedId: string | null;
  onSelect: (asset: FlaggedAsset) => void;
}) {
  const totals = portfolioTotals();

  return (
    <section className="psassets" aria-labelledby="psassets-heading">
      <h3 id="psassets-heading">Assets requiring attention</h3>
      <p className="psassets__hint">
        Select an asset to see the evidence behind it and the options compared.
      </p>

      <div className="psassets__scroll">
        <table className="pstable">
          <caption className="visually-hidden">
            Flagged assets with capital requirement, annual saving, emissions
            reduction and payback. Select an asset name to open its detail.
          </caption>
          <thead>
            <tr>
              <th scope="col">Asset</th>
              <th scope="col">Problem</th>
              <th scope="col" className="pstable__num">CAPEX</th>
              <th scope="col" className="pstable__num">Annual saving</th>
              <th scope="col" className="pstable__num">CO₂ reduction</th>
              <th scope="col" className="pstable__num">Payback</th>
            </tr>
          </thead>
          <tbody>
            {FLAGGED_ASSETS.map((asset) => {
              const selected = asset.id === selectedId;
              return (
                <tr key={asset.id} className={selected ? 'is-selected' : undefined}>
                  <th scope="row">
                    <button
                      type="button"
                      className="pstable__pick"
                      aria-current={selected ? 'true' : undefined}
                      onClick={() => onSelect(asset)}
                    >
                      {asset.name}
                    </button>
                  </th>
                  <td>{asset.problem}</td>
                  <td className="pstable__num">{poundsToK(asset.capex.value)}</td>
                  <td className="pstable__num">
                    {poundsToK(asset.annualSaving.value)}
                  </td>
                  <td className="pstable__num">
                    {tonnes(asset.emissionsReduction.value)} t
                  </td>
                  <td className="pstable__num">
                    {years(paybackYears(asset.capex.value, asset.annualSaving.value))}
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row">Total</th>
              <td>{totals.assetCount} assets</td>
              <td className="pstable__num">{poundsToK(totals.capex)}</td>
              <td className="pstable__num">{poundsToK(totals.annualSaving)}</td>
              <td className="pstable__num">
                {tonnes(totals.emissionsReduction)} t
              </td>
              <td className="pstable__num">
                {years(paybackYears(totals.capex, totals.annualSaving))}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  );
}
