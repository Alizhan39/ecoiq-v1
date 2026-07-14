/**
 * RepairSequence — late AI Agents sub-scene. A scan band sweeps once,
 * bounded pulses fire at each target, and a dark "smoke suppression" overlay
 * ramps in followed by a soft green "clean energy" reveal — both continuous
 * scroll-linked opacity ramps, so the change is progressive and fully
 * reversible by scrolling back up.
 *
 * Refinement pass: removed the dashed SVG connector lines (agent labels →
 * repair targets) for the same reason as `WasteRestoration.tsx` — they
 * duplicated the canvas's own particle stream (`canvasEngine.ts`'s
 * `paintRepairEnergy`/`paintRepairReconstruct`, which now carry the
 * "precise, staged, geometric" energy-transfer signal for this arm more
 * clearly than a generic dashed line did). One clear signal, not two
 * competing ones.
 */
import { m, useTransform, type MotionValue } from 'framer-motion'
import { AGENTS_SUB_RANGES } from '../sceneRanges'
import { REPAIR_TARGETS, SMOKE_AREA, CANVAS_W, CANVAS_H, pct } from '../sceneLayout'
import ContactFlash from './ContactFlash'

export default function RepairSequence({
  scrollYProgress,
  active,
}: {
  scrollYProgress: MotionValue<number>
  active: boolean
}) {
  const [start, end] = AGENTS_SUB_RANGES.repair
  const smokeOpacity = useTransform(scrollYProgress, [start, end], [0, 0.7])
  const cleanOpacity = useTransform(scrollYProgress, [start + 0.015, end], [0, 0.35])
  const scanX = useTransform(scrollYProgress, [start, start + 0.02], ['-20%', '120%'])
  const scanOpacity = useTransform(scrollYProgress, [start, start + 0.005, start + 0.018, start + 0.02], [0, 1, 1, 0])

  return (
    <>
      <m.div
        className="eiq-cine__smoke-suppress"
        style={{ left: pct(SMOKE_AREA.x, CANVAS_W), top: pct(SMOKE_AREA.y, CANVAS_H), opacity: smokeOpacity }}
        aria-hidden="true"
      />
      <m.div
        className="eiq-cine__clean-reveal"
        style={{ left: pct(SMOKE_AREA.x, CANVAS_W), top: pct(SMOKE_AREA.y, CANVAS_H), opacity: cleanOpacity }}
        aria-hidden="true"
      />

      <ContactFlash point={SMOKE_AREA} active={active} tone="warn" />

      <div
        className="eiq-cine__repair-scan-track"
        style={{ left: pct(SMOKE_AREA.x - 180, CANVAS_W), top: pct(SMOKE_AREA.y - 140, CANVAS_H) }}
        aria-hidden="true"
      >
        <m.div className="eiq-cine__repair-scan" style={{ x: scanX, opacity: scanOpacity }} />
      </div>

      {REPAIR_TARGETS.map((point, i) => (
        <div
          key={`${point.x}-${point.y}`}
          className="eiq-cine__repair-target"
          style={{ left: pct(point.x, CANVAS_W), top: pct(point.y, CANVAS_H) }}
          aria-hidden="true"
        >
          <span className={`eiq-cine__repair-pulse${active ? ' is-active' : ''}`} style={{ animationDelay: `${i * 0.25}s` }} />
          <span className="eiq-cine__repair-dot" />
        </div>
      ))}
    </>
  )
}
