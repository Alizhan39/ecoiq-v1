import { useEffect, useRef } from 'react';
import { useScrollProgress } from '@/hooks/useScrollProgress';
import {
  buildParticlePool, paintPipeline, PARTICLE_BUDGET, REDUCED_BUDGET,
  type Particle,
} from './pipelinePainter';

/**
 * The canvas behind "How it works".
 *
 * NO ANIMATION LOOP
 * -----------------
 * There is no requestAnimationFrame loop and no timer. It repaints when scroll
 * progress changes and when the element resizes, which means it does nothing
 * at all while the section is off screen — the scroll listener is not even
 * attached until an IntersectionObserver says it is visible.
 *
 * REDUCED MOTION IS A STATIC FRAME, NOT A BLANK ONE
 * -------------------------------------------------
 * With `prefers-reduced-motion: reduce` the canvas paints one complete frame
 * at full progress and never repaints. The reader still sees the shape of the
 * pipeline; nothing moves. Removing it entirely would take information away
 * from exactly the readers least able to spare it.
 *
 * DECORATION, AND HONESTLY LABELLED AS SUCH
 * -----------------------------------------
 * aria-hidden. Every stage drawn here is a real <li> in HowItWorks. A screen
 * reader, a crawler, and anyone with JavaScript off get the list, which is the
 * primary. This adds no information and is safe to miss.
 */

const MAX_DPR = 2;

function readColors(element: HTMLElement) {
  const style = getComputedStyle(element);
  const token = (name: string, fallback: string) =>
    style.getPropertyValue(name).trim() || fallback;
  return {
    line: token('--line', 'rgba(15,26,20,.1)'),
    node: token('--line-firm', 'rgba(15,26,20,.18)'),
    nodeReached: token('--accent', '#00a86b'),
    particle: token('--accent', '#00a86b'),
    particleStopped: token('--unknown', '#94a3b8'),
  };
}

export function PipelineCanvas({ stages }: { stages: number }) {
  const { ref, progress } = useScrollProgress<HTMLDivElement>();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const poolRef = useRef<Particle[] | null>(null);
  const reducedRef = useRef(false);

  useEffect(() => {
    reducedRef.current = typeof window.matchMedia === 'function'
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    poolRef.current = buildParticlePool(
      20260827, reducedRef.current ? REDUCED_BUDGET : PARTICLE_BUDGET);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = ref.current;
    if (!canvas || !container) return undefined;
    const ctx = canvas.getContext('2d');
    if (!ctx) return undefined;

    const paint = () => {
      const rect = container.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR);
      const w = Math.max(1, Math.round(rect.width));
      const h = Math.max(1, Math.round(rect.height));
      if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
        canvas.width = w * dpr;
        canvas.height = h * dpr;
        canvas.style.width = `${w}px`;
        canvas.style.height = `${h}px`;
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      paintPipeline(
        ctx,
        // One complete, still frame when motion is not wanted.
        reducedRef.current ? 1 : progress,
        poolRef.current ?? [],
        { w, h, stages },
        readColors(container),
      );
    };

    paint();
    // Same rule as the scroll hook: without ResizeObserver the canvas simply
    // does not repaint on resize. It does not throw, and the list behind it is
    // unaffected either way.
    if (typeof ResizeObserver !== 'function') return undefined;
    const observer = new ResizeObserver(paint);
    observer.observe(container);
    return () => observer.disconnect();
  }, [progress, stages, ref]);

  return (
    <div className="pipeline-canvas" ref={ref} aria-hidden="true">
      <canvas ref={canvasRef} />
    </div>
  );
}
