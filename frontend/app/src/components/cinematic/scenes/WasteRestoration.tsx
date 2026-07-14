/**
 * WasteRestoration — left-arm counterpart to RepairSequence (waste/water/land
 * area, left of the globe). Structurally parallel to RepairSequence but kept
 * independent (no shared import) since RepairSequence is tuned, shipped code
 * this pass doesn't otherwise touch. A scan band sweeps once, bounded pulses
 * fire at each target, and a dark "pollution" overlay ramps in *then back
 * down* as it's replaced by a soft green "restored" reveal — unlike
 * RepairSequence's industrial side (which ramps and holds), this side's
 * "before" state visibly resolves within its own window, since the left
 * arm's job reads as finished before the right arm's repair sequence begins.
 *
 * Refinement pass: the dashed SVG connector lines (agent labels → waste
 * targets) were removed here — they were a second, competing visual metaphor
 * for "something is flowing toward the arm" running concurrently with the
 * canvas's own directional particle stream (`canvasEngine.ts`'s
 * `paintWasteExtraction`, which now does that job more clearly). One clear
 * signal instead of two redundant ones (Phase 1/2 audit finding).
 */
import { m, useTransform, type MotionValue } from 'framer-motion'
import { AGENTS_SUB_RANGES } from '../sceneRanges'
import { WASTE_TARGETS, POLLUTION_AREA, CANVAS_W, CANVAS_H, pct } from '../sceneLayout'
import ContactFlash from './ContactFlash'

export default function WasteRestoration({
  scrollYProgress,
  active,
}: {
  scrollYProgress: MotionValue<number>
  active: boolean
}) {
  const [start, end] = AGENTS_SUB_RANGES.waste
  const suppressOpacity = useTransform(scrollYProgress, [start, start + 0.015, end - 0.01, end], [0, 0.6, 0.6, 0.05])
  const restoreOpacity = useTransform(scrollYProgress, [start + 0.015, end], [0, 0.4])
  const scanX = useTransform(scrollYProgress, [start, start + 0.02], ['-20%', '120%'])
  const scanOpacity = useTransform(scrollYProgress, [start, start + 0.005, start + 0.018, start + 0.02], [0, 1, 1, 0])

  return (
    <>
      <m.div
        className="eiq-cine__waste-suppress"
        style={{ left: pct(POLLUTION_AREA.x, CANVAS_W), top: pct(POLLUTION_AREA.y, CANVAS_H), opacity: suppressOpacity }}
        aria-hidden="true"
      />
      <m.div
        className="eiq-cine__restore-reveal"
        style={{ left: pct(POLLUTION_AREA.x, CANVAS_W), top: pct(POLLUTION_AREA.y, CANVAS_H), opacity: restoreOpacity }}
        aria-hidden="true"
      />

      <ContactFlash point={POLLUTION_AREA} active={active} tone="accent" />

      <div
        className="eiq-cine__repair-scan-track"
        style={{ left: pct(POLLUTION_AREA.x - 180, CANVAS_W), top: pct(POLLUTION_AREA.y - 140, CANVAS_H) }}
        aria-hidden="true"
      >
        <m.div className="eiq-cine__repair-scan" style={{ x: scanX, opacity: scanOpacity }} />
      </div>

      {WASTE_TARGETS.map((point, i) => (
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
