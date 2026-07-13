/**
 * IntroScene — Scene 1 (0–14%). Entrance plays once on mount (not scroll-linked
 * — it must be visible immediately at page load, before any scrolling); only
 * the exit (fade + rise) is driven by scroll as the reader moves into Scene 2.
 */
import { m, useTransform, type MotionValue } from 'framer-motion'
import { stagger, staggerItem } from '../../../motion'
import { intro } from '../content'

export default function IntroScene({ scrollYProgress }: { scrollYProgress: MotionValue<number> }) {
  const exitOpacity = useTransform(scrollYProgress, [0.05, 0.13], [1, 0])
  const exitY = useTransform(scrollYProgress, [0.05, 0.14], [0, -50])

  return (
    <m.div className="eiq-cine__scene eiq-cine__scene--intro" style={{ opacity: exitOpacity, y: exitY }}>
      <m.div
        className="eiq-cine__intro-glow"
        aria-hidden="true"
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.5 }}
        transition={{ duration: 1.8 }}
      />
      <m.div variants={stagger(0.12, 0.15)} initial="hidden" animate="show" className="eiq-cine__intro-body">
        <m.div variants={staggerItem} className="eiq-eyebrow eiq-cine__eyebrow">
          {intro.eyebrow}
        </m.div>
        <m.h1 variants={staggerItem} className="eiq-cine__heading">
          {intro.heading}
        </m.h1>
        <m.p variants={staggerItem} className="eiq-cine__lede">
          {intro.body}
        </m.p>
        <m.div variants={staggerItem} className="eiq-cine__cta-row">
          <a className="eiq-btn eiq-btn--primary" href={intro.primaryCta.href}>
            {intro.primaryCta.label}
          </a>
          <a className="eiq-btn eiq-btn--secondary" href={intro.secondaryCta.href}>
            {intro.secondaryCta.label}
          </a>
        </m.div>
      </m.div>
    </m.div>
  )
}
