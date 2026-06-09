/**
 * Metric — a single animated KPI tile. Reusable across all visual-intelligence
 * components. Counts up when `run` is true and lifts subtly on hover.
 */
import { m } from 'framer-motion'
import { useCountUp, formatNumber } from '../../hooks/useCountUp'
import { staggerItem, tFast } from '../../motion/presets'

export interface MetricProps {
  label: string
  value: number
  suffix?: string
  /** Gate the count-up (e.g. wait until on screen). */
  run?: boolean
  /** Accent the value color: 'accent' | 'gold' | 'plain'. */
  tone?: 'accent' | 'gold' | 'plain'
}

export default function Metric({ label, value, suffix, run = true, tone = 'plain' }: MetricProps) {
  const n = useCountUp(value, run)
  const valueColor =
    tone === 'accent' ? 'var(--eiq-accent)' : tone === 'gold' ? 'var(--eiq-gold)' : 'var(--eiq-ink-strong)'
  return (
    <m.div
      className="eiq-metric"
      variants={staggerItem}
      whileHover={{ y: -3, transition: tFast }}
    >
      <div className="eiq-metric__value eiq-num" style={{ color: valueColor }}>
        {formatNumber(n)}
        {suffix ? <span className="eiq-metric__suffix"> {suffix}</span> : null}
      </div>
      <div className="eiq-metric__label">{label}</div>
    </m.div>
  )
}
