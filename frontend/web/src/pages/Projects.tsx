import { listProjects } from '@/api/projects';
import { useApi } from '@/hooks/useApi';
import { EmptyState, ErrorState, Loading } from '@/components/States';
import { quantity } from '@/types/projects';

/**
 * Projects.
 *
 * The estate currently holds none. The page says so rather than being
 * populated with demo rows to look finished — a populated page nobody can act
 * on is worse than an empty one that explains itself.
 */
export default function Projects() {
  const state = useApi(listProjects, []);

  if (state.status === 'loading') return <Loading label="Loading projects" />;
  if (state.status === 'error') return <ErrorState error={state.error} />;

  const { count, verified_count: verified, results } = state.data;

  return (
    <div>
      <header className="prose">
        <h1>Projects</h1>
        <p>
          Interventions with a stated problem, a capital requirement and an
          execution status.
        </p>
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
    </div>
  );
}
