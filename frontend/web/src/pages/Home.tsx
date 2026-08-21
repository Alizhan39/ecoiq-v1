import { getPlatformStats } from '@/api/platform';
import { useApi } from '@/hooks/useApi';
import { ErrorState, Loading } from '@/components/States';
import { counterDisplay } from '@/types/platform';

/**
 * Home.
 *
 * The counters come from the platform SSOT and only the ones flagged
 * `is_proof` are shown. A row count is not proof of anything: "467
 * organisations" is true about a table and false about the product, because
 * none of them has a publishable assessment.
 *
 * A counter whose value is null renders as an em dash. It is never coerced to
 * zero, because "0 verified projects" invites the reader to conclude the
 * projects failed verification when in fact none has been through it.
 */
export default function Home() {
  const state = useApi(getPlatformStats, []);

  return (
    <div>
      <section className="prose">
        <h1>Make every system on Earth work better.</h1>
        <p>
          EcoIQ is decision intelligence for physical systems. It answers one
          question: where should capital and effort go to make a system work
          better — and what evidence supports that answer.
        </p>
      </section>

      <section aria-labelledby="proof">
        <h2 id="proof">What EcoIQ can currently stand behind</h2>

        {state.status === 'loading' ? <Loading label="Loading figures" /> : null}
        {state.status === 'error' ? <ErrorState error={state.error} /> : null}

        {state.status === 'ready' ? (
          <div className="grid grid--3">
            {state.data.counters
              .filter((counter) => counter.is_proof)
              .map((counter) => (
                <div className="card" key={counter.key}>
                  <div className="score__value">{counterDisplay(counter)}</div>
                  <div>{counter.label}</div>
                  {/* The derivation is shown, not hidden. A figure a reader
                      cannot check is indistinguishable from one invented. */}
                  <p className="state__detail">{counter.derivation}</p>
                </div>
              ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}
