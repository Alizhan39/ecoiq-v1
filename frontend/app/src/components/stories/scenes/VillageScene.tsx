/**
 * VillageScene — the Khalifa village transforming from coal to clean.
 * Covers narrative beats 0–4: heavy coal winter → worsening air/health →
 * first heating upgrade → more homes transition → clean community with trees,
 * children and night lighting. The picture carries the meaning; metrics appear
 * as ambient chips, not charts.
 */
import { m } from 'framer-motion'
import { pick, sceneEase as t, type SceneProps } from './types'

const SKY = ['#2b2f2b', '#241f1b', '#1b3029', '#143026', '#0a2420']
const GROUND = ['#211d18', '#231e18', '#15281f', '#102a20', '#0d2a20']
const CO2 = ['5.4', '6.2', '4.1', '2.3', '0.9']
// How many of the 5 homes are upgraded at each beat.
const UPGRADED = [0, 0, 1, 3, 5]
const HOUSES = [56, 138, 220, 302, 380]

function House({ x, upgraded, smoke }: { x: number; upgraded: boolean; smoke: number }) {
  const glow = upgraded ? '#00e89a' : '#f2a65a'
  return (
    <g transform={`translate(${x} 212)`}>
      {/* smoke (only if not upgraded) */}
      <m.g animate={{ opacity: upgraded ? 0 : smoke }} transition={{ duration: 0.6 }}>
        <circle className="eiq-smoke eiq-smoke--1" cx="11" cy="-34" r="7" fill="rgba(180,178,172,0.5)" />
        <circle className="eiq-smoke eiq-smoke--2" cx="15" cy="-44" r="9" fill="rgba(170,168,162,0.4)" />
        <circle className="eiq-smoke eiq-smoke--3" cx="8" cy="-54" r="11" fill="rgba(160,158,152,0.3)" />
      </m.g>
      <rect x="8" y="-30" width="8" height="14" fill="#141f1b" />
      <rect x="-20" y="-16" width="40" height="32" rx="2.5" fill="#15211c" stroke="rgba(255,255,255,0.10)" />
      <path d="M-23,-16 L0,-34 L23,-16 Z" fill="#1b2a23" stroke="rgba(255,255,255,0.10)" />
      <m.rect x="-7" y="-6" width="14" height="14" rx="1.5" animate={{ fill: glow }} transition={t} />
      {/* heat pump appears when upgraded */}
      <m.g initial={false} animate={{ opacity: upgraded ? 1 : 0, scale: upgraded ? 1 : 0.5 }} transition={t} style={{ transformOrigin: '26px 8px' }}>
        <rect x="20" y="2" width="16" height="11" rx="2" fill="#0f2a21" stroke="#00e89a" strokeWidth="1" />
        <circle className="eiq-fan" cx="28" cy="7.5" r="3.4" fill="none" stroke="#00e89a" strokeWidth="0.8" strokeDasharray="2 3" />
      </m.g>
    </g>
  )
}

export default function VillageScene({ active, data = {} }: SceneProps) {
  const upgradedCount = pick(UPGRADED, active)
  const smoke = active === 1 ? 1.3 : 1
  const showTrees = active >= 3
  const showChildren = active >= 4
  const showStats = active >= 4

  return (
    <svg viewBox="0 0 440 300" className="eiq-scene__svg" role="img" aria-label="Village transitioning from coal to clean heating">
      <defs>
        <radialGradient id="eiqVilHaze" cx="50%" cy="30%" r="70%">
          <stop offset="0%" stopColor="rgba(120,110,95,0.0)" />
          <stop offset="100%" stopColor="rgba(90,80,70,0.35)" />
        </radialGradient>
        <linearGradient id="eiqVilAurora" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="rgba(0,232,154,0)" />
          <stop offset="50%" stopColor="rgba(0,232,154,0.45)" />
          <stop offset="100%" stopColor="rgba(90,176,242,0)" />
        </linearGradient>
        <clipPath id="eiqVilClip"><rect width="440" height="300" rx="16" /></clipPath>
      </defs>

      <g clipPath="url(#eiqVilClip)">
        <m.rect width="440" height="300" animate={{ fill: pick(SKY, active) }} transition={t} />
        {/* pollution haze fades as it cleans */}
        <m.rect width="440" height="300" fill="url(#eiqVilHaze)" animate={{ opacity: active <= 1 ? 1 : Math.max(0, 0.5 - (active - 1) * 0.25) }} transition={t} />
        {/* aurora on clean night */}
        <m.rect x="0" y="36" width="440" height="20" fill="url(#eiqVilAurora)" animate={{ opacity: active >= 4 ? 0.9 : 0 }} transition={t} className="eiq-aurora" />
        {/* moon/sun */}
        <m.circle cx="372" cy="60" r="20" animate={{ fill: active >= 3 ? 'rgba(230,245,240,0.85)' : 'rgba(220,180,120,0.5)' }} transition={t} />

        <m.rect x="0" y="236" width="440" height="64" animate={{ fill: pick(GROUND, active) }} transition={t} />

        {/* trees */}
        <m.g animate={{ opacity: showTrees ? 1 : 0 }} transition={t}>
          {[100, 180, 268, 348, 36].map((tx, i) => (
            <g key={i} transform={`translate(${tx} ${242 + (i % 2) * 5})`}>
              <rect x="-1.5" y="6" width="3" height="9" fill="#0c2a20" />
              <path d="M0,-12 L7,7 L-7,7 Z" fill="#12c089" opacity="0.85" />
            </g>
          ))}
        </m.g>

        {/* houses */}
        {HOUSES.map((x, i) => (
          <House key={i} x={x} upgraded={i < upgradedCount} smoke={smoke} />
        ))}

        {/* children (clean stage) */}
        <m.g animate={{ opacity: showChildren ? 1 : 0 }} transition={t}>
          {[170, 250].map((cx, i) => (
            <g key={i} transform={`translate(${cx} 248)`}>
              <circle cx="0" cy="-6" r="3" fill="#e8c46a" />
              <line x1="0" y1="-3" x2="0" y2="4" stroke="#e8c46a" strokeWidth="2" />
              <line x1="0" y1="4" x2="-3" y2="9" stroke="#e8c46a" strokeWidth="1.6" />
              <line x1="0" y1="4" x2="3" y2="9" stroke="#e8c46a" strokeWidth="1.6" />
            </g>
          ))}
        </m.g>

        {/* CO2 badge */}
        <g transform="translate(36 36)">
          <rect x="-16" y="-18" width="120" height="34" rx="17" fill="rgba(0,0,0,0.4)" stroke="rgba(255,255,255,0.1)" />
          <m.text x="0" y="4" fontSize="20" fontWeight="800" className="eiq-num" animate={{ fill: active <= 1 ? '#ef6f6f' : active >= 4 ? '#00e89a' : '#f2a65a' }} transition={t}>
            {pick(CO2, active)}
          </m.text>
          <text x="42" y="-2" fontSize="9" fill="rgba(220,230,226,0.7)">tCO₂</text>
          <text x="42" y="9" fontSize="9" fill="rgba(220,230,226,0.7)">/home·yr</text>
        </g>

        {/* health warning (coal stages) */}
        <m.g transform="translate(404 40)" animate={{ opacity: active <= 1 ? 1 : 0 }} transition={t}>
          <circle r="13" fill="rgba(239,111,111,0.16)" stroke="#ef6f6f" strokeWidth="1.2" />
          <text x="0" y="4" fontSize="13" textAnchor="middle" fill="#ef6f6f" fontWeight="700">!</text>
        </m.g>

        {/* outcome stat chips */}
        <m.g animate={{ opacity: showStats ? 1 : 0, y: showStats ? 0 : 8 }} transition={t}>
          <g transform="translate(20 262)">
            {[
              ['Homes upgraded', data.homesUpgraded ?? '480'],
              ['CO₂ avoided', (data.co2Avoided ?? '1,600') + ' t/yr'],
              ['Saved / home', data.savings ?? '$220/yr'],
            ].map(([label, val], i) => (
              <g key={i} transform={`translate(${i * 140} 0)`}>
                <text x="0" y="0" fontSize="13" fontWeight="800" fill="#fff" className="eiq-num">{val as string}</text>
                <text x="0" y="13" fontSize="9" fill="rgba(220,230,226,0.7)">{label as string}</text>
              </g>
            ))}
          </g>
        </m.g>
      </g>
    </svg>
  )
}
