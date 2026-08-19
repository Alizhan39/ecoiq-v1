/**
 * CinematicStaticStack — reduced-motion AND mobile fallback.
 *
 * No sticky stage, no scroll math, no parallax/zoom/path-drawing/particles.
 * Scenes render as ordinary stacked sections, each a plain Reveal fade-in.
 * Shares `content.ts` with the scroll-driven stage so copy never drifts.
 */
import { Reveal, fadeUp } from '../../motion'
import { intro, evidence, agents, stewardship } from './content'
import {
  HERO_AVIF_SRCSET, HERO_FALLBACK, HERO_HEIGHT, HERO_SIZES, HERO_WEBP_SRCSET, HERO_WIDTH,
} from './heroImage'

export default function CinematicStaticStack() {
  return (
    <div className="eiq-cine-static">
      <Reveal as="section" variants={fadeUp} className="eiq-cine-static__hero">
        {/*
          This stack is the mobile fallback as well as the reduced-motion one,
          so it is the path most phones actually take — the srcset below is what
          stops a 390pt handset pulling the 1536px desktop asset.
        */}
        <picture>
          <source type="image/avif" srcSet={HERO_AVIF_SRCSET} sizes={HERO_SIZES} />
          <source type="image/webp" srcSet={HERO_WEBP_SRCSET} sizes={HERO_SIZES} />
          <img
            src={HERO_FALLBACK}
            alt=""
            aria-hidden="true"
            className="eiq-cine-static__hero-img"
            width={HERO_WIDTH}
            height={HERO_HEIGHT}
            loading="eager"
          />
        </picture>
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

      <Reveal as="section" className="eiq-cine-static__card">
        <ul className="eiq-cine-static__tag-list">
          <li>
            {stewardship.left.label}: {stewardship.left.prefix}
            {stewardship.left.value}
            {stewardship.left.suffix}
          </li>
          <li>
            {stewardship.right.label}: {stewardship.right.prefix}
            {stewardship.right.value}
            {stewardship.right.suffix}
          </li>
        </ul>
      </Reveal>
    </div>
  )
}
