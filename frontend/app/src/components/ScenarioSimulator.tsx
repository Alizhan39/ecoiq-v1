/**
 * ScenarioSimulator — move the policy sliders, watch projections update live.
 *
 * A pure, deterministic model turns three levers (coal phase-out pace, capital
 * deployed, grid electrification) into projected outcomes (households
 * converted, CO₂ avoided, cost per home, composite transition score). Outputs
 * animate smoothly via Framer Motion. No backend, no AI calls — fully client
 * side and instant.
 */
import { m } from 'framer-motion'
import { useMemo, useState } from 'react'
import { Reveal, fadeUp, tBase } from '../motion'
import { formatNumber } from '../hooks/useCountUp'

export interface ScenarioSimulatorProps {
  eyebrow?: string
  title?: string
  /** Baseline coal-heated households in scope. */
  baseHouseholds?: number
  /** CO₂ avoided per fully-converted, fully-clean household, tonnes/yr. */
  co2PerHomeT?: number
}

interface Levers {
  phaseOut: number // %
  capitalM: number // $M
  electrification: number // %
}

function project(l: Levers, baseHouseholds: number, co2PerHomeT: number) {
  const phase = l.phaseOut / 100
  const elec = l.electrification / 100

  // Capital gates how many of the targeted homes can actually be retrofitted.
  // ~ $4,200 per home; capital in $M.
  const fundableHomes = (l.capitalM * 1_000_000) / 4200
  const targetedHomes = baseHouseholds * phase
  const households = Math.min(targetedHomes, fundableHomes)

  // Emissions avoided scale with electrification cleanliness.
  const co2T = households * co2PerHomeT * (0.45 + 0.55 * elec)
  const costPerHome = households > 0 ? (l.capitalM * 1_000_000) / households : 0

  // Composite 0–100: coverage, decarbonisation depth, capital efficiency.
  const coverage = targetedHomes > 0 ? households / Math.max(targetedHomes, 1) : 0
  const score = Math.round(
    100 * (0.4 * phase * coverage + 0.4 * elec + 0.2 * Math.min(1, (4200 / Math.max(costPerHome, 1)))),
  )

  return {
    households: Math.round(households),
    co2Kt: Math.round(co2T / 1000),
    costPerHome: Math.round(costPerHome),
    score: Math.max(0, Math.min(100, score)),
    coverage: Math.round(coverage * 100),
  }
}

function Slider({
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step: number
  unit: string
  onChange: (v: number) => void
}) {
  const pct = ((value - min) / (max - min)) * 100
  return (
    <label className="eiq-sim__slider">
      <span className="eiq-sim__slider-head">
        <span>{label}</span>
        <span className="eiq-num eiq-sim__slider-val">
          {formatNumber(value)}
          {unit}
        </span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ background: `linear-gradient(90deg, var(--eiq-accent) ${pct}%, rgba(255,255,255,0.1) ${pct}%)` }}
      />
    </label>
  )
}

function Projection({ label, value, suffix, max, prefix }: { label: string; value: number; suffix?: string; max: number; prefix?: string }) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div className="eiq-sim__proj">
      <div className="eiq-sim__proj-head">
        <span>{label}</span>
        <span className="eiq-num eiq-sim__proj-val">
          {prefix}
          {formatNumber(value)}
          {suffix ? ` ${suffix}` : ''}
        </span>
      </div>
      <div className="eiq-sim__bar">
        <m.div
          className="eiq-sim__bar-fill"
          initial={false}
          animate={{ scaleX: pct / 100 }}
          transition={tBase}
          style={{ transformOrigin: 'left' }}
        />
      </div>
    </div>
  )
}

export default function ScenarioSimulator(props: ScenarioSimulatorProps) {
  const {
    eyebrow = 'Scenario Simulator',
    title = 'Model the transition — live',
    baseHouseholds = 1_200_000,
    co2PerHomeT = 5.4,
  } = props

  const [levers, setLevers] = useState<Levers>({ phaseOut: 60, capitalM: 320, electrification: 55 })
  const out = useMemo(() => project(levers, baseHouseholds, co2PerHomeT), [levers, baseHouseholds, co2PerHomeT])
  const set = (k: keyof Levers) => (v: number) => setLevers((s) => ({ ...s, [k]: v }))

  return (
    <Reveal variants={fadeUp} className="eiq-sim eiq-panel">
      <div className="eiq-eyebrow">{eyebrow}</div>
      <h2 className="eiq-sim__title">{title}</h2>
      <p className="eiq-sim__lede">
        Adjust the policy levers. Projections recompute instantly from EcoIQ's transition model.
      </p>

      <div className="eiq-sim__grid">
        <div className="eiq-sim__controls">
          <Slider label="Coal phase-out pace" value={levers.phaseOut} min={0} max={100} step={5} unit="%" onChange={set('phaseOut')} />
          <Slider label="Capital deployed" value={levers.capitalM} min={0} max={600} step={10} unit="$M" onChange={set('capitalM')} />
          <Slider label="Grid electrification" value={levers.electrification} min={0} max={100} step={5} unit="%" onChange={set('electrification')} />
        </div>

        <div className="eiq-sim__outputs">
          <div className="eiq-sim__score">
            <span className="eiq-sim__score-num eiq-num">{out.score}</span>
            <span className="eiq-sim__score-label">Transition score</span>
          </div>
          <Projection label="Households converted" value={out.households} max={baseHouseholds} />
          <Projection label="CO₂ avoided" value={out.co2Kt} suffix="kt / yr" max={Math.round((baseHouseholds * co2PerHomeT) / 1000)} />
          <Projection label="Cost per home" value={out.costPerHome} prefix="$" max={8000} />
        </div>
      </div>
    </Reveal>
  )
}
