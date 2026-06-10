/**
 * ImpactGlobe — EcoIQ Visual Intelligence, Phase 0 reference component.
 *
 * Purpose for Phase 0: prove the full island pipeline end to end —
 * Django JSON → typed React props → animated, self-contained visual — with a
 * small bundle and zero runtime dependencies beyond React.
 *
 * It renders a rotating SVG globe motif ringed by impact "pins", with animated
 * counters for the headline metrics (villages, homes upgraded, CO₂ avoided,
 * sponsors). It deliberately does NOT pull in three.js yet: the heavyweight 3D
 * WebGL globe will arrive in a later phase as a lazy-loaded sibling
 * (ImpactGlobe3D), reusing the exact same props contract defined here.
 *
 * Accessibility / safety:
 *   - Respects prefers-reduced-motion (no count-up, no spin).
 *   - All values have sane defaults, so a missing/partial data-props still
 *     renders something coherent rather than throwing.
 */
import { useEffect, useReducer, useRef, useState } from 'react'

export interface ImpactGlobeProps {
  /** Headline title shown above the metrics. */
  title?: string
  /** Optional short kicker/eyebrow. */
  eyebrow?: string
  /** Number of villages reached. */
  villages?: number
  /** Homes upgraded from coal to electric heating. */
  homesUpgraded?: number
  /** Tonnes of CO₂ avoided per year. */
  co2ReducedTons?: number
  /** Number of sponsors / contributing partners. */
  sponsors?: number
  /** Optional CTA. */
  ctaLabel?: string
  ctaHref?: string
  /** Pins to plot around the globe (label + optional value). */
  pins?: Array<{ label: string; value?: string }>
}

const DEFAULTS: Required<Omit<ImpactGlobeProps, 'pins' | 'ctaLabel' | 'ctaHref' | 'eyebrow'>> = {
  title: 'Khalifa Tours — Real-World Impact',
  villages: 0,
  homesUpgraded: 0,
  co2ReducedTons: 0,
  sponsors: 0,
}

function prefersReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

/** Count up to `target` over ~900ms unless reduced motion is requested. */
function useCountUp(target: number, run: boolean): number {
  const [value, setValue] = useState(run ? 0 : target)
  useEffect(() => {
    if (!run) {
      setValue(target)
      return
    }
    let raf = 0
    const start = performance.now()
    const duration = 900
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      setValue(Math.round(target * eased))
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, run])
  return value
}

function formatNumber(n: number): string {
  return n.toLocaleString('en-US')
}

function Metric({ label, value, suffix }: { label: string; value: string; suffix?: string }) {
  return (
    <div className="eiq-ig__metric">
      <div className="eiq-ig__metric-value">
        {value}
        {suffix ? <span className="eiq-ig__metric-suffix"> {suffix}</span> : null}
      </div>
      <div className="eiq-ig__metric-label">{label}</div>
    </div>
  )
}

export default function ImpactGlobe(props: ImpactGlobeProps) {
  const reduced = prefersReducedMotion()
  const animate = !reduced

  const title = props.title ?? DEFAULTS.title
  const pins = props.pins ?? []

  // Animate only once the component is on screen.
  const hostRef = useRef<HTMLDivElement>(null)
  const [visible, markVisible] = useReducer(() => true, false)
  useEffect(() => {
    if (!animate) return
    const el = hostRef.current
    if (!el || typeof IntersectionObserver === 'undefined') {
      markVisible()
      return
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          markVisible()
          io.disconnect()
        }
      },
      { threshold: 0.25 },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [animate])

  const run = animate && visible
  const villages = useCountUp(props.villages ?? DEFAULTS.villages, run)
  const homes = useCountUp(props.homesUpgraded ?? DEFAULTS.homesUpgraded, run)
  const co2 = useCountUp(props.co2ReducedTons ?? DEFAULTS.co2ReducedTons, run)
  const sponsors = useCountUp(props.sponsors ?? DEFAULTS.sponsors, run)

  return (
    <div className="eiq-ig" ref={hostRef} data-reduced={reduced ? 'true' : 'false'}>
      <div className="eiq-ig__visual" aria-hidden="true">
        <svg viewBox="0 0 240 240" className="eiq-ig__globe" role="img">
          <defs>
            <radialGradient id="eiqGlobeFill" cx="38%" cy="32%" r="75%">
              <stop offset="0%" stopColor="#0d3b32" />
              <stop offset="55%" stopColor="#072019" />
              <stop offset="100%" stopColor="#03100c" />
            </radialGradient>
            <radialGradient id="eiqGlobeGlow" cx="50%" cy="50%" r="50%">
              <stop offset="60%" stopColor="rgba(0,232,154,0)" />
              <stop offset="100%" stopColor="rgba(0,232,154,0.18)" />
            </radialGradient>
          </defs>
          <circle cx="120" cy="120" r="112" fill="url(#eiqGlobeGlow)" />
          <circle cx="120" cy="120" r="92" fill="url(#eiqGlobeFill)" stroke="rgba(0,232,154,0.35)" strokeWidth="1" />
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
          <ul className="eiq-ig__pins">
            {pins.slice(0, 6).map((pin, i) => (
              <li key={`${pin.label}-${i}`} className="eiq-ig__pin">
                <span className="eiq-ig__pin-dot" />
                <span className="eiq-ig__pin-label">{pin.label}</span>
                {pin.value ? <span className="eiq-ig__pin-value">{pin.value}</span> : null}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="eiq-ig__panel">
        {props.eyebrow ? <div className="eiq-ig__eyebrow">{props.eyebrow}</div> : null}
        <h3 className="eiq-ig__title">{title}</h3>
        <div className="eiq-ig__metrics">
          <Metric label="Villages reached" value={formatNumber(villages)} />
          <Metric label="Homes upgraded" value={formatNumber(homes)} />
          <Metric label="CO₂ avoided" value={formatNumber(co2)} suffix="t / yr" />
          <Metric label="Sponsors" value={formatNumber(sponsors)} />
        </div>
        {props.ctaLabel && props.ctaHref ? (
          <a className="eiq-ig__cta" href={props.ctaHref}>
            {props.ctaLabel}
            <span aria-hidden="true"> →</span>
          </a>
        ) : null}
      </div>
    </div>
  )
}
