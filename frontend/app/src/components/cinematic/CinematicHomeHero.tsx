/**
 * CinematicHomeHero — EcoIQ homepage cinematic scrollytelling entry point.
 *
 * Branches into one of two render paths that share the same copy (content.ts):
 *   - reduced motion OR mobile (<760px) → CinematicStaticStack (stacked, no scroll math)
 *   - otherwise (desktop/tablet)        → the pinned scroll-driven stage below
 *
 * This slice implements Scenes 1–3 (Introduction, Evidence, AI Agents) and
 * releases into PillarsSection. Scenes 4–8 land in a follow-up pass — see
 * sceneRanges.ts for how the timeline already reserves their percentages.
 */
import { useReducedMotion } from 'framer-motion'
import { useRef } from 'react'
import { useMediaQuery } from '../../hooks/useMediaQuery'
import { useCinematicScroll } from './useCinematicScroll'
import { SLICE_HEIGHT_VH } from './sceneRanges'
import CinematicBackground from './CinematicBackground'
import CinematicStaticStack from './CinematicStaticStack'
import IntroScene from './scenes/IntroScene'
import EvidenceScene from './scenes/EvidenceScene'
import AgentsScene from './scenes/AgentsScene'
import PillarsSection from './PillarsSection'

function CinematicScrollStage() {
  const wrapperRef = useRef<HTMLDivElement>(null)
  const { scrollYProgress, activeScene } = useCinematicScroll(wrapperRef)

  return (
    <div ref={wrapperRef} className="eiq-cine" style={{ height: `${SLICE_HEIGHT_VH}vh` }}>
      <div className="eiq-cine__stage">
        <CinematicBackground scrollYProgress={scrollYProgress} />
        <IntroScene scrollYProgress={scrollYProgress} />
        <EvidenceScene scrollYProgress={scrollYProgress} isActive={activeScene === 1} />
        <AgentsScene scrollYProgress={scrollYProgress} isActive={activeScene === 2} />
      </div>
    </div>
  )
}

export default function CinematicHomeHero() {
  const prefersReducedMotion = useReducedMotion()
  const isMobile = useMediaQuery('(max-width: 759px)')
  const useStatic = prefersReducedMotion || isMobile

  return (
    <>
      {useStatic ? <CinematicStaticStack /> : <CinematicScrollStage />}
      <PillarsSection />
    </>
  )
}
