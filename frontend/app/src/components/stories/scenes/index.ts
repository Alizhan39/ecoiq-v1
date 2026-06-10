/**
 * Scene registry — maps a narrative `variant` to its scene visual.
 * Adding a new storytelling visual (e.g. for Country / Company pages) is a
 * one-line addition here.
 */
import type { SceneComponent } from './types'
import VillageScene from './VillageScene'
import EcosystemScene from './EcosystemScene'
import TimelineScene from './TimelineScene'
import IntelligenceScene from './IntelligenceScene'

export const SCENES: Record<string, SceneComponent> = {
  village: VillageScene,
  ecosystem: EcosystemScene,
  timeline: TimelineScene,
  intelligence: IntelligenceScene,
}
