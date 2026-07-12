/**
 * ArmEngagement — small claw-tip decals only; the source image is never
 * transformed, so there's no risk of the arms visually detaching from their
 * bases. Left arm glows accent-green (engaging the restored side), right
 * arm glows warm (engaging the polluted/industrial side). Pulses are
 * bounded (3 iterations, not infinite), gated by `active` — mirrors the
 * existing particle-track pattern from EvidenceScene.
 */
import { m, useTransform, type MotionValue } from 'framer-motion'
import { AGENTS_SUB_RANGES } from '../sceneRanges'
import { LEFT_ARM_CLAW, RIGHT_ARM_CLAW, CANVAS_W, CANVAS_H, pct } from '../sceneLayout'

function ClawDecal({
  point,
  tone,
  glowOpacity,
  active,
}: {
  point: { x: number; y: number }
  tone: 'accent' | 'warn'
  glowOpacity: MotionValue<number>
  active: boolean
}) {
  return (
    <div
      className="eiq-cine__claw-decal"
      style={{ left: pct(point.x, CANVAS_W), top: pct(point.y, CANVAS_H) }}
      aria-hidden="true"
    >
      <m.span className={`eiq-cine__claw-glow eiq-cine__claw-glow--${tone}`} style={{ opacity: glowOpacity }} />
      <span className={`eiq-cine__claw-pulse eiq-cine__claw-pulse--${tone}${active ? ' is-active' : ''}`} />
    </div>
  )
}

export default function ArmEngagement({
  scrollYProgress,
  active,
}: {
  scrollYProgress: MotionValue<number>
  active: boolean
}) {
  const [start] = AGENTS_SUB_RANGES.arms
  // Ramps in over a short window, then holds (useTransform clamps past the range end by default).
  const glowOpacity = useTransform(scrollYProgress, [start, start + 0.02], [0, 1])

  return (
    <>
      <ClawDecal point={LEFT_ARM_CLAW} tone="accent" glowOpacity={glowOpacity} active={active} />
      <ClawDecal point={RIGHT_ARM_CLAW} tone="warn" glowOpacity={glowOpacity} active={active} />
    </>
  )
}
