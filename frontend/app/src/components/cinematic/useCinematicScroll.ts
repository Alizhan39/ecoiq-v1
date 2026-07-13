/**
 * useCinematicScroll — drives the pinned cinematic stage from scroll position.
 *
 * `scrollYProgress` runs 0→1 across the tall wrapper (see sceneRanges.ts for
 * why the same fractions work unchanged as more scenes are added). Scene
 * components read it directly via useTransform for continuous crossfades;
 * `activeScene` is a small derived discrete index for the pieces that need a
 * boolean "is this scene live" (popIn labels, particle gating) rather than a
 * continuous value.
 */
import { useState, type RefObject } from 'react'
import { useScroll, useMotionValueEvent, type MotionValue } from 'framer-motion'
import { SCENE_RANGES, IMPLEMENTED_SCENE_COUNT } from './sceneRanges'

export interface CinematicScroll {
  scrollYProgress: MotionValue<number>
  activeScene: number
}

export function useCinematicScroll(wrapperRef: RefObject<HTMLElement>): CinematicScroll {
  const { scrollYProgress } = useScroll({ target: wrapperRef, offset: ['start start', 'end end'] })
  const [activeScene, setActiveScene] = useState(0)

  useMotionValueEvent(scrollYProgress, 'change', (v) => {
    let next = 0
    for (let i = 0; i < IMPLEMENTED_SCENE_COUNT; i++) {
      const [start] = SCENE_RANGES[i]
      if (v >= start) next = i
    }
    setActiveScene((prev) => (prev === next ? prev : next))
  })

  return { scrollYProgress, activeScene }
}
