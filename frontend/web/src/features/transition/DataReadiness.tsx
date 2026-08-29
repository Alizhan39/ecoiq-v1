/**
 * DataReadiness — what the model could accept, against what it holds.
 *
 * THE DISTINCTION THIS SECTION IS ENTIRELY ABOUT
 * ----------------------------------------------
 * "The architecture supports equipment data" and "EcoIQ has equipment data"
 * are different statements, and a table of categories with ticks beside them
 * says the second while meaning the first. So every row carries both columns
 * explicitly, and the collected column reads the same for every row today.
 *
 * An available slot is not collected data. That is the last of the product
 * truths this page rests on, and the one most easily lost to a
 * confident-looking table.
 */
import { unknownOutcome } from './domain/unknown';

interface DataCategory {
  label: string;
  useIn: string;
  /** Where it lands in the domain model, so the claim is checkable. */
  slot: string;
}

const CATEGORIES: readonly DataCategory[] = [
  { label: 'Equipment', useIn: 'Identifies what exists and what a retrofit replaces', slot: 'Equipment' },
  { label: 'Energy consumption', useIn: 'Sizes electrical loads and the drive case', slot: 'ResourceFlow.quantity' },
  { label: 'Process heat', useIn: 'Sizes the electrification and recovery case', slot: 'ResourceFlow.quantity' },
  { label: 'Fuel', useIn: 'The flow electrification removes', slot: 'ResourceFlow (fuel)' },
  { label: 'Water', useIn: 'Discharge volume, and what a reuse loop returns', slot: 'ResourceFlow (water)' },
  { label: 'Throughput', useIn: 'Normalises everything else against output', slot: 'Process' },
  { label: 'Waste', useIn: 'What material recovery would divert', slot: 'ResourceFlow (waste)' },
  { label: 'Operating hours', useIn: 'Turns a rate into an annual quantity', slot: 'Quantity' },
  { label: 'Evidence', useIn: 'Why a loss was believed real, and whether it changed', slot: 'LossPoint.evidenceIds' },
  { label: 'CapEx and OpEx', useIn: 'Cost, saving, payback — later, and only from real figures', slot: 'EconomicOutcome' },
];

export function DataReadiness({ headingId = 'itdata-heading' }: { headingId?: string }) {
  // Read from the model rather than asserted in markup: if a field ever stops
  // being null, this section stops claiming nothing is collected.
  const outcome = unknownOutcome();
  const anyCollected = Object.values(outcome).some((v) => v !== null);

  return (
    <section className="itdata" aria-labelledby={headingId}>
      <h2 id={headingId}>What the model can accept</h2>
      <p>
        The architecture has a place for each of these. None of it is being
        collected — EcoIQ ingests no facility data today, and an available slot
        is not collected data.
      </p>

      <div className="itdata__scroll">
        <table className="itdata__table">
          <caption>
            Two different statements, kept in separate columns on purpose.
          </caption>
          <thead>
            <tr>
              <th scope="col">Category</th>
              <th scope="col">What it would be used for</th>
              <th scope="col">Architecture supports</th>
              <th scope="col">Production ingestion</th>
            </tr>
          </thead>
          <tbody>
            {CATEGORIES.map((c) => (
              <tr key={c.label}>
                <th scope="row">{c.label}</th>
                <td>{c.useIn}</td>
                <td className="itdata__yes">Yes — <code>{c.slot}</code></td>
                <td className="itdata__no">
                  {anyCollected ? 'Review this row' : 'None'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
