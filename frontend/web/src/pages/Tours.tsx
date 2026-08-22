/**
 * Eco Tours.
 *
 * The product today is INTEREST CAPTURE, not booking. There is no availability
 * calendar, no payment flow and no inventory behind this page, so it offers
 * none of those — a booking form that cannot book is a lie with a submit
 * button.
 *
 * The enquiry goes to the existing leads app rather than a new mechanism.
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

      <section aria-labelledby="tours-register">
        <h2 id="tours-register">Register interest</h2>
        <p>
          Email <a href="mailto:hello@ecoiq.uk">hello@ecoiq.uk</a> with the
          region you are interested in.
        </p>
        <p className="state__detail">
          A form here would need a lead endpoint that this page does not yet
          have. Email works today, and is honest about what happens next.
        </p>
      </section>
    </div>
  );
}
