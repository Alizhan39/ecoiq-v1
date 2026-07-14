/**
 * Cinematic homepage hero — scene timeline.
 *
 * Ranges are fractions (0–1) of the *eventual* full 8-scene design, on a
 * ~620vh total scroll span. Only the first 3 scenes are implemented in this
 * slice — the wrapper height is set to `FULL_TIMELINE_VH * sceneRanges[IMPLEMENTED_SCENE_COUNT - 1][1]`
 * so `scrollYProgress` (0→1 over the wrapper) lines up with these exact
 * fractions without renormalization. Extending to 8 scenes later is just
 * growing the wrapper to `FULL_TIMELINE_VH` — these numbers don't change.
 */
export const FULL_TIMELINE_VH = 620

/**
 * Refinement pass note: Scene 3's span was widened from 0.14 to 0.21 of the
 * timeline (a compressed 21vh of actual scroll distance for the waste →
 * recovery → repair → stabilize → verify sequence proved too fast to read
 * as distinct beats — found during this pass's audit). Scenes 4-8 (still
 * unimplemented placeholders) absorb the difference; scenes 1-2 are
 * untouched since IntroScene/EvidenceScene are out of scope for this pass.
 */
export const SCENE_RANGES: [number, number][] = [
  [0, 0.14], // 1 — Introduction
  [0.14, 0.29], // 2 — Evidence becomes visible
  [0.29, 0.5], // 3 — AI Agents activate
  [0.5, 0.62], // 4 — Mizan Analysis (not yet implemented)
  [0.62, 0.73], // 5 — Recommended pathway (not yet implemented)
  [0.73, 0.84], // 6 — Capital Guardian (not yet implemented)
  [0.84, 0.92], // 7 — Approve and Act (not yet implemented)
  [0.92, 1], // 8 — Verified outcomes (not yet implemented)
]

export const IMPLEMENTED_SCENE_COUNT = 3

export const SLICE_END = SCENE_RANGES[IMPLEMENTED_SCENE_COUNT - 1][1]

export const SLICE_HEIGHT_VH = Math.round(FULL_TIMELINE_VH * SLICE_END)

/**
 * Sub-staging within Scene 3 (AI Agents, 0.29–0.5). Retimed this pass — the
 * previous [0.35,0.43] window for the whole waste→repair→verify sequence
 * (~21vh of real scroll) was too compressed to read as distinct beats (Phase
 * 1 audit finding). Repair now explicitly starts only once waste's own
 * window is mostly resolved (Phase 3: "right arm activates only after the
 * left intervention settles"), and `verify` is its own room after repair
 * ends rather than squeezed into repair's last 0.007 sliver, so VERIFIED
 * never appears before the physical outcomes are visually complete (Phase
 * 4). Small overlaps are still deliberate (motion-style-guide.md §4: "at
 * most 3 concurrent scroll-driven effect groups... sequential, not
 * simultaneous") — not simultaneous starts, just no dead gap between beats.
 */
export const AGENTS_SUB_RANGES = {
  rotation: [0.29, 0.35] as [number, number],
  arms: [0.33, 0.38] as [number, number],
  waste: [0.35, 0.415] as [number, number],
  repair: [0.405, 0.475] as [number, number],
}

/**
 * The globe's "alive" layer (GlobeRotationOverlay) was previously gated only
 * to `rotation`, which ended before `waste`/`repair` even started — no
 * visible cause→effect between an arm acting and the Earth responding.
 * These ranges gate response-specific globe layers (a localized glow near
 * the pollution/repair area, brightening only while that arm is active) so
 * the Earth visibly reacts during each intervention. `verify` now gets its
 * own dedicated window right after `repair` ends, not a sliver carved out
 * of repair's tail.
 */
export const GLOBE_RESPONSE_RANGES = {
  waste: AGENTS_SUB_RANGES.waste,
  repair: AGENTS_SUB_RANGES.repair,
  verify: [AGENTS_SUB_RANGES.repair[1], AGENTS_SUB_RANGES.repair[1] + 0.017] as [number, number],
}

/**
 * Documentation-only mapping from the 8 cinematic beats in the design brief
 * to the scroll ranges above — no on-screen beat labels are rendered from
 * this (inventing new visible slide text would fight the "no
 * word-by-word/staged text" and minimal-text rules); it exists purely so a
 * future reader can find "where is Recovery" without reverse-engineering sub
 * -range names.
 */
export const BEAT_LABELS: Record<string, [number, number]> = {
  '1 Observe': [0, 0.29],
  '2 Detect': [0.14, 0.29],
  '3 Waste intervention': [AGENTS_SUB_RANGES.waste[0], AGENTS_SUB_RANGES.waste[0] + (AGENTS_SUB_RANGES.waste[1] - AGENTS_SUB_RANGES.waste[0]) * 0.5],
  '4 Recovery': [AGENTS_SUB_RANGES.waste[0] + (AGENTS_SUB_RANGES.waste[1] - AGENTS_SUB_RANGES.waste[0]) * 0.5, AGENTS_SUB_RANGES.waste[1]],
  '5 Repair intervention': [AGENTS_SUB_RANGES.repair[0], AGENTS_SUB_RANGES.repair[0] + (AGENTS_SUB_RANGES.repair[1] - AGENTS_SUB_RANGES.repair[0]) * 0.6],
  '6 System stabilization': [AGENTS_SUB_RANGES.repair[0] + (AGENTS_SUB_RANGES.repair[1] - AGENTS_SUB_RANGES.repair[0]) * 0.6, AGENTS_SUB_RANGES.repair[1]],
  '7 Verify': GLOBE_RESPONSE_RANGES.verify,
  '8 Continue monitoring': [GLOBE_RESPONSE_RANGES.verify[1], SCENE_RANGES[2][1]],
}
