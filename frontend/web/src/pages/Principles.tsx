import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchPrincipleRegistry } from '@/api/principles';
import { ErrorState, Loading } from '@/components/States';
import { useApi } from '@/hooks/useApi';
import type { Principle } from '@/types/principles';

/**
 * The 114 stewardship principles EcoIQ assesses against.
 *
 * WHAT THIS PAGE IS, AND IS NOT
 * -----------------------------
 * It describes the METHOD. No organisation appears on it, no evidence, no
 * finding — those live on an investigation, which is a different claim
 * entirely. A framework page that quietly showed how organisations scored
 * against each principle would be a league table wearing a methodology page's
 * clothes.
 *
 * WHY THE QUESTION IS THE HEADLINE
 * --------------------------------
 * Every principle is rendered question-first, because the question is what
 * EcoIQ actually does with it. A principle reduced to its title is a category
 * label; the question is the thing an investigation has to answer, and it is
 * what makes the framework checkable by someone who disagrees with it.
 */
export default function Principles() {
  const state = useApi((signal) => fetchPrincipleRegistry(signal), []);
  const [category, setCategory] = useState<string>('');

  const grouped = useMemo(() => {
    if (state.status !== 'ready') return [];
    const { categories, principles } = state.data;
    return categories
      .filter((c) => !category || c.key === category)
      .map((c) => ({
        ...c,
        principles: principles.filter((p) => p.category === c.key),
      }));
  }, [state, category]);

  if (state.status === 'loading') return <Loading />;
  if (state.status === 'error') return <ErrorState error={state.error} />;

  const { total, categories } = state.data;

  return (
    <div className="principles">
      <h1>The {total} stewardship principles</h1>
      <p className="prose">
        EcoIQ does not begin with a score. It begins with a question. These are
        the {total} questions an organisation is investigated against, grouped
        into {categories.length} domains.
      </p>
      <p className="prose state__detail">
        A principle is not a metric. It is a question that evidence has to
        answer, and an organisation EcoIQ has not investigated against a
        principle is reported as unassessed — never as zero, and never as a
        pass.
      </p>

      <div className="filters" role="group" aria-label="Filter by domain">
        <button
          type="button"
          className={category === '' ? 'chip chip--on' : 'chip'}
          aria-pressed={category === ''}
          onClick={() => setCategory('')}
        >
          All {total}
        </button>
        {categories.map((c) => (
          <button
            key={c.key}
            type="button"
            className={category === c.key ? 'chip chip--on' : 'chip'}
            aria-pressed={category === c.key}
            onClick={() => setCategory(c.key)}
          >
            {c.label} <span className="chip__count">{c.principle_count}</span>
          </button>
        ))}
      </div>

      {grouped.map((group) => (
        <section key={group.key} aria-labelledby={`domain-${group.key}`}>
          <h2 id={`domain-${group.key}`}>
            {group.label}{' '}
            <span className="principles__count">{group.principles.length}</span>
          </h2>
          <ul className="principles__list">
            {group.principles.map((principle) => (
              <li key={principle.kpi_id}>
                <PrincipleRow principle={principle} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

function PrincipleRow({ principle }: { principle: Principle }) {
  return (
    <Link className="principles__item" to={`/principles/${principle.kpi_id}/`}>
      <span className="principles__num">#{principle.kpi_id}</span>
      <span className="principles__body">
        <span className="principles__title">{principle.title}</span>
        <span className="principles__question">{principle.question}</span>
      </span>
      <span className="principles__go" aria-hidden="true">&rarr;</span>
      <span className="visually-hidden">
        Read principle {principle.kpi_id}, {principle.title}
      </span>
    </Link>
  );
}
