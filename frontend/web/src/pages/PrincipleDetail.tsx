import { Link, useParams } from 'react-router-dom';
import { fetchPrincipleRegistry } from '@/api/principles';
import { ErrorState, Loading } from '@/components/States';
import { useApi } from '@/hooks/useApi';

/**
 * One principle, on its own.
 *
 * WHY THIS READS THE WHOLE REGISTRY
 * ---------------------------------
 * There is no per-principle endpoint, and adding one would buy nothing: the
 * registry is 114 rows of static framework text, it names no organisation, and
 * it is the same for every reader. One request that the previous page has
 * usually already made beats a second endpoint to maintain.
 *
 * WHAT AN UNKNOWN ID DOES
 * -----------------------
 * Renders "no such principle" rather than an empty shell. An id outside 1-114
 * is not a principle awaiting evidence — it does not exist, and a page that
 * looked merely unassessed would say something false about the framework's
 * size.
 *
 * WHAT IS DELIBERATELY ABSENT
 * ---------------------------
 * Any organisation's standing. This page is the question; an investigation is
 * the answer, and the two are not shown as one thing.
 */
export default function PrincipleDetail() {
  const { kpiId } = useParams();
  const state = useApi((signal) => fetchPrincipleRegistry(signal), []);

  if (state.status === 'loading') return <Loading />;
  if (state.status === 'error') return <ErrorState error={state.error} />;

  const id = Number(kpiId);
  const principle = state.data.principles.find((p) => p.kpi_id === id);

  if (!principle) {
    return (
      <div className="principle">
        <h1>No such principle</h1>
        <p className="prose">
          EcoIQ assesses against {state.data.total} stewardship principles,
          numbered 1 to {state.data.total}. There is no principle {kpiId}.
        </p>
        <p>
          <Link to="/principles/">Browse all {state.data.total} principles</Link>
        </p>
      </div>
    );
  }

  const domain = state.data.categories.find((c) => c.key === principle.category);

  return (
    <article className="principle">
      <p className="principle__eyebrow">
        <Link to="/principles/">Stewardship principles</Link>
        {domain ? <> &middot; {domain.label}</> : null}
      </p>
      <h1>
        <span className="principle__num">#{principle.kpi_id}</span>{' '}
        {principle.title}
      </h1>
      <p className="principle__tagline">{principle.tagline}</p>

      <section aria-labelledby="principle-question">
        <h2 id="principle-question">The question</h2>
        <p className="principle__question">{principle.question}</p>
      </section>

      {principle.principle_statement ? (
        <section aria-labelledby="principle-signal">
          <h2 id="principle-signal">What EcoIQ looks for</h2>
          <p className="prose">{principle.principle_statement}</p>
        </section>
      ) : null}

      {principle.metrics.length > 0 ? (
        <section aria-labelledby="principle-metrics">
          <h2 id="principle-metrics">Indicators</h2>
          <p className="prose state__detail">
            What evidence against this principle tends to consist of. These are
            the indicators an investigation looks for — not a checklist, and not
            a score: an organisation is not assessed on how many of them it can
            produce.
          </p>
          <ul className="principle__metrics">
            {principle.metrics.map((metric) => (
              <li key={metric}>{metric}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-labelledby="principle-how">
        <h2 id="principle-how">How this gets answered</h2>
        <p className="prose">
          An investigation links evidence to this principle, records what each
          item supports or conflicts with, and derives a verdict from the
          confirmed evidence only. Evidence awaiting review is shown and counts
          toward nothing. Where the evidence does not carry a conclusion, the
          principle is reported as insufficient — which is an answer, not a
          failure to produce one.
        </p>
        <p>
          <Link to="/companies/">Find an organisation to investigate</Link>
        </p>
      </section>
    </article>
  );
}
