import { NARRATIVE } from './content';

/**
 * Problem → Evidence → Recommendation → Human decision → Intervention →
 * Measurement → Verified outcome.
 *
 * An ordered list, not a row of arrows drawn in CSS: the order is the meaning,
 * and a screen reader should get it from the markup rather than from a
 * decorative glyph. The connector is a pseudo-element and is aria-hidden by
 * virtue of being one.
 */
export function NarrativeStrip({ headingId }: { headingId: string }) {
  return (
    <section className="psnarrative" aria-labelledby={headingId}>
      <h3 id={headingId}>The sequence this demonstration walks through</h3>
      <ol className="psnarrative__list">
        {NARRATIVE.map((step) => (
          <li className="psnarrative__step" key={step.number}>
            <span className="psnarrative__number">{step.number}</span>
            <h4 className="psnarrative__name">{step.name}</h4>
            <p className="psnarrative__detail">{step.detail}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
