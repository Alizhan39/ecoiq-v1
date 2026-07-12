/**
 * PillarsSection — the five EcoIQ pillars. Normal document flow, renders
 * after the cinematic sequence releases. Reuses Reveal + the shared
 * stagger/hoverLift presets — no glassmorphism, no SaaS gradients.
 *
 * Card entrance (opacity/y/scale) and the icon glow use local variants tuned
 * to this section's spec rather than the generic `staggerItem`, since the
 * glow is deliberately delayed relative to its card — both still propagate
 * from the same parent `stagger()` trigger, just with different per-element
 * `transition.delay`, which is how Framer's variant propagation is meant to
 * be used (no extra observers needed).
 */
import { m, type Variants } from 'framer-motion'
import { Reveal, stagger, tBase, tFast, hoverLift } from '../../motion'
import { pillars } from './content'

const cardVariant: Variants = {
  hidden: { opacity: 0, y: 24, scale: 0.985 },
  show: { opacity: 1, y: 0, scale: 1, transition: tBase },
}

const iconGlowVariant: Variants = {
  hidden: { opacity: 0, scale: 0.8 },
  show: { opacity: 1, scale: 1, transition: { ...tFast, delay: 0.16 } },
}

const ICONS: Record<string, JSX.Element> = {
  'Evidence Memory': (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <path d="M7 3h7l4 4v14H7z" strokeLinejoin="round" />
      <path d="M14 3v4h4" strokeLinejoin="round" />
      <path d="M9.5 12h5M9.5 15h5M9.5 18h3" strokeLinecap="round" />
    </svg>
  ),
  'AI Agents': (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <circle cx="12" cy="6" r="2.4" />
      <circle cx="5.5" cy="17" r="2.4" />
      <circle cx="18.5" cy="17" r="2.4" />
      <path d="M12 8.4V13M12 13 7.2 15.2M12 13l4.8 2.2" strokeLinecap="round" />
    </svg>
  ),
  'Humanity in Control': (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <circle cx="12" cy="7" r="3.2" />
      <path d="M5 21c0-4 3.2-6.5 7-6.5s7 2.5 7 6.5" strokeLinecap="round" />
    </svg>
  ),
  'Verified Outcomes': (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" strokeLinejoin="round" />
      <path d="M8.7 12.2l2.2 2.2 4.4-4.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  'The Better Way': (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M15.5 8.5l-2 5-5 2 2-5z" strokeLinejoin="round" />
    </svg>
  ),
}

export default function PillarsSection() {
  return (
    <Reveal as="section" className="eiq-pillars">
      <div className="eiq-pillars__head">
        <div className="eiq-eyebrow">The EcoIQ System</div>
        <h2 className="eiq-pillars__heading">Five pillars, one continuous decision system.</h2>
      </div>

      <m.div className="eiq-pillars__grid" variants={stagger(0.1)} initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.2 }}>
        {pillars.map((p) => (
          <m.div
            key={p.title}
            className="eiq-pillars__card"
            variants={cardVariant}
            whileHover={hoverLift.hover}
            whileFocus={hoverLift.hover}
            tabIndex={0}
          >
            <m.div className="eiq-pillars__icon" variants={iconGlowVariant}>
              {ICONS[p.title]}
            </m.div>
            <h3 className="eiq-pillars__title">{p.title}</h3>
            <p className="eiq-pillars__body">{p.body}</p>
          </m.div>
        ))}
      </m.div>
    </Reveal>
  )
}
