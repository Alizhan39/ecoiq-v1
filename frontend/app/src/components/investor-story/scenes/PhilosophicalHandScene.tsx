/**
 * PhilosophicalHandScene — Scene 11, the true visual climax. Deliberately
 * NOT built from the eyebrow/heading/paragraph/card shell every other scene
 * uses — full-bleed composition, large negative space, and manipulators at
 * actor scale (120px, not the 44–56px badge size used everywhere else).
 *
 * Reveal order builds the "capital and real-world start disconnected, then
 * EcoIQ forms the bridge" idea entirely through stagger delay (existing
 * `stagger()` primitive, just called with larger/later delay values — no
 * new timing token, no new primitive): capital side → real-world side →
 * the three manipulators → the large headline only after the bridge has
 * visually formed → the mechanism recap → the brand moment.
 */
import { m } from 'framer-motion'
import { Reveal, drawPath, stagger, staggerItem } from '../../../motion'
import { philosophicalHand } from '../content'
import ManipulatorGlyph from '../ManipulatorGlyph'

export default function PhilosophicalHandScene() {
  return (
    <Reveal as="section" className="eiq-inv__scene eiq-inv__scene--bridge eiq-inv__scene--climax">
      <div className="eiq-inv__climax-bleed">
        <div className="eiq-inv__climax-eyebrow eiq-eyebrow">{philosophicalHand.eyebrow}</div>
        <p className="eiq-inv__climax-question">{philosophicalHand.question}</p>
        <p className="eiq-inv__climax-answer">{philosophicalHand.answer}</p>

        <div className="eiq-inv__climax-triptych">
          {/* Capital — left, disconnected at first */}
          <m.div
            className="eiq-inv__climax-side eiq-inv__climax-side--capital"
            variants={stagger(0.09)}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, amount: 0.15 }}
          >
            <span className="eiq-inv__climax-side-label">{philosophicalHand.leftLabel}</span>
            {philosophicalHand.capitalFlow.map((step) => (
              <m.div key={step} className="eiq-inv__climax-flow-step" variants={staggerItem}>
                {step}
              </m.div>
            ))}
          </m.div>

          {/* EcoIQ — the three manipulators, forming the bridge, revealed after both sides */}
          <m.div
            className="eiq-inv__climax-center"
            variants={stagger(0.16, 0.35)}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, amount: 0.15 }}
          >
            {philosophicalHand.manipulators.map((man) => (
              <m.div key={man.label} className="eiq-inv__climax-manipulator" variants={staggerItem}>
                <ManipulatorGlyph tint={man.tint} size={120} />
                <h3>{man.label}</h3>
                <ul>
                  {man.actions.map((a) => (
                    <li key={a}>{a}</li>
                  ))}
                </ul>
                {man.note && <p className="eiq-inv__climax-manipulator-note">{man.note}</p>}
              </m.div>
            ))}
            <svg className="eiq-inv__climax-span" viewBox="0 0 400 12" preserveAspectRatio="none" aria-hidden="true">
              <m.path
                d="M0 6 H400"
                variants={drawPath({ duration: 1.1, delay: 0.6 })}
                fill="none"
                stroke="var(--eiq-border-accent)"
                strokeWidth="1.5"
              />
            </svg>
          </m.div>

          {/* Real-world need — right, disconnected at first */}
          <m.div
            className="eiq-inv__climax-side eiq-inv__climax-side--world"
            variants={stagger(0.07, 0.1)}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, amount: 0.15 }}
          >
            <span className="eiq-inv__climax-side-label">{philosophicalHand.rightLabel}</span>
            {philosophicalHand.transformExamples.map((ex) => (
              <m.div key={ex} className="eiq-inv__climax-world-chip" variants={staggerItem}>
                {ex}
              </m.div>
            ))}
          </m.div>
        </div>

        {/* The statement — largest typography on the homepage; escalation is
            entirely type-scale + space, not a new animation. Mount-triggered
            (not whileInView) with a fixed delay: this element sits ~19,000px
            down the page, and its own whileInView tracking was found to
            never fire that deep in this environment even when the element
            was fully centered in viewport — the outer Reveal already gates
            the whole scene to when it's scrolled into view, so a delayed
            mount animation still reads as a staged reveal once visible. */}
        <m.div
          className="eiq-inv__climax-statement"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.9 }}
        >
          <h2 className="eiq-inv__climax-headline">
            <span>{philosophicalHand.headline}</span>
            <span>{philosophicalHand.headlineLine2}</span>
          </h2>
        </m.div>

        {/* Mechanism recap — the concrete six-step chain behind the metaphor,
            now subordinate to the statement rather than competing with it. */}
        <m.div
          className="eiq-inv__bridge-chain"
          variants={stagger(0.08)}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.3 }}
        >
          {philosophicalHand.chain.map((step, i) => (
            <m.div key={step} className="eiq-inv__bridge-chain-step" variants={staggerItem}>
              <span>{step}</span>
              {i < philosophicalHand.chain.length - 1 && (
                <span className="eiq-inv__bridge-chain-arrow" aria-hidden="true">→</span>
              )}
            </m.div>
          ))}
        </m.div>

        <m.div
          className="eiq-inv__closing-lines"
          variants={stagger(0.1)}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.4 }}
        >
          {philosophicalHand.closingLines.map((line) => (
            <m.p key={line} variants={staggerItem}>
              {line}
            </m.p>
          ))}
        </m.div>

        <div className="eiq-inv__brand-moment">
          <div className="eiq-inv__brand-word">{philosophicalHand.brand}</div>
          <div className="eiq-inv__brand-triple">
            {philosophicalHand.triple.map((t) => (
              <span key={t}>{t}</span>
            ))}
          </div>
        </div>
      </div>
    </Reveal>
  )
}
