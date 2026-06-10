/**
 * ImpactGlobe — flagship visual-intelligence component.
 *
 * Renders a luminous rotating globe motif beside a panel of animated impact
 * KPIs. Built on the EcoIQ design system + Framer Motion (scroll reveal,
 * staggered metrics, hover micro-interactions). Reduced-motion safe.
 *
 * The heavyweight WebGL globe (three.js / R3F) will arrive later as a
 * lazy-loaded ImpactGlobe3D reusing this exact props contract.
 */
import { m } from 'framer-motion'
import { useEffect, useReducer, useRef } from 'react'
import Metric from './shared/Metric'
import { Reveal } from '../motion'
import { fadeUp, scaleIn, stagger, staggerItem, tFast } from '../motion/presets'

export interface ImpactGlobeProps {
  title?: string
  eyebrow?: string
  villages?: number
  homesUpgraded?: number
  co2ReducedTons?: number
  sponsors?: number
  ctaLabel?: string
  ctaHref?: string
  pins?: Array<{ label: string; value?: string }>
}

export default function ImpactGlobe(props: ImpactGlobeProps) {
  const {
    title = 'Khalifa Tours — Real-World Impact',
    eyebrow = 'Khalifa Tours',
    villages = 0,
    homesUpgraded = 0,
    co2ReducedTons = 0,
    sponsors = 0,
    ctaLabel,
    ctaHref,
    pins = [],
  } = props

  // Gate counters until on screen.
  const hostRef = useRef<HTMLDivElement>(null)
  const [seen, see] = useReducer(() => true, false)
  useEffect(() => {
    const el = hostRef.current
    if (!el || typeof IntersectionObserver === 'undefined') return see()
    const io = new IntersectionObserver(
      (e) => e.some((x) => x.isIntersecting) && (see(), io.disconnect()),
      { threshold: 0.25 },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])

  return (
    <Reveal variants={fadeUp} className="eiq-ig eiq-panel" >
      <div ref={hostRef} className="eiq-ig__inner">
        {/* ── Globe visual ── */}
        <m.div className="eiq-ig__visual" variants={scaleIn} aria-hidden="true">
          <svg viewBox="0 0 240 240" className="eiq-ig__globe" role="img">
            <defs>
              <radialGradient id="eiqGlobeFill" cx="38%" cy="32%" r="75%">
                <stop offset="0%" stopColor="#0d3b32" />
                <stop offset="55%" stopColor="#072019" />
                <stop offset="100%" stopColor="#03100c" />
              </radialGradient>
              <radialGradient id="eiqGlobeGlow" cx="50%" cy="50%" r="50%">
                <stop offset="58%" stopColor="rgba(0,232,154,0)" />
                <stop offset="100%" stopColor="rgba(0,232,154,0.20)" />
              </radialGradient>
            </defs>
            <circle cx="120" cy="120" r="114" fill="url(#eiqGlobeGlow)" />
            <circle
              cx="120" cy="120" r="92"
              fill="url(#eiqGlobeFill)"
              stroke="rgba(0,232,154,0.35)" strokeWidth="1"
            />
            <g className="eiq-ig__grid" stroke="rgba(0,232,154,0.22)" strokeWidth="0.75" fill="none">
              <ellipse cx="120" cy="120" rx="92" ry="32" />
              <ellipse cx="120" cy="120" rx="92" ry="60" />
              <ellipse cx="120" cy="120" rx="60" ry="92" />
              <ellipse cx="120" cy="120" rx="32" ry="92" />
              <line x1="28" y1="120" x2="212" y2="120" />
              <line x1="120" y1="28" x2="120" y2="212" />
            </g>
          </svg>

          {pins.length > 0 && (
            <m.ul className="eiq-ig__pins" variants={stagger(0.06)} initial="hidden" whileInView="show" viewport={{ once: true }}>
              {pins.slice(0, 6).map((pin, i) => (
                <m.li key={`${pin.label}-${i}`} className="eiq-ig__pin" variants={staggerItem} whileHover={{ y: -2, transition: tFast }}>
                  <span className="eiq-ig__pin-dot" />
                  <span className="eiq-ig__pin-label">{pin.label}</span>
                  {pin.value ? <span className="eiq-ig__pin-value eiq-num">{pin.value}</span> : null}
                </m.li>
              ))}
            </m.ul>
          )}
        </m.div>

        {/* ── Metrics panel ── */}
        <div className="eiq-ig__panel">
          <div className="eiq-eyebrow">{eyebrow}</div>
          <h3 className="eiq-ig__title">{title}</h3>
          <m.div className="eiq-ig__metrics" variants={stagger(0.08, 0.1)} initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.3 }}>
            <Metric label="Villages reached" value={villages} run={seen} tone="accent" />
            <Metric label="Homes upgraded" value={homesUpgraded} run={seen} />
            <Metric label="CO₂ avoided" value={co2ReducedTons} suffix="t / yr" run={seen} />
            <Metric label="Sponsors" value={sponsors} run={seen} tone="gold" />
          </m.div>
          {ctaLabel && ctaHref ? (
            <m.a className="eiq-ig__cta" href={ctaHref} whileHover={{ x: 4, transition: tFast }}>
              {ctaLabel}
              <span aria-hidden="true"> →</span>
            </m.a>
          ) : null}
        </div>
      </div>
    </Reveal>
  )
}
