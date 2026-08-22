/**
 * EcoIQ Visual Intelligence — component registry.
 * Maps `data-island="Name"` → React component.
 *
 * CinematicHomeHero was removed with templates/landing.html. It was the only
 * consumer of the six hero image variants under static/img/hero/ — 646 kB that
 * no page referenced once `/` became React. Dropping it from the registry is
 * what lets the bundle stop naming those files, which is what lets them be
 * deleted.
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
  CountUpValue,
  InvestorScrollStory,
}
