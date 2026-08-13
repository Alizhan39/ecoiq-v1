/**
 * Khalifah Field Intelligence — the field/stewardship layer, in one screen.
 *
 * The claim this has ten seconds to land
 * --------------------------------------
 * Eco Tours are not tourism. A visitor arrives at a place and leaves
 * understanding it as a system. The video carries that emotionally; the
 * narrative beside it names the four moves — observe, understand, steward,
 * act — and the pipeline strip ties them to the same spine as the hero's
 * Decision Pipeline, so this reads as EcoIQ doing EcoIQ in the physical world
 * rather than a travel product bolted on.
 *
 * Consolidated, not appended
 * --------------------------
 * This replaces a longer first version (1,611px) that carried a four-way
 * audience switch, a three-card path grid and a Field Passport concept block —
 * six links and four competing CTAs. That fought the commercial core it sits
 * below. What survived: the footage, the honesty labels, the stewardship idea
 * (now the STEWARD step) and a single primary CTA. Everything the removed
 * blocks pointed at is still reachable from the homepage's Product
 * Architecture section, which is where product choice belongs.
 *
 * Truthfulness, hard-coded
 * ------------------------
 * The clip is illustrative brand footage of an unsurveyed location and the
 * tour operation is NOT confirmed operational. So the section describes a
 * model being developed, never an established service: no "Book", "Reserve",
 * "Available dates" or "Next departure"; no score, percentage or ecological
 * finding about the place on screen; a permanent "Illustrative field
 * experience" badge and an explicit in-development line.
 *
 * Accessibility over motion
 * -------------------------
 * All four steps are always rendered and readable. Playback only *emphasises*
 * the current one — it never reveals or hides information, so nothing here is
 * conveyed by motion alone and the reduced-motion path needs no special
 * content, only stilled transitions.
 *
 * Motion is CSS off `data-stage`, for the reason recorded at length in
 * `ProductArchitecture.tsx`: Framer `animate` props do not update after mount
 * in these islands. Elements stay `m.*` under `MotionProvider`; locked values
 * only; no new token, no `layoutId`, no `domMax`, no `motion.*`.
 */
import { m } from 'framer-motion'
import { useCallback, useEffect, useId, useRef, useState } from 'react'

import { useMediaQuery } from '../../hooks/useMediaQuery'

export type KhalifahFieldIntelligenceProps = {
  /** Derivatives produced offline from the 4K HEVC master. */
  src1080?: string
  src720?: string
  poster?: string
  /** Existing routes, resolved server-side. */
  toursHref?: string
  howItWorksHref?: string
}

/**
 * Stage boundaries are fractions of duration taken from the supplied file's
 * real cuts (15.04s; cuts at 2.75s, 6.75s, 12.54s), so each beat changes on a
 * shot change rather than mid-shot.
 *   observe     0.000 -> 0.183  trail ride
 *   understand  0.183 -> 0.449  alpine lake
 *   steward     0.449 -> 0.833  underwater recovery
 *   act         0.833 -> 1.000  the team, to camera
 */
const STAGE_BOUNDS = [0.183, 0.449, 0.833] as const

const STEPS = [
  {
    id: 'observe',
    index: '01',
    title: 'Observe',
    copy: 'Landscape, people, biodiversity, infrastructure and local context — seen first-hand, in place.',
    /** The single word that surfaces over the footage at this beat. */
    marker: 'Place',
  },
  {
    id: 'understand',
    index: '02',
    title: 'Understand',
    copy: 'EcoIQ connects what is observed in the field with evidence, systems and opportunities.',
    marker: 'Evidence',
  },
  {
    id: 'steward',
    index: '03',
    title: 'Steward',
    copy: 'Visitors do not simply consume a destination. They understand how to care for it, improve it and take part in it.',
    marker: 'Stewardship',
  },
  {
    id: 'act',
    index: '04',
    title: 'Act',
    copy: 'Field observations can connect to projects, enterprises, conservation and local value creation.',
    marker: 'Action',
  },
] as const

type StageId = (typeof STEPS)[number]['id']

/** The same spine as the hero's Decision Pipeline, stated in field terms. */
const PIPELINE = ['Field', 'Observe', 'Evidence', 'Assess', 'Decide', 'Stewardship']

/**
 * Privacy-safe and vendor-free: this repo has no analytics library, so events
 * go to an optional global a future privacy-preserving collector can define.
 * Event name and a coarse enum only — no identifiers, free text or URLs.
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
  howItWorksHref = '/methodology/',
}: KhalifahFieldIntelligenceProps) {
  const baseId = useId()
  const reduced = useMediaQuery('(prefers-reduced-motion: reduce)')
  const wide = useMediaQuery('(min-width: 768px)')

  const videoRef = useRef<HTMLVideoElement | null>(null)
  /**
   * Visibility is measured on the media frame, never the section: the section
   * is taller than a viewport, so its intersection ratio can never reach the
   * threshold and sources would never attach. Found by measuring.
   */
  const mediaRef = useRef<HTMLDivElement | null>(null)

  const [stage, setStage] = useState<StageId>('observe')
  const [playing, setPlaying] = useState(false)
  const [muted, setMuted] = useState(true)
  /** Sources render only after the frame has been near the viewport once. */
  const [sourcesReady, setSourcesReady] = useState(false)
  const userPaused = useRef(false)
  const startedOnce = useRef(false)

  useEffect(() => {
    const node = mediaRef.current
    if (!node || typeof IntersectionObserver === 'undefined') return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setSourcesReady(true)
          if (!reduced && !userPaused.current) {
            videoRef.current?.play().catch(() => {
              /* Autoplay refusal is fine — poster and controls remain. */
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
    setStage(STEPS[index].id)
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

  const activeMarker = STEPS.find((step) => step.id === stage)?.marker ?? STEPS[0].marker

  return (
    <section className="eiq-mo-root eiq-kfi" aria-labelledby={`${baseId}-title`} data-stage={stage}>
      <div className="eiq-kfi-inner">
        <header className="eiq-kfi-head">
          <p className="eiq-kfi-label">Khalifah Field Intelligence</p>
          <h2 id={`${baseId}-title`} className="eiq-kfi-h2">
            Don&rsquo;t just visit a place. Understand it.
          </h2>
          <p className="eiq-kfi-lede">
            EcoIQ Eco Tours connect people with the ecological, cultural and economic
            intelligence of a place — turning a journey into an understanding of how that
            place works, what it needs and what could be built next.
          </p>
        </header>

        <div className="eiq-kfi-grid">
          {/* ---- the footage: dominant, cinematic, one marker at a time ---- */}
          <figure className="eiq-kfi-media" ref={mediaRef}>
            {/*
              The frame reserves its aspect ratio before any media arrives, so
              neither the poster nor the video can shift layout.
            */}
            <video
              ref={videoRef}
              className="eiq-kfi-video"
              poster={poster}
              muted={muted}
              playsInline
              preload="none"
              onTimeUpdate={onTimeUpdate}
              onPlay={() => {
                setPlaying(true)
                if (!startedOnce.current) {
                  startedOnce.current = true
                  emit('khalifah_field_video_started')
                }
              }}
              onPause={() => setPlaying(false)}
              onEnded={() => {
                setPlaying(false)
                setStage('act')
                emit('khalifah_field_video_completed')
              }}
              aria-label="Illustrative Khalifah field experience: a highland trail ride, an alpine lake, underwater waste recovery, and the field team."
            >
              {sourcesReady && <source src={wide ? src1080 : src720} type="video/mp4" />}
            </video>

            {/*
              One word, low-left, clear of the burned-in end card centred in the
              final shot. Decorative: the same words are permanent text in the
              step list, so nothing is said only here.
            */}
            <p className="eiq-kfi-marker" aria-hidden="true">
              <span className="eiq-kfi-marker-dot" />
              {activeMarker}
            </p>

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
                onClick={() => setMuted((current) => !current)}
              >
                {muted ? 'Unmute' : 'Mute'}
                <span className="eiq-kfi-sr"> footage audio</span>
              </button>
              <ol className="eiq-kfi-progress" aria-hidden="true">
                {STEPS.map((step) => (
                  <li key={step.id} data-step={step.id} />
                ))}
              </ol>
            </div>

            <figcaption className="eiq-kfi-sr">
              Illustrative footage. EcoIQ has not surveyed the location shown. The four
              steps beside this video describe how an EcoIQ field experience is designed
              to work, not findings about this place.
            </figcaption>
          </figure>

          {/* ---- the narrative: always readable, playback only emphasises ---- */}
          <div className="eiq-kfi-narrative">
            <p className="eiq-kfi-concept">
              See the system. Understand the place. Steward what comes next.
            </p>
            <ol className="eiq-kfi-steps" role="list">
              {STEPS.map((step) => (
                <li key={step.id} data-step={step.id}>
                  <span className="eiq-kfi-step-n">{step.index}</span>
                  <div>
                    <h3 className="eiq-kfi-step-t">{step.title}</h3>
                    <p className="eiq-kfi-step-c">{step.copy}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </div>

        {/* ---- same spine as the hero, stated in field terms ---- */}
        <ol className="eiq-kfi-pipeline" role="list" aria-label="How field observation becomes stewardship">
          {PIPELINE.map((node, i) => (
            <li key={node} style={{ '--i': i } as React.CSSProperties}>
              {node}
            </li>
          ))}
        </ol>

        <div className="eiq-kfi-foot">
          <div className="eiq-kfi-cta-row">
            <m.a
              className="eiq-kfi-cta eiq-kfi-cta--primary"
              href={toursHref}
              onClick={() => emit('khalifah_ecotours_clicked')}
            >
              Explore Eco Tours
            </m.a>
            <a className="eiq-kfi-cta" href={howItWorksHref}>
              See how EcoIQ works
            </a>
          </div>
          {/*
            The operational truth, stated where the CTA is — not buried. The
            tour business is not confirmed operational, so this describes a
            model in development.
          */}
          <p className="eiq-kfi-status">
            The EcoIQ field model is in development. Explore the approach and register
            interest — no dates are on sale.
          </p>
        </div>
      </div>
    </section>
  )
}
