import { Link } from 'react-router-dom';
import { listProjects } from '@/api/projects';
import { useApi } from '@/hooks/useApi';
import { EmptyState, ErrorState, Loading } from '@/components/States';
import { quantity } from '@/types/projects';

/**
 * Projects.
 *
 * TWO SECTIONS, NEVER ONE LIST
 * ----------------------------
 * Recorded projects come from the database. There are none. Programme concepts
 * come from projects/data.py — five real intentions at concept or design
 * stage, with indicative budgets and nothing built.
 *
 * They are rendered in separate sections with separate headings, and the
 * concepts section leads with what it is. Interleaving them would turn five
 * ideas into "five projects" — the same substitution as a score standing in
 * for evidence, and more tempting, because the merged page looks finished.
 *
 * The empty state for recorded projects is shown even when concepts exist. It
 * is the honest answer to "what has EcoIQ delivered", and hiding it behind a
 * populated-looking page would answer a different question.
 */
export default function Projects() {
  const state = useApi(listProjects, []);

  if (state.status === 'loading') return <Loading label="Loading projects" />;
  if (state.status === 'error') return <ErrorState error={state.error} />;

  const { count, verified_count: verified, results, concepts } = state.data;

  return (
    <div>
      <header className="prose">
        <h1>Projects</h1>
        <p>
          Interventions with a stated problem, a capital requirement and an
          execution status. Recorded projects are listed first; programme
          concepts, which have not been implemented, are listed separately
          below.
        </p>
        <h2>Recorded projects</h2>
      </header>

      {count === 0 ? (
        <EmptyState>
          <p>No projects are on record yet.</p>
          <p className="state__detail">
            Projects appear here once they carry a problem statement, a
            baseline and a capital requirement. None is shown until then.
          </p>
        </EmptyState>
      ) : (
        <>
          <p className="state__detail">
            {count} on record · {verified} independently verified
          </p>
          <ul className="grid">
            {results.map((project) => (
              <li className="card" key={project.slug}>
                <h3>{project.name}</h3>
                <p className="state__detail">
                  {project.company} · {project.location || 'Location not recorded'}
                </p>
                <dl className="evidence">
                  <div className="evidence__item">
                    <dt>Capital</dt>
                    <dd>{quantity(project.investment_usd, 'USD')}</dd>
                  </div>
                  <div className="evidence__item">
                    <dt>CO₂ reduction</dt>
                    <dd>{quantity(project.co2_reduction_tonnes, 't')}</dd>
                  </div>
                </dl>
                <p>
                  <span
                    className={
                      project.verified
                        ? 'status-badge status-badge--production'
                        : 'status-badge status-badge--specification'
                    }
                  >
                    {project.verified ? 'Independently verified' : 'Not verified'}
                  </span>
                </p>
              </li>
            ))}
          </ul>
        </>
      )}

      {concepts.length > 0 ? (
        <section aria-labelledby="concepts" className="prose">
          <h2 id="concepts">Programme concepts</h2>
          <p>
            Work EcoIQ intends to do, at concept or design stage.{' '}
            <strong>None of it has been implemented</strong>, and every figure
            attached to it is indicative. They are listed separately from
            recorded projects for exactly that reason.
          </p>
          <ul className="grid">
            {concepts.map((concept) => (
              <li className="card card--muted" key={concept.slug}>
                <h3>
                  <Link to={`/projects/${concept.slug}`}>{concept.name}</Link>
                </h3>
                <p className="state__detail">
                  {concept.location || 'Location not set'} ·{' '}
                  {concept.timeline_label}
                </p>
                <p>{concept.tagline}</p>
                <p>
                  <span className="status-badge status-badge--specification">
                    Concept · {concept.status}
                  </span>
                </p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
