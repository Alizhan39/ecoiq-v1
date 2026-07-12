/**
 * EcoIQ Visual Intelligence — motion presets.
 *
 * Shared Framer Motion variants and transitions so every component animates
 * with the same premium, restrained character. Curves come from the design
 * tokens. Keep motion purposeful: entrances, focus, and data reveals — never
 * gratuitous.
 */
import type { Variants, Transition } from 'framer-motion'
import { ease, duration } from '../design/tokens'

export const tBase: Transition = { duration: duration.base, ease: ease.out }
export const tFast: Transition = { duration: duration.fast, ease: ease.out }
export const tSlow: Transition = { duration: duration.slow, ease: ease.out }

/** Fade + rise — the default entrance for panels and cards. */
export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: tBase },
}

/** Subtle scale-in for visuals / globes. */
export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.94 },
  show: { opacity: 1, scale: 1, transition: tSlow },
}

/** Parent that staggers its children's entrances. */
export const stagger = (gap = 0.08, delay = 0): Variants => ({
  hidden: {},
  show: {
    transition: { staggerChildren: gap, delayChildren: delay },
  },
})

/** Child item for use inside a `stagger` parent. */
export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: tBase },
}

/** SVG stroke draw-in (pathLength 0→1) for chart lines, links, and map borders. */
export const drawPath = (transition: Transition = tSlow): Variants => ({
  hidden: { pathLength: 0, opacity: 0 },
  show: { pathLength: 1, opacity: 1, transition },
})

/** Scale + fade pop-in for map/network nodes and pins, staggered by index via `transition.delay`. */
export const popIn = (transition: Transition = tFast, fromScale = 0): Variants => ({
  hidden: { scale: fromScale, opacity: 0 },
  show: { scale: 1, opacity: 1, transition },
})

/** Premium hover lift for interactive cards. */
export const hoverLift = {
  rest: { y: 0, boxShadow: '0 24px 60px -30px rgba(0,0,0,0.8)' },
  hover: {
    y: -4,
    boxShadow: '0 28px 70px -28px rgba(0,232,154,0.22)',
    transition: tFast,
  },
}
