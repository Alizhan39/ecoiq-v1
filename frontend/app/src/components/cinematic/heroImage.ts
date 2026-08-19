/**
 * Responsive source sets for the homepage hero.
 *
 * The master is a 1536x1024 photographic image that shipped as a 2,592,714-byte
 * lossless PNG in RGB mode — no alpha, so PNG bought nothing. Variants are
 * pre-generated and committed by `python manage.py build_hero_images`; nothing
 * is encoded at request time.
 *
 * Widths are chosen for real devices, not round numbers: 768 covers 1x tablets,
 * 1152 covers a 390pt phone at DPR 3 (1170 CSS px) so those devices stop pulling
 * the desktop asset, and 1536 is the master width for desktop and DPR-2 laptops.
 *
 * Kept in one module because both CinematicBackground (the scroll cinematic) and
 * CinematicStaticStack (the reduced-motion fallback) render the same hero, and
 * the preload hint in templates/landing.html has to stay in step with both.
 */
const BASE = '/static/img/hero/ecoiq-better-way-hero'

export const HERO_AVIF_SRCSET =
  `${BASE}-768.avif 768w, ${BASE}-1152.avif 1152w, ${BASE}-1536.avif 1536w`

export const HERO_WEBP_SRCSET =
  `${BASE}-768.webp 768w, ${BASE}-1152.webp 1152w, ${BASE}-1536.webp 1536w`

/** Universal fallback. Only browsers without WebP ever download this. */
export const HERO_FALLBACK = `${BASE}-1536.jpg`

/** The hero is full-bleed in both layouts, so the slot is always the viewport. */
export const HERO_SIZES = '100vw'

export const HERO_WIDTH = 1536
export const HERO_HEIGHT = 1024
