/**
 * FinalJoiningScene — Scene 12, the resolution. Manipulators recede (no new
 * motion — reused fadeUp-style Reveal entrance, nothing retracts via a new
 * primitive), the vision statement is explicitly disclaimed as architecture
 * rather than achieved scale, and the story closes on the real final CTAs.
 */
import { m } from 'framer-motion'
import { Reveal, stagger, staggerItem, hoverLift } from '../../../motion'
import { finalJoining } from '../content'

export default function FinalJoiningScene() {
  return (
    <Reveal as="section" className="eiq-inv__scene eiq-inv__scene--final">
      <m.div
        className="eiq-inv__progression"
        variants={stagger(0.12)}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.3 }}
      >
        {finalJoining.progression.map((step, i) => (
          <m.div key={step} className="eiq-inv__progression-step" variants={staggerItem}>
            <span>{step}</span>
            {i < finalJoining.progression.length - 1 && <span className="eiq-inv__progression-arrow" aria-hidden="true">→</span>}
          </m.div>
        ))}
      </m.div>
      <p className="eiq-inv__illustrative-note">{finalJoining.progressionDisclaimer}</p>

      <div className="eiq-inv__brand-moment eiq-inv__brand-moment--final">
        <div className="eiq-inv__brand-word">{finalJoining.brand}</div>
        <div className="eiq-inv__brand-triple">
          {finalJoining.triple.map((t) => (
            <span key={t}>{t}</span>
          ))}
        </div>
      </div>

      <div className="eiq-inv__supporting-lines">
        {finalJoining.supportingLines.map((line) => (
          <p key={line}>{line}</p>
        ))}
      </div>

      <m.div
        className="eiq-inv__final-cta-row"
        variants={stagger(0.1)}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.4 }}
      >
        <m.a
          className="eiq-btn eiq-btn--primary"
          variants={staggerItem}
          whileHover={hoverLift.hover}
          href={finalJoining.ctas.primary.href}
        >
          {finalJoining.ctas.primary.label}
        </m.a>
        <m.a
          className="eiq-btn eiq-btn--secondary"
          variants={staggerItem}
          whileHover={hoverLift.hover}
          href={finalJoining.ctas.secondary.href}
        >
          {finalJoining.ctas.secondary.label}
        </m.a>
        <m.a
          className="eiq-btn eiq-btn--secondary"
          variants={staggerItem}
          whileHover={hoverLift.hover}
          href={finalJoining.ctas.investor.href}
        >
          {finalJoining.ctas.investor.label}
        </m.a>
      </m.div>
      <a className="eiq-inv__text-link" href={finalJoining.ctas.textLink.href}>
        {finalJoining.ctas.textLink.label}
      </a>
    </Reveal>
  )
}
