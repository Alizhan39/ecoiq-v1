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

export const SCENE_RANGES: [number, number][] = [
  [0, 0.14], // 1 — Introduction
  [0.14, 0.29], // 2 — Evidence becomes visible
  [0.29, 0.43], // 3 — AI Agents activate
  [0.43, 0.57], // 4 — Mizan Analysis (not yet implemented)
  [0.57, 0.69], // 5 — Recommended pathway (not yet implemented)
  [0.69, 0.82], // 6 — Capital Guardian (not yet implemented)
  [0.82, 0.91], // 7 — Approve and Act (not yet implemented)
  [0.91, 1], // 8 — Verified outcomes (not yet implemented)
]

export const IMPLEMENTED_SCENE_COUNT = 3

export const SLICE_END = SCENE_RANGES[IMPLEMENTED_SCENE_COUNT - 1][1]

export const SLICE_HEIGHT_VH = Math.round(FULL_TIMELINE_VH * SLICE_END)

/**
 * Sub-staging within Scene 3 (AI Agents, 0.29–0.43): rotation begins early,
 * arm engagement fires in the middle (holding through repair), repair
 * activates late and settles before the 0.43 release into Pillars. Ranges
 * overlap slightly on purpose for a continuous, non-mechanical feel.
 */
export const AGENTS_SUB_RANGES = {
  rotation: [0.29, 0.36] as [number, number],
  arms: [0.33, 0.39] as [number, number],
  repair: [0.37, 0.43] as [number, number],
}
