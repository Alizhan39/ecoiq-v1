/**
 * BetterWayScene — the current pathway separates into alternatives, shown
 * side by side with three safety states (eligible/conditional/blocked).
 * Blocked options are visually distinct and do not carry a "proceed" cue.
 */
import { m } from 'framer-motion'
import { Reveal, stagger, staggerItem, hoverLift } from '../../../motion'
import { betterWay } from '../content'
import ManipulatorGlyph from '../ManipulatorGlyph'

export default function BetterWayScene() {
  return (
    <Reveal as="section" className="eiq-inv__scene eiq-inv__scene--better-way">
      <div className="eiq-inv__glyph-row" aria-hidden="true">
        <ManipulatorGlyph tint="var(--eiq-info)" />
        <span className="eiq-inv__glyph-label">Compare &amp; Block — Better Way Comparison</span>
      </div>
      <p className="eiq-inv__scene-copy">{betterWay.copy}</p>

      <div className="eiq-inv__baseline">
        <span className="eiq-inv__baseline-label">{betterWay.baseline.label}</span>
        <span>{betterWay.baseline.description}</span>
      </div>

      <m.div
        className="eiq-inv__options-grid"
        variants={stagger(0.09)}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.2 }}
      >
        {betterWay.options.map((opt) => (
          <m.div
            key={opt.id}
            className={`eiq-inv__option eiq-inv__option--${opt.state}`}
            variants={staggerItem}
            whileHover={opt.state !== 'blocked' ? hoverLift.hover : undefined}
          >
            <span className={`eiq-inv__option-badge eiq-inv__option-badge--${opt.state}`}>{opt.state}</span>
            <div className="eiq-inv__option-title">{opt.label}</div>
            <div className="eiq-inv__option-desc">{opt.description}</div>
            <div className="eiq-inv__option-note">{opt.note}</div>
          </m.div>
        ))}
      </m.div>

      <p className="eiq-inv__supporting-line">{betterWay.supportingLine}</p>
    </Reveal>
  )
}
