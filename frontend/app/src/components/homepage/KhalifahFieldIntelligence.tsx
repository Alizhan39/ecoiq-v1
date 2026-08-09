/**
 * Khalifah Field Intelligence — the experiential layer under the commercial core.
 *
 * The information problem
 * -----------------------
 * EcoIQ explains environmental systems through data. This section has to make
 * one claim land: field experience is not sightseeing bolted onto a data
 * product, it is where the data gets its meaning. A conventional tourism video
 * block would say the opposite — footage first, product second.
 *
 * So the footage is used as an *argument*, run in three beats: what a person
 * sees, what EcoIQ sees, and what should happen next. The overlay stays thin
 * and the reading happens in a panel beside (desktop) or below (mobile) the
 * video, because burying a landscape under boxes is the exact failure mode the
 * brief rules out.
 *
 * Truthfulness constraints, deliberately hard-coded
 * -------------------------------------------------
 * The supplied clip is illustrative brand footage, not a surveyed site, and
 * Khalifah Eco Tours is NOT confirmed operational. So: no numeric scores, no
 * water-stress / biodiversity / emissions / financing claims about the place
 * on screen, no "Book", "Reserve", "Available dates" or "Next departure"
 * anywhere. The EcoIQ lens is labelled `Illustrative EcoIQ lens` and the Field
 * Brief demonstrates *how* EcoIQ would examine a place. The Field Passport is
 * labelled `Concept preview` and its counters are em dashes, never numbers.
 *
 * Why the stage transitions are CSS
 * ---------------------------------
 * Same constraint documented at length in `ProductArchitecture.tsx`: Framer
 * `animate` props do not update after mount in these islands, though the
 * elements re-render correctly. Elements stay `m.*` under `MotionProvider`;
 * transitions are CSS driven off `data-stage`, using only the locked values
 * (0.18s / 0.42s / 0.7s, cubic-bezier(0.22, 1, 0.36, 1)). No new token, no
 * `layoutId`, no `domMax`, no `motion.*`.
 *
 * Reduced motion
 * --------------
 * Nothing here is animation-gated. Under `prefers-reduced-motion: reduce` the
 * video does not autoplay, and the four stages stop being a timed sequence —
 * they render stacked and complete, so the whole argument is readable from a
 * still poster. The user can still press play.
 */
import { m } from 'framer-motion'
import { useCallback, useEffect, useId, useRef, useState } from 'react'

import { useMediaQuery } from '../../hooks/useMediaQuery'

export type KhalifahFieldIntelligenceProps = {
  /** Derivatives produced offline from the supplied master. */
  src1080?: string
  src720?: string
  poster?: string
  /** Existing routes, resolved server-side. */
  toursHref?: string
  intelligenceHref?: string
  projectsHref?: string
  stewardshipHref?: string
  delegationHref?: string
}

type Audience = 'traveller' | 'student' | 'investor' | 'delegation'

type AudienceCopy = {
  id: Audience
  label: string
  headline: string
  supporting: string
  ctaLabel: string
  ctaKey: 'tours' | 'projects' | 'delegation'
}

/**
 * Stage boundaries are fractions of duration, derived from the supplied file's
 * actual cuts (15.04s; cuts at 2.75s, 6.75s, 10.08s, 12.54s) rather than
 * guessed timestamps — so each beat changes on a shot change, not mid-shot.
 *   human   0.00 -> 0.183  (trail ride)
 *   lens    0.183 -> 0.449 (alpine lake)
 *   brief   0.449 -> 0.833 (underwater stewardship work)
 *   action  0.833 -> 1.00  (team, to camera)
 */
const STAGE_BOUNDS = [0.183, 0.449, 0.833] as const

const STAGE_IDS = ['human', 'lens', 'brief', 'action'] as const
type StageId = (typeof STAGE_IDS)[number]

const AUDIENCES: AudienceCopy[] = [
  {
    id: 'traveller',
    label: 'Traveller',
    headline: 'Experience nature with context.',
    supporting: 'Understand the landscape rather than simply visit it.',
    ctaLabel: 'Explore Eco Tours',
    ctaKey: 'tours',
  },
  {
    id: 'student',
    label: 'Student',
    headline: 'Turn the landscape into a living classroom.',
    supporting: 'Explore how ecosystems, communities, resources and stewardship connect.',
    ctaLabel: 'Explore Educational Experiences',
    ctaKey: 'tours',
  },
  {
    id: 'investor',
    label: 'Investor',
    headline: 'See projects and places beyond the spreadsheet.',
    supporting:
      'Use field experience alongside evidence and your own independent due diligence to understand real-world context.',
    ctaLabel: 'Explore Projects',
    ctaKey: 'projects',
  },
  {
    id: 'delegation',
    label: 'Delegation',
    headline: 'Understand transition challenges on the ground.',
    supporting:
      'Curated field experiences connecting landscapes, projects, communities and local expertise.',
    ctaLabel: 'Plan a Private Delegation',
    ctaKey: 'delegation',
  },
]

const LENSES = [
  'Landscape',
  'Ecosystem',
  'Water',
  'Community',
  'Infrastructure',
  'Stewardship',
  'Opportunity',
]

const OPPORTUNITY_TYPES = [
  'Restoration',
  'Sustainable agriculture',
  'Nature-based tourism',
  'Community enterprise',
  'Project discovery',
]

const ACTIONS = [
  { label: 'Protect', note: 'Keep what is working' },
  { label: 'Restore', note: 'Repair what is degraded' },
  { label: 'Finance', note: 'Fund what is viable' },
  { label: 'Experience', note: 'Go and understand it' },
]

const PASSPORT_ROWS = [
  'Places explored',
  'Ecosystems observed',
  'Local experts met',
  'Projects discovered',
  'Stewardship actions',
  'Learning completed',
]

/**
 * Privacy-safe, vendor-free. This repo has no analytics library and the brief
 * forbids adding one, so events go to an optional global that a future
 * privacy-preserving collector can define. No identifiers, no free text, no
 * URLs, no timing fingerprints — an event name and at most a coarse enum.
 */
function emit(event: string, detail?: Record<string, string>): void {
  const sink = (window as unknown as { ecoiqAnalytics?: (e: string, d?: object) => void })
    .ecoiqAnalytics
  if (typeof sink === 'function') sink(event, detail)
}

export default function KhalifahFieldIntelligence({
  src1080 = '/static/video/khalifah-field-1080.mp4',
  src720 = '/static/video/khalifah-field-720.mp4',
  poster = '/static/video/khalifah-field-poster.jpg',
  toursHref = '/khalifa-tours/',
  intelligenceHref = '/platform/',
  projectsHref = '/projects/',
  stewardshipHref = '/stewardship/',
  delegationHref = '/request-access/enterprise/',
}: KhalifahFieldIntelligenceProps) {
  const baseId = useId()
  const reduced = useMediaQuery('(prefers-reduced-motion: reduce)')
  const wide = useMediaQuery('(min-width: 768px)')

  const sectionRef = useRef<HTMLElement | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  /**
   * Visibility is measured on the media figure, NOT the section. The section is
   * taller than a viewport, so its intersection ratio can never reach a 0.4
   * threshold and the observer would never fire — sources would never attach
   * and the video would never play. The figure is ~16:9 and always can.
   */
  const mediaRef = useRef<HTMLElement | null>(null)

  const [audience, setAudience] = useState<Audience>('traveller')
  const [stage, setStage] = useState<StageId>('human')
  const [playing, setPlaying] = useState(false)
  const [muted, setMuted] = useState(true)
  /**
   * Sources are attached only after the section has been near the viewport
   * once. With `preload="none"` a browser should not fetch anyway, but not
   * rendering <source> at all is the guarantee — nothing can request 7.9MB
   * during initial homepage load.
   */
  const [sourcesReady, setSourcesReady] = useState(false)
  /** A manual pause must not be undone by the observer scrolling back in. */
  const userPaused = useRef(false)
  const startedOnce = useRef(false)

  const active = AUDIENCES.find((a) => a.id === audience) ?? AUDIENCES[0]
  const ctaHref =
    active.ctaKey === 'projects'
      ? projectsHref
      : active.ctaKey === 'delegation'
        ? delegationHref
        : toursHref

  // Attach sources and drive playback from visibility.
  useEffect(() => {
    const node = mediaRef.current
    if (!node || typeof IntersectionObserver === 'undefined') return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setSourcesReady(true)
          if (!reduced && !userPaused.current) {
            videoRef.current?.play().catch(() => {
              /* Autoplay refusal is fine — the poster and controls remain. */
            })
          }
        } else {
          videoRef.current?.pause()
        }
      },
      { threshold: 0.35 },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [reduced])

  const onTimeUpdate = useCallback(() => {
    const video = videoRef.current
    if (!video || !video.duration) return
    const progress = video.currentTime / video.duration
    const index = STAGE_BOUNDS.filter((bound) => progress >= bound).length
    setStage(STAGE_IDS[index])
  }, [])

  const togglePlay = useCallback(() => {
    const video = videoRef.current
    if (!video) return
    setSourcesReady(true)
    if (video.paused) {
      userPaused.current = false
      void video.play().catch(() => undefined)
    } else {
      userPaused.current = true
      video.pause()
    }
  }, [])

  const onPlay = useCallback(() => {
    setPlaying(true)
    if (!startedOnce.current) {
      startedOnce.current = true
      emit('khalifah_field_video_started')
    }
  }, [])

  const chooseAudience = useCallback((next: Audience) => {
    setAudience(next)
    emit('khalifah_audience_selected', { audience: next })
  }, [])

  /** Under reduced motion every stage is shown at once, so no stage is "the" stage. */
  const stageAttr = reduced ? 'all' : stage

  return (
    <section
      ref={sectionRef}
      className="eiq-mo-root eiq-kfi"
      aria-labelledby={`${baseId}-title`}
      data-stage={stageAttr}
    >
      <div className="eiq-kfi-inner">
        <header className="eiq-kfi-head">
          <p className="eiq-kfi-label">Khalifah Field Intelligence</p>
          <h2 id={`${baseId}-title`} className="eiq-kfi-h2">
            See what the data cannot show alone.
          </h2>
          <p className="eiq-kfi-lede">
            EcoIQ connects environmental intelligence with real-world field experience —
            helping people understand landscapes, communities, risks and opportunities
            where they actually exist.
          </p>
          <p className="eiq-kfi-arrow">From screen → to field → to action.</p>
        </header>

        {/* Audience switch — the footage is constant, the reading changes. */}
        <div
          className="eiq-kfi-audience"
          role="tablist"
          aria-label="Read this field experience as"
        >
          {AUDIENCES.map((option) => (
            <button
              key={option.id}
              type="button"
              role="tab"
              id={`${baseId}-tab-${option.id}`}
              aria-selected={audience === option.id}
              aria-controls={`${baseId}-audience-panel`}
              tabIndex={audience === option.id ? 0 : -1}
              className="eiq-kfi-aud-btn"
              data-selected={audience === option.id ? 'true' : 'false'}
              onClick={() => chooseAudience(option.id)}
              onKeyDown={(event) => {
                // Roving focus, per the tablist pattern.
                if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return
                event.preventDefault()
                const i = AUDIENCES.findIndex((a) => a.id === audience)
                const next =
                  event.key === 'ArrowRight'
                    ? AUDIENCES[(i + 1) % AUDIENCES.length]
                    : AUDIENCES[(i - 1 + AUDIENCES.length) % AUDIENCES.length]
                chooseAudience(next.id)
                document.getElementById(`${baseId}-tab-${next.id}`)?.focus()
              }}
            >
              {option.label}
            </button>
          ))}
        </div>

        <div
          className="eiq-kfi-audience-panel"
          id={`${baseId}-audience-panel`}
          role="tabpanel"
          aria-labelledby={`${baseId}-tab-${audience}`}
        >
          <p className="eiq-kfi-aud-headline">{active.headline}</p>
          <p className="eiq-kfi-aud-support">{active.supporting}</p>
          <a
            className="eiq-kfi-aud-cta"
            href={ctaHref}
            onClick={() =>
              emit(
                active.ctaKey === 'projects'
                  ? 'khalifah_projects_clicked'
                  : 'khalifah_ecotours_clicked',
                { audience: active.id },
              )
            }
          >
            {active.ctaLabel}
          </a>
          {/* Tours are not confirmed operational — interest, never a booking. */}
          <a className="eiq-kfi-quiet-link" href={delegationHref}>
            Register interest
          </a>
        </div>

        {/* ---- the experience: footage left, reading right ---- */}
        <div className="eiq-kfi-stage-grid">
          <figure className="eiq-kfi-media" ref={mediaRef}>
            <video
              ref={videoRef}
              className="eiq-kfi-video"
              poster={poster}
              muted={muted}
              playsInline
              preload="none"
              loop={false}
              onTimeUpdate={onTimeUpdate}
              onPlay={onPlay}
              onPause={() => setPlaying(false)}
              onEnded={() => {
                setPlaying(false)
                setStage('action')
                emit('khalifah_field_video_completed')
              }}
              aria-label="Illustrative Khalifah field experience footage: a highland trail ride, an alpine lake, underwater waste recovery, and the field team."
            >
              {sourcesReady && <source src={wide ? src1080 : src720} type="video/mp4" />}
            </video>

            {/* One caption, not a HUD. */}
            <div className="eiq-kfi-overlay" aria-hidden="true">
              <span className="eiq-kfi-overlay-q" data-for="human">
                What do you see?
              </span>
              <span className="eiq-kfi-overlay-q" data-for="lens">
                Now see what EcoIQ sees.
              </span>
              <span className="eiq-kfi-overlay-q" data-for="brief">
                EcoIQ Field Brief
              </span>
              <span className="eiq-kfi-overlay-q" data-for="action">
                What should happen next?
              </span>
            </div>

            <p className="eiq-kfi-illustrative">Illustrative field experience</p>

            <div className="eiq-kfi-controls">
              <button type="button" className="eiq-kfi-ctrl" onClick={togglePlay}>
                {playing ? 'Pause' : 'Play'}
                <span className="eiq-kfi-sr"> the field experience</span>
              </button>
              <button
                type="button"
                className="eiq-kfi-ctrl"
                aria-pressed={!muted}
                onClick={() => setMuted((m2) => !m2)}
              >
                {muted ? 'Unmute' : 'Mute'}
                <span className="eiq-kfi-sr"> footage audio</span>
              </button>
              <ol className="eiq-kfi-progress" aria-hidden="true">
                {STAGE_IDS.map((id) => (
                  <li key={id} data-step={id} />
                ))}
              </ol>
            </div>
            <figcaption className="eiq-kfi-sr">
              Illustrative footage. EcoIQ has not surveyed the location shown; the lenses
              and Field Brief below demonstrate how EcoIQ examines a place, and are not
              findings about this one.
            </figcaption>
          </figure>

          {/*
            All four readings are always in the DOM, stacked in one grid cell and
            cross-faded. That keeps the whole argument available to assistive
            technology and to reduced-motion users, who get them laid out in full
            rather than as a timed sequence they cannot follow.
          */}
          <div className="eiq-kfi-stages">
            <div className="eiq-kfi-panel" data-panel="human">
              <h3 className="eiq-kfi-panel-h">What do you see?</h3>
              <p className="eiq-kfi-panel-note">A person sees a landscape.</p>
              <ul className="eiq-kfi-chips" role="list">
                {['Landscape', 'People', 'Nature', 'Movement'].map((chip, i) => (
                  <li key={chip} style={{ '--i': i } as React.CSSProperties}>
                    {chip}
                  </li>
                ))}
              </ul>
            </div>

            <div className="eiq-kfi-panel" data-panel="lens">
              <h3 className="eiq-kfi-panel-h">Now see what EcoIQ sees.</h3>
              <p className="eiq-kfi-badge">Illustrative EcoIQ lens</p>
              <ul className="eiq-kfi-chips" role="list">
                {LENSES.map((lens, i) => (
                  <li key={lens} style={{ '--i': i } as React.CSSProperties}>
                    {lens}
                  </li>
                ))}
              </ul>
              <p className="eiq-kfi-panel-note">
                Conceptual lenses, not an assessment of this location.
              </p>
            </div>

            <div className="eiq-kfi-panel" data-panel="brief">
              <h3 className="eiq-kfi-panel-h">EcoIQ Field Brief</h3>
              <p className="eiq-kfi-badge">Illustrative EcoIQ lens</p>
              <dl className="eiq-kfi-brief">
                <div>
                  <dt>Location</dt>
                  <dd>Illustrative field experience</dd>
                </div>
                <div>
                  <dt>Landscape</dt>
                  <dd>Natural / rural environment</dd>
                </div>
                <div>
                  <dt>EcoIQ lenses</dt>
                  <dd>Biodiversity · Water · Community · Infrastructure · Stewardship</dd>
                </div>
                <div>
                  <dt>Opportunity types</dt>
                  <dd>{OPPORTUNITY_TYPES.join(' · ')}</dd>
                </div>
              </dl>
              <p className="eiq-kfi-panel-note">
                How EcoIQ would examine a place — not a claim about the footage.
              </p>
            </div>

            <div className="eiq-kfi-panel" data-panel="action">
              <h3 className="eiq-kfi-panel-h">What should happen next?</h3>
              <ul className="eiq-kfi-actions" role="list">
                {ACTIONS.map((action, i) => (
                  <li key={action.label} style={{ '--i': i } as React.CSSProperties}>
                    <strong>{action.label}</strong>
                    <span>{action.note}</span>
                  </li>
                ))}
              </ul>
              <p className="eiq-kfi-closing">
                Understand the land.
                <br />
                Meet the people.
                <br />
                Find the action.
              </p>
            </div>
          </div>
        </div>

        {/* ---- three paths, not five ---- */}
        <ul className="eiq-kfi-paths" role="list">
          <li>
            <p className="eiq-kfi-path-k">Experience it</p>
            <h3>Khalifah Eco Tours</h3>
            <p className="eiq-kfi-path-copy">
              Field experiences that explain the landscape you are standing in.
            </p>
            <m.a
              className="eiq-kfi-cta eiq-kfi-cta--primary"
              href={toursHref}
              onClick={() => emit('khalifah_ecotours_clicked')}
            >
              Explore Khalifah Eco Tours
            </m.a>
          </li>
          <li>
            <p className="eiq-kfi-path-k">Analyse it</p>
            <h3>EcoIQ Intelligence</h3>
            <p className="eiq-kfi-path-copy">
              Explore the companies, projects, countries and environmental signals behind
              real-world decisions.
            </p>
            <m.a
              className="eiq-kfi-cta"
              href={intelligenceHref}
              onClick={() => emit('khalifah_intelligence_clicked')}
            >
              Explore EcoIQ Intelligence
            </m.a>
          </li>
          <li>
            <p className="eiq-kfi-path-k">Act on it</p>
            <h3>Projects</h3>
            <p className="eiq-kfi-path-copy">
              See the projects behind the landscapes, and what each one still needs.
            </p>
            <m.a
              className="eiq-kfi-cta"
              href={projectsHref}
              onClick={() => emit('khalifah_projects_clicked')}
            >
              Explore Projects
            </m.a>
          </li>
        </ul>

        {/* ---- stewardship layer ---- */}
        <div className="eiq-kfi-khalifah">
          <div>
            <p className="eiq-kfi-label">Khalifah</p>
            <p className="eiq-kfi-khalifah-line">
              Stewardship is not only understanding what exists. It is understanding our
              responsibility toward it.
            </p>
            <a className="eiq-kfi-quiet-link" href={stewardshipHref}>
              Explore stewardship methodology
            </a>
          </div>
          <ol className="eiq-kfi-ladder" role="list">
            {['Understand', 'Care', 'Act', 'Account'].map((step, i) => (
              <li key={step} style={{ '--i': i } as React.CSSProperties}>
                {step}
              </li>
            ))}
          </ol>
        </div>

        {/* ---- field passport, concept only ---- */}
        <div className="eiq-kfi-passport">
          <div className="eiq-kfi-passport-head">
            <p className="eiq-kfi-label">Khalifah Field Passport</p>
            <p className="eiq-kfi-badge">Concept preview</p>
          </div>
          <ul className="eiq-kfi-passport-rows" role="list">
            {PASSPORT_ROWS.map((row) => (
              <li key={row}>
                <span>{row}</span>
                {/* Never a number: nothing has been recorded, and inventing counts would be a lie. */}
                <span aria-label="not yet recorded">—</span>
              </li>
            ))}
          </ul>
          <p className="eiq-kfi-panel-note">
            Your journey becomes a record of what you learned, experienced and
            contributed.
          </p>
        </div>
      </div>
    </section>
  )
}
