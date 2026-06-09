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

/** Premium hover lift for interactive cards. */
export const hoverLift = {
  rest: { y: 0, boxShadow: '0 24px 60px -30px rgba(0,0,0,0.8)' },
  hover: {
    y: -4,
    boxShadow: '0 28px 70px -28px rgba(0,232,154,0.22)',
    transition: tFast,
  },
}
