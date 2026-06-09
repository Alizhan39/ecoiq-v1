/**
 * Reveal — scroll-triggered entrance wrapper. Animates once when ~25% of the
 * element enters the viewport. Built on the lightweight `m.div` (LazyMotion).
 */
import { m } from 'framer-motion'
import type { Variants } from 'framer-motion'
import type { ReactNode } from 'react'
import { fadeUp } from './presets'

interface RevealProps {
  children: ReactNode
  variants?: Variants
  className?: string
  /** Stagger children: pass a stagger() parent variant and Reveal.Item kids. */
  once?: boolean
  as?: 'div' | 'section' | 'li' | 'ul'
}

export default function Reveal({
  children,
  variants = fadeUp,
  className,
  once = true,
  as = 'div',
}: RevealProps) {
  const Comp = m[as]
  return (
    <Comp
      className={className}
      variants={variants}
      initial="hidden"
      whileInView="show"
      viewport={{ once, amount: 0.25 }}
    >
      {children}
    </Comp>
  )
}
