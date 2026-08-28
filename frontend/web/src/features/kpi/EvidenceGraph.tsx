import { useMemo } from 'react';
import type { KpiEvidence, KpiInvestigation } from '@/types/kpi';
import { LEGAL_STATUS_LABEL, RELATION_LABEL } from '@/types/kpi';

/**
 * The causal graph: two branches converging on one principle.
 *
 * THE POINT OF THE PICTURE
 * ------------------------
 * An organisation can protect people from manipulation by others while itself
 * shaping the choice environment. Those are not opposites to be averaged into a
 * middle number — they are two true things, and the graph exists to hold them
 * both in view at once. The left branch is what the organisation restrains in
 * others; the right is what it controls itself. They meet at the principle.
 *
 * WHY HAND-BUILT SVG
 * ------------------
 * `frontend/web` ships react, react-dom and react-router-dom. Nothing else.
 * Adding a graph library for one diagram would put a rendering engine into
 * every page's bundle to draw eleven nodes. This is ~200 lines of SVG with no
 * runtime dependency and no layout shift.
 *
 * ACCESSIBILITY IS NOT THE FALLBACK
 * ---------------------------------
 * The SVG is `aria-hidden`, and the same structure is emitted as a real nested
 * list underneath it. A screen reader gets the relationships as text, not a
 * description of a picture. Relation is carried by label AND shape AND colour —
 * never colour alone. Nodes are buttons, so the graph is keyboard-navigable in
 * document order.
 */

export interface GraphNode {
  id: string;
  kind: 'actor' | 'control' | 'behaviour' | 'finding' | 'outcome' | 'principle';
  label: string;
  sublabel?: string;
  branch: 'protect' | 'control' | 'spine';
  evidence?: KpiEvidence;
}

const COL = { protect: 150, spine: 400, control: 650 };
/** Fixed layout rows. Named rather than indexed so the compiler sees numbers. */
const ROW_ACTOR = 40;
const ROW_BRANCH = 130;
const ROW_CONTEXT = 310;
const ROW_PRINCIPLE = 400;

export function EvidenceGraph({
  inv, onSelect, selectedId,
}: {
  inv: KpiInvestigation;
  onSelect: (e: KpiEvidence | null) => void;
  selectedId: number | null;
}) {
  const { nodes, edges } = useMemo(() => buildGraph(inv), [inv]);

  return (
    <figure className="kpi-graph">
      <figcaption className="kpi-graph__caption">
        How the evidence connects. The left branch is manipulation the organisation
        restrains in others; the right is the choice environment it controls itself.
        Both are assessed against the same principle.
      </figcaption>

      <svg
        className="kpi-graph__svg"
        viewBox="0 0 800 470"
        role="presentation"
        aria-hidden="true"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <marker id="kpi-arrow" viewBox="0 0 10 10" refX="9" refY="5"
                  markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" className="kpi-graph__arrowhead" />
          </marker>
        </defs>

        {edges.map((e) => {
          const a = nodes.find((n) => n.id === e.from);
          const b = nodes.find((n) => n.id === e.to);
          // An edge whose endpoints were not built is dropped, not asserted
          // into existence — a missing node is a data question, not a render one.
          if (!a || !b) return null;
          return (
            <path
              key={`${e.from}-${e.to}`}
              className={`kpi-graph__edge kpi-graph__edge--${e.tone}`}
              d={curve(COL[a.branch], a.y, COL[b.branch], b.y)}
              markerEnd="url(#kpi-arrow)"
              style={{ animationDelay: `${e.step * 140}ms` }}
            />
          );
        })}

        {nodes.map((n, i) => (
          <g
            key={n.id}
            className={[
              'kpi-graph__node',
              `kpi-graph__node--${n.kind}`,
              `kpi-graph__node--${n.branch}`,
              n.evidence && n.evidence.id === selectedId ? 'is-selected' : '',
            ].join(' ')}
            style={{ animationDelay: `${i * 90}ms` }}
            transform={`translate(${COL[n.branch]}, ${n.y})`}
          >
            <rect x={-110} y={-24} width={220} height={48} rx={8} />
            <text className="kpi-graph__node-label" y={n.sublabel ? -4 : 5}>
              {n.label}
            </text>
            {n.sublabel ? (
              <text className="kpi-graph__node-sub" y={13}>{n.sublabel}</text>
            ) : null}
          </g>
        ))}
      </svg>

      {/*
        The same graph, as content. Not a summary of the picture — the picture
        is a rendering of this.
      */}

      {/*
        Visually hidden, because the figcaption above already introduces this
        section on screen and a second visible heading would change a design
        nobody asked to change.

        It exists so the three branch headings below have a parent. Without it
        they sat at H3 directly under the page H1, and a reader navigating by
        heading level — which is how screen-reader users move through a long
        page — got an outline that skipped a level exactly where the evidence
        starts. Measured across the public routes, this was the only page with
        a broken outline.
      */}
      <h2 className="visually-hidden" id="evidence-graph-heading">
        The evidence, as a chain
      </h2>
      <ol className="kpi-graph__semantic" aria-labelledby="evidence-graph-heading">
        {(['protect', 'control', 'spine'] as const).map((branch) => {
          const inBranch = nodes.filter((n) => n.branch === branch);
          if (!inBranch.length) return null;
          return (
            <li key={branch}>
              <h3>{BRANCH_HEADING[branch]}</h3>
              <ol>
                {inBranch.map((n) => (
                  <li key={n.id}>
                    {n.evidence ? (
                      <button
                        type="button"
                        className="kpi-graph__hit"
                        aria-pressed={n.evidence.id === selectedId}
                        onClick={() => onSelect(
                          n.evidence!.id === selectedId ? null : n.evidence!)}
                      >
                        <span className="kpi-graph__hit-label">{n.label}</span>
                        <span className={`kpi-chip kpi-chip--${n.evidence.relation}`}>
                          {RELATION_LABEL[n.evidence.relation]}
                        </span>
                        <span className="kpi-chip kpi-chip--status">
                          {LEGAL_STATUS_LABEL[n.evidence.legal_status]}
                        </span>
                        {!n.evidence.counts_toward_assessment ? (
                          <span className="kpi-chip kpi-chip--excluded">
                            Excluded from assessment
                          </span>
                        ) : null}
                      </button>
                    ) : (
                      <span className="kpi-graph__hit kpi-graph__hit--static">
                        {n.label}{n.sublabel ? ` — ${n.sublabel}` : ''}
                      </span>
                    )}
                  </li>
                ))}
              </ol>
            </li>
          );
        })}
      </ol>
    </figure>
  );
}

const BRANCH_HEADING = {
  protect: 'Manipulation the organisation restrains in others',
  control: 'The choice environment the organisation controls',
  spine: 'Assessment',
} as const;

type PositionedNode = GraphNode & { y: number };

function buildGraph(inv: KpiInvestigation): {
  nodes: PositionedNode[];
  edges: { from: string; to: string; tone: string; step: number }[];
} {
  const supports = inv.evidence.filter((e) => e.relation === 'supports');
  const conflicts = inv.evidence.filter((e) => e.relation === 'conflicts');
  const context = inv.evidence.filter((e) => e.relation === 'context');

  const nodes: PositionedNode[] = [
    { id: 'actor', kind: 'actor', branch: 'spine', y: ROW_ACTOR,
      label: inv.company.name, sublabel: inv.company.sector },
  ];
  const edges: { from: string; to: string; tone: string; step: number }[] = [];

  supports.slice(0, 2).forEach((e, i) => {
    const id = `s${e.id}`;
    nodes.push({ id, kind: 'control', branch: 'protect', y: ROW_BRANCH + i * 78,
      label: shorten(e.title), sublabel: e.source_authority, evidence: e });
    edges.push({ from: 'actor', to: id, tone: 'support', step: i });
  });

  conflicts.slice(0, 2).forEach((e, i) => {
    const id = `c${e.id}`;
    nodes.push({ id, kind: 'finding', branch: 'control', y: ROW_BRANCH + i * 78,
      label: shorten(e.title), sublabel: e.source_authority, evidence: e });
    edges.push({ from: 'actor', to: id, tone: 'conflict', step: i });
  });

  context.slice(0, 1).forEach((e) => {
    const id = `x${e.id}`;
    nodes.push({ id, kind: 'behaviour', branch: 'control', y: ROW_CONTEXT,
      label: shorten(e.title), sublabel: e.source_authority, evidence: e });
    conflicts.slice(0, 1).forEach((c) =>
      edges.push({ from: `c${c.id}`, to: id, tone: 'context', step: 3 }));
  });

  nodes.push({
    id: 'principle', kind: 'principle', branch: 'spine', y: ROW_PRINCIPLE,
    label: `Principle #${inv.stewardship_principle.kpi_id}`,
    sublabel: inv.assessment.verdict_label,
  });

  supports.slice(0, 2).forEach((e) =>
    edges.push({ from: `s${e.id}`, to: 'principle', tone: 'support', step: 4 }));
  conflicts.slice(0, 2).forEach((e) =>
    edges.push({ from: `c${e.id}`, to: 'principle', tone: 'conflict', step: 5 }));

  return { nodes, edges };
}

/** A cubic curve, vertical-biased so branches read as flow rather than wiring. */
function curve(x1: number, y1: number, x2: number, y2: number): string {
  const mid = (y1 + y2) / 2;
  return `M ${x1} ${y1 + 24} C ${x1} ${mid}, ${x2} ${mid}, ${x2} ${y2 - 26}`;
}

/**
 * The distinctive half of a title.
 *
 * Evidence titles read "Authority — what it is", and the authority is already
 * the node's sublabel. Taking the first segment therefore labelled every node
 * with the same company name; the informative half is what follows the dash.
 */
function shorten(title: string | null | undefined): string {
  // `title` is nullable: an evidence record whose source recorded no title has
  // none, and the API stopped substituting the idempotency key for one. A graph
  // node is not the place to discover that — this crashed the whole
  // investigation page with "Cannot read properties of null" until it was
  // caught in a browser.
  if (!title) return 'Untitled source';
  const parts = title.split('—').map((p) => p.trim()).filter(Boolean);
  const distinctive = (parts.length > 1 ? parts[1] : parts[0]) ?? title;
  const clean = distinctive.replace(/\s*\([^)]*\)\s*$/, '');
  return clean.length > 32 ? `${clean.slice(0, 31)}…` : clean;
}
