/**
 * ScoreRing — animated circular progress for a 0–100 score. Draws the arc in
 * with Framer Motion and counts the number up. Reduced-motion safe.
 */
import { m } from 'framer-motion'
import { useEffect, useReducer, useRef } from 'react'
import { useCountUp } from '../../hooks/useCountUp'
import { tSlow } from '../../motion/presets'

export interface ScoreRingProps {
  value: number
  label?: string
  size?: number
  /** 'accent' | 'gold' */
  tone?: 'accent' | 'gold'
}

export default function ScoreRing({ value, label = 'Transition Score', size = 168, tone = 'accent' }: ScoreRingProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [seen, see] = useReducer(() => true, false)
  useEffect(() => {
    const el = ref.current
    if (!el || typeof IntersectionObserver === 'undefined') return see()
    const io = new IntersectionObserver((e) => e.some((x) => x.isIntersecting) && (see(), io.disconnect()), {
      threshold: 0.4,
    })
    io.observe(el)
    return () => io.disconnect()
  }, [])

  const n = useCountUp(value, seen, 1200)
  const stroke = 10
  const r = (size - stroke) / 2 - 4
  const c = 2 * Math.PI * r
  const pct = Math.min(100, Math.max(0, value)) / 100
  const color = tone === 'gold' ? 'var(--eiq-gold)' : 'var(--eiq-accent)'

  return (
    <div className="eiq-ring" ref={ref} style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
        <defs>
          <filter id="eiqRingGlow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="4" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={stroke} />
        <m.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          filter="url(#eiqRingGlow)"
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: seen ? c * (1 - pct) : c }}
          transition={tSlow}
          style={{ transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }}
        />
      </svg>
      <div className="eiq-ring__center">
        <div className="eiq-ring__value eiq-num">{n}</div>
        <div className="eiq-ring__label">{label}</div>
      </div>
    </div>
  )
}
