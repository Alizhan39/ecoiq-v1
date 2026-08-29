import { useState } from 'react';
import { AssetDetail } from './AssetDetail';
import { AssetList } from './AssetList';
import { ApprovalGate } from './ApprovalGate';
import { DemonstrationNotice } from './DemonstrationNotice';
import { EstateOverview } from './EstateOverview';
import { EvidencePanel } from './EvidencePanel';
import { MrvLoop } from './MrvLoop';
import { NarrativeStrip } from './NarrativeStrip';
import { FLAGGED_ASSETS, LEISURE_CENTRE_ANOMALY, type FlaggedAsset } from './demoData';

/**
 * The London Borough Sustainability Command Centre — a SECTION of
 * /public-sector/, not a page of its own.
 *
 * WHY IT IS EMBEDDED RATHER THAN LINKED
 * -------------------------------------
 * It used to be /public-sector/borough-demo/. A buyer who has to click through
 * to a second URL to see the product work is a buyer who may not, and the
 * whole proposition — find waste, compare interventions, inspect evidence,
 * approve, measure, verify — is the part that cannot be conveyed by a bullet
 * list. It belongs on the page that makes the argument.
 *
 * The components below are unchanged from when this was a route. Only the
 * heading levels moved down one, because the demonstration is now an <h2>
 * inside a page whose <h1> is the public-sector proposition.
 *
 * FICTITIOUS THROUGHOUT
 * ---------------------
 * No real borough, organisation, asset or saving. The notice renders at the
 * top of this section and again beside its closing line, and every quantity in
 * the dataset carries `basis: 'illustrative'` — enforced by demoData.test.ts,
 * so a figure cannot be added later without the label.
 *
 * NO NEW ARCHITECTURE
 * -------------------
 * Client-rendered from one static module. No API call, no model, no migration,
 * no route into the evidence database — a public page has no business holding
 * a session against the real evidence store.
 */
export function BoroughCommandCentre({ headingId }: { headingId: string }) {
  const priority = FLAGGED_ASSETS.find(
    (asset) => asset.id === LEISURE_CENTRE_ANOMALY.assetId,
  )!;
  const [selected, setSelected] = useState<FlaggedAsset>(priority);

  return (
    <section className="psdemo" aria-labelledby={headingId}>
      <p className="pshero__eyebrow">Interactive demonstration</p>
      <h2 id={headingId}>London Borough Sustainability Command Centre</h2>
      <p className="psdemo__lede">
        Find waste, compare interventions, inspect the evidence, approve the
        action, verify the saving. The sequence EcoIQ runs on a real estate,
        with figures that describe none.
      </p>
      <DemonstrationNotice />

      <NarrativeStrip headingId={`${headingId}-narrative`} />

      <EstateOverview headingId={`${headingId}-estate`} />

      <div className="psdemo__body">
        <AssetList selectedId={selected.id} onSelect={setSelected} />
        <AssetDetail asset={selected} />
      </div>

      <EvidencePanel headingId={`${headingId}-evidence`} />

      <ApprovalGate headingId={`${headingId}-approval`} />

      <MrvLoop headingId={`${headingId}-mrv`} />

      <DemonstrationNotice compact />
    </section>
  );
}
