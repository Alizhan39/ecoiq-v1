/**
 * CountUpValue — generic numeric-KPI island. Progressive enhancement: Django
 * renders the real number as static text (data-props), and this hydrates it
 * with a count-up once the element enters the viewport. Gates on
 * IntersectionObserver with disconnect-after-first-trigger (same pattern as
 * ScoreRing/ImpactGlobe), so it never replays on scroll re-entry. Reduced
 * motion is handled inside useCountUp itself (snaps straight to the value).
 */
import { useEffect, useRef, useReducer } from 'react'
import { useCountUp, formatNumber } from '../../hooks/useCountUp'

export interface CountUpValueProps {
  value: number
  suffix?: string
  ms?: number
}

export default function CountUpValue({ value, suffix = '', ms = 1200 }: CountUpValueProps) {
  const ref = useRef<HTMLSpanElement>(null)
  const [seen, see] = useReducer(() => true, false)

  useEffect(() => {
    const el = ref.current
    if (!el || typeof IntersectionObserver === 'undefined') return see()
    const io = new IntersectionObserver(
      (entries) => entries.some((e) => e.isIntersecting) && (see(), io.disconnect()),
      { threshold: 0.4 },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])

  const n = useCountUp(value, seen, ms)

  return (
    <span ref={ref}>
      {formatNumber(n)}
      {suffix}
    </span>
  )
}
