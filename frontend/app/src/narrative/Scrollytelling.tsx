/**
 * Scrollytelling — the reusable Visual Narrative engine.
 *
 * Layout: a sticky VISUAL panel paired with a column of stepped TEXT. As the
 * reader scrolls, the active scene updates and the visual morphs to explain the
 * text being read. This is the standard EcoIQ section shape:
 *   - Information layer  → the scene text
 *   - Visual layer       → renderVisual(active) — auto-animates per scene
 *   - Interaction layer  → scroll + clickable scene dots
 *
 * The engine is content-agnostic: pass scenes + a visual renderer. Specific
 * narratives (e.g. HeatingTransitionStory) supply the SVG vocabulary.
 */
import type { ReactNode } from 'react'
import { m } from 'framer-motion'
import { useActiveScene } from './useActiveScene'

export interface Scene {
  kicker?: string
  title: string
  body: string
}

export interface ScrollytellingProps {
  eyebrow?: string
  heading?: string
  scenes: Scene[]
  /** Render the visual for the active scene index (sticky panel). */
  renderVisual: (active: number) => ReactNode
  /** Optional aspect for the sticky visual, default 4/5 portrait-ish. */
}

export default function Scrollytelling({ eyebrow, heading, scenes, renderVisual }: ScrollytellingProps) {
  const { containerRef, active, setActive } = useActiveScene(scenes.length)

  return (
    <div className="eiq-scrolly">
      {(eyebrow || heading) && (
        <div className="eiq-scrolly__head">
          {eyebrow ? <div className="eiq-eyebrow">{eyebrow}</div> : null}
          {heading ? <h2 className="eiq-scrolly__heading">{heading}</h2> : null}
        </div>
      )}

      <div className="eiq-scrolly__body" ref={containerRef}>
        {/* Sticky visual */}
        <div className="eiq-scrolly__visual-col">
          <div className="eiq-scrolly__visual">
            {renderVisual(active)}
            <div className="eiq-scrolly__dots" role="tablist" aria-label="Scenes">
              {scenes.map((s, i) => (
                <button
                  key={i}
                  className={`eiq-scrolly__dot${i === active ? ' is-active' : ''}`}
                  aria-label={s.title}
                  aria-selected={i === active}
                  role="tab"
                  onClick={() => {
                    setActive(i)
                    const el = containerRef.current?.querySelector<HTMLElement>(`[data-scene="${i}"]`)
                    el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
                  }}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Stepped text */}
        <div className="eiq-scrolly__steps">
          {scenes.map((s, i) => (
            <m.div
              key={i}
              data-scene={i}
              className={`eiq-scrolly__step${i === active ? ' is-active' : ''}`}
              initial={false}
              animate={{ opacity: i === active ? 1 : 0.32 }}
              transition={{ duration: 0.4 }}
            >
              {s.kicker ? <div className="eiq-scrolly__kicker">{s.kicker}</div> : null}
              <h3 className="eiq-scrolly__title">{s.title}</h3>
              <p className="eiq-scrolly__text">{s.body}</p>
            </m.div>
          ))}
        </div>
      </div>
    </div>
  )
}
