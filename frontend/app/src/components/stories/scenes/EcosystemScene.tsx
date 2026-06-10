/**
 * EcosystemScene — the Khalifa Tour value exchange as a living ecosystem.
 * A chain Visitor → Household → Community → Environment with particles flowing
 * along the links (the value moving through the system). The active scene
 * highlights successive links; nodes pulse. Not a chart — a living diagram.
 */
import { m } from 'framer-motion'
import { sceneEase as t, type SceneProps } from './types'

const NODES = [
  { id: 'visitor', label: 'Visitor', x: 70, glyph: '🧭' },
  { id: 'household', label: 'Household', x: 180, glyph: '🏠' },
  { id: 'community', label: 'Community', x: 290, glyph: '🤝' },
  { id: 'environment', label: 'Environment', x: 400, glyph: '🌿' },
]
const CY = 150
const EXCHANGE = ['funds a retrofit', 'cleaner, warmer home', 'shared prosperity', 'cleaner air for all']

export default function EcosystemScene({ active }: SceneProps) {
  // How many links are "live" — grows with the narrative, min 1.
  const liveLinks = Math.min(NODES.length - 1, Math.max(1, active + 1))

  return (
    <svg viewBox="0 0 470 300" className="eiq-scene__svg" role="img" aria-label="Khalifa Tour value ecosystem">
      <defs>
        <radialGradient id="eiqEcoBg" cx="50%" cy="40%" r="60%">
          <stop offset="0%" stopColor="rgba(0,232,154,0.10)" />
          <stop offset="100%" stopColor="rgba(0,232,154,0)" />
        </radialGradient>
        <clipPath id="eiqEcoClip"><rect width="470" height="300" rx="16" /></clipPath>
      </defs>

      <g clipPath="url(#eiqEcoClip)">
        <rect width="470" height="300" fill="#07201c" />
        <rect width="470" height="300" fill="url(#eiqEcoBg)" />

        {/* links + flowing particles */}
        {NODES.slice(0, -1).map((n, i) => {
          const next = NODES[i + 1]
          const live = i < liveLinks
          return (
            <g key={i}>
              <line x1={n.x + 26} y1={CY} x2={next.x - 26} y2={CY} stroke={live ? 'rgba(0,232,154,0.5)' : 'rgba(255,255,255,0.10)'} strokeWidth="1.5" />
              {live && (
                <>
                  <circle r="3.5" fill="#00e89a" className="eiq-eco-flow" style={{ offsetPath: `path('M ${n.x + 26} ${CY} L ${next.x - 26} ${CY}')`, animationDelay: `${i * 0.4}s` } as React.CSSProperties} />
                  <circle r="2.5" fill="#7ef5cf" className="eiq-eco-flow eiq-eco-flow--2" style={{ offsetPath: `path('M ${n.x + 26} ${CY} L ${next.x - 26} ${CY}')`, animationDelay: `${i * 0.4 + 1}s` } as React.CSSProperties} />
                  <text x={(n.x + next.x) / 2} y={CY - 16} textAnchor="middle" fontSize="9" fill="rgba(0,232,154,0.85)">{EXCHANGE[i]}</text>
                </>
              )}
            </g>
          )
        })}

        {/* nodes */}
        {NODES.map((n, i) => {
          const on = i <= liveLinks
          return (
            <g key={n.id}>
              <m.circle
                cx={n.x} cy={CY} r="26"
                fill={on ? 'rgba(0,232,154,0.10)' : 'rgba(255,255,255,0.03)'}
                stroke={on ? '#00e89a' : 'rgba(255,255,255,0.16)'}
                strokeWidth="1.4"
                initial={false}
                animate={{ scale: on ? 1 : 0.92, opacity: on ? 1 : 0.6 }}
                transition={t}
                style={{ transformOrigin: `${n.x}px ${CY}px` }}
              />
              {on && <circle cx={n.x} cy={CY} r="26" fill="none" stroke="#00e89a" strokeWidth="1.2" className="eiq-eco-pulse" style={{ transformOrigin: `${n.x}px ${CY}px` }} />}
              <text x={n.x} y={CY + 5} textAnchor="middle" fontSize="18">{n.glyph}</text>
              <text x={n.x} y={CY + 46} textAnchor="middle" fontSize="11" fontWeight="700" fill={on ? '#fff' : 'rgba(220,230,226,0.6)'}>{n.label}</text>
            </g>
          )
        })}
      </g>
    </svg>
  )
}
