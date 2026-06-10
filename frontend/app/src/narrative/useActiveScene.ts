/**
 * useActiveScene — drives scrollytelling. Observes the text "steps" inside a
 * container and reports which one is currently in the reading band (center of
 * viewport), so the bound visual can morph to match what's being read.
 *
 * The interaction layer: scroll position selects the active scene; callers may
 * also setActive() directly (e.g. clickable scene dots / keyboard).
 */
import { useEffect, useRef, useState } from 'react'

export function useActiveScene(count: number) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [active, setActive] = useState(0)

  useEffect(() => {
    const root = containerRef.current
    if (!root) return
    const steps = Array.from(root.querySelectorAll<HTMLElement>('[data-scene]'))
    if (steps.length === 0) return

    if (typeof IntersectionObserver === 'undefined') {
      setActive(0)
      return
    }

    const io = new IntersectionObserver(
      (entries) => {
        // Pick the most-visible intersecting step in the central band.
        let bestI = -1
        let bestRatio = -1
        entries.forEach((e) => {
          if (!e.isIntersecting) return
          const i = Number((e.target as HTMLElement).dataset.scene)
          if (e.intersectionRatio > bestRatio) {
            bestRatio = e.intersectionRatio
            bestI = i
          }
        })
        if (bestI >= 0) setActive(bestI)
      },
      // Thin central reading band: a step is "active" as it crosses the middle.
      { rootMargin: '-42% 0px -42% 0px', threshold: [0, 0.5, 1] },
    )
    steps.forEach((s) => io.observe(s))
    return () => io.disconnect()
  }, [count])

  return { containerRef, active, setActive }
}
