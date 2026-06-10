/**
 * HeatingScene — the morphing visual for the coal-to-clean heating narrative.
 *
 * One SVG that transforms across four stages to *explain the text automatically*:
 *   0 — Coal heat:   grey smoke, hazy sky, orange stove glow, particulates, high CO₂
 *   1 — Retrofit:    heat pump appears, smoke clears, glow turns green
 *   2 — Scale:       a whole village lights up clean
 *   3 — Clean air:   sky clears to night-teal with aurora, trees, near-zero CO₂
 *
 * No charts — the picture itself carries the meaning. Reduced-motion safe
 * (loops are CSS and disabled by the global reduced-motion rule).
 */
import { m } from 'framer-motion'

function pick<T>(arr: T[], i: number): T {
  return arr[Math.min(Math.max(i, 0), arr.length - 1)]
}

const SKY = ['#3a403b', '#324039', '#173129', '#07201c']
const GROUND = ['#241f1a', '#22241e', '#102a20', '#0a2a1f']
const GLOW = ['#f2a65a', '#00e89a', '#00e89a', '#00e89a']
const CO2 = ['5.4', '2.6', '2.6', '0.9']
const t = { duration: 1.0, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] }

function House({ x, y, s = 1, glow }: { x: number; y: number; s?: number; glow: string }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <rect x="-26" y="-2" width="52" height="40" rx="3" fill="#16231e" stroke="rgba(255,255,255,0.10)" />
      <path d="M-30,-2 L0,-26 L30,-2 Z" fill="#1d2c25" stroke="rgba(255,255,255,0.10)" />
      <m.rect x="-9" y="12" width="18" height="18" rx="2" animate={{ fill: glow }} transition={t} />
    </g>
  )
}

export default function HeatingScene({ active }: { active: number }) {
  const glow = pick(GLOW, active)
  const showPump = active >= 1
  const showVillage = active >= 2
  const showTrees = active >= 3
  const smoke = active === 0 ? 1 : 0

  return (
    <svg viewBox="0 0 400 300" className="eiq-heat__svg" role="img" aria-label="Coal to clean heating transition">
      <defs>
        <radialGradient id="eiqHeatSun" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="rgba(255,255,255,0.5)" />
          <stop offset="100%" stopColor="rgba(255,255,255,0)" />
        </radialGradient>
        <linearGradient id="eiqAurora" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="rgba(0,232,154,0)" />
          <stop offset="50%" stopColor="rgba(0,232,154,0.5)" />
          <stop offset="100%" stopColor="rgba(90,176,242,0)" />
        </linearGradient>
        <clipPath id="eiqHeatClip">
          <rect x="0" y="0" width="400" height="300" rx="16" />
        </clipPath>
      </defs>

      <g clipPath="url(#eiqHeatClip)">
        {/* sky */}
        <m.rect x="0" y="0" width="400" height="300" animate={{ fill: pick(SKY, active) }} transition={t} />

        {/* sun / haze → aurora */}
        <m.circle cx="320" cy="70" r="60" fill="url(#eiqHeatSun)" animate={{ opacity: active >= 3 ? 0 : 0.8 - active * 0.2 }} transition={t} />
        <m.rect x="0" y="40" width="400" height="22" fill="url(#eiqAurora)" animate={{ opacity: active >= 3 ? 0.9 : 0 }} transition={t} className="eiq-aurora" />

        {/* ground */}
        <m.rect x="0" y="232" width="400" height="68" animate={{ fill: pick(GROUND, active) }} transition={t} />

        {/* village (sides) */}
        <m.g animate={{ opacity: showVillage ? 1 : 0, x: showVillage ? 0 : -10 }} transition={t}>
          <House x={86} y={206} s={0.72} glow={glow} />
        </m.g>
        <m.g animate={{ opacity: showVillage ? 1 : 0, x: showVillage ? 0 : 10 }} transition={t}>
          <House x={320} y={208} s={0.72} glow={glow} />
        </m.g>

        {/* trees */}
        <m.g animate={{ opacity: showTrees ? 1 : 0 }} transition={t}>
          {[150, 250, 360, 40].map((tx, i) => (
            <g key={i} transform={`translate(${tx} ${238 + (i % 2) * 6})`}>
              <rect x="-1.5" y="6" width="3" height="10" fill="#0c2a20" />
              <path d="M0,-14 L8,8 L-8,8 Z" fill="#12c089" opacity="0.85" />
            </g>
          ))}
        </m.g>

        {/* main house */}
        <House x={200} y={196} s={1} glow={glow} />

        {/* chimney */}
        <rect x="214" y="166" width="12" height="20" fill="#16231e" stroke="rgba(255,255,255,0.10)" />

        {/* coal smoke */}
        <m.g animate={{ opacity: smoke }} transition={{ duration: 0.6 }}>
          <circle className="eiq-smoke eiq-smoke--1" cx="220" cy="156" r="9" fill="rgba(180,180,175,0.55)" />
          <circle className="eiq-smoke eiq-smoke--2" cx="226" cy="144" r="11" fill="rgba(170,170,165,0.45)" />
          <circle className="eiq-smoke eiq-smoke--3" cx="216" cy="132" r="13" fill="rgba(160,160,155,0.35)" />
        </m.g>

        {/* particulates (coal only) */}
        <m.g animate={{ opacity: active === 0 ? 1 : 0 }} transition={{ duration: 0.5 }}>
          {[[240, 120], [200, 110], [264, 150], [180, 140]].map(([px, py], i) => (
            <circle key={i} className={`eiq-particle eiq-particle--${i}`} cx={px} cy={py} r="2" fill="rgba(200,150,120,0.7)" />
          ))}
        </m.g>

        {/* heat pump unit */}
        <m.g
          initial={false}
          animate={{ opacity: showPump ? 1 : 0, scale: showPump ? 1 : 0.6 }}
          transition={t}
          style={{ transformOrigin: '243px 214px' }}
        >
          <rect x="232" y="206" width="26" height="18" rx="3" fill="#0f2a21" stroke="var(--eiq-accent)" strokeWidth="1.2" />
          <circle cx="245" cy="215" r="6" fill="none" stroke="var(--eiq-accent)" strokeWidth="1" />
          <circle className="eiq-fan" cx="245" cy="215" r="6" fill="none" stroke="var(--eiq-accent)" strokeWidth="1" strokeDasharray="3 5" />
        </m.g>

        {/* CO2 badge */}
        <g transform="translate(40 36)">
          <rect x="-16" y="-18" width="118" height="34" rx="17" fill="rgba(0,0,0,0.35)" stroke="rgba(255,255,255,0.1)" />
          <m.text x="0" y="4" fontSize="20" fontWeight="800" animate={{ fill: active === 0 ? '#f2a65a' : '#00e89a' }} transition={t} className="eiq-num">
            {pick(CO2, active)}
          </m.text>
          <text x="40" y="-2" fontSize="9" fill="var(--eiq-muted)">tCO₂</text>
          <text x="40" y="9" fontSize="9" fill="var(--eiq-muted)">/home·yr</text>
        </g>
      </g>
    </svg>
  )
}
