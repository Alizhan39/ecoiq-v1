/**
 * About.
 *
 * Two rules govern this page.
 *
 * The first is that everything on it describes what EcoIQ does TODAY. The
 * long-term direction — energy, transport and aviation, cities and buildings,
 * nature and resources — is real and is stated as a direction, in a section
 * that says plainly that those decision engines are not implemented. A page
 * that describes a roadmap in the present tense is the failure this whole
 * programme exists to remove.
 *
 * The second is that the mechanism is the argument. Coverage, provenance and
 * confidence are what make an assessment worth anything, so they are explained
 * here rather than being summarised as "rigorous methodology".
 */
export default function About() {
  return (
    <div className="prose">
      <h1>About EcoIQ</h1>
      <p>
        EcoIQ is evidence-backed decision intelligence for companies,
        investments and projects. It assesses an organisation against the
        evidence actually recorded about it — and publishes an assessment only
        where that evidence supports one.
      </p>
      <p>
        That last clause is the product. Most systems in this space will return
        a number for any organisation you ask about, because returning nothing
        looks like a failure. EcoIQ returns nothing when it has nothing, and
        tells you exactly what is missing.
      </p>

      <section aria-labelledby="how">
        <h2 id="how">How an assessment is built</h2>
        <dl>
          <div>
            <dt>Provenance — where each number came from</dt>
            <dd>
              Every stored value records its origin: measured from a source,
              inferred by EcoIQ from a source, estimated, modelled, seeded, or
              legacy data predating the record. The record is append-only, so
              an earlier belief stays answerable, and derived values record the
              specific provenance rows they were computed from rather than just
              which metrics.
            </dd>
          </div>
          <div>
            <dt>Evidence Coverage — how much of the assessment is supported</dt>
            <dd>
              A ratio over the material inputs an assessment needs, weighted by
              how much each one actually matters to the result. Reported as the
              ratio and its two halves — <em>eleven of sixteen inputs
              supported</em> — because a percentage on its own hides how big
              the question was. Seeded and legacy values never count.
            </dd>
          </div>
          <div>
            <dt>Confidence — how good that support is</dt>
            <dd>
              One of four labels, never a percentage. Coverage and confidence
              are deliberately separate: complete coverage built on unverified
              press releases is complete and weak; partial coverage from
              independently verified audits is incomplete and strong. One
              number cannot say both, and averaging them describes neither.
            </dd>
          </div>
          <div>
            <dt>Publication — the gate</dt>
            <dd>
              A score is published only when every material input is supported
              by evidence EcoIQ can stand behind. Contamination anywhere
              beneath a value — including several layers down — disqualifies
              it. One module makes that decision, and every surface asks it.
            </dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="today">
        <h2 id="today">What that means right now</h2>
        <p>
          <strong>
            No organisation currently has a published score.
          </strong>{' '}
          What EcoIQ holds is historic data recorded before provenance was
          tracked, and the system will not publish an assessment it cannot
          stand behind. Every organisation page says so, and says what is
          missing.
        </p>
        <p>
          This is the correct state, not a fault. Coverage rises as evidence is
          recorded and reviewed, and an assessment becomes publishable when it
          genuinely is — not when a page needs something to display.
        </p>
      </section>

      <section aria-labelledby="direction">
        <h2 id="direction">Where this is going</h2>
        <p>
          The longer-term direction is system-level decision intelligence across
          four domains:
        </p>
        <ul>
          <li>Energy</li>
          <li>Transport and aviation</li>
          <li>Cities and buildings</li>
          <li>Nature and resources</li>
        </ul>
        <p>
          <strong>
            None of those decision engines is implemented today.
          </strong>{' '}
          They are the direction, not the product. What exists now is the
          organisation-level assessment described above, plus the experimental
          work listed in <a href="/labs">EcoIQ Labs</a> — each item there
          carrying its real status rather than a launch date.
        </p>
      </section>

      <section aria-labelledby="who">
        <h2 id="who">Who builds it</h2>
        <p>
          EcoIQ was founded in London by Alizhan Tazabekov, to close a gap that
          became hard to ignore: heavy industry was being evaluated on
          financial metrics alone, and transition was discussed in policy
          papers but rarely quantified at the level of an individual company.
        </p>
        <p>
          EcoIQ is not an ESG rating agency and not a consultancy. It has no
          enterprise customers to name yet. When it does, they will appear as
          case studies with real numbers — until then this page says nothing
          about them, and there are no logos on it for the same reason.
        </p>
        <p>
          <a href="/trust">How EcoIQ handles evidence and data</a> ·{' '}
          <a href="/contact">Get in touch</a>
        </p>
      </section>
    </div>
  );
}
