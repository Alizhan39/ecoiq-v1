import { Link } from 'react-router-dom';
import {
  ASSURANCE, COMMERCIAL_BANDS, COMMERCIAL_BASIS, CONTROLS, DATA_GOVERNANCE,
  DELIVERY, DELIVERY_ENTRY, ENGAGEMENT_CAPABILITIES, OUTCOMES, PLATFORM,
  POSITIONING, PROCUREMENT_PACK, SERVICES, SERVICES_BASIS, SUPPLIER,
  SUPPORT_MODEL,
} from '@/features/publicsector/content';
import { BoroughCommandCentre } from '@/features/publicsector/BoroughCommandCentre';

/**
 * /public-sector/ — the whole public-sector proposition, on one page.
 *
 * ONE ROUTE, ON PURPOSE
 * ---------------------
 * This began as three routes: an overview, a borough demonstration, and a
 * procurement reference page. Splitting it read well as an information
 * architecture and worked badly as an argument. A buyer who has to click to a
 * second URL to see the product work is a buyer who may not, and the
 * demonstration is the part a bullet list cannot do. The procurement detail
 * had the opposite problem: it was a page nobody arrives at, holding the
 * answers somebody has to find before they can raise a requisition.
 *
 * So both are sections here, and there is one canonical public-sector URL.
 * Nothing was thrown away — the demonstration components and the content
 * module are the same ones, embedded rather than routed.
 *
 * THE ORDER IS THE ARGUMENT
 * -------------------------
 * What it delivers, what you can buy, then the thing working, then how it is
 * delivered, what it runs on, how it is governed, what it costs, and who the
 * supplier is. Proof sits in the middle, where a reader who is still deciding
 * will reach it, rather than at the end where only a convinced reader would.
 *
 * WHERE THE CLAIMS COME FROM
 * --------------------------
 * features/publicsector/content.ts, which holds every one of them together so
 * they can be checked as a set. The rule the copy follows: no unsupported
 * positive claim, and no invented certification, client, framework or
 * capability — enforced by core/tests_public_sector.py, which scans this
 * file's sources rather than trusting a review.
 */

/** The real enterprise enquiry funnel, with the engagement type pre-selected.
 *  Same route /pricing/ uses; it has its own lead model and abuse screening. */
const ENQUIRY = '/request-access/enterprise/?engagement=government_sovereign';

export default function PublicSector() {
  return (
    <div className="pspage">
      {/* ── HERO ─────────────────────────────────────────────────────────── */}
      <header className="pshero">
        <p className="pshero__eyebrow">{POSITIONING.eyebrow}</p>
        <h1>{POSITIONING.headline}</h1>
        <p className="pshero__lede">{POSITIONING.description}</p>
        <p className="pshero__supporting">{POSITIONING.supporting}</p>
        <div className="pshero__actions">
          <a className="psbutton psbutton--primary" href={ENQUIRY}>
            Request a pilot
          </a>
          <a className="psbutton" href="#borough-demo">
            See it working
          </a>
          <a className="psbutton psbutton--quiet" href="#procurement">
            Procurement information
          </a>
        </div>
      </header>

      {/* ── OUTCOMES ─────────────────────────────────────────────────────── */}
      <section className="pssection" aria-labelledby="psoutcomes">
        <h2 id="psoutcomes">What it delivers</h2>
        <ul className="psgrid psgrid--outcomes">
          {OUTCOMES.map((outcome) => (
            <li className="pscard" key={outcome.title}>
              <h3>{outcome.title}</h3>
              <p>{outcome.detail}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* ── SERVICES ─────────────────────────────────────────────────────── */}
      <section className="pssection" id="services" aria-labelledby="psservices">
        <h2 id="psservices">Services</h2>
        <ol className="psgrid psgrid--services">
          {SERVICES.map((service) => (
            <li className="pscard pscard--numbered" key={service.number}>
              <p className="pscard__number">{service.number}</p>
              <h3>{service.name}</h3>
              <p>{service.summary}</p>
            </li>
          ))}
        </ol>
        <p className="psnote">{SERVICES_BASIS}</p>
      </section>

      {/* ── THE DEMONSTRATION ────────────────────────────────────────────────
          Estate overview, the ranked asset list, the Leisure Centre
          drill-down, the evidence panel, the human approval gate and the MRV
          loop — all of it inside this page. */}
      <div id="borough-demo">
        <BoroughCommandCentre headingId="psdemo-heading" />
      </div>

      {/* ── DELIVERY ─────────────────────────────────────────────────────── */}
      <section className="pssection" aria-labelledby="psdelivery">
        <h2 id="psdelivery">Delivery model</h2>
        <ol className="psflow">
          {DELIVERY.map((stage) => (
            <li className="psflow__stage" key={stage.number}>
              <span className="psflow__number">{stage.number}</span>
              <h3>{stage.name}</h3>
              <p>{stage.detail}</p>
            </li>
          ))}
        </ol>
        <p className="psnote">{DELIVERY_ENTRY}</p>
      </section>

      {/* ── TECHNOLOGY ───────────────────────────────────────────────────── */}
      <section className="pssection" aria-labelledby="pstech">
        <h2 id="pstech">Technology</h2>
        <p className="pssection__lede">
          What the platform runs today, and what a delivery builds on top of
          it.
        </p>
        <div className="pscolumns">
          <div>
            <h3 className="pscolumns__head">The platform</h3>
            <ul className="pslist">
              {PLATFORM.map((item) => (
                <li className="pslist__item" key={item.name}>
                  <h4>{item.name}</h4>
                  <p>{item.detail}</p>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="pscolumns__head">Built within an engagement</h3>
            <ul className="pslist">
              {ENGAGEMENT_CAPABILITIES.map((item) => (
                <li className="pslist__item" key={item.name}>
                  <h4>{item.name}</h4>
                  <p>{item.detail}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* ── SECURITY AND GOVERNANCE ──────────────────────────────────────── */}
      <section className="pssection" aria-labelledby="pssecurity">
        <h2 id="pssecurity">Security and governance</h2>
        <p className="pssection__lede">
          Controls that are implemented in the running system.
        </p>
        <ul className="pslist">
          {CONTROLS.map((control) => (
            <li className="pslist__item" key={control.name}>
              <h3>{control.name}</h3>
              <p>{control.detail}</p>
            </li>
          ))}
        </ul>

        <h3 className="pssection__subhead">Data governance</h3>
        <ul className="pslist">
          {DATA_GOVERNANCE.map((item) => (
            <li className="pslist__item" key={item.name}>
              <h4>{item.name}</h4>
              <p>{item.detail}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* ── COMMERCIAL ───────────────────────────────────────────────────── */}
      <section className="pssection" aria-labelledby="pscommercial">
        <h2 id="pscommercial">Indicative engagement sizes</h2>
        <ul className="psgrid psgrid--bands">
          {COMMERCIAL_BANDS.map((band) => (
            <li className="pscard pscard--band" key={band.name}>
              <h3>{band.name}</h3>
              <p className="pscard__range">{band.range}</p>
              <p>{band.shape}</p>
            </li>
          ))}
        </ul>
        <p className="psnote">{COMMERCIAL_BASIS}</p>
      </section>

      {/* ── SUPPLIER AND PROCUREMENT ─────────────────────────────────────── */}
      <section
        className="pssection pssupplier"
        id="procurement"
        aria-labelledby="pssupplier"
      >
        <h2 id="pssupplier">Supplier and procurement information</h2>
        <p className="pssupplier__statement">{SUPPLIER.statement}</p>
        <dl className="pssupplier__facts">
          <div>
            <dt>Company</dt>
            <dd>{SUPPLIER.company}</dd>
          </div>
          <div>
            <dt>Company number</dt>
            <dd>{SUPPLIER.companyNumber}</dd>
          </div>
          <div>
            <dt>Jurisdiction</dt>
            <dd>{SUPPLIER.jurisdiction}</dd>
          </div>
          <div>
            <dt>Positioning</dt>
            <dd>{SUPPLIER.positioning}</dd>
          </div>
        </dl>
        <p className="psnote">{SUPPLIER.note}</p>

        <h3 className="pssection__subhead">Support</h3>
        <dl className="psdl">
          {SUPPORT_MODEL.map((item) => (
            <div key={item.name}>
              <dt>{item.name}</dt>
              <dd>{item.detail}</dd>
            </div>
          ))}
        </dl>

        <h3 className="pssection__subhead">Assurance and documentation</h3>
        <dl className="psdl">
          {ASSURANCE.map((item) => (
            <div key={item.name}>
              <dt>{item.name}</dt>
              <dd>{item.detail}</dd>
            </div>
          ))}
        </dl>
        <p className="psnote">{PROCUREMENT_PACK.body}</p>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────────── */}
      <section className="pscta" aria-labelledby="pscta-heading">
        <h2 id="pscta-heading">Request a pilot</h2>
        <p>
          The normal way in is a diagnostic on a defined part of an estate: what
          data exists, what it can currently support, and where the gaps are. A
          few weeks of work, ending in a written finding you can take to a
          capital decision.
        </p>
        <div className="pshero__actions">
          <a className="psbutton psbutton--primary" href={ENQUIRY}>
            Request a pilot
          </a>
          <a className="psbutton" href={ENQUIRY}>
            {PROCUREMENT_PACK.cta}
          </a>
          <Link className="psbutton psbutton--quiet" to="/contact">
            Ask a general question
          </Link>
        </div>
      </section>
    </div>
  );
}
