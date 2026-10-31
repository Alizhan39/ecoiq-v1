import { useState } from 'react';
import { getCompany, listCompanies } from '@/api/companies';
import { useApi } from '@/hooks/useApi';
import { EmptyState, ErrorState, Loading } from '@/components/States';
import { Assessment } from '@/features/intelligence/Assessment';
import { Picker } from '@/features/intelligence/Picker';

/**
 * Intelligence.
 *
 * The question this answers today: what do we know about this organisation,
 * how reliable is it, and what should give a decision-maker pause.
 *
 * It is built entirely on capability that exists. There is no energy,
 * aviation, cities or nature calculator here, because no backend implements
 * one — and a calculator that returns invented numbers would be worse than an
 * absent feature by exactly the margin this programme has spent itself closing.
 */
export default function Intelligence() {
  const [selected, setSelected] = useState<string | null>(null);

  const list = useApi((signal) => listCompanies({}, signal), []);
  const detail = useApi(
    (signal) =>
      selected ? getCompany(selected, signal) : Promise.resolve(null),
    [selected],
  );

  return (
    <div className="intelligence">
      <header className="prose">
        <h1>Intelligence</h1>
        <p>
          Assess an organisation, and see exactly how much evidence sits behind
          the answer.
        </p>
      </header>

      <div className="intelligence__layout">
        <aside className="intelligence__picker">
          {list.status === 'loading' ? <Loading label="Loading organisations" /> : null}
          {list.status === 'error' ? <ErrorState error={list.error} /> : null}
          {list.status === 'ready' ? (
            <Picker
              companies={list.data.results}
              selected={selected}
              onSelect={setSelected}
            />
          ) : null}
        </aside>

        <div className="intelligence__detail">
          {selected === null ? (
            <EmptyState>
              Choose an organisation to see its evidence, risks and assessment.
            </EmptyState>
          ) : null}

          {selected !== null && detail.status === 'loading' ? <Loading /> : null}
          {selected !== null && detail.status === 'error' ? (
            <ErrorState error={detail.error} />
          ) : null}
          {detail.status === 'ready' && detail.data !== null ? (
            <Assessment company={detail.data} />
          ) : null}
        </div>
      </div>
    </div>
  );
}
