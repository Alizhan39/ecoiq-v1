/**
 * EcoIQ country intelligence model.
 *
 * Keyed by ISO 3166-1 numeric id (what Natural Earth / world-atlas TopoJSON
 * uses as feature ids), with alpha-2 codes for routing/filtering. The four
 * active markets carry full intel; every other country resolves to a
 * "research coverage planned" default via `getCountryIntel`.
 */

export type CoverageStatus = 'active' | 'planned' | 'research'

export interface CountryIntel {
  iso2: string
  name: string
  region: string
  status: CoverageStatus
  companiesRanked: number
  transitionRisks: string[]
  manufacturers: string[]
  projectOpportunities: number
  slug?: string
  note?: string
}

/** Full manufacturer taxonomy — institutional supply-chain categories. */
export const MANUFACTURER_CATEGORIES = [
  'Clean heating',
  'Heat pumps',
  'Electric boilers',
  'Solar',
  'Wind',
  'Insulation',
  'Smart meters',
  'Industrial efficiency',
  'Water / waste systems',
] as const

/** ISO numeric (world-atlas feature id) → intel for active/planned markets. */
export const COUNTRY_INTEL: Record<string, CountryIntel> = {
  // ── Active markets ────────────────────────────────────────────────────────
  '398': {
    iso2: 'KZ', name: 'Kazakhstan', region: 'Central Asia', status: 'active',
    companiesRanked: 64, projectOpportunities: 22, slug: 'kazakhstan',
    transitionRisks: ['Coal-heavy power mix', 'Household coal heating', 'Industrial emissions intensity'],
    manufacturers: ['Clean heating', 'Electric boilers', 'Insulation', 'Solar', 'Smart meters'],
    note: 'JETP-eligible pipeline; national heating transition underway.',
  },
  '826': {
    iso2: 'GB', name: 'United Kingdom', region: 'Western Europe', status: 'active',
    companiesRanked: 96, projectOpportunities: 14, slug: 'united-kingdom',
    transitionRisks: ['Gas heating dependency', 'Grid flexibility', 'Industrial cluster decarbonisation'],
    manufacturers: ['Heat pumps', 'Smart meters', 'Insulation', 'Solar', 'Wind', 'Industrial efficiency'],
    note: 'Mature disclosure baseline; deep green-bond market.',
  },
  '682': {
    iso2: 'SA', name: 'Saudi Arabia', region: 'Middle East', status: 'active',
    companiesRanked: 31, projectOpportunities: 11, slug: 'saudi-arabia',
    transitionRisks: ['Hydrocarbon revenue concentration', 'Cooling energy demand', 'Water stress'],
    manufacturers: ['Solar', 'Smart meters', 'Heat pumps', 'Water / waste systems'],
    note: 'Vision 2030 diversification; Islamic finance depth.',
  },
  '792': {
    iso2: 'TR', name: 'Türkiye', region: 'Anatolia / Eurasia', status: 'active',
    companiesRanked: 23, projectOpportunities: 9, slug: 'turkiye',
    transitionRisks: ['Lignite generation', 'Energy import exposure', 'Seismic-resilient retrofit need'],
    manufacturers: ['Heat pumps', 'Electric boilers', 'Solar', 'Wind', 'Insulation'],
    note: 'Clean-heating manufacturing corridor serving EU and Central Asia.',
  },
}

/** Default for any country without explicit coverage. */
export function getCountryIntel(isoNumeric: string, name: string): CountryIntel {
  const known = COUNTRY_INTEL[isoNumeric]
  if (known) return known
  return {
    iso2: '', name, region: '', status: 'research',
    companiesRanked: 0, projectOpportunities: 0,
    transitionRisks: [], manufacturers: [],
    note: 'Research coverage planned.',
  }
}

export const STATUS_LABEL: Record<CoverageStatus, string> = {
  active: 'Active coverage',
  planned: 'Coverage planned',
  research: 'Research coverage planned',
}
