/**
 * EcoIQ Visual Intelligence — component registry.
 *
 * The single place that maps a `data-island="Name"` string to a React
 * component. Future visual-intelligence components (TransitionMap, RiskRadar,
 * ESGGraph, StakeholderMap, ScenarioSimulator, ...) register here.
 *
 * Phase 0 ships exactly one: ImpactGlobe.
 */
import type { ComponentType } from 'react'
import ImpactGlobe from './components/ImpactGlobe'
import RiskRadar from './components/RiskRadar'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const registry: Record<string, ComponentType<any>> = {
  ImpactGlobe,
  RiskRadar,
}
