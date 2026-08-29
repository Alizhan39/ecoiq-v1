import { useEffect, useMemo, useRef, useState } from 'react';
import {
  buildPulsePool, edgePath, FLOW_STYLE, MOBILE_PULSE_BUDGET, paintFlows,
  PULSE_BUDGET, REDUCED_PULSE_BUDGET, type Pulse,
} from './flowPainter';
import { glyphFor } from './equipmentGlyphs';
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
/** Glyphs are drawn in a 40x40 box; this makes them legible in the container. */
const GLYPH_SCALE = 1.9;
/**
 * Opacity at which a node's label appears.
 *
 * Above one half, so at a replacement exactly one of the two labels is ever
 * shown: the outgoing one drops below the threshold as the incoming one
 * crosses it.
 */
const LABEL_THRESHOLD = 0.55;


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
    fuel: token('--danger-strong', '#7a1420'),
  };
}

export interface IndustrialTransitionSceneProps {
  /**
   * Scroll progress, 0 to 1, from whoever owns the scroll container.
   *
   * NOT read here. This component's own element is inside a position:sticky
   * panel, so it does not move relative to the viewport as the page scrolls —
   * an internal useScrollProgress therefore froze, and the drawing showed
   * modernised equipment at the legacy stage because its progress never
   * advanced past whatever it measured on mount.
   *
   * One scroll source of truth, owned by the page, passed down. That is also
   * what keeps the drawing, the state panel and the narrative on the same
   * frame — they are all given the same number rather than each measuring.
   */
  progress: number;
}

export function IndustrialTransitionScene({ progress }: IndustrialTransitionSceneProps) {
  const ref = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const poolRef = useRef<Pulse[] | null>(null);
  const [reduced, setReduced] = useState(false);
  /**
   * Container size in CSS pixels.
   *
   * Needed because SVG's `transform` attribute does NOT accept percentages —
   * `translate(8%, 30%)` is invalid and browsers drop it, which stacked every
   * piece of equipment on the origin. It went unnoticed while this was a faint
   * background; it is fatal now the schematic is the point. Positions are
   * therefore computed against a measured box.
   */
  const [size, setSize] = useState({ w: 0, h: 0 });

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
      setSize((prev) => (prev.w === w && prev.h === h ? prev : { w, h }));
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
              className={[
                'itscene__edge',
                `itscene__edge--${edge.kind}`,
                edge.loss ? 'is-loss' : '',
                // A returning flow is drawn as a loop and named as one, so a
                // reader can tell "this goes back" from "this goes on".
                edge.bow ? 'is-loop' : '',
              ].filter(Boolean).join(' ')}
              d={`M ${path.a.x * 100} ${path.a.y * 100} Q ${mx * 100} ${my * 100} ${path.b.x * 100} ${path.b.y * 100}`}
              strokeDasharray={style.dash.join(' ') || undefined}
              // Real screen pixels. This was width/4 when the scene was a
              // faint background behind text; with vectorEffect the result was
              // a 0.4px line, which is invisible. The schematic is the primary
              // visual now, so the pipes are drawn at the width the flow style
              // actually specifies.
              strokeWidth={style.width}
              opacity={opacity * (edge.loss ? 0.75 : 1)}
              vectorEffect="non-scaling-stroke"
              fill="none"
            />
          );
        })}
      </svg>

      {/* Equipment sits in its own SVG so it is never distorted by the
          non-uniform viewBox the topology needs. */}
      <svg className="itscene__nodes" focusable="false">
        {size.w > 0 ? scene.nodes.map(({ node, opacity }) => {
          const glyph = glyphFor(node.equipment);
          return (
            <g
              key={node.id}
              className={`itscene__node itscene__node--${node.kind}`}
              transform={`translate(${(node.x * size.w).toFixed(1)}, ${(node.y * size.h).toFixed(1)})`}
              opacity={opacity}
            >
              {/* Glyphs are authored in a 40x40 box; this SVG has no viewBox
                  because the node positions are percentages of the container.
                  So the symbol is scaled here rather than being redrawn at
                  whatever size the container happens to be. */}
              <g transform={`scale(${GLYPH_SCALE})`}>
                <path className="itscene__glyph" d={glyph.d} />
                {glyph.detail
                  ? <path className="itscene__glyph-detail" d={glyph.detail} />
                  : null}
              </g>
              {/* The label is part of the schematic, not a tooltip. A P&ID
                  without tags is a picture of pipes. */}
              {/*
                Anchor follows position. A label centred on a node near either
                edge is clipped by the container — "Grid connection" lost its
                first characters at 390px. Anchoring to the start on the left
                and to the end on the right keeps the text inside the frame
                whatever the container width, rather than nudging one node
                until it happens to fit one viewport.

                Shown only while this node is the dominant one. A replacement
                puts the old equipment and the new in the SAME position, which
                is the point — the glyphs crossfade so a retrofit reads as one
                thing becoming another. Two labels doing the same thing is not
                a crossfade, it is unreadable: "Fixed-speed motor" and
                "Variable-speed drive" overprinted each other for the whole
                transition. The glyphs still blend; the text hands over.
              */}
              {opacity >= LABEL_THRESHOLD ? (
                <text
                  className="itscene__label"
                  x={node.x < 0.2 ? -14 : node.x > 0.8 ? 14 : 0}
                  y={16 * GLYPH_SCALE + 12}
                  textAnchor={node.x < 0.2 ? 'start' : node.x > 0.8 ? 'end' : 'middle'}
                >
                  {node.label}
                </text>
              ) : null}
            </g>
          );
        }) : null}
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
