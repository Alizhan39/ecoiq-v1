/**
 * ESGGraph — animated multi-series trajectory chart (E / S / G over time).
 * Draws each line in via pathLength, fills an area under the focus series, and
 * reveals the legend on a stagger. Reduced-motion safe.
 */
import { m } from 'framer-motion'
import { Reveal, fadeUp, stagger, staggerItem } from '../motion'

export interface ESGSeries {
  key: string
  label: string
  color: string
  /** y-values 0–100, evenly spaced over `years`. */
  values: number[]
}

export interface ESGGraphProps {
  eyebrow?: string
  title?: string
  years?: (number | string)[]
  series?: ESGSeries[]
}

const W = 720
const H = 320
const PAD = { l: 40, r: 20, t: 20, b: 36 }

export default function ESGGraph(props: ESGGraphProps) {
  const {
    eyebrow = 'Trajectory',
    title = 'ESG Performance Trajectory',
    years = [],
    series = [],
  } = props

  const innerW = W - PAD.l - PAD.r
  const innerH = H - PAD.t - PAD.b
  const n = Math.max(years.length, 2)

  const xAt = (i: number) => PAD.l + (i / (n - 1)) * innerW
  const yAt = (v: number) => PAD.t + (1 - Math.min(100, Math.max(0, v)) / 100) * innerH

  const toPath = (vals: number[]) =>
    vals.map((v, i) => `${i === 0 ? 'M' : 'L'}${xAt(i)},${yAt(v)}`).join(' ')

  const areaPath = (vals: number[]) =>
    `${toPath(vals)} L${xAt(vals.length - 1)},${PAD.t + innerH} L${xAt(0)},${PAD.t + innerH} Z`

  return (
    <Reveal variants={fadeUp} className="eiq-esg eiq-panel">
      <div className="eiq-eyebrow">{eyebrow}</div>
      <h2 className="eiq-esg__title">{title}</h2>

      <svg viewBox={`0 0 ${W} ${H}`} className="eiq-esg__svg" role="img" aria-label={title}>
        <defs>
          <linearGradient id="eiqEsgArea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(0,232,154,0.22)" />
            <stop offset="100%" stopColor="rgba(0,232,154,0)" />
          </linearGradient>
        </defs>

        {/* gridlines */}
        {[0, 25, 50, 75, 100].map((g) => (
          <g key={g}>
            <line x1={PAD.l} y1={yAt(g)} x2={W - PAD.r} y2={yAt(g)} stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
            <text x={PAD.l - 8} y={yAt(g) + 3} fontSize="10" fill="var(--eiq-faint)" textAnchor="end">
              {g}
            </text>
          </g>
        ))}

        {/* x labels */}
        {years.map((yr, i) => (
          <text key={`x${i}`} x={xAt(i)} y={H - 12} fontSize="10" fill="var(--eiq-muted)" textAnchor="middle">
            {yr}
          </text>
        ))}

        {/* area under first series */}
        {series[0] && (
          <m.path
            d={areaPath(series[0].values)}
            fill="url(#eiqEsgArea)"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.6 }}
          />
        )}

        {/* series lines */}
        {series.map((s, si) => (
          <m.path
            key={s.key}
            d={toPath(s.values)}
            fill="none"
            stroke={s.color}
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: 0, opacity: 0 }}
            whileInView={{ pathLength: 1, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 1.2, ease: 'easeInOut', delay: si * 0.2 }}
          />
        ))}
      </svg>

      <m.ul className="eiq-esg__legend" variants={stagger(0.08, 0.4)} initial="hidden" whileInView="show" viewport={{ once: true }}>
        {series.map((s) => (
          <m.li key={s.key} variants={staggerItem}>
            <span className="eiq-esg__swatch" style={{ background: s.color }} />
            {s.label}
          </m.li>
        ))}
      </m.ul>
    </Reveal>
  )
}
