/**
 * ExpectedVsActualScene — split comparison. Field names mirror the real
 * execution_monitoring.expected_vs_actual() shape; "NOT YET REPORTED" is
 * used verbatim because it's the literal string that real service returns
 * when no actual value has been recorded — not an invented placeholder.
 */
import { m } from 'framer-motion'
import { Reveal, stagger, staggerItem } from '../../../motion'
import { expectedVsActual } from '../content'
import ManipulatorGlyph from '../ManipulatorGlyph'

export default function ExpectedVsActualScene() {
  return (
    <Reveal as="section" className="eiq-inv__scene eiq-inv__scene--eva">
      <div className="eiq-inv__glyph-row" aria-hidden="true">
        <ManipulatorGlyph tint="var(--eiq-info)" />
        <span className="eiq-inv__glyph-label">Verify — Verified Outcome</span>
      </div>
      <p className="eiq-inv__scene-copy">{expectedVsActual.copy}</p>

      <div className="eiq-inv__eva-head">
        <span>Expected</span>
        <span>Actual</span>
      </div>

      <m.div
        variants={stagger(0.08)}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.3 }}
      >
        {expectedVsActual.metrics.map((m_) => (
          <m.div key={m_.label} className="eiq-inv__eva-row" variants={staggerItem}>
            <span className="eiq-inv__eva-metric-label">{m_.label}</span>
            <span className="eiq-inv__eva-expected eiq-num">{m_.expected}</span>
            <span className="eiq-inv__eva-actual eiq-num">{m_.actual}</span>
          </m.div>
        ))}
      </m.div>
    </Reveal>
  )
}
