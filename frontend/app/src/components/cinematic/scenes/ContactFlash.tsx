/**
 * ContactFlash — a single bright flash-then-fade at the point where a scan
 * or repair beam reaches its target. Fires exactly once (`animation-iteration
 * -count: 1`, gated by `prefers-reduced-motion` like every other bounded
 * pulse in this tree) — even more restrained than the existing 3-iteration
 * claw/repair pulses, since a contact flash is a single instant, not a
 * held signal.
 */
import { CANVAS_W, CANVAS_H, pct } from '../sceneLayout'

export default function ContactFlash({
  point,
  active,
  tone,
}: {
  point: { x: number; y: number }
  active: boolean
  tone: 'accent' | 'warn'
}) {
  return (
    <div className="eiq-cine__contact-flash" style={{ left: pct(point.x, CANVAS_W), top: pct(point.y, CANVAS_H) }} aria-hidden="true">
      <span className={`eiq-cine__contact-flash-burst eiq-cine__contact-flash-burst--${tone}${active ? ' is-active' : ''}`} />
    </div>
  )
}
