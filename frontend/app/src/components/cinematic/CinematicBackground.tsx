/**
 * CinematicBackground — the persistent hero image + ambient scale/glow +
 * depth canvas. Decorative: all real information is carried by sibling
 * overlay layers, so the image itself is hidden from assistive technology.
 *
 * The fade-in and initial 1.04→1 scale settle play once on mount — they must
 * be visible immediately at page load, before any scrolling. The further
 * "slightly increase scale" bumps are scroll-linked, layered via a separate
 * wrapping transform so they don't fight the mount animation on the same
 * element/property. Two small additional bumps (waste/repair) give a
 * restrained camera-push feel during each intervention — still capped under
 * 1% extra scale, no aggressive zoom, combined with `Math.max` rather than a
 * single breakpoint array since waste/repair's ranges overlap.
 */
import { m, useTransform, type MotionValue } from 'framer-motion'
import { ease } from '../../design/tokens'
import { AGENTS_SUB_RANGES } from './sceneRanges'
import GlobeRotationOverlay, { GlobeInterventionSpots } from './GlobeRotationOverlay'
import HeroCanvas from './HeroCanvas'

const HERO_IMAGE = '/static/img/hero/ecoiq-better-way-hero.png'

export default function CinematicBackground({ scrollYProgress }: { scrollYProgress: MotionValue<number> }) {
  const baseScale = useTransform(scrollYProgress, [0.14, 0.29], [1, 1.03])
  const wasteBump = useTransform(scrollYProgress, AGENTS_SUB_RANGES.waste, [1, 1.008])
  const repairBump = useTransform(scrollYProgress, AGENTS_SUB_RANGES.repair, [1, 1.008])
  const scrollScale = useTransform([baseScale, wasteBump, repairBump], (v: number[]) => v[0] * Math.max(v[1], v[2]))

  return (
    <div className="eiq-cine__bg" aria-hidden="true">
      <m.div style={{ scale: scrollScale }} className="eiq-cine__bg-scale-wrap">
        <m.img
          src={HERO_IMAGE}
          alt=""
          className="eiq-cine__bg-img"
          initial={{ opacity: 0, scale: 1.04 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.4, ease: ease.out }}
          width={1536}
          height={1024}
          loading="eager"
          // @ts-expect-error fetchpriority is valid HTML but not yet in React's img typings
          fetchpriority="high"
        />
      </m.div>
      <div className="eiq-cine__bg-scrim" />
      <div className="eiq-cine__bg-glow" />
      <GlobeRotationOverlay scrollYProgress={scrollYProgress} />
      <GlobeInterventionSpots scrollYProgress={scrollYProgress} />
      <HeroCanvas scrollYProgress={scrollYProgress} />
    </div>
  )
}
