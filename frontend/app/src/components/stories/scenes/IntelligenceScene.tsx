/**
 * IntelligenceScene — how EcoIQ works, as an operating picture.
 * Four phases over a stylized Kazakhstan map: IDENTIFY villages (scanning beam
 * lights up dots) → MEASURE impact (rings) → TRACK outcomes (links to a hub) →
 * REPORT (a document assembles). Palantir-style operational visualization.
 */
import { m } from 'framer-motion'
import { sceneEase as t, type SceneProps } from './types'
import { KZ_PATH } from '../../kazakhstan/geo'

// Village points scattered across the south (viewBox 0..1000 x 0..480 → scaled).
const SITES = [
  [536, 346], [584, 360], [648, 378], [872, 338],
  [700, 320], [610, 300], [760, 360], [500, 320],
] as const
const HUB: [number, number] = [690, 150]
const PHASES = ['Identify', 'Measure', 'Track', 'Report']

export default function IntelligenceScene({ active }: SceneProps) {
  const phase = Math.min(active, 3)
  const identify = phase >= 0
  const measure = phase >= 1
  const track = phase >= 2
  const report = phase >= 3

  return (
    <svg viewBox="0 0 1000 480" className="eiq-scene__svg" role="img" aria-label="EcoIQ intelligence: identify, measure, track, report">
      <defs>
        <linearGradient id="eiqScan" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="rgba(0,232,154,0)" />
          <stop offset="50%" stopColor="rgba(0,232,154,0.5)" />
          <stop offset="100%" stopColor="rgba(0,232,154,0)" />
        </linearGradient>
        <clipPath id="eiqIntelClip"><rect width="1000" height="480" rx="16" /></clipPath>
      </defs>

      <g clipPath="url(#eiqIntelClip)">
        <rect width="1000" height="480" fill="#06140f" />
        {/* graticule */}
        <g stroke="rgba(255,255,255,0.045)" strokeWidth="1">
          {[120, 240, 360].map((y) => <line key={y} x1="0" y1={y} x2="1000" y2={y} />)}
          {[250, 500, 750].map((x) => <line key={x} x1={x} y1="0" x2={x} y2="480" />)}
        </g>

        <path d={KZ_PATH} fill="rgba(0,232,154,0.04)" stroke="rgba(0,232,154,0.30)" strokeWidth="1.4" />

        {/* scanning beam (identify) */}
        {identify && !report && (
          <rect x="-160" y="0" width="160" height="480" fill="url(#eiqScan)" className="eiq-scan-beam" />
        )}

        {/* track links to hub */}
        {track && SITES.map(([x, y], i) => (
          <m.line key={`t${i}`} x1={x} y1={y} x2={HUB[0]} y2={HUB[1]}
            stroke="rgba(0,232,154,0.35)" strokeWidth="1"
            initial={{ pathLength: 0, opacity: 0 }} animate={{ pathLength: 1, opacity: 1 }} transition={{ duration: 0.8, delay: i * 0.06 }} />
        ))}

        {/* village dots */}
        {SITES.map(([x, y], i) => (
          <g key={i}>
            {measure && <circle cx={x} cy={y} r="14" fill="none" stroke="rgba(0,232,154,0.5)" strokeWidth="1" className="eiq-measure-ring" style={{ animationDelay: `${i * 0.15}s`, transformOrigin: `${x}px ${y}px` }} />}
            <m.circle cx={x} cy={y} r="5" fill={identify ? '#00e89a' : 'rgba(255,255,255,0.2)'} initial={false} animate={{ scale: identify ? 1 : 0.6, opacity: identify ? 1 : 0.4 }} transition={{ delay: i * 0.05, ...t }} style={{ transformOrigin: `${x}px ${y}px` }} />
          </g>
        ))}

        {/* hub + report document */}
        {track && (
          <g>
            <circle cx={HUB[0]} cy={HUB[1]} r="22" fill="rgba(0,232,154,0.12)" stroke="#00e89a" strokeWidth="1.5" />
            <text x={HUB[0]} y={HUB[1] + 5} textAnchor="middle" fontSize="15" fontWeight="800" fill="#fff">IQ</text>
          </g>
        )}
        <m.g initial={false} animate={{ opacity: report ? 1 : 0, y: report ? 0 : 16 }} transition={t}>
          <g transform="translate(820 70)">
            <rect x="0" y="0" width="120" height="150" rx="8" fill="#0c211a" stroke="var(--eiq-accent)" strokeWidth="1.4" />
            {[24, 48, 72, 96, 120].map((ly, i) => (
              <line key={i} x1="16" y1={ly} x2={i % 2 ? 86 : 104} y2={ly} stroke="rgba(0,232,154,0.5)" strokeWidth="3" strokeLinecap="round" />
            ))}
            <text x="60" y="142" textAnchor="middle" fontSize="11" fill="var(--eiq-muted)">Impact report</text>
          </g>
        </m.g>

        {/* phase label */}
        <g transform="translate(40 56)">
          {PHASES.map((p, i) => (
            <text key={p} x={i * 96} y="0" fontSize="14" fontWeight={i === phase ? 800 : 500} fill={i === phase ? '#00e89a' : i < phase ? 'rgba(0,232,154,0.5)' : 'rgba(255,255,255,0.3)'}>
              {i + 1}. {p}
            </text>
          ))}
        </g>
      </g>
    </svg>
  )
}
