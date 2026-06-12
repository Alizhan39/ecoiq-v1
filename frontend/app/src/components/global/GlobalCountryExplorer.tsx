/**
 * GlobalCountryExplorer — interactive world map on real open-source geography.
 *
 * Geometry: Natural Earth 110m countries (world-atlas TopoJSON, public domain),
 * loaded lazily via dynamic import so the ~100KB dataset ships as a separate
 * chunk only when this island mounts. Projection: d3-geo Natural Earth I.
 *
 * Every country is selectable. Four active markets carry full EcoIQ intel;
 * everything else shows "Research coverage planned". Selecting Kazakhstan
 * additionally reveals a second-level national map with clearly-labelled demo
 * layers. A search list mirrors the map for mobile / keyboard / no-pointer use.
 */
import { AnimatePresence, m } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import { geoNaturalEarth1, geoPath } from 'd3-geo'
import { Reveal, fadeUp, tFast } from '../../motion'
import {
  CountryIntel,
  getCountryIntel,
  STATUS_LABEL,
} from './countries'
import KazakhstanDetail from './KazakhstanDetail'

interface CountryFeature {
  id: string
  name: string
  d: string
}

const WIDTH = 960
const HEIGHT = 480

export interface GlobalCountryExplorerProps {
  eyebrow?: string
  title?: string
}

export default function GlobalCountryExplorer(props: GlobalCountryExplorerProps) {
  const {
    eyebrow = 'Global Intelligence',
    title = 'Select any country. See EcoIQ coverage.',
  } = props

  const [features, setFeatures] = useState<CountryFeature[]>([])
  const [kzGeoD, setKzGeoD] = useState<string | null>(null)
  const [hover, setHover] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string>('398') // Kazakhstan default
  const [selectedName, setSelectedName] = useState<string>('Kazakhstan')
  const [query, setQuery] = useState('')
  const [loadError, setLoadError] = useState(false)

  // Lazy-load the Natural Earth topology as its own chunk.
  useEffect(() => {
    let alive = true
    Promise.all([
      import('world-atlas/countries-110m.json'),
      import('topojson-client'),
    ])
      .then(([atlas, topojson]) => {
        if (!alive) return
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const topo = (atlas as any).default ?? atlas
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const fc = topojson.feature(topo, topo.objects.countries) as any
        const projection = geoNaturalEarth1().fitSize([WIDTH, HEIGHT], fc)
        const path = geoPath(projection)
        const fs: CountryFeature[] = fc.features
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .map((f: any) => ({
            id: String(f.id),
            name: f.properties?.name ?? 'Unknown',
            d: path(f) ?? '',
          }))
          .filter((f: CountryFeature) => f.d)
        setFeatures(fs)

        // Kazakhstan national outline for the second-level map, projected alone.
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const kz = fc.features.find((f: any) => String(f.id) === '398')
        if (kz) {
          const kzProj = geoNaturalEarth1().fitSize([720, 420], kz)
          setKzGeoD(geoPath(kzProj)(kz))
        }
      })
      .catch(() => alive && setLoadError(true))
    return () => {
      alive = false
    }
  }, [])

  const intel: CountryIntel = useMemo(
    () => getCountryIntel(selectedId, selectedName),
    [selectedId, selectedName],
  )

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    const list = [...features].sort((a, b) => a.name.localeCompare(b.name))
    return q ? list.filter((f) => f.name.toLowerCase().includes(q)) : list
  }, [features, query])

  const select = (f: { id: string; name: string }) => {
    setSelectedId(f.id)
    setSelectedName(f.name)
  }

  return (
    <Reveal variants={fadeUp} className="eiq-gx eiq-panel">
      <div className="eiq-eyebrow">{eyebrow}</div>
      <h2 className="eiq-gx__title">{title}</h2>

      <div className="eiq-gx__grid">
        {/* World map */}
        <div className="eiq-gx__map">
          {loadError && (
            <p className="eiq-gx__error">Map data unavailable — use the country list.</p>
          )}
          {!loadError && features.length === 0 && (
            <div className="eiq-gx__loading" aria-hidden="true">Loading world geometry…</div>
          )}
          {features.length > 0 && (
            <svg
              viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
              role="img"
              aria-label="World map — select a country"
            >
              {features.map((f) => {
                const known = getCountryIntel(f.id, f.name)
                const active = known.status === 'active'
                const isSel = f.id === selectedId
                return (
                  <path
                    key={f.id + f.name}
                    d={f.d}
                    className={`eiq-gx__country${active ? ' is-covered' : ''}${isSel ? ' is-selected' : ''}`}
                    onMouseEnter={() => setHover(f.name)}
                    onMouseLeave={() => setHover(null)}
                    onClick={() => select(f)}
                  >
                    <title>{f.name}</title>
                  </path>
                )
              })}
            </svg>
          )}
          <AnimatePresence>
            {hover && (
              <m.div
                className="eiq-gx__tip"
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={tFast}
              >
                {hover}
              </m.div>
            )}
          </AnimatePresence>
          <div className="eiq-gx__legend">
            <span><i className="eiq-gx__swatch eiq-gx__swatch--active" /> Active coverage</span>
            <span><i className="eiq-gx__swatch" /> Research coverage planned</span>
          </div>
        </div>

        {/* Search list — mobile / keyboard fallback, always usable */}
        <div className="eiq-gx__list">
          <input
            className="eiq-gx__search"
            type="search"
            placeholder="Search countries…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search countries"
          />
          <ul role="listbox" aria-label="Countries">
            {filtered.slice(0, 200).map((f) => {
              const known = getCountryIntel(f.id, f.name)
              return (
                <li key={f.id + f.name}>
                  <button
                    role="option"
                    aria-selected={f.id === selectedId}
                    className={`eiq-gx__item${f.id === selectedId ? ' is-selected' : ''}`}
                    onClick={() => select(f)}
                  >
                    <span>{f.name}</span>
                    {known.status === 'active' && <span className="eiq-gx__badge">Active</span>}
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      </div>

      {/* Country detail panel */}
      <AnimatePresence mode="wait">
        <m.div
          key={selectedId + selectedName}
          className="eiq-gx__detail"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={tFast}
        >
          <div className="eiq-gx__detail-head">
            <h3 className="eiq-gx__name">{intel.name}</h3>
            <span className={`eiq-gx__status eiq-gx__status--${intel.status}`}>
              {STATUS_LABEL[intel.status]}
            </span>
            {intel.region && <span className="eiq-gx__region">{intel.region}</span>}
          </div>

          {intel.status === 'active' ? (
            <>
              <div className="eiq-gx__stats">
                <div className="eiq-metric">
                  <div className="eiq-metric__value">{intel.companiesRanked}</div>
                  <div className="eiq-metric__label">Companies ranked</div>
                </div>
                <div className="eiq-metric">
                  <div className="eiq-metric__value">{intel.projectOpportunities}</div>
                  <div className="eiq-metric__label">Project opportunities</div>
                </div>
              </div>

              <div className="eiq-gx__block">
                <div className="eiq-gx__block-label">Key transition risks</div>
                <ul className="eiq-gx__risks">
                  {intel.transitionRisks.map((r) => <li key={r}>{r}</li>)}
                </ul>
              </div>

              <div className="eiq-gx__block">
                <div className="eiq-gx__block-label">Manufacturer &amp; technology intelligence</div>
                <div className="eiq-gx__mfg">
                  {intel.manufacturers.map((c) => (
                    <span key={c} className="eiq-gx__mfg-chip">{c}</span>
                  ))}
                </div>
              </div>

              {intel.note && <p className="eiq-gx__note">{intel.note}</p>}

              <div className="eiq-gx__ctas">
                {intel.slug && (
                  <a className="eiq-gx__cta eiq-gx__cta--primary" href={`/countries/${intel.slug}/`}>
                    View country intelligence →
                  </a>
                )}
                <a className="eiq-gx__cta" href="mailto:alizhan@ecoiq.uk?subject=Country+Briefing+Request">
                  Request briefing
                </a>
                <a className="eiq-gx__cta" href={`/manufacturers/${intel.iso2 ? `?country=${intel.iso2}` : ''}`}>
                  Explore manufacturers
                </a>
              </div>
            </>
          ) : (
            <p className="eiq-gx__planned">
              {intel.name} is not yet under active EcoIQ coverage. Research coverage is planned —
              institutional clients can commission early scoping.
              <a className="eiq-gx__cta" href="mailto:alizhan@ecoiq.uk?subject=Coverage+Request" style={{ marginLeft: 10 }}>
                Request coverage →
              </a>
            </p>
          )}
        </m.div>
      </AnimatePresence>

      {/* Second-level Kazakhstan map (real national outline + demo layers) */}
      {selectedId === '398' && kzGeoD && <KazakhstanDetail outlineD={kzGeoD} />}
    </Reveal>
  )
}
