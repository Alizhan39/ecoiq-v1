/**
 * What EcoIQ does today.
 *
 * Every item is backed by a PRODUCTION module in platform_registry.agents,
 * checked against the registry before this file was written. Nothing here
 * describes a capability that does not run.
 */
const CAPABILITIES = [
  {
    title: 'Evaluate organisations',
    detail:
      'Six weighted pillars over sixteen material inputs. The composite is '
      + 'withheld unless every dimension it claims to weigh is known.',
  },
  {
    title: 'Assess evidence quality',
    detail:
      'Coverage says how much of what an assessment needs is supported. '
      + 'Confidence says how good that support is. They are separate answers.',
  },
  {
    title: 'Explain provenance',
    detail:
      'Every stored value records where it came from, and every derived value '
      + 'records the exact rows it was computed from.',
  },
  {
    title: 'Identify evidence gaps',
    detail:
      'Which inputs are missing, and which hold a value that cannot be stood '
      + 'behind — two different problems, reported separately.',
  },
  {
    title: 'Assess financing readiness',
    detail:
      'Capital-readiness assessment, gated on the same evidence rule as the '
      + 'score it rests on.',
  },
  {
    title: 'Score decision integrity',
    detail:
      'QDF assesses whether a decision is being made on defensible ground.',
  },
] as const;

export function Capabilities() {
  return (
    <section aria-labelledby="today">
      <h2 id="today">What EcoIQ does today</h2>
      <p className="prose">
        Evidence-backed decision intelligence for companies, investments and
        projects.
      </p>
      <ul className="grid grid--3 capability-list">
        {CAPABILITIES.map((capability) => (
          <li className="card" key={capability.title}>
            <h3>{capability.title}</h3>
            <p>{capability.detail}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
