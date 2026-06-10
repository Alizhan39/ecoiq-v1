/**
 * TimelineScene — Sadaqah Jariyah: impact that keeps growing after you leave.
 * A tree of ongoing charity gains height and canopy across 1 / 5 / 10 years,
 * while cumulative metrics (energy saved, emissions avoided, families helped)
 * count up. The visual literally keeps growing as the reader scrolls.
 */
import { m } from 'framer-motion'
import { useCountUp, formatNumber } from '../../../hooks/useCountUp'
import { pick, sceneEase as t, type SceneProps } from './types'

const YEARS = ['1 year', '5 years', '10 years']
const MULT = [1, 5, 10]
// Canopy layers revealed per stage (cumulative).
const CANOPY = [
  { cx: 0, cy: -70, r: 26 },
  { cx: -22, cy: -54, r: 22 },
  { cx: 22, cy: -54, r: 22 },
  { cx: -34, cy: -34, r: 18 },
  { cx: 34, cy: -34, r: 18 },
  { cx: 0, cy: -92, r: 20 },
]

function GrowMetric({ label, base, suffix, active }: { label: string; base: number; suffix: string; active: number }) {
  const value = base * pick(MULT, active)
  const n = useCountUp(value, true, 700)
  return (
    <div className="eiq-tl__metric">
      <div className="eiq-tl__metric-val eiq-num">{formatNumber(n)}<span className="eiq-tl__metric-suffix"> {suffix}</span></div>
      <div className="eiq-tl__metric-label">{label}</div>
    </div>
  )
}

export default function TimelineScene({ active, data = {} }: SceneProps) {
  const stage = Math.min(active, 2)
  const trunkH = [40, 64, 86][stage]
  const canopyCount = [2, 4, 6][stage]
  const energyBase = data.energyMwhPerYear ?? 1200
  const co2Base = data.co2PerYear ?? 1600
  const familiesBase = data.familiesPerYear ?? 480

  return (
    <div className="eiq-tl">
      <svg viewBox="0 0 300 280" className="eiq-scene__svg eiq-tl__svg" role="img" aria-label="Growing impact over 1, 5 and 10 years">
        <defs>
          <radialGradient id="eiqTlGlow" cx="50%" cy="40%" r="55%">
            <stop offset="0%" stopColor="rgba(0,232,154,0.16)" />
            <stop offset="100%" stopColor="rgba(0,232,154,0)" />
          </radialGradient>
          <clipPath id="eiqTlClip"><rect width="300" height="280" rx="16" /></clipPath>
        </defs>
        <g clipPath="url(#eiqTlClip)">
          <rect width="300" height="280" fill="#07201c" />
          <rect width="300" height="280" fill="url(#eiqTlGlow)" />
          <line x1="40" y1="232" x2="260" y2="232" stroke="rgba(255,255,255,0.08)" />

          <g transform="translate(150 232)">
            {/* trunk */}
            <m.rect x="-5" width="10" rx="2" fill="#3a6f57" animate={{ y: -trunkH, height: trunkH }} transition={t} />
            {/* canopy (cumulative reveal) */}
            <g transform={`translate(0 ${0})`}>
              {CANOPY.map((c, i) => (
                <m.circle
                  key={i}
                  cx={c.cx}
                  r={c.r}
                  fill={i % 2 ? '#12c089' : '#0fae7c'}
                  initial={false}
                  animate={{ cy: c.cy - (trunkH - 40), opacity: i < canopyCount ? 0.92 : 0, scale: i < canopyCount ? 1 : 0.3 }}
                  transition={t}
                  style={{ transformOrigin: 'center' }}
                />
              ))}
            </g>
            {/* falling/floating leaves = ongoing benefit */}
            {[-30, 14, 40].map((lx, i) => (
              <circle key={i} cx={lx} cy={-trunkH - 10} r="3" fill="#7ef5cf" className={`eiq-leaf eiq-leaf--${i}`} />
            ))}
          </g>

          {/* year marker */}
          <text x="150" y="262" textAnchor="middle" fontSize="13" fontWeight="800" fill="#00e89a">{pick(YEARS, stage)}</text>
        </g>
      </svg>

      <div className="eiq-tl__metrics">
        <GrowMetric label="Energy saved" base={energyBase} suffix="MWh" active={active} />
        <GrowMetric label="CO₂ avoided" base={co2Base} suffix="t" active={active} />
        <GrowMetric label="Families helped" base={familiesBase} suffix="" active={active} />
      </div>
    </div>
  )
}
