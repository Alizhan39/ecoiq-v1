/**
 * HeroCanvas — the hero's single <canvas> element.
 *
 * Deliberately has no independent animation loop. It subscribes to
 * `scrollYProgress` the same way every other overlay in this tree does
 * (`useMotionValueEvent(..., 'change', ...)`) and calls `paintHero`
 * synchronously from that callback — Framer Motion already batches these via
 * its own internal scheduler, so there's no risk of over-repainting, and
 * "pause when off-screen" comes for free from `useScroll`'s own clamping
 * (it stops emitting once the wrapper scrolls out of range, exactly like
 * every other scroll-linked overlay already relies on).
 *
 * The only other thing that triggers a repaint is a ResizeObserver — one
 * synchronous repaint on resize, not a new timer — so "resize doesn't break
 * the animation" without adding any persistent loop.
 */
import { useEffect, useRef } from 'react'
import { useMotionValueEvent, type MotionValue } from 'framer-motion'
import { useMediaQuery } from '../../hooks/useMediaQuery'
import { buildParticlePool, paintHero, type Particle } from './canvasEngine'

const MAX_DPR = 2

export default function HeroCanvas({ scrollYProgress }: { scrollYProgress: MotionValue<number> }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const poolRef = useRef<Particle[] | null>(null)
  const dimsRef = useRef({ w: 0, h: 0, dpr: 1 })
  const isTablet = useMediaQuery('(max-width: 1024px)')

  // (Re)build the particle pool whenever the density tier changes (desktop <-> tablet).
  useEffect(() => {
    poolRef.current = buildParticlePool(20260713, isTablet ? 'reduced' : 'full')
  }, [isTablet])

  useEffect(() => {
    const canvas = canvasRef.current
    const container = canvas?.parentElement
    if (!canvas || !container) return

    const context = canvas.getContext('2d')
    if (!context) return
    const ctx: CanvasRenderingContext2D = context

    function resize() {
      if (!canvas || !container) return
      const rect = container.getBoundingClientRect()
      const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR)
      canvas.width = Math.round(rect.width * dpr)
      canvas.height = Math.round(rect.height * dpr)
      canvas.style.width = `${rect.width}px`
      canvas.style.height = `${rect.height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      dimsRef.current = { w: rect.width, h: rect.height, dpr }
      // One synchronous repaint with the current scroll value — resizing
      // must not leave a stale frame, and must not start a new timer either.
      if (poolRef.current) {
        paintHero(ctx, scrollYProgress.get(), dimsRef.current, poolRef.current)
      }
    }

    resize()
    const observer = new ResizeObserver(resize)
    observer.observe(container)
    return () => observer.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useMotionValueEvent(scrollYProgress, 'change', (v) => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!ctx || !poolRef.current) return
    paintHero(ctx, v, dimsRef.current, poolRef.current)
  })

  return <canvas ref={canvasRef} className="eiq-cine__hero-canvas" aria-hidden="true" />
}
