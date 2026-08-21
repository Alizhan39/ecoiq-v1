import { getPlatformStats } from '@/api/platform';
import { useApi } from '@/hooks/useApi';
import { ErrorState, Loading } from '@/components/States';
import { isEvaluated, type ModuleSummary } from '@/types/platform';

/**
 * EcoIQ Labs.
 *
 * A controlled home for experimental work, so the primary product does not
 * read as thirty unrelated applications.
 *
 * Every status and every basis comes from the canonical registry. Nothing here
 * is written by hand, which means a module cannot be presented as more mature
 * on this page than it is in the code.
 */
const ORDER = ['BETA', 'EXPERIMENTAL', 'PLANNED', 'SPECIFICATION'] as const;

const HEADING: Record<string, string> = {
  BETA: 'Beta',
  EXPERIMENTAL: 'Experimental',
  PLANNED: 'Planned',
  SPECIFICATION: 'Specified, not built',
};

const EXPLANATION: Record<string, string> = {
  BETA: 'Real code with meaningful tests. Evaluation is incomplete, so these '
    + 'carry no enterprise-readiness claim.',
  EXPERIMENTAL: 'Working experiments. Useful to look at, not to depend on.',
  PLANNED: 'Not functional. Listed so the direction is legible.',
  SPECIFICATION: 'Written designs with no implementation.',
};

function Group({ status, modules }: { status: string; modules: ModuleSummary[] }) {
  if (modules.length === 0) return null;
  return (
    <section aria-labelledby={`labs-${status}`}>
      <h2 id={`labs-${status}`}>
        {HEADING[status] ?? status}{' '}
        <span className="labs__count">{modules.length}</span>
      </h2>
      <p className="prose state__detail">{EXPLANATION[status]}</p>
      <ul className="grid">
        {modules.map((module) => (
          <li className="card card--muted" key={module.key}>
            <h3>
              {module.name}{' '}
              <span
                className={`status-badge status-badge--${status.toLowerCase()}`}
              >
                {HEADING[status] ?? status}
              </span>
            </h3>
            {/* The BASIS, from the registry. A status without a stated reason
                is an assertion, and this page is where that would show. */}
            <p>{module.basis}</p>
            <p className="state__detail">
              Evaluation:{' '}
              {isEvaluated(module) ? module.evaluation : 'not yet measured'}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function Labs() {
  const state = useApi(getPlatformStats, []);

  if (state.status === 'loading') return <Loading label="Loading modules" />;
  if (state.status === 'error') return <ErrorState error={state.error} />;

  const modules = state.data.modules;
  const production = modules.filter((m) => m.status === 'PRODUCTION');

  return (
    <div className="labs">
      <header className="prose">
        <h1>EcoIQ Labs</h1>
        <p>
          Work that is real but not ready. Everything below is grouped by what
          can honestly be claimed about it, and the grouping comes from the
          code — not from this page.
        </p>
        <p className="state__detail">
          {production.length} modules are in production and are not listed here;
          they are the product.
        </p>
      </header>

      {ORDER.map((status) => (
        <Group
          key={status}
          status={status}
          modules={modules.filter((m) => m.status === status)}
        />
      ))}
    </div>
  );
}
