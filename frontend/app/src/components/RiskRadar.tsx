/**
 * RiskRadar — multi-axis risk/ESG radar chart.
 *
 * A reusable visual-intelligence primitive: pass labelled axes (0–100) and it
 * renders a luminous polygon over a graticule, with the polygon drawing in via
 * Framer Motion and per-axis values revealing on a stagger. Reduced-motion safe.
 *
 * Used on Company pages (ESG risk radar) and anywhere a small-multiples risk
 * fingerprint is needed.
 */
import { m } from 'framer-motion'
import { tBase, tSlow } from '../motion/presets'

export interface RadarAxis {
  label: string
  /** 0–100. */
  value: number
}

export interface RiskRadarProps {
  title?: string
  eyebrow?: string
  axes?: RadarAxis[]
  /** Overall composite score shown in the center, 0–100. */
  score?: number
  scoreLabel?: string
}

const SIZE = 260
const C = SIZE / 2
const R = 96

function pointAt(angle: number, radius: number): [number, number] {
  // angle in radians, 0 at top, clockwise.
  return [C + radius * Math.sin(angle), C - radius * Math.cos(angle)]
}

export default function RiskRadar(props: RiskRadarProps) {
  const {
    title = 'ESG Risk Radar',
    eyebrow = 'Company Intelligence',
    score = 0,
    scoreLabel = 'Composite',
    axes = [],
  } = props

  const n = Math.max(axes.length, 3)
  const ring = [0.25, 0.5, 0.75, 1]

  const polygon = axes
    .map((a, i) => {
      const angle = (i / n) * Math.PI * 2
      const [x, y] = pointAt(angle, (Math.min(100, Math.max(0, a.value)) / 100) * R)
      return `${x},${y}`
    })
    .join(' ')

  return (
    <m.div
      className="eiq-radar eiq-panel"
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0, transition: tBase }}
      viewport={{ once: true, amount: 0.3 }}
    >
      <div className="eiq-radar__head">
        <div className="eiq-eyebrow">{eyebrow}</div>
        <h3 className="eiq-radar__title">{title}</h3>
      </div>

      <div className="eiq-radar__body">
        <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="eiq-radar__svg" role="img" aria-label={title}>
          <defs>
            <radialGradient id="eiqRadarFill" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="rgba(0,232,154,0.35)" />
              <stop offset="100%" stopColor="rgba(0,232,154,0.06)" />
            </radialGradient>
          </defs>

          {/* graticule rings */}
          {ring.map((r) => (
            <circle key={r} cx={C} cy={C} r={R * r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="1" />
          ))}

          {/* axis spokes + labels */}
          {axes.map((a, i) => {
            const angle = (i / n) * Math.PI * 2
            const [x, y] = pointAt(angle, R)
            const [lx, ly] = pointAt(angle, R + 18)
            return (
              <g key={a.label}>
                <line x1={C} y1={C} x2={x} y2={y} stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
                <text
                  x={lx} y={ly}
                  fill="var(--eiq-muted)" fontSize="10"
                  textAnchor={lx > C + 4 ? 'start' : lx < C - 4 ? 'end' : 'middle'}
                  dominantBaseline="middle"
                >
                  {a.label}
                </text>
              </g>
            )
          })}

          {/* data polygon — draws in */}
          {axes.length >= 3 && (
            <m.polygon
              points={polygon}
              fill="url(#eiqRadarFill)"
              stroke="var(--eiq-accent)"
              strokeWidth="1.5"
              initial={{ opacity: 0, scale: 0.6 }}
              whileInView={{ opacity: 1, scale: 1, transition: tSlow }}
              viewport={{ once: true }}
              style={{ transformOrigin: `${C}px ${C}px` }}
            />
          )}

          {/* vertices */}
          {axes.map((a, i) => {
            const angle = (i / n) * Math.PI * 2
            const [x, y] = pointAt(angle, (Math.min(100, Math.max(0, a.value)) / 100) * R)
            return <circle key={`v${i}`} cx={x} cy={y} r="3" fill="var(--eiq-accent)" />
          })}
        </svg>

        {/* center score */}
        <div className="eiq-radar__score">
          <div className="eiq-radar__score-value eiq-num">{Math.round(score)}</div>
          <div className="eiq-radar__score-label">{scoreLabel}</div>
        </div>
      </div>
    </m.div>
  )
}
