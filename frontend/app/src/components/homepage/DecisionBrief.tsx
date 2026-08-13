/**
 * Sample Decision Brief — the proof-of-product section.
 *
 * The information problem
 * -----------------------
 * "AI-assisted climate intelligence" is a category claim. A visitor cannot
 * price it, challenge it or buy it until they have seen what actually lands on
 * their desk. A dashboard screenshot would not fix that: dashboards show
 * *data*, and the thing EcoIQ sells is a *decision* — a position someone can
 * defend in a meeting.
 *
 * So the section is built as the decision itself, disclosed in the order a
 * reader would interrogate it:
 *
 *   71 / PROCEED — WITH CONDITIONS     the position
 *     -> Why 71?                       the five dimensions behind it
 *     -> Key finding                   what the dimensions mean together
 *     -> Recommended next move         what to do about it
 *     -> What changes the decision?    what would move the position
 *
 * That last step is the argument. A score is a number; a score plus the levers
 * that move it is an instrument. The scenario controls exist to teach that
 * EcoIQ explains *what changes the decision*, not merely what the decision is.
 *
 * Truthfulness, hard-coded
 * ------------------------
 * Every figure here is invented for illustration. There is no customer, no
 * asset and no survey behind it. So: a permanent "Illustrative EcoIQ decision
 * brief" label, scenario output framed as "potential decision improvement"
 * under an "Illustrative scenario" heading, and nowhere the words forecast,
 * prediction, expected or guaranteed. The uplift arithmetic is deliberately
 * simple and visible in this file rather than dressed up as a model.
 *
 * Motion
 * ------
 * The reveal runs once, on entry, and communicates causality: the score emits
 * its dimensions, the dimensions resolve into a finding, the finding produces
 * a recommendation. Nothing loops. Transitions are CSS off `data-*`, for the
 * reason recorded in `ProductArchitecture.tsx` — Framer `animate` props do not
 * update after mount in these islands. Elements stay `m.*` under
 * `MotionProvider`; locked values only; no new token, no `layoutId`, no
 * `domMax`, no `motion.*`.
 *
 * Reduced motion / no interaction
 * -------------------------------
 * Every panel is real text in the DOM at all times. The disclosure is a
 * genuine disclosure (`aria-expanded` + `aria-controls`), and under
 * `prefers-reduced-motion` the whole brief renders open and still, so the
 * argument survives with no animation and no clicking.
 */
import { m } from 'framer-motion'
import { useCallback, useEffect, useId, useRef, useState } from 'react'

import { useMediaQuery } from '../../hooks/useMediaQuery'

export type DecisionBriefProps = {
  reviewHref?: string
  methodologyHref?: string
}

type Dimension = {
  id: string
  label: string
  score: number
  /** Which levers touch this dimension, and by how much. Illustrative only. */
  liftedBy?: Partial<Record<LeverId, number>>
}

type LeverId = 'evidence' | 'energy' | 'financing'

const BASE_SCORE = 71

const DIMENSIONS: Dimension[] = [
  { id: 'evidence', label: 'Evidence Quality', score: 82, liftedBy: { evidence: 9 } },
  { id: 'transition', label: 'Transition Risk', score: 61, liftedBy: { energy: 12 } },
  { id: 'implementation', label: 'Implementation Readiness', score: 74, liftedBy: { energy: 5 } },
  { id: 'capital', label: 'Capital Readiness', score: 68, liftedBy: { financing: 11 } },
  { id: 'stewardship', label: 'Stewardship Alignment', score: 76 },
]

const LEVERS: { id: LeverId; label: string }[] = [
  { id: 'evidence', label: 'Resolve evidence gaps' },
  { id: 'energy', label: 'Improve energy pathway' },
  { id: 'financing', label: 'Secure financing structure' },
]

/** Reveal steps, in causal order. Each waits for the one before it. */
const STEPS = ['score', 'dimensions', 'finding', 'recommendation'] as const

export default function DecisionBrief({
  reviewHref = '/request-access/review/',
  methodologyHref = '/methodology/',
}: DecisionBriefProps) {
  const baseId = useId()
  const reduced = useMediaQuery('(prefers-reduced-motion: reduce)')

  const rootRef = useRef<HTMLElement | null>(null)
  /** The entry reveal must happen exactly once, never on re-scroll. */
  const revealed = useRef(false)
  const [step, setStep] = useState<number>(reduced ? STEPS.length : 0)
  const [expanded, setExpanded] = useState(false)
  const [levers, setLevers] = useState<Set<LeverId>>(new Set())

  // Run the causal reveal once, when the brief first enters the viewport.
  useEffect(() => {
    if (reduced) {
      setStep(STEPS.length)
      return
    }
    const node = rootRef.current
    if (!node || typeof IntersectionObserver === 'undefined') return
    const timers: number[] = []
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting || revealed.current) return
        revealed.current = true
        observer.disconnect()
        // score -> dimensions -> finding -> recommendation
        STEPS.forEach((_, i) => {
          timers.push(window.setTimeout(() => setStep(i + 1), i * 520))
        })
      },
      { threshold: 0.3 },
    )
    observer.observe(node)
    return () => {
      observer.disconnect()
      timers.forEach(window.clearTimeout)
    }
  }, [reduced])

  const toggleLever = useCallback((id: LeverId) => {
    setLevers((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  /**
   * Illustrative arithmetic, kept deliberately transparent: each selected
   * lever adds its declared points to the dimensions it touches, and the
   * headline is the mean of the five. This is a teaching device for "what
   * moves the decision", not a model output — hence the label above it.
   */
  const projected = DIMENSIONS.map((d) => {
    const lift = [...levers].reduce((sum, lever) => sum + (d.liftedBy?.[lever] ?? 0), 0)
    return { ...d, projectedScore: Math.min(100, d.score + lift) }
  })
  const projectedHeadline = Math.round(
    projected.reduce((sum, d) => sum + d.projectedScore, 0) / projected.length,
  )
  const delta = projectedHeadline - BASE_SCORE
  /**
   * The headline the visitor is currently looking at. The disclosure label
   * tracks it, so the control never reads "Why 71?" beside a score of 76.
   */
  const headline = levers.size ? projectedHeadline : BASE_SCORE

  /**
   * `none` until the reveal starts, so the entry transition has a state to
   * animate *from*. Without it the brief would render fully formed and the
   * causal sequence would never be seen.
   */
  const stepName = step === 0 ? 'none' : STEPS[Math.min(step, STEPS.length) - 1]
  /**
   * Under reduced motion the breakdown is open and stays open. `aria-expanded`
   * follows the same value as `hidden`, so state and exposure cannot disagree.
   */
  const breakdownOpen = expanded || reduced

  return (
    <section
      ref={rootRef}
      className="eiq-mo-root eiq-db"
      aria-labelledby={`${baseId}-title`}
      data-step={reduced ? 'all' : stepName}
      data-expanded={breakdownOpen ? 'true' : 'false'}
    >
      <div className="eiq-db-inner">
        <header className="eiq-db-head">
          <p className="eiq-db-label">Sample decision brief</p>
          <h2 id={`${baseId}-title`} className="eiq-db-h2">
            See the decision, not the dashboard.
          </h2>
          <p className="eiq-db-lede">
            EcoIQ turns fragmented evidence into a decision your team can understand,
            challenge and act on.
          </p>
        </header>

        <div className="eiq-db-card">
          <p className="eiq-db-illustrative">Illustrative EcoIQ decision brief</p>

          {/* ---- the position ---- */}
          <div className="eiq-db-verdict">
            <div className="eiq-db-score">
              <span className="eiq-db-score-n">{headline}</span>
              <span className="eiq-db-score-d">/ 100</span>
            </div>
            <div>
              <p className="eiq-db-asset">Industrial Portfolio — Transition Review</p>
              <p className="eiq-db-decision">Proceed — with conditions</p>
              {levers.size > 0 && (
                <p className="eiq-db-delta">
                  Potential decision improvement: +{delta} under the selected illustrative
                  scenario
                </p>
              )}
            </div>
          </div>

          {/* ---- why 71? ---- */}
          <button
            type="button"
            className="eiq-db-why"
            aria-expanded={breakdownOpen}
            aria-controls={`${baseId}-breakdown`}
            onClick={() => setExpanded((v) => !v)}
          >
            <span aria-hidden="true" className="eiq-db-why-icon">
              +
            </span>
            Why {headline}?
          </button>

          <div id={`${baseId}-breakdown`} className="eiq-db-breakdown" hidden={!breakdownOpen}>
            <ol className="eiq-db-dims" role="list">
              {projected.map((d, i) => {
                const moved = d.projectedScore !== d.score
                return (
                  <li key={d.id} style={{ '--i': i } as React.CSSProperties}>
                    <span className="eiq-db-dim-l">{d.label}</span>
                    <span className="eiq-db-dim-bar" aria-hidden="true">
                      <span
                        className="eiq-db-dim-fill"
                        style={{ width: `${d.projectedScore}%` }}
                        data-moved={moved ? 'true' : 'false'}
                      />
                    </span>
                    <span className="eiq-db-dim-n">
                      {d.projectedScore}
                      {moved && <span className="eiq-db-dim-was"> (from {d.score})</span>}
                    </span>
                  </li>
                )
              })}
            </ol>
          </div>

          {/* ---- what it means, and what to do ---- */}
          <div className="eiq-db-reads">
            <div className="eiq-db-read" data-read="finding">
              <h3>Key finding</h3>
              <p>
                The project is viable, but implementation risk remains concentrated in energy
                exposure and evidence gaps.
              </p>
            </div>
            <div className="eiq-db-read" data-read="recommendation">
              <h3>Recommended next move</h3>
              <p>
                Resolve the two evidence gaps and model the preferred transition scenario
                before capital deployment.
              </p>
            </div>
          </div>

          {/* ---- the levers: what changes the decision ---- */}
          <div className="eiq-db-levers">
            <div className="eiq-db-levers-head">
              <h3>What changes the decision?</h3>
              <p className="eiq-db-scenario-tag">Illustrative scenario</p>
            </div>
            <ul className="eiq-db-lever-list" role="list">
              {LEVERS.map((lever) => (
                <li key={lever.id}>
                  <button
                    type="button"
                    className="eiq-db-lever"
                    aria-pressed={levers.has(lever.id)}
                    onClick={() => toggleLever(lever.id)}
                  >
                    {lever.label}
                  </button>
                </li>
              ))}
            </ul>
            <p className="eiq-db-note">
              Selecting a lever shows how the same brief could read if that condition were
              met. Illustrative only — not a forecast of any real outcome.
            </p>
          </div>
        </div>

        <div className="eiq-db-cta-row">
          <m.a className="eiq-db-cta eiq-db-cta--primary" href={reviewHref}>
            Request Your EcoIQ Review
          </m.a>
          <a className="eiq-db-cta" href={methodologyHref}>
            See Methodology
          </a>
          {/* Carried over from the retired review CTA block — it lowers the bar
              to enquire and had no other home. */}
          <p className="eiq-db-reassure">No payment required to submit a review request.</p>
        </div>
      </div>
    </section>
  )
}
