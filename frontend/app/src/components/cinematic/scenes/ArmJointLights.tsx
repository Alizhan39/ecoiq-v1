/**
 * ArmJointLights — sequenced glow decals tracing an arm from shoulder to
 * wrist, staggered so light appears to travel through the joints toward the
 * claw as the arm engages. Same "opacity-only decal over the baked photo"
 * technique ArmEngagement's ClawDecal already uses — no transform on the
 * source image, no distortion. Each joint ramps in at a slightly later point
 * within `range`, so by the time the claw's own pulse fires the energy
 * already reads as having traveled the arm's length.
 *
 * Always exactly 3 joints (shoulder/elbow/wrist) — three fixed `useTransform`
 * calls rather than mapping over a dynamic array, since hooks can't be
 * called inside a loop.
 */
import { m, useTransform, type MotionValue } from 'framer-motion'
import { CANVAS_W, CANVAS_H, pct } from '../sceneLayout'

interface Point {
  x: number
  y: number
}

function JointDecal({
  point,
  opacity,
  tone,
}: {
  point: Point
  opacity: ReturnType<typeof useTransform<number, number>>
  tone: 'accent' | 'warn'
}) {
  return (
    <div className="eiq-cine__joint-decal" style={{ left: pct(point.x, CANVAS_W), top: pct(point.y, CANVAS_H) }} aria-hidden="true">
      <m.span className={`eiq-cine__joint-glow eiq-cine__joint-glow--${tone}`} style={{ opacity }} />
    </div>
  )
}

export default function ArmJointLights({
  scrollYProgress,
  range,
  joints,
  tone,
}: {
  scrollYProgress: MotionValue<number>
  range: [number, number]
  joints: [Point, Point, Point]
  tone: 'accent' | 'warn'
}) {
  const [start, end] = range
  const span = end - start
  const shoulderOpacity = useTransform(scrollYProgress, [start, start + span * 0.15], [0, 1])
  const elbowOpacity = useTransform(scrollYProgress, [start + span * 0.25, start + span * 0.4], [0, 1])
  const wristOpacity = useTransform(scrollYProgress, [start + span * 0.5, start + span * 0.65], [0, 1])

  return (
    <>
      <JointDecal point={joints[0]} opacity={shoulderOpacity} tone={tone} />
      <JointDecal point={joints[1]} opacity={elbowOpacity} tone={tone} />
      <JointDecal point={joints[2]} opacity={wristOpacity} tone={tone} />
    </>
  )
}
