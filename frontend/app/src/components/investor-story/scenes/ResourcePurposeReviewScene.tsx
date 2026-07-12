/**
 * ResourcePurposeReviewScene — leads with the one message that matters in
 * three seconds (does this project deserve capital in this form at all),
 * then a compact Resource → Purpose Review → Stewardship Questions →
 * Proceed/Reconsider/Block flow. The seven stewardship questions are
 * preserved verbatim (full text still in the DOM, nothing deleted) from
 * capital_guardian/services/resource_purpose_review.py, but presented as a
 * dense node grid — term + one-word gloss prominent, full question as
 * smaller supporting text — rather than seven stacked paragraphs.
 */
import { m } from 'framer-motion'
import { Reveal, drawPath, popIn, stagger, staggerItem } from '../../../motion'
import { resourcePurposeReview, stewardshipQuestions } from '../content'
import ManipulatorGlyph from '../ManipulatorGlyph'

export default function ResourcePurposeReviewScene() {
  return (
    <Reveal as="section" className="eiq-inv__scene eiq-inv__scene--rpr">
      <div className="eiq-inv__glyph-row" aria-hidden="true">
        <ManipulatorGlyph tint="var(--eiq-gold)" />
        <span className="eiq-inv__glyph-label">Review — Resource Purpose Review</span>
      </div>

      <h2 className="eiq-inv__dominant-message">{resourcePurposeReview.dominantMessage}</h2>
      <p className="eiq-inv__scene-copy">{resourcePurposeReview.copy}</p>

      {/* Resource → Purpose Review → Stewardship Questions → outcome, the
          3-second visual shape of this whole scene. */}
      <m.div
        className="eiq-inv__rpr-flow"
        variants={stagger(0.1)}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.3 }}
      >
        {resourcePurposeReview.decisionFlow.map((step, i) => (
          <m.div key={step} className="eiq-inv__rpr-flow-step" variants={staggerItem}>
            <span>{step}</span>
            {i < resourcePurposeReview.decisionFlow.length - 1 && (
              <svg className="eiq-inv__rpr-flow-arrow" viewBox="0 0 24 12" aria-hidden="true">
                <m.path
                  d="M0 6 H20 M14 1 L20 6 L14 11"
                  variants={drawPath({ duration: 0.4, delay: i * 0.08 })}
                  fill="none"
                  stroke="var(--eiq-gold)"
                  strokeWidth="1.5"
                />
              </svg>
            )}
          </m.div>
        ))}
      </m.div>

      {/* Compact stewardship node grid — full honest meaning preserved as
          smaller supporting text, term + one-word gloss carry the 3-second read. */}
      <m.div
        className="eiq-inv__stewardship-grid eiq-inv__stewardship-grid--compact"
        variants={stagger(0.06)}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.2 }}
      >
        {stewardshipQuestions.map((q) => (
          <m.div key={q.term} className="eiq-inv__stewardship-node" variants={staggerItem}>
            <div className="eiq-inv__stewardship-term">{q.term}</div>
            <div className="eiq-inv__stewardship-short">{q.short}</div>
            <div className="eiq-inv__stewardship-body">{q.body}</div>
          </m.div>
        ))}
      </m.div>

      {/* Outcome: proceed / reconsider / block — the same three safety
          states used in the Better Way scene, reused not reinvented. */}
      <m.div
        className="eiq-inv__rpr-outcomes"
        variants={stagger(0.1)}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.3 }}
      >
        {resourcePurposeReview.outcomes.map((o) => (
          <m.div
            key={o.label}
            className={`eiq-inv__rpr-outcome eiq-inv__rpr-outcome--${o.tone}`}
            variants={popIn(undefined, 0.9)}
          >
            <span className="eiq-inv__rpr-outcome-label">{o.label}</span>
            <span className="eiq-inv__rpr-outcome-detail">{o.detail}</span>
          </m.div>
        ))}
      </m.div>

      {/* Pathway of physical/economic consequences — preserved from the
          original scene, now secondary to the decision flow above it. */}
      <div className="eiq-inv__pathway eiq-inv__pathway--secondary">
        {resourcePurposeReview.pathway.map((step, i) => (
          <div key={step} className="eiq-inv__pathway-step">
            <span>{step}</span>
            {i < resourcePurposeReview.pathway.length - 1 && <span className="eiq-inv__pathway-sep" aria-hidden="true">→</span>}
          </div>
        ))}
      </div>

      <p className="eiq-inv__scene-copy eiq-inv__scene-copy--close">{resourcePurposeReview.closingCopy}</p>
    </Reveal>
  )
}
