import { Link } from 'react-router-dom';
import { getPlatformStats } from '@/api/platform';
import { useApi } from '@/hooks/useApi';
import { ErrorState, Loading } from '@/components/States';
import { counterDisplay } from '@/types/platform';
import { Capabilities } from '@/features/home/Capabilities';
import { HowItWorks } from '@/features/home/HowItWorks';
import { Verticals } from '@/features/home/Verticals';

/**
 * Home.
 *
 * The positioning distinguishes two things that a product page usually blurs:
 * what EcoIQ does TODAY, and what it is being built toward. Both are stated;
 * neither is dressed as the other.
 *
 * Counters come from the platform SSOT and only `is_proof` ones are eligible.
 * A counter at zero is OMITTED rather than displayed: "0 published
 * assessments" is accurate and tells a visitor nothing useful, and a proof
 * section that proves nothing is worse than no proof section.
 */
export default function Home() {
  const state = useApi(getPlatformStats, []);

  const proof =
    state.status === 'ready'
      ? state.data.counters.filter(
          // Explicit, because `(value ?? 0) > 0` reads as a coalesce and the
          // lint rule is right to reject it on sight: null and 0 mean
          // different things everywhere else in this codebase, and a reader
          // should not have to work out that here they happen to align.
          (c) => c.is_proof && c.value !== null && c.value > 0,
        )
      : [];

  return (
    <div className="home">
      <section className="prose hero">
        <h1>Make better decisions with evidence you can inspect.</h1>
        <p>
          EcoIQ assesses organisations, investments and projects — and shows
          you exactly how much evidence sits behind every answer, and how good
          that evidence is.
        </p>
        <p className="hero__direction">
          The longer aim is to make every system on Earth work better. Today
          the platform does the part below.
        </p>
        <p>
          <Link className="cta" to="/intelligence">
            Explore Intelligence
          </Link>
        </p>
      </section>

      <Capabilities />

      <section aria-labelledby="trust">
        <h2 id="trust">What sits behind an answer</h2>
        <p className="prose">
          Every assessment carries its own evidence record. When the evidence
          does not support a number, EcoIQ shows the gap instead of the number.
        </p>
        <ul className="grid grid--3">
          <li className="card">
            <h3>Evidence coverage</h3>
            <p>How much of what the assessment needs is supported.</p>
          </li>
          <li className="card">
            <h3>Confidence</h3>
            <p>How good that support is — separately from how much of it there is.</p>
          </li>
          <li className="card">
            <h3>Provenance</h3>
            <p>Where each value came from, and what it was computed from.</p>
          </li>
        </ul>

        {state.status === 'loading' ? <Loading label="Loading figures" /> : null}
        {state.status === 'error' ? <ErrorState error={state.error} /> : null}

        {/* Rendered only when there is something real to show. */}
        {proof.length > 0 ? (
          <ul className="grid grid--3 proof">
            {proof.map((counter) => (
              <li className="card" key={counter.key}>
                <div className="score__value">{counterDisplay(counter)}</div>
                <div>{counter.label}</div>
                <p className="state__detail">{counter.derivation}</p>
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      <HowItWorks />

      {/*
        A worked example, labelled as one. Placed before the pathways because
        "how does this reach a conclusion?" is the question a first visitor
        actually has, and the honest answer is a chain they can walk rather
        than a description of one.
      */}
      <section aria-labelledby="worked-example" className="worked">
        <h2 id="worked-example">See how EcoIQ reaches a conclusion</h2>
        <p className="worked__lede">
          A complete investigation, end to end: the question, the evidence, each
          source and its standing, what supports and what conflicts, the
          regulatory position, what remediation followed, and what remains
          unresolved.
        </p>
        <p className="worked__note">
          A demonstration, and labelled as one throughout. It shows how the
          evidence architecture works; it is not a published EcoIQ assessment of
          the organisation it names.
        </p>
        <p>
          <Link className="cta" to="/companies/apple/kpis/114/">
            Explore a worked investigation
          </Link>
        </p>
      </section>

      <section aria-labelledby="pathways">
        <h2 id="pathways">Where to start</h2>
        <ul className="grid grid--3">
          <li className="card">
            <h3><Link to="/intelligence">Company &amp; investment intelligence</Link></h3>
            <p>Assess an organisation and inspect the evidence behind it.</p>
          </li>
          <li className="card">
            <h3><Link to="/projects">Projects</Link></h3>
            <p>Interventions, capital and execution status.</p>
          </li>
          <li className="card">
            <h3><Link to="/tours">Eco Tours</Link></h3>
            <p>Stewardship travel, currently open for interest.</p>
          </li>
        </ul>
      </section>

      <Verticals />
    </div>
  );
}
