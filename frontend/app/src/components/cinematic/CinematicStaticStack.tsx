/**
 * CinematicStaticStack — reduced-motion AND mobile fallback.
 *
 * No sticky stage, no scroll math, no parallax/zoom/path-drawing/particles.
 * Scenes render as ordinary stacked sections, each a plain Reveal fade-in.
 * Shares `content.ts` with the scroll-driven stage so copy never drifts.
 */
import { Reveal, fadeUp } from '../../motion'
import { intro, evidence, agents } from './content'

const HERO_IMAGE = '/static/img/hero/ecoiq-better-way-hero.png'

export default function CinematicStaticStack() {
  return (
    <div className="eiq-cine-static">
      <Reveal as="section" variants={fadeUp} className="eiq-cine-static__hero">
        <img
          src={HERO_IMAGE}
          alt=""
          aria-hidden="true"
          className="eiq-cine-static__hero-img"
          width={1536}
          height={1024}
          loading="eager"
        />
        <div className="eiq-cine-static__hero-scrim" aria-hidden="true" />
        <div className="eiq-cine-static__hero-body">
          <div className="eiq-eyebrow eiq-cine__eyebrow">{intro.eyebrow}</div>
          <h1 className="eiq-cine__heading">{intro.heading}</h1>
          <p className="eiq-cine__lede">{intro.body}</p>
          <div className="eiq-cine__cta-row">
            <a className="eiq-btn eiq-btn--primary" href={intro.primaryCta.href}>
              {intro.primaryCta.label}
            </a>
            <a className="eiq-btn eiq-btn--secondary" href={intro.secondaryCta.href}>
              {intro.secondaryCta.label}
            </a>
          </div>
        </div>
      </Reveal>

      <Reveal as="section" className="eiq-cine-static__card">
        <p className="eiq-cine__scene-copy">{evidence.copy}</p>
        <ul className="eiq-cine-static__tag-list">
          {evidence.sources.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      </Reveal>

      <Reveal as="section" className="eiq-cine-static__card">
        <p className="eiq-cine__scene-copy">{agents.copy}</p>
        <ul className="eiq-cine-static__tag-list">
          {agents.roster.map((a) => (
            <li key={a}>{a}</li>
          ))}
        </ul>
      </Reveal>
    </div>
  )
}
