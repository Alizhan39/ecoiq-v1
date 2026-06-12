/**
 * DigitalTwinPreview — preview of the EcoIQ Digital Twin: a country-level map
 * with toggleable intelligence layers (project sites, manufacturers, grid
 * infrastructure). Explicitly labelled as a preview with illustrative
 * positions — not live data.
 */
import { AnimatePresence, m } from 'framer-motion'
import { useState } from 'react'
import { Reveal, fadeUp, tFast } from '../../motion'
import { KZ_PATH, KZ_VIEWBOX } from '../kazakhstan/geo'

type LayerId = 'projects' | 'manufacturers' | 'grid'

interface TwinPoint {
  x: number
  y: number
  label: string
}

const LAYERS: Record<LayerId, { name: string; color: string; points: TwinPoint[] }> = {
  projects: {
    name: 'Project sites',
    color: '#00e89a',
    points: [
      { x: 872, y: 338, label: 'Almaty clean-air retrofit cluster' },
      { x: 648, y: 378, label: 'Shymkent heating transition zone' },
      { x: 584, y: 360, label: 'Turkistan pilot district' },
      { x: 300, y: 300, label: 'Aktobe industrial corridor' },
    ],
  },
  manufacturers: {
    name: 'Manufacturers',
    color: '#e8c46a',
    points: [
      { x: 820, y: 300, label: 'Electric boiler assembly — Almaty region' },
      { x: 700, y: 340, label: 'Insulation production — south corridor' },
      { x: 420, y: 220, label: 'Solar module logistics hub' },
    ],
  },
  grid: {
    name: 'Grid & infrastructure',
    color: '#5ab0f2',
    points: [
      { x: 760, y: 260, label: 'Southern grid reinforcement zone' },
      { x: 520, y: 280, label: 'Transmission corridor' },
      { x: 360, y: 200, label: 'Northern generation cluster' },
    ],
  },
}

export interface DigitalTwinPreviewProps {
  eyebrow?: string
  title?: string
  body?: string
}

export default function DigitalTwinPreview(props: DigitalTwinPreviewProps) {
  const {
    eyebrow = 'EcoIQ Digital Twin · Preview',
    title = 'A living model of the transition landscape',
    body = 'The EcoIQ Digital Twin overlays company scores, project sites, manufacturer capacity, and grid context on a single country model — so capital allocators can see where transition-ready demand, supply chains, and infrastructure intersect.',
  } = props
  const [on, setOn] = useState<Record<LayerId, boolean>>({
    projects: true,
    manufacturers: true,
    grid: false,
  })
  const [hover, setHover] = useState<string | null>(null)

  const toggle = (id: LayerId) => setOn((s) => ({ ...s, [id]: !s[id] }))

  return (
    <Reveal variants={fadeUp} className="eiq-twin eiq-panel">
      <div className="eiq-twin__head">
        <div>
          <div className="eiq-eyebrow">{eyebrow}</div>
          <h2 className="eiq-twin__title">{title}</h2>
          <p className="eiq-twin__body">{body}</p>
        </div>

        {/* Layer toggles */}
        <div className="eiq-twin__layers" role="group" aria-label="Data layers">
          {(Object.keys(LAYERS) as LayerId[]).map((id) => (
            <button
              key={id}
              className={`eiq-twin__layer${on[id] ? ' is-on' : ''}`}
              onClick={() => toggle(id)}
              aria-pressed={on[id]}
            >
              <span className="eiq-twin__dot" style={{ background: LAYERS[id].color }} aria-hidden="true" />
              {LAYERS[id].name}
            </button>
          ))}
        </div>
      </div>

      <div className="eiq-twin__map">
        <svg viewBox={KZ_VIEWBOX} role="img" aria-label="Kazakhstan digital twin preview map">
          <path d={KZ_PATH} fill="rgba(0,232,154,0.04)" stroke="rgba(0,232,154,0.3)" strokeWidth="1.4" />
          {(Object.keys(LAYERS) as LayerId[]).map((id) =>
            on[id]
              ? LAYERS[id].points.map((p) => (
                  <g
                    key={`${id}-${p.label}`}
                    onMouseEnter={() => setHover(p.label)}
                    onMouseLeave={() => setHover(null)}
                    onFocus={() => setHover(p.label)}
                    onBlur={() => setHover(null)}
                    tabIndex={0}
                    role="img"
                    aria-label={p.label}
                  >
                    <circle cx={p.x} cy={p.y} r="14" fill={LAYERS[id].color} opacity="0.14" />
                    <circle cx={p.x} cy={p.y} r="5" fill={LAYERS[id].color} />
                  </g>
                ))
              : null,
          )}
        </svg>
        <AnimatePresence>
          {hover && (
            <m.div
              className="eiq-twin__tip"
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={tFast}
            >
              {hover}
            </m.div>
          )}
        </AnimatePresence>
      </div>

      <p className="eiq-twin__disclaimer">
        Preview with illustrative layer positions — not live operational data.
      </p>
    </Reveal>
  )
}
