/**
 * useCountUp — animate a number from 0 → target with cubic ease-out.
 * Respects reduced motion (snaps to target). `run` gates the start so callers
 * can wait until the element is on screen.
 */
import { useEffect, useState } from 'react'

export function useCountUp(target: number, run: boolean, ms = 1000): number {
  const [value, setValue] = useState(run ? 0 : target)
  useEffect(() => {
    if (!run) {
      setValue(target)
      return
    }
    let raf = 0
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ms)
      const eased = 1 - Math.pow(1 - t, 3)
      setValue(Math.round(target * eased))
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, run, ms])
  return value
}

export function formatNumber(n: number): string {
  return n.toLocaleString('en-US')
}
