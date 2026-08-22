import { Link } from 'react-router-dom';

/** The enterprise enquiry form, which pre-selects the engagement type. */
const ENQUIRY = '/request-access/enterprise/';

/**
 * Pricing.
 *
 * WHAT THE AUDIT FOUND
 * --------------------
 * There is no productised pricing. `/pricing/` collected no payment, and the
 * Stripe app that does exist (`ecoiq_commerce`) ships with
 * ECOIQ_BILLING_PROVIDER=none, no live keys and no checkout reachable from this
 * page. Every route through it ended at an enquiry form.
 *
 * The page it replaces published four fixed price bands — £15,000 to £400,000 —
 * for engagements that have never been sold, each with a checklist of included
 * capabilities. Several of those capabilities are not implemented: SSO and
 * access controls do not exist, overnight monitoring is scheduler-ready rather
 * than running, workflow automation is not built. A price list is a commitment
 * to deliver what it itemises.
 *
 * So the structure survives — the four ways an engagement genuinely can start
 * are real, and are the founder's own commercial model — and the two things
 * that could not be supported do not:
 *
 *   * the price bands, which no transaction has ever validated;
 *   * the feature checklists, which promised unbuilt capability.
 *
 * Scope and price are agreed per engagement, which is what actually happens.
 *
 * The CTAs still feed leads.EnterpriseEnquiry with the engagement type
 * pre-selected, exactly as before. That funnel is real, works, and has its own
 * lead model and abuse screening — sending enterprise enquiries to the general
 * contact form instead would have been a commercial regression dressed as a
 * simplification.
 */

const TRACKS = [
  {
    name: 'Diagnostic',
    engagement: 'enterprise_diagnostic',
    shape: 'Fixed scope, a few weeks',
    body: 'A focused assessment of what evidence an organisation holds, how '
      + 'much of it is decision-grade, and which decisions it could support. '
      + 'Ends in a written findings report.',
  },
  {
    name: 'Pilot',
    engagement: 'pilot_90day',
    shape: 'A defined portfolio or business unit',
    body: 'EcoIQ applied to a real decision on a bounded set of companies, '
      + 'assets or projects, with the evidence and its gaps laid out. Ends in '
      + 'a decision you can act on, or a clear statement that the evidence '
      + 'does not support one.',
  },
  {
    name: 'Deployment',
    engagement: 'enterprise_deployment',
    shape: 'Organisation-wide',
    body: 'Implementation against internal systems, governance and security '
      + 'requirements. Scoped from what a diagnostic or pilot established '
      + 'rather than from a template.',
  },
  {
    name: 'Programme',
    engagement: 'annual_licence',
    shape: 'Continuing',
    body: 'Ongoing access, monitoring and reporting, renewed on a defined '
      + 'term.',
  },
  {
    name: 'Government and sovereign',
    engagement: 'government_sovereign',
    shape: 'National or institutional',
    body: 'Programmes run with a ministry, regulator or sovereign fund, where '
      + 'procurement, data residency and public accountability shape the scope '
      + 'before anything else does.',
  },
  {
    name: 'Founding partner',
    engagement: 'founding_partner',
    shape: 'Limited',
    body: 'A small number of organisations working with EcoIQ early, with '
      + 'direct influence on what gets built. Terms are agreed individually.',
  },
] as const;

export default function Pricing() {
  return (
    <div className="prose">
      <h1>Pricing</h1>
      <p>
        EcoIQ engagements begin with a conversation, not a checkout. Scope,
        evidence access, integration effort and duration differ enough between
        organisations that a fixed tier would be wrong for almost everyone.
      </p>

      <section aria-labelledby="tracks">
        <h2 id="tracks">How an engagement starts</h2>
        <ul className="grid">
          {TRACKS.map((track) => (
            <li className="card" key={track.name}>
              <h3>{track.name}</h3>
              <p className="state__detail">{track.shape}</p>
              <p>{track.body}</p>
              <p>
                {/* The real enterprise enquiry flow, with the engagement type
                    pre-selected — not the general contact form. It has its own
                    lead model, its own fields and its own abuse screening, and
                    routing enterprise enquiries away from it would lose all
                    three. */}
                <a href={`${ENQUIRY}?engagement=${track.engagement}`}>
                  Enquire about {track.name.toLowerCase()}
                </a>
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="how">
        <h2 id="how">How the price is set</h2>
        <p>
          Per engagement, against the scope agreed in writing beforehand. The
          things that move it are the number of organisations or assets in
          scope, how much evidence already exists in a usable form, how many
          systems have to be integrated, and the governance and security
          requirements involved.
        </p>
        <p>
          <strong>There are no published price bands on this page.</strong>{' '}
          EcoIQ has not yet delivered a commercial engagement, so any figure
          here would be an asking price presented as a going rate. When there
          are engagements to reference, this page will say what they cost.
        </p>
      </section>

      <section aria-labelledby="expect">
        <h2 id="expect">What you get, and what you do not</h2>
        <p>
          Every engagement is built on the same thing the product is:{' '}
          <Link to="/about">evidence coverage, provenance and confidence</Link>,
          with an assessment published only where the evidence supports one. If
          the evidence for a decision is not there, an EcoIQ engagement will
          tell you that and show you the gap — it will not produce a number to
          fill the space.
        </p>
        <p>
          Capabilities that are still experimental are listed as such in{' '}
          <Link to="/labs">EcoIQ Labs</Link> and are not sold as part of an
          engagement.
        </p>
      </section>

      <p>
        <a className="cta" href={ENQUIRY}>Start an enquiry</a>
        {' '}
        <Link to="/contact">or ask a general question</Link>
      </p>
    </div>
  );
}
