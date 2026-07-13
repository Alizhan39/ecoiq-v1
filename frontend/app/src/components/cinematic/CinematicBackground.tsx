/**
 * CinematicBackground — the persistent hero image + ambient scale/glow.
 * Decorative: all real information is carried by sibling overlay layers, so
 * the image itself is hidden from assistive technology.
 *
 * The fade-in and initial 1.04→1 scale settle play once on mount — they must
 * be visible immediately at page load, before any scrolling. Only the
 * further "slightly increase the globe scale" bump for Scene 2 is
 * scroll-linked, layered via a separate wrapping transform so it doesn't
 * fight the mount animation on the same element/property.
 */
import { m, useTransform, type MotionValue } from 'framer-motion'
import { ease } from '../../design/tokens'
import GlobeRotationOverlay from './GlobeRotationOverlay'

const HERO_IMAGE = '/static/img/hero/ecoiq-better-way-hero.png'

export default function CinematicBackground({ scrollYProgress }: { scrollYProgress: MotionValue<number> }) {
  const scrollScale = useTransform(scrollYProgress, [0.14, 0.29], [1, 1.03])

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
    </div>
  )
}
