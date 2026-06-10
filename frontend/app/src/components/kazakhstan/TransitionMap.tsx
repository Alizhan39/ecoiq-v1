/**
 * TransitionMap — interactive Kazakhstan regions. Click/hover a region node to
 * drive a detail panel: projects, funding required, households impacted,
 * expected emissions reduction. Selection animates with Framer Motion.
 */
import { AnimatePresence, m } from 'framer-motion'
import { useState } from 'react'
import { Reveal, fadeUp, tFast } from '../../motion'
import { formatNumber } from '../../hooks/useCountUp'
import { KZ_PATH, KZ_VIEWBOX, regionXY } from './geo'

export interface RegionData {
  id: string
  name: string
  projects: number
  fundingNeededM: number
  households: number
  emissionsReductionKt: number
  note?: string
}

export interface TransitionMapProps {
  eyebrow?: string
  title?: string
  regions?: RegionData[]
}

export default function TransitionMap(props: TransitionMapProps) {
  const {
    eyebrow = 'Regional Intelligence',
    title = 'Transition Map — Southern Kazakhstan',
    regions = [],
  } = props
  const [activeId, setActiveId] = useState(regions[0]?.id ?? '')
  const active = regions.find((r) => r.id === activeId) ?? regions[0]

  return (
    <Reveal variants={fadeUp} className="eiq-tmap eiq-panel">
      <div className="eiq-eyebrow">{eyebrow}</div>
      <h2 className="eiq-tmap__title">{title}</h2>

      <div className="eiq-tmap__grid">
        {/* Map */}
        <div className="eiq-tmap__map">
          <svg viewBox={KZ_VIEWBOX} className="eiq-tmap__svg" role="img" aria-label={title}>
            <path d={KZ_PATH} fill="rgba(0,232,154,0.05)" stroke="rgba(0,232,154,0.35)" strokeWidth="1.4" />
            {regions.map((r) => {
              const xy = regionXY(r.id)
              if (!xy) return null
              const on = r.id === activeId
              return (
                <g
                  key={r.id}
                  className="eiq-tmap__node"
                  onClick={() => setActiveId(r.id)}
                  onMouseEnter={() => setActiveId(r.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setActiveId(r.id)}
                  aria-label={r.name}
                >
                  {on && (
                    <m.circle
                      cx={xy.x}
                      cy={xy.y}
                      r="16"
                      fill="rgba(232,196,106,0.18)"
                      initial={{ scale: 0.6, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={tFast}
                      style={{ transformOrigin: `${xy.x}px ${xy.y}px` }}
                    />
                  )}
                  <circle cx={xy.x} cy={xy.y} r={on ? 7 : 5} fill={on ? 'var(--eiq-gold)' : 'var(--eiq-accent)'} />
                  <text x={xy.x + 14} y={xy.y + 4} fontSize="13" fill={on ? 'var(--eiq-ink-strong)' : 'var(--eiq-muted)'} fontWeight={on ? 700 : 500}>
                    {r.name}
                  </text>
                </g>
              )
            })}
          </svg>
        </div>

        {/* Detail panel */}
        <div className="eiq-tmap__detail">
          <AnimatePresence mode="wait">
            {active && (
              <m.div
                key={active.id}
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -12 }}
                transition={tFast}
              >
                <h3 className="eiq-tmap__region">{active.name}</h3>
                {active.note ? <p className="eiq-tmap__note">{active.note}</p> : null}
                <dl className="eiq-tmap__stats">
                  <div>
                    <dt>Projects</dt>
                    <dd className="eiq-num">{active.projects}</dd>
                  </div>
                  <div>
                    <dt>Funding required</dt>
                    <dd className="eiq-num">${formatNumber(active.fundingNeededM)}M</dd>
                  </div>
                  <div>
                    <dt>Households impacted</dt>
                    <dd className="eiq-num">{formatNumber(active.households)}</dd>
                  </div>
                  <div>
                    <dt>Emissions reduction</dt>
                    <dd className="eiq-num">{formatNumber(active.emissionsReductionKt)} kt / yr</dd>
                  </div>
                </dl>
              </m.div>
            )}
          </AnimatePresence>

          <div className="eiq-tmap__chips">
            {regions.map((r) => (
              <button
                key={r.id}
                className={`eiq-tmap__chip${r.id === activeId ? ' is-active' : ''}`}
                onClick={() => setActiveId(r.id)}
              >
                {r.name}
              </button>
            ))}
          </div>
        </div>
      </div>
    </Reveal>
  )
}
