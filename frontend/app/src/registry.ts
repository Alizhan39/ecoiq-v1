/**
 * EcoIQ Visual Intelligence — component registry.
 * Maps `data-island="Name"` → React component.
 *
 * AN ENTRY HERE IS WHAT KEEPS A MODULE ALIVE
 * ------------------------------------------
 * main.tsx mounts by `data-island` attribute and nothing else, so a component
 * reaches the bundle only by being named below. That makes this file the whole
 * liveness boundary for `frontend/app`: a registry entry whose island no
 * template mounts keeps its component — and everything that component imports —
 * in a bundle every page downloads, for a page that no longer exists.
 *
 * CinematicHomeHero was the first instance, removed with templates/landing.html
 * because it was the only consumer of the 646 kB hero image tree.
 *
 * Ten more went the same way once the public product routes became React. Their
 * templates were deleted by the migration and are now 301 redirects:
 *
 *   global_intelligence.html         DigitalTwinPreview, GlobalCountryExplorer
 *   kazakhstan_transition_brief.html AIStorytelling, ESGGraph, KazakhstanHero,
 *                                    ScenarioSimulator, StakeholderMap,
 *                                    TransitionMap
 *   khalifa_tours_impact.html        NarrativeStory
 *   landing.html                     InvestorScrollStory
 *
 * The four below are mounted by templates that still exist — checked against
 * every `data-island` in the repository, not assumed. Before adding an entry,
 * make sure a live template actually mounts it.
 */
import type { ComponentType } from 'react'
import ImpactGlobe from './components/ImpactGlobe'
import RiskRadar from './components/RiskRadar'
import HeatingTransitionStory from './components/stories/HeatingTransitionStory'
import CountUpValue from './components/cinematic/CountUpValue'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const registry: Record<string, ComponentType<any>> = {
  ImpactGlobe,
  RiskRadar,
  HeatingTransitionStory,
  CountUpValue,
}
