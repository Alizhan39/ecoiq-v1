/**
 * StakeholderMap — a radial network of the four stakeholder groups around the
 * EcoIQ core. Hovering/focusing a node highlights its link and shows its role.
 * Links draw in; nodes scale in on a stagger.
 */
import { m } from 'framer-motion'
import { useState } from 'react'
import { Reveal, fadeUp, tFast } from '../motion'

export interface Stakeholder {
  id: string
  label: string
  role: string
  /** A short value-exchange line. */
  value?: string
}

export interface StakeholderMapProps {
  eyebrow?: string
  title?: string
  coreLabel?: string
  stakeholders?: Stakeholder[]
}

const W = 720
const H = 460
const CX = W / 2
const CY = H / 2
const R = 168

export default function StakeholderMap(props: StakeholderMapProps) {
  const {
    eyebrow = 'Value Network',
    title = 'Stakeholder Map',
    coreLabel = 'EcoIQ',
    stakeholders = [],
  } = props
  const [active, setActive] = useState<string>(stakeholders[0]?.id ?? '')
  const n = Math.max(stakeholders.length, 1)

  const pos = (i: number) => {
    const angle = -Math.PI / 2 + (i / n) * Math.PI * 2
    return { x: CX + R * Math.cos(angle), y: CY + R * Math.sin(angle) }
  }

  const activeNode = stakeholders.find((s) => s.id === active)

  return (
    <Reveal variants={fadeUp} className="eiq-stake eiq-panel">
      <div className="eiq-eyebrow">{eyebrow}</div>
      <h2 className="eiq-stake__title">{title}</h2>

      <div className="eiq-stake__grid">
        <svg viewBox={`0 0 ${W} ${H}`} className="eiq-stake__svg" role="img" aria-label={title}>
          {/* links */}
          {stakeholders.map((s, i) => {
            const p = pos(i)
            const on = s.id === active
            return (
              <m.line
                key={`l-${s.id}`}
                x1={CX}
                y1={CY}
                x2={p.x}
                y2={p.y}
                stroke={on ? 'var(--eiq-accent)' : 'rgba(255,255,255,0.12)'}
                strokeWidth={on ? 2 : 1}
                initial={{ pathLength: 0, opacity: 0 }}
                whileInView={{ pathLength: 1, opacity: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.8, delay: 0.2 + i * 0.1 }}
              />
            )
          })}

          {/* core */}
          <circle cx={CX} cy={CY} r="46" fill="rgba(0,232,154,0.10)" stroke="var(--eiq-accent)" strokeWidth="1.5" />
          <text x={CX} y={CY + 5} textAnchor="middle" fontSize="16" fontWeight="700" fill="var(--eiq-ink-strong)">
            {coreLabel}
          </text>

          {/* nodes */}
          {stakeholders.map((s, i) => {
            const p = pos(i)
            const on = s.id === active
            return (
              <m.g
                key={s.id}
                onMouseEnter={() => setActive(s.id)}
                onClick={() => setActive(s.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setActive(s.id)}
                className="eiq-stake__node"
                initial={{ scale: 0, opacity: 0 }}
                whileInView={{ scale: 1, opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.5 + i * 0.12, ...tFast }}
                style={{ transformOrigin: `${p.x}px ${p.y}px` }}
              >
                <circle cx={p.x} cy={p.y} r={on ? 40 : 36} fill={on ? 'rgba(232,196,106,0.16)' : 'rgba(255,255,255,0.04)'} stroke={on ? 'var(--eiq-gold)' : 'rgba(255,255,255,0.16)'} strokeWidth="1.5" />
                <text x={p.x} y={p.y + 4} textAnchor="middle" fontSize="12" fontWeight={on ? 700 : 500} fill={on ? 'var(--eiq-ink-strong)' : 'var(--eiq-muted)'}>
                  {s.label}
                </text>
              </m.g>
            )
          })}
        </svg>

        <div className="eiq-stake__detail">
          {activeNode && (
            <m.div key={activeNode.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={tFast}>
              <h3 className="eiq-stake__role-title">{activeNode.label}</h3>
              <p className="eiq-stake__role">{activeNode.role}</p>
              {activeNode.value ? <p className="eiq-stake__value">{activeNode.value}</p> : null}
            </m.div>
          )}
        </div>
      </div>
    </Reveal>
  )
}
