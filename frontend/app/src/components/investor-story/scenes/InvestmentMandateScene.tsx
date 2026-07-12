/**
 * InvestmentMandateScene — introduces the investor side via a structured
 * mandate instrument, not a handshake. The mandate concept itself has no
 * live backend model (audited — confirmed absent); every value here is
 * explicitly labelled illustrative.
 *
 * Hierarchy: Mandate → Fit Check → Aligned/Conditional/Not Aligned → Human
 * Review. Headline criteria + the overall fit verdict carry the 3-second
 * read; the remaining criteria and the six individual fit dimensions are
 * preserved in full as secondary, smaller detail — not deleted.
 */
import { m } from 'framer-motion'
import { Reveal, stagger, staggerItem, popIn } from '../../../motion'
import { mandate } from '../content'
import ManipulatorGlyph from '../ManipulatorGlyph'

export default function InvestmentMandateScene() {
  return (
    <Reveal as="section" className="eiq-inv__scene eiq-inv__scene--mandate">
      <div className="eiq-inv__glyph-row" aria-hidden="true">
        <ManipulatorGlyph tint="var(--eiq-gold)" />
        <span className="eiq-inv__glyph-label">Present — Financial Modelling &amp; Capital Allocation</span>
      </div>

      <h2 className="eiq-inv__dominant-message">{mandate.dominantMessage}</h2>

      <div className="eiq-inv__mandate-card">
        <div className="eiq-inv__mandate-head">
          <span className="eiq-inv__flag">Illustrative</span>
          <h3 className="eiq-inv__mandate-title">{mandate.title}</h3>
          <p className="eiq-inv__mandate-sub">{mandate.sublabel}</p>
        </div>

        <m.div
          className="eiq-inv__mandate-criteria"
          variants={stagger(0.06)}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.3 }}
        >
          {mandate.headlineCriteria.map((c) => (
            <m.div key={c.label} className="eiq-inv__mandate-criterion" variants={staggerItem}>
              <div className="eiq-inv__mandate-criterion-label">{c.label}</div>
              <div className="eiq-inv__mandate-criterion-value">{c.value}</div>
            </m.div>
          ))}
        </m.div>

        <details className="eiq-inv__mandate-more">
          <summary>+{mandate.secondaryCriteria.length} more criteria</summary>
          <div className="eiq-inv__mandate-criteria eiq-inv__mandate-criteria--secondary">
            {mandate.secondaryCriteria.map((c) => (
              <div key={c.label} className="eiq-inv__mandate-criterion">
                <div className="eiq-inv__mandate-criterion-label">{c.label}</div>
                <div className="eiq-inv__mandate-criterion-value">{c.value}</div>
              </div>
            ))}
          </div>
        </details>
      </div>

      <p className="eiq-inv__scene-copy">{mandate.copy}</p>

      {/* Overall verdict — the dominant fit signal. Mount-triggered (not
          whileInView): this element's own viewport tracking was found not
          to fire reliably this deep in the page even when fully centered
          in view; the outer Reveal already gates the whole scene to when
          it scrolls into view, so this still reads as a staged reveal. */}
      <m.div
        className={`eiq-inv__fit-verdict eiq-inv__fit-verdict--${mandate.overallFit.verdict.toLowerCase()}`}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, delay: 0.3 }}
      >
        <span className="eiq-inv__fit-verdict-label">{mandate.overallFit.verdict}</span>
        <span className="eiq-inv__fit-verdict-detail">{mandate.overallFit.detail}</span>
      </m.div>

      <details className="eiq-inv__mandate-more">
        <summary>See all 6 fit dimensions</summary>
        <m.div
          className="eiq-inv__fit-grid"
          variants={stagger(0.07)}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.3 }}
        >
          {mandate.fitChecks.map((f) => (
            <m.div key={f.label} className="eiq-inv__fit-chip" variants={popIn(undefined, 0.9)}>
              <span className="eiq-inv__fit-label">{f.label}</span>
              <span className="eiq-inv__fit-note">{f.note}</span>
            </m.div>
          ))}
        </m.div>
      </details>

      <p className="eiq-inv__illustrative-note">{mandate.humanReviewNote}</p>

      <div className="eiq-inv__cta-row">
        <a className="eiq-btn eiq-btn--primary" href={mandate.primaryCta.href}>
          {mandate.primaryCta.label}
        </a>
        <a className="eiq-btn eiq-btn--secondary" href={mandate.secondaryCta.href}>
          {mandate.secondaryCta.label}
        </a>
      </div>
    </Reveal>
  )
}
