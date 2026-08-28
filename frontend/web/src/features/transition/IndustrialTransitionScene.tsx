import { useEffect, useMemo, useRef, useState } from 'react';
import { useScrollProgress } from '@/hooks/useScrollProgress';
import {
  buildPulsePool, edgePath, FLOW_STYLE, MOBILE_PULSE_BUDGET, paintFlows,
  PULSE_BUDGET, REDUCED_PULSE_BUDGET, type Pulse,
} from './flowPainter';
import { currentStage, sceneAt, recoveredFraction } from './topology';

/**
 * A schematic of industrial modernisation, driven by scroll position.
 *
 * WHAT IT IS NOT
 * --------------
 * Not telemetry, not a live feed, not anything EcoIQ operates. No element is
 * labelled as a sensor, an agent, or under EcoIQ's control, because
 * `platform_registry/agents.py` says plainly there are no PRODUCTION AI agents
 * and no sensor ingestion. The stashed cinematic hero was rejected for drawing
 * exactly those things; a claim made in pictures is still a claim.
 *
 * It illustrates what an industrial transition looks like in general. That is
 * a statement about engineering, not about this product's reach.
 *
 * NO ANIMATION LOOP, NO TIMER
 * ---------------------------
 * Same contract as PipelineCanvas. Everything derives from `progress`, so the
 * component repaints when scroll changes and does nothing while off screen —
 * `useScrollProgress` does not even attach its listener until an
 * IntersectionObserver says the section is visible.
 *
 * That answers the rAF-after-unmount and hidden-tab concerns structurally
 * rather than by handling them: there is no loop to leak and nothing to pause.
 * A hidden tab does not scroll, so no work happens; when it is shown again the
 * next scroll event repaints from the true position, because position is the
 * only input.
 *
 * STRUCTURE IN SVG, MOTION IN CANVAS
 * ----------------------------------
 * Equipment, pipes and labels are real SVG elements: few, textual, worth
 * inspecting. Pulses are many and move, so they are painted on one canvas.
 * Hundreds of animated DOM nodes is what this split avoids.
 *
 * BACKGROUND, WITH TEXT ON TOP
 * ----------------------------
 * aria-hidden and non-interactive. Everything it conveys is also written in
 * the stage list beside it, so a reader with JavaScript off, a screen reader,
 * or a crawler loses nothing.
 */

const MAX_DPR = 2;
const MOBILE_WIDTH = 720;

const NODE_GLYPH: Record<string, string> = {
  grid: 'M -7 -7 L 7 -7 M -7 0 L 7 0 M -7 7 L 7 7 M 0 -7 L 0 7',
  process: 'M -9 -7 L 9 -7 L 9 7 L -9 7 Z',
  thermal: 'M -8 6 Q -4 -8 0 0 Q 4 8 8 -6',
  motor: 'M -7 -7 L 7 -7 L 7 7 L -7 7 Z M -7 0 L 7 0',
  water: 'M 0 -8 Q 7 0 0 8 Q -7 0 0 -8 Z',
  store: 'M -8 -5 L 8 -5 L 8 5 L -8 5 Z M -8 0 L 8 0',
  recovery: 'M -7 3 A 7 7 0 1 1 4 6 M 4 6 L 7 1 M 4 6 L 0 8',
  measure: 'M -8 6 L -3 -2 L 2 3 L 8 -6',
};

function readColors(el: HTMLElement) {
  const style = getComputedStyle(el);
  const token = (name: string, fallback: string) =>
    style.getPropertyValue(name).trim() || fallback;
  return {
    electricity: token('--accent', '#00a86b'),
    heat: token('--warn-strong', '#8a4008'),
    water: token('--unknown', '#6b7f8e'),
    material: token('--ink-soft', '#5c7063'),
    waste: token('--danger', '#c02734'),
    evidence: token('--ink', '#0f1a14'),
  };
}

export function IndustrialTransitionScene() {
  const { ref, progress } = useScrollProgress<HTMLDivElement>();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const poolRef = useRef<Pulse[] | null>(null);
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const wantsReduced = typeof window.matchMedia === 'function'
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    setReduced(wantsReduced);
    const narrow = typeof window.innerWidth === 'number'
      && window.innerWidth < MOBILE_WIDTH;
    // Fewer pulses on a narrow screen: the topology still reads, the work does
    // not. Reduced motion gets none — the SVG carries the whole illustration.
    const budget = wantsReduced ? REDUCED_PULSE_BUDGET
      : narrow ? MOBILE_PULSE_BUDGET : PULSE_BUDGET;
    poolRef.current = buildPulsePool(20260828, budget);
  }, []);

  /**
   * With reduced motion the scene is pinned to a complete, finished frame
   * rather than blanked. The reader still sees the modernised system; nothing
   * moves. Removing it entirely would take the illustration away from exactly
   * the readers least able to spare it.
   */
  const shown = reduced ? 1 : progress;
  const scene = useMemo(() => sceneAt(shown), [shown]);
  const stage = currentStage(shown);

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
      paintFlows(ctx, shown, poolRef.current ?? [], { w, h }, readColors(container));
    };

    paint();
    // Without ResizeObserver the canvas simply does not repaint on resize. It
    // does not throw, and the SVG beneath it is unaffected.
    if (typeof ResizeObserver !== 'function') return undefined;
    const observer = new ResizeObserver(paint);
    observer.observe(container);
    return () => observer.disconnect();
  }, [shown, ref]);

  return (
    <div className="itscene" ref={ref} aria-hidden="true">
      <svg
        className="itscene__svg"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        focusable="false"
      >
        {scene.edges.map(({ edge, opacity }) => {
          const path = edgePath(edge);
          if (!path) return null;
          const style = FLOW_STYLE[edge.kind];
          const mx = (path.a.x + path.b.x) / 2 - (path.b.y - path.a.y) * path.bow;
          const my = (path.a.y + path.b.y) / 2 + (path.b.x - path.a.x) * path.bow;
          return (
            <path
              key={edge.id}
              className={`itscene__edge itscene__edge--${edge.kind}`}
              d={`M ${path.a.x * 100} ${path.a.y * 100} Q ${mx * 100} ${my * 100} ${path.b.x * 100} ${path.b.y * 100}`}
              strokeDasharray={style.dash.join(' ') || undefined}
              strokeWidth={style.width / 4}
              opacity={opacity * (edge.loss ? 0.5 : 0.75)}
              vectorEffect="non-scaling-stroke"
              fill="none"
            />
          );
        })}
      </svg>

      {/* Equipment sits in its own SVG so it is never distorted by the
          non-uniform viewBox the topology needs. */}
      <svg className="itscene__nodes" focusable="false">
        {scene.nodes.map(({ node, opacity }) => (
          <g
            key={node.id}
            className={`itscene__node itscene__node--${node.kind}`}
            transform={`translate(${node.x * 100}% , ${node.y * 100}%)`}
            opacity={opacity}
          >
            <path d={NODE_GLYPH[node.kind] ?? NODE_GLYPH.process} />
          </g>
        ))}
      </svg>

      <canvas className="itscene__canvas" ref={canvasRef} />

      {/* Read by the caller, not shown: the stage list beside the scene is the
          text primary, and duplicating it here would repeat it to a screen
          reader that has already been told. */}
      <span
        className="visually-hidden"
        data-stage={stage.key}
        data-recovered={recoveredFraction(shown).toFixed(2)}
      />
    </div>
  );
}
