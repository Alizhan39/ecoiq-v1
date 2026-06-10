/**
 * LazyMotion provider — loads only the DOM animation features Framer Motion
 * needs, shrinking the bundle vs. importing the full `motion` component. Use the
 * lightweight `m.*` components (not `motion.*`) inside this provider.
 */
import { LazyMotion, domAnimation, MotionConfig } from 'framer-motion'
import type { ReactNode } from 'react'
import { ease, duration } from '../design/tokens'

export default function MotionProvider({ children }: { children: ReactNode }) {
  return (
    <LazyMotion features={domAnimation} strict>
      {/* `reducedMotion="user"` makes every animation honor the OS setting. */}
      <MotionConfig reducedMotion="user" transition={{ duration: duration.base, ease: ease.out }}>
        {children}
      </MotionConfig>
    </LazyMotion>
  )
}
