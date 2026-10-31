import { Link } from 'react-router-dom';

/**
 * Eco Tours.
 *
 * The product today is INTEREST CAPTURE, not booking. There is no availability
 * calendar, no payment flow and no inventory behind this page, so it offers
 * none of those — a booking form that cannot book is a lie with a submit
 * button.
 *
 * The enquiry goes through /contact, which is a real endpoint with real abuse
 * screening. An earlier version of this page published a `hello@ecoiq.uk`
 * address that appears nowhere else in the repository and that nothing shows
 * to exist — an invented contact route is the same category of fabrication as
 * an invented number, and worse, because someone would write to it.
 *
 * The full programme narrative lives at /khalifa-tours/, which is still
 * server-rendered. This page leads with the status and links there, rather
 * than restating it less well.
 */
export default function Tours() {
  return (
    <div className="prose">
      <h1>Eco Tours</h1>
      <p>
        Stewardship travel: small groups, real restoration work, and a record of
        what changed as a result.
      </p>

      <section aria-labelledby="tours-status">
        <h2 id="tours-status">
          Currently open for interest{' '}
          <span className="status-badge status-badge--beta">Beta</span>
        </h2>
        <p>
          Tours are being planned with local partners. There is no booking or
          payment yet — registering interest tells us where to run the first
          ones, and we will come back to you before anything is scheduled.
        </p>
      </section>

      <section aria-labelledby="tours-programme">
        <h2 id="tours-programme">The programme</h2>
        <p>
          <a href="/khalifa-tours/">
            Khalifa Stewardship Tours — the full itinerary and intent
          </a>
        </p>
        <p className="state__detail">
          That page describes what an expedition is designed to be. Nothing on
          it has run yet.
        </p>
      </section>

      <section aria-labelledby="tours-register">
        <h2 id="tours-register">Register interest</h2>
        <p>
          <Link className="cta" to="/contact">Tell us where to run the first one</Link>
        </p>
        <p className="state__detail">
          Registering interest tells us which regions to plan for. We will come
          back to you before anything is scheduled — there is nothing to book
          yet.
        </p>
      </section>
    </div>
  );
}
