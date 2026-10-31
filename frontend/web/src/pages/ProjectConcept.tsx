import { Link, useParams } from 'react-router-dom';
import { listProjects } from '@/api/projects';
import { useApi } from '@/hooks/useApi';
import { EmptyState, ErrorState, Loading } from '@/components/States';

/**
 * One programme concept.
 *
 * Reads the same list endpoint rather than a detail route: there are five of
 * them, they are editorial content, and a second endpoint would be a second
 * place for the framing to drift. Whatever this page says about a concept, the
 * list page said too.
 *
 * The status badge is rendered from `status_key` and is never omitted. A
 * concept page that reads like a case study is the failure mode here — the
 * reader has to be able to tell, without inference, that nothing on this page
 * has been built.
 */
export default function ProjectConcept() {
  const { slug } = useParams<{ slug: string }>();
  const state = useApi(listProjects, []);

  if (state.status === 'loading') return <Loading label="Loading concept" />;
  if (state.status === 'error') return <ErrorState error={state.error} />;

  const concept = state.data.concepts.find((item) => item.slug === slug);

  if (!concept) {
    return (
      <EmptyState>
        <p>No programme concept with that name.</p>
        <p className="state__detail">
          <Link to="/projects">All projects and concepts</Link>
        </p>
      </EmptyState>
    );
  }

  return (
    <div className="prose">
      <p className="state__detail">
        <Link to="/projects">← Projects</Link>
      </p>

      <h1>{concept.name}</h1>
      <p>{concept.tagline}</p>

      <p>
        <span className="status-badge status-badge--specification">
          Concept · {concept.status}
        </span>
      </p>
      <p className="state__detail">
        This is a programme concept, not an implementation. Nothing described
        below has been built, and every figure on this page is indicative.
      </p>

      <dl className="evidence">
        <div className="evidence__item">
          <dt>Location</dt>
          <dd>{concept.location || '—'}</dd>
        </div>
        <div className="evidence__item">
          <dt>Sector</dt>
          <dd>{concept.sector || '—'}</dd>
        </div>
        <div className="evidence__item">
          <dt>Timeline</dt>
          <dd>{concept.timeline_label || '—'}</dd>
        </div>
      </dl>

      <section aria-labelledby="problem">
        <h2 id="problem">The problem</h2>
        <p>{concept.problem}</p>
      </section>

      <section aria-labelledby="approach">
        <h2 id="approach">The proposed approach</h2>
        <p>{concept.solution}</p>
      </section>

      {concept.expected_impact.length > 0 ? (
        <section aria-labelledby="impact">
          <h2 id="impact">Intended impact</h2>
          <p className="state__detail">
            Targets, not measurements. Nothing here has been observed.
          </p>
          <ul className="grid">
            {concept.expected_impact.map((item) => (
              <li className="card card--muted" key={item.label}>
                <h3>{item.value}</h3>
                <p>{item.label}</p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {concept.timeline_phases.length > 0 ? (
        <section aria-labelledby="phases">
          <h2 id="phases">Phases</h2>
          <ol className="pipeline">
            {concept.timeline_phases.map((phase) => (
              <li key={phase.phase}>
                <strong>{phase.phase} · {phase.window}</strong>
                <span>{phase.detail}</span>
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      {concept.partnership_opportunities.length > 0 ? (
        <section aria-labelledby="partners">
          <h2 id="partners">Who this needs</h2>
          <ul>
            {concept.partnership_opportunities.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-labelledby="funding">
        <h2 id="funding">Funding</h2>
        <p>
          <strong>{concept.funding_amount}</strong>{' '}
          <span className="state__detail">{concept.funding_label}</span>
        </p>
        <p className="state__detail">{concept.funding_note}</p>
      </section>

      <p>
        <Link className="cta" to="/contact">Discuss this concept</Link>
      </p>
    </div>
  );
}
