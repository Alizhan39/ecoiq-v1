/**
 * EcoIQ Visual Intelligence — design tokens.
 *
 * The single source of truth for the dark institutional design system. These
 * mirror the CSS custom properties in design/system.css so components can read
 * values in JS (e.g. for SVG fills, Framer Motion colors) without hard-coding.
 *
 * Aesthetic target: a premium AI visual-intelligence platform — deep,
 * near-black greens; restrained luminous accents; depth through layering and
 * soft glows; tabular numerics. Not a generic SaaS dashboard.
 */

export const color = {
  // Background scale — deepest to surface.
  bg900: '#03100c',
  bg800: '#06140f',
  bg700: '#0a1c16',
  surface: '#0c211a',
  surfaceRaised: '#0f2a21',

  // Accents.
  accent: '#00e89a',
  accentDim: '#0bbf82',
  accentGlow: 'rgba(0, 232, 154, 0.18)',
  gold: '#e8c46a',
  goldGlow: 'rgba(232, 196, 106, 0.55)',

  // Signal colors for data viz.
  warn: '#f2a65a',
  danger: '#ef6f6f',
  info: '#5ab0f2',

  // Text.
  ink: '#e7f3ee',
  inkStrong: '#ffffff',
  muted: '#8fa9a0',
  faint: '#5f746c',

  // Lines.
  border: 'rgba(255, 255, 255, 0.06)',
  borderAccent: 'rgba(0, 232, 154, 0.16)',
} as const

export const radius = {
  sm: '10px',
  md: '14px',
  lg: '18px',
  xl: '24px',
  pill: '999px',
} as const

export const space = {
  xs: '6px',
  sm: '10px',
  md: '16px',
  lg: '24px',
  xl: '32px',
  xxl: '48px',
} as const

export const font = {
  sans: 'inherit',
  mono: '"SF Mono", "JetBrains Mono", ui-monospace, "Roboto Mono", Menlo, monospace',
} as const

/** Premium easing curves (cubic-bezier). */
export const ease = {
  /** easeOutExpo-ish — confident, decelerating entrances. */
  out: [0.22, 1, 0.36, 1] as [number, number, number, number],
  /** Smooth in-out for hovers / loops. */
  inOut: [0.65, 0, 0.35, 1] as [number, number, number, number],
} as const

export const duration = {
  fast: 0.18,
  base: 0.42,
  slow: 0.7,
} as const

/** Reusable layered shadow + glow recipes. */
export const elevation = {
  panel: '0 24px 60px -30px rgba(0, 0, 0, 0.8)',
  raised: '0 18px 48px -24px rgba(0, 0, 0, 0.7)',
  accentGlow: `0 10px 40px -8px ${color.accentGlow}`,
} as const
