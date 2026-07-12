/**
 * CapitalGuardianScene — the real Capital Guardian lifecycle stage sequence
 * (audited from capital_trace.py's capital_protection_chain_for_entry), plus
 * one worked example of the real red-flag-rule concept. No live entry is
 * bound to this project, so per-stage status is illustrative.
 */
import { m } from 'framer-motion'
import { Reveal, drawPath, stagger, staggerItem } from '../../../motion'
import { capitalGuardian } from '../content'
import ManipulatorGlyph from '../ManipulatorGlyph'

export default function CapitalGuardianScene() {
  return (
    <Reveal as="section" className="eiq-inv__scene eiq-inv__scene--capital-guardian">
      <div className="eiq-inv__glyph-row" aria-hidden="true">
        <ManipulatorGlyph tint="var(--eiq-accent)" />
        <span className="eiq-inv__glyph-label">Guide &amp; Protect — Capital Guardian &amp; Monitoring</span>
      </div>
      <p className="eiq-inv__scene-copy">{capitalGuardian.copy}</p>
      <p className="eiq-inv__supporting-line">{capitalGuardian.supportingLine}</p>

      <m.div
        className="eiq-inv__lifecycle"
        variants={stagger(0.07)}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.2 }}
      >
        {capitalGuardian.stages.map((stage, i) => (
          <m.div key={stage.label} className="eiq-inv__lifecycle-stage" variants={staggerItem}>
            <div className="eiq-inv__lifecycle-dot" />
            <div className="eiq-inv__lifecycle-label">{stage.label}</div>
            <div className="eiq-inv__lifecycle-detail eiq-num">{stage.detail}</div>
            {i < capitalGuardian.stages.length - 1 && (
              <svg className="eiq-inv__lifecycle-connector" viewBox="0 0 40 4" aria-hidden="true">
                <m.line x1="0" y1="2" x2="40" y2="2" variants={drawPath({ duration: 0.35, delay: i * 0.05 })} stroke="var(--eiq-border-accent)" strokeWidth="2" />
              </svg>
            )}
          </m.div>
        ))}
      </m.div>

      <div className="eiq-inv__redflag-example">
        <span className="eiq-inv__redflag-barrier" aria-hidden="true" />
        <div>
          <div className="eiq-inv__redflag-title">{capitalGuardian.redFlagExample.label}</div>
          <div className="eiq-inv__redflag-desc">{capitalGuardian.redFlagExample.description}</div>
          <div className="eiq-inv__redflag-note">{capitalGuardian.redFlagExample.note}</div>
        </div>
      </div>
    </Reveal>
  )
}
