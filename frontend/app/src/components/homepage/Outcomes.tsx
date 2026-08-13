/**
 * Outcomes — the "so what?" that follows the Decision Brief.
 *
 * The information problem
 * -----------------------
 * The section above proves EcoIQ produces a decision. This one has to answer
 * the question a buyer asks next: and then what happens to my business? Four
 * benefit cards would answer it badly — a grid says these are four separate
 * things you get, when the actual claim is that one thing leads to the next:
 * seeing risk is what makes a decision possible, a decision is what makes
 * action prioritisable, and action is what produces impact worth measuring.
 *
 * So it is built as a single chain, not a set. The connectors between stages
 * are the content: they carry the causality the grid would have thrown away.
 * The loop closes deliberately — measured impact becomes evidence for the next
 * decision — which is the same spine as the hero pipeline and the Khalifah
 * field section, stated in commercial terms.
 *
 * Honesty
 * -------
 * No customer statistics, no percentages, no invented case studies. The
 * outcome chips name *kinds* of result ("Risk reduced", "Evidence
 * strengthened"), never quantities, and the section explicitly says EcoIQ does
 * not replace management judgement.
 *
 * Motion
 * ------
 * The chain activates once, in order, when the section enters the viewport.
 * Earlier stages stay fully legible and merely quieten — activation is
 * emphasis, never reveal, so nothing is conveyed by animation alone and the
 * reduced-motion path needs no substitute content. No loops, no keyframes, no
 * scroll hijacking.
 *
 * Transitions are CSS off `data-active`, for the reason recorded at length in
 * `ProductArchitecture.tsx`: Framer `animate` props do not update after mount
 * in these islands. Elements stay `m.*` under `MotionProvider`; locked values
 * only; no new token, no `layoutId`, no `domMax`, no `motion.*`.
 */
import { m } from 'framer-motion'
import { useEffect, useId, useRef, useState } from 'react'

import { useMediaQuery } from '../../hooks/useMediaQuery'

export type OutcomesProps = {
  enterpriseHref?: string
}

const STAGES = [
  {
    id: 'risk',
    step: 'Risk',
    label: 'See the risk',
    copy: 'Identify missing evidence, transition exposure, governance weaknesses and execution risk before they become expensive surprises.',
    items: ['Evidence gaps', 'Transition exposure', 'Governance weakness', 'Execution risk'],
  },
  {
    id: 'decision',
    step: 'Decision',
    label: 'Make the decision',
    copy: 'Turn evidence into a clear recommendation, understand the conditions behind it and see what would change the outcome.',
    items: ['Clear recommendation', 'Stated conditions', 'What moves the score'],
  },
  {
    id: 'action',
    step: 'Action',
    label: 'Prioritise the action',
    copy: 'Translate the decision into a focused sequence of interventions, responsibilities and next steps.',
    items: ['90-day priorities', 'Evidence closure', 'Scenario modelling', 'Capital preparation'],
  },
  {
    id: 'impact',
    step: 'Impact',
    label: 'Measure the impact',
    copy: 'Track what changed, verify outcomes and feed new evidence back into the next decision cycle.',
    items: ['Risk reduced', 'Evidence strengthened', 'Capital readiness improved', 'Actions verified'],
  },
] as const

/** What the chain is worth commercially — plain statements, no numbers. */
const VALUE = [
  'Reduce avoidable risk',
  'Identify waste and inefficiency',
  'Prioritise capital and interventions',
  'Create evidence for boards, investors and stakeholders',
]

export default function Outcomes({
  enterpriseHref = '/request-access/enterprise/',
}: OutcomesProps) {
  const baseId = useId()
  const reduced = useMediaQuery('(prefers-reduced-motion: reduce)')

  const rootRef = useRef<HTMLElement | null>(null)
  /** The chain advances once. Casual re-scrolling must never replay it. */
  const played = useRef(false)
  const [active, setActive] = useState(reduced ? STAGES.length : 0)

  useEffect(() => {
    if (reduced) {
      setActive(STAGES.length)
      return
    }
    const node = rootRef.current
    if (!node || typeof IntersectionObserver === 'undefined') return
    const timers: number[] = []
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting || played.current) return
        played.current = true
        observer.disconnect()
        STAGES.forEach((_, i) => {
          timers.push(window.setTimeout(() => setActive(i + 1), i * 480))
        })
      },
      { threshold: 0.25 },
    )
    observer.observe(node)
    return () => {
      observer.disconnect()
      timers.forEach(window.clearTimeout)
    }
  }, [reduced])

  return (
    <section
      ref={rootRef}
      className="eiq-mo-root eiq-oc"
      aria-labelledby={`${baseId}-title`}
      data-active={reduced ? 'all' : String(active)}
    >
      <div className="eiq-oc-inner">
        <header className="eiq-oc-head">
          <p className="eiq-oc-label">Outcomes</p>
          <h2 id={`${baseId}-title`} className="eiq-oc-h2">
            From analysis to measurable outcomes.
          </h2>
          <p className="eiq-oc-lede">
            EcoIQ helps teams move from fragmented evidence to clearer decisions,
            prioritised action and measurable impact.
          </p>
        </header>

        {/*
          An ordered list, because the order is the argument. Each stage is a
          real list item with a real heading; nothing here is a clickable div.
        */}
        <ol className="eiq-oc-chain" role="list">
          {STAGES.map((stage, i) => (
            <li key={stage.id} data-stage={stage.id} data-index={i}>
              <div className="eiq-oc-connector" aria-hidden="true">
                <span className="eiq-oc-connector-fill" />
              </div>
              <p className="eiq-oc-step">{stage.step}</p>
              <h3 className="eiq-oc-stage-label">{stage.label}</h3>
              <p className="eiq-oc-copy">{stage.copy}</p>
              <ul className="eiq-oc-items" role="list">
                {stage.items.map((item, j) => (
                  <li key={item} style={{ '--i': j } as React.CSSProperties}>
                    {item}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ol>

        <p className="eiq-oc-loop">
          Measured impact becomes evidence for the next decision.
        </p>

        <div className="eiq-oc-foot">
          <ul className="eiq-oc-value" role="list">
            {VALUE.map((v) => (
              <li key={v}>{v}</li>
            ))}
          </ul>
          <div className="eiq-oc-trust">
            <p className="eiq-oc-trust-line">
              EcoIQ does not replace management judgement. It helps teams make that
              judgement with better evidence.
            </p>
            <m.a className="eiq-oc-cta" href={enterpriseHref}>
              Explore Enterprise Use Cases
            </m.a>
          </div>
        </div>
      </div>
    </section>
  )
}
