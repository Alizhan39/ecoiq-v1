/**
 * How EcoIQ Works — the operating model in one glance.
 *
 * The information problem
 * -----------------------
 * The real product architecture is a twelve-stage loop: detect, diagnose,
 * generate, simulate, optimize, match, finance, execute, verify, measure,
 * learn, repeat. Printed as twelve equal cards it is unreadable — the visitor
 * counts boxes instead of understanding a system, and the single most
 * important property, that it *closes*, disappears into the grid.
 *
 * So the twelve stages are grouped into four phases the eye can hold —
 * UNDERSTAND, DECIDE, ACT, LEARN — and the detail sits behind disclosure. The
 * visitor gets the operating model in about ten seconds and the full loop only
 * if they want it. Nothing is simplified away; it is ranked.
 *
 * The closing claim is the point of the section: LEARN returns to UNDERSTAND,
 * so implementation outcomes make the next decision better. A loop that ended
 * at EXECUTE would describe a consultancy. This one describes a system that
 * compounds.
 *
 * Layout economics
 * ----------------
 * This replaces ~1,143px of legacy explanation (the agents block, the old
 * three-step how-it-works, and a digital-twin caption). A single shared detail
 * strip is used rather than expanding each column in place, so opening a phase
 * costs no extra height and the section stays roughly constant — the whole
 * reason the page can shrink.
 *
 * Honesty
 * -------
 * EcoIQ is analyst-reviewed, so the trust rail states that explicitly rather
 * than implying an autonomous machine. The specialist-AI chips name four
 * domains as examples and link to the real agents page; the homepage does not
 * catalogue the agent roster.
 *
 * Motion
 * ------
 * One pass on entry: a signal enters, each phase lights in turn, and the
 * return path draws back to UNDERSTAND. It runs once — the observer
 * disconnects — and no phase is hidden before it activates, so the model reads
 * completely with animation off. CSS off `data-*`, for the reason recorded in
 * `ProductArchitecture.tsx`. Elements stay `m.*` under `MotionProvider`;
 * locked values only; no new token, no `layoutId`, no `domMax`, no `motion.*`,
 * and no visualisation dependency.
 */
import { m } from 'framer-motion'
import { useCallback, useEffect, useId, useRef, useState } from 'react'

import { useMediaQuery } from '../../hooks/useMediaQuery'

export type HowEcoIQWorksProps = {
  platformHref?: string
  methodologyHref?: string
  agentsHref?: string
  workbenchHref?: string
  councilHref?: string
}

type PhaseId = 'understand' | 'decide' | 'act' | 'learn'

const PHASES: {
  id: PhaseId
  name: string
  meaning: string
  copy: string
  /** The real loop stages, each with at most one short sentence. */
  stages: { name: string; note: string }[]
}[] = [
  {
    id: 'understand',
    name: 'Understand',
    meaning: 'Find the problem before it becomes expensive.',
    copy: 'EcoIQ detects material signals, identifies what is changing and diagnoses the underlying cause.',
    stages: [
      { name: 'Detect', note: 'Surface the signal that matters from the noise around it.' },
      { name: 'Diagnose', note: 'Establish what is actually driving it.' },
    ],
  },
  {
    id: 'decide',
    name: 'Decide',
    meaning: 'Explore options before committing resources.',
    copy: 'Generate possible interventions, simulate their consequences and identify the strongest decision pathway.',
    stages: [
      { name: 'Generate', note: 'Put credible interventions on the table.' },
      { name: 'Simulate', note: 'Test what each one would do.' },
      { name: 'Optimize', note: 'Choose the pathway that holds up best.' },
    ],
  },
  {
    id: 'act',
    name: 'Act',
    meaning: 'Connect the decision to the people and capital required.',
    copy: 'Match the solution with relevant providers, financing pathways and execution capability.',
    stages: [
      { name: 'Match', note: 'Find who can deliver it.' },
      { name: 'Finance', note: 'Identify how it gets funded.' },
      { name: 'Execute', note: 'Put it into the ground.' },
    ],
  },
  {
    id: 'learn',
    name: 'Prove & Learn',
    meaning: 'Prove what happened and make the next decision better.',
    copy: 'Verify implementation, measure outcomes and feed real-world evidence back into the system.',
    stages: [
      { name: 'Verify', note: 'Confirm it was actually done.' },
      { name: 'Measure', note: 'Quantify what changed.' },
      { name: 'Learn', note: 'Update the model of how this works.' },
      { name: 'Repeat', note: 'The next decision starts better informed.' },
    ],
  },
]

/** Domains, not a roster. The agents page is the catalogue. */
const SPECIALISTS = ['Climate', 'Finance', 'Governance', 'Stewardship']

/** EcoIQ is analyst-reviewed; the rail says so rather than implying autonomy. */
const TRUST_RAIL = ['Evidence', 'AI analysis', 'Verification', 'Analyst review', 'Decision']

export default function HowEcoIQWorks({
  platformHref = '/platform/',
  methodologyHref = '/methodology/',
  agentsHref = '/ai-agents/',
  workbenchHref = '/ai-agents/workbench/',
  councilHref = '/ai-agents/council-demo/',
}: HowEcoIQWorksProps) {
  const baseId = useId()
  const reduced = useMediaQuery('(prefers-reduced-motion: reduce)')

  const rootRef = useRef<HTMLElement | null>(null)
  const played = useRef(false)
  const [lit, setLit] = useState(reduced ? PHASES.length + 1 : 0)
  const [open, setOpen] = useState<PhaseId | null>(null)

  useEffect(() => {
    if (reduced) {
      setLit(PHASES.length + 1)
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
        // Four phases light in turn, then the return path draws. Once.
        for (let i = 1; i <= PHASES.length + 1; i++) {
          timers.push(window.setTimeout(() => setLit(i), (i - 1) * 460))
        }
      },
      { threshold: 0.25 },
    )
    observer.observe(node)
    return () => {
      observer.disconnect()
      timers.forEach(window.clearTimeout)
    }
  }, [reduced])

  const toggle = useCallback((id: PhaseId) => {
    setOpen((current) => (current === id ? null : id))
  }, [])

  /** Reduced motion shows every phase's detail at once, in a column. */
  const detailState = reduced ? 'all' : (open ?? 'none')

  return (
    <section
      ref={rootRef}
      className="eiq-hw"
      aria-labelledby={`${baseId}-title`}
      data-lit={reduced ? 'all' : String(lit)}
      data-detail={detailState}
    >
      <div className="eiq-hw-inner">
        <header className="eiq-hw-head">
          <p className="eiq-hw-label">EcoIQ Impact Engine&trade;</p>
          <h2 id={`${baseId}-title`} className="eiq-hw-h2">
            One system. From signal to verified impact.
          </h2>
          {/*
            The differentiation, stated once and plainly: most AI stops at the
            answer. Scope is deliberately "complex real-world problems" — never
            "any problem", which would be a claim we cannot stand behind.
          */}
          <p className="eiq-hw-lede">
            A conventional AI returns an answer. EcoIQ continues past it — connecting data,
            people, capital and technology to real-world action across complex problems.
          </p>
        </header>

        {/* The signal that enters the system. */}
        <p className="eiq-hw-signal" aria-hidden="true">
          <span className="eiq-hw-signal-dot" />
          Signal
        </p>

        {/*
          Four phases, each a real disclosure button. The heading lives inside
          the button so screen readers get "Understand, collapsed" rather than
          an unlabelled control.
        */}
        <ol className="eiq-hw-phases" role="list">
          {PHASES.map((phase, i) => (
            <li key={phase.id} data-phase={phase.id} data-index={i}>
              <span className="eiq-hw-rail" aria-hidden="true">
                <span className="eiq-hw-rail-fill" />
              </span>
              <h3 className="eiq-hw-phase-h">
                <button
                  type="button"
                  className="eiq-hw-phase-btn"
                  aria-expanded={reduced ? true : open === phase.id}
                  aria-controls={`${baseId}-detail-${phase.id}`}
                  onClick={() => toggle(phase.id)}
                >
                  <span className="eiq-hw-phase-n">{`0${i + 1}`}</span>
                  <span className="eiq-hw-phase-name">{phase.name}</span>
                  <span className="eiq-hw-phase-count" aria-hidden="true">
                    {phase.stages.length}
                  </span>
                </button>
              </h3>
              <p className="eiq-hw-meaning">{phase.meaning}</p>
            </li>
          ))}
        </ol>

        {/*
          One shared detail strip rather than expanding each column in place:
          opening a phase costs no extra page height, which is the whole reason
          this section can replace ~1,143px of legacy explanation.
        */}
        <div className="eiq-hw-details">
          {PHASES.map((phase) => (
            <div
              key={phase.id}
              id={`${baseId}-detail-${phase.id}`}
              className="eiq-hw-detail"
              data-for={phase.id}
              hidden={!reduced && open !== phase.id}
            >
              <p className="eiq-hw-detail-copy">{phase.copy}</p>
              <ol className="eiq-hw-stages" role="list">
                {phase.stages.map((stage, j) => (
                  <li key={stage.name} style={{ '--i': j } as React.CSSProperties}>
                    <span className="eiq-hw-stage-name">{stage.name}</span>
                    <span className="eiq-hw-stage-note">{stage.note}</span>
                  </li>
                ))}
              </ol>
              {phase.id === 'decide' && (
                <div className="eiq-hw-specialists">
                  <p>
                    Specialist AI investigates different parts of the decision:{' '}
                    {SPECIALISTS.join(' · ')}.
                  </p>
                  {/*
                    The three agent entry points the retired #4 block owned. They
                    are real destinations the product depends on being reachable
                    from the homepage, so they move here rather than disappearing
                    with the block — as links, not as a 674px explainer.
                  */}
                  <ul className="eiq-hw-agent-links" role="list">
                    <li>
                      <a href={agentsHref}>Try the AI agents</a>
                    </li>
                    <li>
                      <a href={councilHref}>Watch the agent council</a>
                    </li>
                    <li>
                      <a href={workbenchHref}>See how a decision happened</a>
                    </li>
                  </ul>
                </div>
              )}
            </div>
          ))}
          {/*
            The collapsed state shows the whole loop as one quiet line rather
            than a "select a phase" hint. It fills the reserved box with the
            actual twelve stages — so the loop is legible at a glance and the
            reserved space costs nothing in comprehension — and it is what the
            phase buttons then drill into.
          */}
          <div className="eiq-hw-overview" hidden={reduced || open !== null}>
            <p className="eiq-hw-overview-l">The full loop</p>
            <ol className="eiq-hw-overview-loop" role="list">
              {PHASES.flatMap((phase) => phase.stages).map((stage) => (
                <li key={stage.name}>{stage.name}</li>
              ))}
            </ol>
            <p className="eiq-hw-overview-hint">Select a phase above for what each stage does.</p>
          </div>
        </div>

        {/* The loop closes — the claim this section exists to make. */}
        <div className="eiq-hw-loop">
          <span className="eiq-hw-loop-arc" aria-hidden="true" />
          <p className="eiq-hw-loop-lines">
            <strong>EcoIQ does not stop at recommendation.</strong> It follows the decision
            through execution, verification and learning — every completed decision feeds
            evidence back into the system, improving the next one.
          </p>
          <p className="eiq-hw-tagline">From problems to measurable progress.</p>
        </div>

        <div className="eiq-hw-foot">
          <ol className="eiq-hw-trust" role="list" aria-label="How a decision is checked">
            {TRUST_RAIL.map((node) => (
              <li key={node}>{node}</li>
            ))}
          </ol>
          <div className="eiq-hw-ctas">
            <m.a className="eiq-hw-cta eiq-hw-cta--primary" href={platformHref}>
              Explore the EcoIQ Platform
            </m.a>
            <a className="eiq-hw-cta" href={methodologyHref}>
              View Methodology
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
