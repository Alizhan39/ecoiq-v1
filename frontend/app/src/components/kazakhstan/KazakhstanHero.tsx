/**
 * KazakhstanHero — flagship hero for the Transition Brief.
 * Animated Kazakhstan map (drawing border, pulsing region nodes, ambient
 * graticule) + live headline metrics + a transition score ring.
 */
import { m } from 'framer-motion'
import Metric from '../shared/Metric'
import ScoreRing from '../shared/ScoreRing'
import { Reveal, fadeUp, stagger, tSlow } from '../../motion'
import { KZ_PATH, KZ_REGIONS, KZ_VIEWBOX } from './geo'

export interface KazakhstanHeroProps {
  eyebrow?: string
  title?: string
  subtitle?: string
  transitionScore?: number
  households?: number
  fundingNeededM?: number
  co2PotentialMt?: number
  regionsActive?: number
}

export default function KazakhstanHero(props: KazakhstanHeroProps) {
  const {
    eyebrow = 'EcoIQ Climate Intelligence · 2025',
    title = 'Kazakhstan Energy Transition Brief',
    subtitle = 'Coal-to-electric heating retrofit — investment-grade transition intelligence across four southern regions.',
    transitionScore = 0,
    households = 0,
    fundingNeededM = 0,
    co2PotentialMt = 0,
    regionsActive = 0,
  } = props

  return (
    <Reveal variants={fadeUp} className="eiq-khero eiq-panel">
      <div className="eiq-khero__grid">
        {/* ── Map visual ── */}
        <div className="eiq-khero__map" aria-hidden="true">
          <svg viewBox={KZ_VIEWBOX} className="eiq-khero__svg" role="img">
            <defs>
              <linearGradient id="eiqKzFill" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="rgba(0,232,154,0.16)" />
                <stop offset="100%" stopColor="rgba(0,232,154,0.03)" />
              </linearGradient>
              <radialGradient id="eiqKzAmbient" cx="62%" cy="78%" r="55%">
                <stop offset="0%" stopColor="rgba(0,232,154,0.18)" />
                <stop offset="100%" stopColor="rgba(0,232,154,0)" />
              </radialGradient>
            </defs>

            <rect x="0" y="0" width="1000" height="480" fill="url(#eiqKzAmbient)" />

            {/* graticule */}
            <g stroke="rgba(255,255,255,0.05)" strokeWidth="1">
              {[100, 200, 300].map((y) => (
                <line key={`h${y}`} x1="40" y1={y} x2="960" y2={y} />
              ))}
              {[250, 500, 750].map((x) => (
                <line key={`v${x}`} x1={x} y1="40" x2={x} y2="420" />
              ))}
            </g>

            <m.path
              d={KZ_PATH}
              fill="url(#eiqKzFill)"
              stroke="var(--eiq-accent)"
              strokeWidth="1.6"
              initial={{ pathLength: 0, opacity: 0 }}
              whileInView={{ pathLength: 1, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 1.6, ease: 'easeInOut' }}
            />

            {/* region nodes */}
            {KZ_REGIONS.map((r, i) => (
              <g key={r.id}>
                <m.circle
                  cx={r.x}
                  cy={r.y}
                  r="6"
                  fill="var(--eiq-gold)"
                  initial={{ scale: 0, opacity: 0 }}
                  whileInView={{ scale: 1, opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.9 + i * 0.15, ...tSlow }}
                  style={{ transformOrigin: `${r.x}px ${r.y}px` }}
                />
                <circle cx={r.x} cy={r.y} r="6" fill="none" stroke="var(--eiq-gold)" strokeWidth="1.5" className="eiq-khero__pulse" />
              </g>
            ))}
          </svg>
        </div>

        {/* ── Copy + score ── */}
        <div className="eiq-khero__body">
          <div className="eiq-eyebrow">{eyebrow}</div>
          <h1 className="eiq-khero__title">{title}</h1>
          <p className="eiq-khero__subtitle">{subtitle}</p>

          <div className="eiq-khero__score">
            <ScoreRing value={transitionScore} label="Transition Readiness" />
          </div>
        </div>
      </div>

      {/* ── Live metrics strip ── */}
      <m.div className="eiq-khero__metrics" variants={stagger(0.08, 0.2)} initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.3 }}>
        <Metric label="Households in scope" value={households} tone="accent" />
        <Metric label="Funding required" value={fundingNeededM} suffix="$M" />
        <Metric label="CO₂ abatement potential" value={co2PotentialMt} suffix="Mt / yr" tone="gold" />
        <Metric label="Active regions" value={regionsActive} />
      </m.div>
    </Reveal>
  )
}
