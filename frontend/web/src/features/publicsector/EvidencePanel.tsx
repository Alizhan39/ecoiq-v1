import { LEISURE_CENTRE_EVIDENCE, type EvidenceItem } from './demoData';

/**
 * What the recommendation rests on.
 *
 * The claim this panel makes is narrow and checkable: "recommendation backed
 * by traceable evidence" means every item has a named source, a date, a stated
 * method and a status — not that every item is strong. Two here are not, and
 * they are shown at their real strength.
 *
 * THE COLOUR NEVER CARRIES THE MEANING
 * ------------------------------------
 * Confidence and status are words first. The tint is an accelerant for a
 * sighted reader scanning quickly; remove it and the table still says
 * everything it said before. That is the rule the rest of this product's
 * status chips already follow.
 */
export function EvidencePanel({ headingId }: { headingId: string }) {
  return (
    <section className="psevidence" aria-labelledby={headingId}>
      <h3 id={headingId}>Evidence behind the recommendation</h3>
      <p className="psevidence__lede">
        Seven sources, each with where it came from, when, how it was produced
        and what state it is in. Two are not strong, and the panel says so
        rather than averaging them into the rest.
      </p>

      <div className="psassets__scroll">
        <table className="pstable">
          <caption className="visually-hidden">
            Evidence items with source, date, confidence, methodology and
            status.
          </caption>
          <thead>
            <tr>
              <th scope="col">Evidence</th>
              <th scope="col">Source</th>
              <th scope="col">Date</th>
              <th scope="col">Confidence</th>
              <th scope="col">Methodology</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {LEISURE_CENTRE_EVIDENCE.map((item) => (
              <tr key={item.id}>
                <th scope="row">{item.type}</th>
                <td>{item.source}</td>
                <td>
                  <time dateTime={item.date}>{formatDate(item.date)}</time>
                </td>
                <td>
                  <span className={confidenceClass(item)}>{item.confidence}</span>
                </td>
                <td className="pstable__method">{item.methodology}</td>
                <td>
                  <span className={statusClass(item)}>{item.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="psevidence__note">
        <strong>Recommendation backed by traceable evidence.</strong> The
        outstanding maintenance history is why "request further analysis" is a
        real option below rather than a decorative third button — it is the gap
        a reviewer would send this back to close.
      </p>
    </section>
  );
}

function confidenceClass(item: EvidenceItem): string {
  return `pschip pschip--confidence-${item.confidence.toLowerCase()}`;
}

function statusClass(item: EvidenceItem): string {
  return `pschip pschip--status-${item.status.toLowerCase()}`;
}

/** 2026-07-31 → 31 Jul 2026. Fixed input, so no locale surprises. */
function formatDate(iso: string): string {
  const [year, month, day] = iso.split('-');
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const name = months[Number(month) - 1];
  return name ? `${Number(day)} ${name} ${year}` : iso;
}
