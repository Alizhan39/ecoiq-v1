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
import DigitalTwinPreview from './components/intelligence/DigitalTwinPreview'
import GlobalCountryExplorer from './components/global/GlobalCountryExplorer'
import CinematicHomeHero from './components/cinematic/CinematicHomeHero'
import CountUpValue from './components/cinematic/CountUpValue'
import InvestorScrollStory from './components/investor-story/InvestorScrollStory'

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
  DigitalTwinPreview,
  GlobalCountryExplorer,
  CinematicHomeHero,
  CountUpValue,
  InvestorScrollStory,
}
