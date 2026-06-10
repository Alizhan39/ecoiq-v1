/**
 * EcoIQ Visual Intelligence — component registry.
 * Maps `data-island="Name"` → React component.
 */
import type { ComponentType } from 'react'
import ImpactGlobe from './components/ImpactGlobe'
import RiskRadar from './components/RiskRadar'
import ESGGraph from './components/ESGGraph'
import ScenarioSimulator from './components/ScenarioSimulator'
import StakeholderMap from './components/StakeholderMap'
import AIStorytelling from './components/AIStorytelling'
import KazakhstanHero from './components/kazakhstan/KazakhstanHero'
import TransitionMap from './components/kazakhstan/TransitionMap'
import HeatingTransitionStory from './components/stories/HeatingTransitionStory'
import NarrativeStory from './components/stories/NarrativeStory'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const registry: Record<string, ComponentType<any>> = {
  ImpactGlobe,
  RiskRadar,
  ESGGraph,
  ScenarioSimulator,
  StakeholderMap,
  AIStorytelling,
  KazakhstanHero,
  TransitionMap,
  HeatingTransitionStory,
  NarrativeStory,
}
