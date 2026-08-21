/**
 * The system verticals EcoIQ is being built to support.
 *
 * Every one is PLANNED: no backend implements an energy, aviation, cities or
 * nature decision engine today. These cards explain direction and offer no
 * "Analyse" affordance — a button that cannot do the thing it names is worse
 * than no button.
 */
const VERTICALS = [
  { name: 'Energy', detail: 'Generation, grid and transition decisions.' },
  { name: 'Transport & Aviation', detail: 'Fleet, fuel and route decisions.' },
  { name: 'Cities & Buildings', detail: 'Retrofit, efficiency and use.' },
  { name: 'Nature & Resources', detail: 'Water, land and material flows.' },
] as const;

export function Verticals() {
  return (
    <section aria-labelledby="verticals" className="verticals">
      <h2 id="verticals">Systems EcoIQ is being built for</h2>
      <p className="prose">
        Not available yet. Listed so the direction is legible, not to imply a
        product.
      </p>
      <ul className="grid">
        {VERTICALS.map((vertical) => (
          <li className="card card--muted" key={vertical.name}>
            <h3>
              {vertical.name}{' '}
              <span className="status-badge status-badge--specification">
                Planned
              </span>
            </h3>
            <p>{vertical.detail}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
