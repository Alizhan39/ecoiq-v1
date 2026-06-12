/**
 * KazakhstanDetail — second-level national map shown when Kazakhstan is
 * selected in the GlobalCountryExplorer. The outline is the real Natural Earth
 * geometry (projected and passed in by the parent). Layers are DEMO/preview
 * positions, clearly labelled — oblast boundaries would require the
 * geoBoundaries open dataset (flagged as a data TODO, not faked here).
 */
import { m } from 'framer-motion'
import { useState } from 'react'
import { tFast } from '../../motion'

type LayerId = 'coal' | 'pilots' | 'partners' | 'air'

interface DemoPoint {
  x: number // 0–1 fraction of the 720×420 frame
  y: number
  label: string
}

const LAYERS: Record<LayerId, { name: string; color: string; points: DemoPoint[] }> = {
  coal: {
    name: 'Coal-heating priority zones',
    color: '#ef6f6f',
    points: [
      { x: 0.86, y: 0.78, label: 'Almaty valley — winter inversion zone' },
      { x: 0.62, y: 0.86, label: 'Shymkent district heating belt' },
      { x: 0.36, y: 0.30, label: 'Kostanay private-home cluster' },
    ],
  },
  pilots: {
    name: 'Clean heating retrofit pilots',
    color: '#00e89a',
    points: [
      { x: 0.83, y: 0.72, label: 'Almaty region pilot — electric boiler retrofits' },
      { x: 0.58, y: 0.80, label: 'Turkistan pilot district' },
    ],
  },
  partners: {
    name: 'Manufacturer / install partners',
    color: '#e8c46a',
    points: [
      { x: 0.78, y: 0.62, label: 'Boiler assembly & install partner — southeast' },
      { x: 0.50, y: 0.55, label: 'Insulation supply partner — central corridor' },
    ],
  },
  air: {
    name: 'Air quality / transition risk',
    color: '#5ab0f2',
    points: [
      { x: 0.88, y: 0.82, label: 'PM2.5 seasonal hotspot (placeholder index)' },
      { x: 0.30, y: 0.42, label: 'Industrial emissions zone (placeholder index)' },
    ],
  },
}

const W = 720
const H = 420

export default function KazakhstanDetail({ outlineD }: { outlineD: string }) {
  const [on, setOn] = useState<Record<LayerId, boolean>>({
    coal: true,
    pilots: true,
    partners: false,
    air: false,
  })
  const [hover, setHover] = useState<string | null>(null)
  const toggle = (id: LayerId) => setOn((s) => ({ ...s, [id]: !s[id] }))

  return (
    <m.div
      className="eiq-kzd"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={tFast}
    >
      <div className="eiq-kzd__head">
        <div>
          <div className="eiq-gx__block-label">Kazakhstan — national view</div>
          <p className="eiq-kzd__sub">
            Real Natural Earth national outline. Layer positions are demo/preview data.
          </p>
        </div>
        <div className="eiq-kzd__layers" role="group" aria-label="Kazakhstan demo layers">
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

      <div className="eiq-kzd__map">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Kazakhstan national map with demo layers">
          <path d={outlineD} fill="rgba(0,232,154,0.04)" stroke="rgba(0,232,154,0.32)" strokeWidth="1.2" />
          {(Object.keys(LAYERS) as LayerId[]).map((id) =>
            on[id]
              ? LAYERS[id].points.map((p) => (
                  <g
                    key={`${id}-${p.label}`}
                    tabIndex={0}
                    role="img"
                    aria-label={p.label}
                    onMouseEnter={() => setHover(p.label)}
                    onMouseLeave={() => setHover(null)}
                    onFocus={() => setHover(p.label)}
                    onBlur={() => setHover(null)}
                  >
                    <circle cx={p.x * W} cy={p.y * H} r="13" fill={LAYERS[id].color} opacity="0.14" />
                    <circle cx={p.x * W} cy={p.y * H} r="4.5" fill={LAYERS[id].color} />
                  </g>
                ))
              : null,
          )}
        </svg>
        {hover && <div className="eiq-twin__tip">{hover}</div>}
      </div>

      <p className="eiq-twin__disclaimer">
        Demo layers — illustrative positions only. Oblast boundaries pending open
        geoBoundaries dataset integration; per-home pilot data reported via EcoIQ.
      </p>
    </m.div>
  )
}
