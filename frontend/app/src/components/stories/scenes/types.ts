/**
 * Shared contract for narrative scene visuals.
 *
 * A scene visual is a self-contained SVG that reacts to the active scene index
 * (0-based) and optional data. It is the "Visual layer" of a narrative section;
 * the engine (Scrollytelling) supplies `active` from scroll position.
 *
 * Reuse: future Country / Company pages add a new scene component + a `variant`
 * key in scenes/index.ts and immediately get the full narrative treatment.
 */
import type { ComponentType } from 'react'

export interface SceneProps {
  active: number
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data?: Record<string, any>
}

export type SceneComponent = ComponentType<SceneProps>

export function pick<T>(arr: T[], i: number): T {
  return arr[Math.min(Math.max(i, 0), arr.length - 1)]
}

export const sceneEase = { duration: 1.0, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] }
