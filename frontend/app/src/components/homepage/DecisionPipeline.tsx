/**
 * Hero sequence: evidence becomes a decision.
 *
 * The information problem this solves: "evidence-to-capital intelligence
 * platform" is abstract, and a visitor cannot picture what EcoIQ does to an
 * input. Four cards fading in would not fix that — they would show four
 * unrelated things. So the sequence *transforms*: one stage hands off to the
 * next, each new stage entering from the one before it, until a decision
 * resolves. The transformation is the message.
 *
 * Why not `layoutId`
 * ------------------
 * The motion map originally specified shared-layout animation. It cannot be
 * used here: `MotionProvider` mounts `LazyMotion` with `domAnimation`, which
 * does not include layout animation — that needs `domMax`, a larger bundle —
 * and `strict` is on, so `motion.*` throws and only `m.*` is available. No
 * island in the codebase uses `layout` or `layoutId` today.
 *
 * Switching the provider to `domMax` for one hero would regress a deliberate
 * performance decision. Transform and opacity express the same handoff, and
 * the motion library asks for exactly that anyway. So the stages travel with
 * `y`/`opacity` and the connectors draw with `scaleY`.
 *
 * Reduced motion: `MotionConfig reducedMotion="user"` in the provider already
 * neutralises the transforms globally — no local `useReducedMotion()` needed
 * for that. What it cannot do is decide the *information* layout, so this
 * component does branch on the preference for one thing: when reduced motion
 * is on, every stage renders at once as a complete static pipeline rather than
 * arriving one at a time. That is the "different static representation"
 * exception, and the only place this file checks.
 */
import { AnimatePresence, m, useReducedMotion } from 'framer-motion'
import { useEffect, useState } from 'react'

import { color, duration, ease, font, radius } from '../../design/tokens'

type Stage = {
  id: string
  label: string
  detail: string
  tone: 'neutral' | 'signal' | 'accent'
}

/**
 * The four beats. Deliberately the same vocabulary the rest of the page uses,
 * so the hero teaches the words the product cards then rely on.
 */
const STAGES: Stage[][] = [
  [{ id: 'evidence', label: 'Evidence', detail: 'Disclosures, filings, operational data', tone: 'neutral' }],
  [
    { id: 'risk', label: 'Risk', detail: 'Transition and governance signals', tone: 'signal' },
    { id: 'readiness', label: 'Readiness', detail: 'Evidence quality and gaps', tone: 'signal' },
  ],
  [{ id: 'capital', label: 'Capital pathways', detail: 'Indicative routes to finance', tone: 'signal' }],
  [{ id: 'decision', label: 'Proceed with conditions', detail: 'Decision brief · 90-day actions', tone: 'accent' }],
]

/** Beat length. `slow` reads as deliberate; faster feels like a slideshow. */
const BEAT_MS = duration.slow * 1000

const TONE: Record<Stage['tone'], { border: string; text: string; glow: string }> = {
  neutral: { border: color.border, text: color.ink, glow: 'transparent' },
  signal: { border: color.borderAccent, text: color.ink, glow: 'transparent' },
  accent: { border: 'rgba(0,232,154,.42)', text: color.accent, glow: color.accentGlow },
}

function StageCard({ stage }: { stage: Stage }) {
  const tone = TONE[stage.tone]
  return (
    <m.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: duration.base, ease: ease.out }}
      style={{
        background: color.surface,
        border: `1px solid ${tone.border}`,
        borderRadius: radius.md,
        padding: '14px 18px',
        minWidth: 0,
        flex: '1 1 0',
        boxShadow: tone.glow === 'transparent' ? 'none' : `0 10px 40px -8px ${tone.glow}`,
      }}
    >
      <div style={{ color: tone.text, fontWeight: 700, fontSize: '.95rem', letterSpacing: '-.01em' }}>
        {stage.label}
      </div>
      <div style={{ color: color.muted, fontSize: '.78rem', marginTop: 4, lineHeight: 1.4 }}>
        {stage.detail}
      </div>
    </m.div>
  )
}

/** Vertical rule between beats. Draws downward so the eye follows the handoff. */
function Connector() {
  return (
    <m.div
      aria-hidden="true"
      initial={{ scaleY: 0, opacity: 0 }}
      animate={{ scaleY: 1, opacity: 1 }}
      transition={{ duration: duration.base, ease: ease.out }}
      style={{
        width: 1,
        height: 22,
        margin: '0 auto',
        transformOrigin: 'top',
        background: `linear-gradient(180deg, ${color.borderAccent}, transparent)`,
      }}
    />
  )
}

export default function DecisionPipeline() {
  const reduced = useReducedMotion()
  // Reduced motion shows the whole pipeline immediately; there is no sequence
  // to follow, so every beat is present from the first paint.
  const [beat, setBeat] = useState(reduced ? STAGES.length : 1)

  useEffect(() => {
    if (reduced || beat >= STAGES.length) return
    const timer = window.setTimeout(() => setBeat((n) => n + 1), BEAT_MS)
    return () => window.clearTimeout(timer)
  }, [beat, reduced])

  const visible = STAGES.slice(0, beat)
  const complete = beat >= STAGES.length

  return (
    <div>
      {/*
        The sequence is decorative *timing* over information that is fully
        present in the DOM by the end. Screen readers get the finished pipeline
        announced once, rather than four interruptions as beats land.
      */}
      <div aria-live="off">
        {visible.map((row, index) => (
          <div key={row[0].id}>
            {index > 0 && <Connector />}
            <div style={{ display: 'flex', gap: 10 }}>
              <AnimatePresence initial={!reduced}>
                {row.map((stage) => (
                  <StageCard key={stage.id} stage={stage} />
                ))}
              </AnimatePresence>
            </div>
          </div>
        ))}
      </div>

      {/*
        Appears only once the sequence resolves, so it does not compete with the
        transformation for attention. Never hidden from assistive tech.
      */}
      <m.p
        initial={{ opacity: 0 }}
        animate={{ opacity: complete ? 1 : 0 }}
        transition={{ duration: duration.base, ease: ease.out }}
        style={{
          fontFamily: font.mono,
          fontSize: '.7rem',
          letterSpacing: '.08em',
          textTransform: 'uppercase',
          color: color.faint,
          marginTop: 16,
          marginBottom: 0,
        }}
      >
        Illustrative — every EcoIQ conclusion is traceable to evidence
      </m.p>
    </div>
  )
}
