import { Link, useParams } from 'react-router-dom';
import { getAssessment } from '@/api/companies';
import type { AsyncState } from '@/hooks/useApi';
import { useApi } from '@/hooks/useApi';
import { fetchCompanyPrinciples } from '@/api/principles';
import { ErrorState, Loading } from '@/components/States';
import { EvidenceSummary, ScoreDisplay } from '@/components/EvidenceState';
import { metric } from '@/types/assessment';
import type {
  Assessment, Controversy, DecisionIntegrity, Ethics, EvidenceGaps,
  FinancingReadiness, Pillar, Shariah,
} from '@/types/assessment';
import type { CompanyPrincipleMatrix } from '@/types/principles';
import { hasBeenInvestigated } from '@/types/principles';

/**
 * One organisation.
 *
 * ORDER IS THE ARGUMENT
 * ---------------------
 * Everything above Material evidence answers *can I trust this*. Everything
 * below answers *what does it say*. Evidence precedes conclusion here as it
 * does in the Intelligence flow, because a reader who meets the score first
 * has already formed a view by the time they reach its basis.
 *
 * WHAT IS NOT HERE
 * ----------------
 * Four panels from the server-rendered page were audited out
 * (docs/product/COMPANY_PAGE_PANELS.md): matched financing pathways, data
 * status, watchlist — all behind sign-in — and the stock strip, removed.
 *
 * Every panel below renders only if the API sent it, and the API sends none of
 * them unless the assessment is publishable. There is no "empty ethics panel"
 * state, because an empty panel beside a real one is still a claim.
 */
export default function CompanyDetail() {
  const { slug } = useParams<{ slug: string }>();
  const state = useApi(
    (signal) => getAssessment(slug ?? '', signal),
    [slug],
  );

  if (state.status === 'loading') return <Loading label="Loading assessment" />;
  if (state.status === 'error') return <ErrorState error={state.error} />;

  const a: Assessment = state.data;

  return (
    <article className="prose">
      <header>
        <h1>{a.name}</h1>
        <p className="state__detail">
          {[a.sector, a.country].filter(Boolean).join(' · ') || '—'}
        </p>
      </header>

      {/* `exactOptionalPropertyTypes` is on, so an absent note is spread
          away rather than passed as undefined — the prop is optional, not
          optional-or-undefined, and the compiler is right to insist. */}
      <ScoreDisplay
        company={a}
        {...(a.evidence_note ? { note: a.evidence_note.detail } : {})}
      />
      <EvidenceSummary coverage={a.evidence_coverage} confidence={a.confidence} />

      {a.material_evidence ? <MaterialEvidence pillars={a.material_evidence} /> : null}
      {a.decision_risks ? <DecisionRisks {...a.decision_risks} /> : null}
      {a.ethics ? <EthicsPanel ethics={a.ethics} /> : null}
      {a.shariah ? <ShariahPanel shariah={a.shariah} /> : null}
      {a.financing_readiness
        ? <FinancingPanel financing={a.financing_readiness} /> : null}

      <Gaps gaps={a.evidence_gaps} published={a.score_status === 'PUBLISHED'} />

      <StewardshipKpiPreview slug={slug ?? ''} />

      <section aria-labelledby="methodology">
        <h2 id="methodology">Provenance and methodology</h2>
        <p>
          Every value above records where it came from, and every derived value
          records the specific provenance rows it was computed from. An
          assessment is published only when every material input is supported by
          evidence EcoIQ can stand behind.
        </p>
        <p>
          <a href="/trust/">How EcoIQ handles evidence</a>
        </p>
      </section>
    </article>
  );
}


function MaterialEvidence({ pillars }: { pillars: Pillar[] }) {
  return (
    <section aria-labelledby="material">
      <h2 id="material">Material evidence</h2>
      <dl className="evidence">
        {pillars.map((pillar) => (
          <div className="evidence__item" key={pillar.key}>
            <dt>{pillar.label}</dt>
            {/* An unassessed pillar is an em dash. Rendering it as 0 would
                draw a bar at the floor and read as "scored zero". */}
            <dd>{metric(pillar.value)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}


function DecisionRisks({
  integrity, controversies,
}: { integrity: DecisionIntegrity | null; controversies: Controversy[] }) {
  return (
    <section aria-labelledby="risks">
      <h2 id="risks">Decision risks</h2>

      {integrity ? (
        <dl className="evidence">
          <div className="evidence__item">
            <dt>Decision integrity</dt>
            <dd>{metric(integrity.score)}</dd>
          </div>
          <div className="evidence__item">
            <dt>Risk level</dt>
            <dd>{integrity.risk_level || '—'}</dd>
          </div>
          <div className="evidence__item">
            <dt>Evidence status</dt>
            <dd>{integrity.evidence_status || '—'}</dd>
          </div>
        </dl>
      ) : null}

      {integrity?.red_line_breached ? (
        <p className="state state--error" role="alert">
          A red line has been breached. This is a disqualifying finding, not a
          score adjustment.
        </p>
      ) : null}

      {controversies.length > 0 ? (
        <ul>
          {controversies.map((c) => (
            <li key={c.title}>
              <strong>{c.title}</strong>{' '}
              <span className="state__detail">
                {c.category} · {c.severity} · {c.status}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="state__detail">
          {/* "None recorded" — not "none exist". A check nobody ran is not a
              pass, and this page must not imply one. */}
          No controversies are recorded. That is a statement about what EcoIQ
          holds, not a finding that none exist.
        </p>
      )}
    </section>
  );
}


function EthicsPanel({ ethics }: { ethics: Ethics }) {
  return (
    <section aria-labelledby="ethics">
      <h2 id="ethics">Ethics and governance</h2>
      <dl className="evidence">
        <div className="evidence__item">
          <dt>Net ethical impact</dt>
          <dd>{metric(ethics.net_ethical_impact)}</dd>
        </div>
        <div className="evidence__item">
          <dt>Transition stewardship</dt>
          <dd>{metric(ethics.transition_stewardship)}</dd>
        </div>
        <div className="evidence__item">
          <dt>Regenerative value</dt>
          <dd>{metric(ethics.regenerative_value)}</dd>
        </div>
      </dl>

      {ethics.key_harms.length > 0 ? (
        <>
          <h3>Recorded harms</h3>
          <ul>{ethics.key_harms.map((h) => <li key={h}>{h}</li>)}</ul>
        </>
      ) : null}

      <p className="state__detail">
        {/* Named so it cannot be mistaken for Evidence Confidence above. */}
        Engine confidence: {ethics.engine_confidence || '—'} · Formula{' '}
        {ethics.formula_version || '—'} ·{' '}
        {ethics.analyst_reviewed
          ? 'reviewed by an analyst'
          : 'not reviewed by an analyst'}
      </p>
    </section>
  );
}


function ShariahPanel({ shariah }: { shariah: Shariah }) {
  return (
    <section aria-labelledby="shariah">
      <h2 id="shariah">Shariah eligibility screen</h2>
      {/* The disclaimer renders WITH the result, above it, every time. A
          methodology result separated from the statement that it is not a
          ruling becomes, to a reader, a ruling. The audit kept this panel on
          exactly that condition. */}
      <p className="state state--note">{shariah.disclaimer}</p>
      <dl className="evidence">
        <div className="evidence__item">
          <dt>Overall</dt>
          <dd>{shariah.overall_result || '—'}</dd>
        </div>
        <div className="evidence__item">
          <dt>Business activity</dt>
          <dd>{shariah.business_activity_result || '—'}</dd>
        </div>
        <div className="evidence__item">
          <dt>Financial ratios</dt>
          <dd>{shariah.financial_ratio_result || '—'}</dd>
        </div>
        <div className="evidence__item">
          <dt>Data completeness</dt>
          <dd>
            {shariah.data_completeness_pct === null
              ? '—' : `${shariah.data_completeness_pct}%`}
          </dd>
        </div>
      </dl>
      <p className="state__detail">
        Methodology: {shariah.methodology || '—'} · {shariah.review_status || '—'}
      </p>
    </section>
  );
}


function FinancingPanel({ financing }: { financing: FinancingReadiness }) {
  return (
    <section aria-labelledby="financing">
      <h2 id="financing">Financing readiness</h2>
      <p className="state__detail">
        {/* Readiness, not a shortlist. The matched-pathway panel names
            instruments and moved behind sign-in — that is closer to advice. */}
        What this organisation could meet, not a recommendation of any
        particular instrument.
      </p>
      <dl className="evidence">
        <div className="evidence__item">
          <dt>Readiness</dt>
          <dd>{metric(financing.readiness)}</dd>
        </div>
        <div className="evidence__item">
          <dt>Tier</dt>
          <dd>{financing.tier || '—'}</dd>
        </div>
        <div className="evidence__item">
          <dt>Evidence completeness</dt>
          <dd>{metric(financing.evidence_completeness)}</dd>
        </div>
      </dl>

      {financing.missing_requirements.length > 0 ? (
        <>
          <h3>Not yet met</h3>
          <ul>
            {financing.missing_requirements.map((r) => <li key={r}>{r}</li>)}
          </ul>
        </>
      ) : null}
    </section>
  );
}


function Gaps({ gaps, published }: { gaps: EvidenceGaps; published: boolean }) {
  return (
    <section aria-labelledby="gaps">
      <h2 id="gaps">Evidence gaps</h2>
      <p>
        {gaps.covered} of {gaps.required} material inputs are supported by
        evidence EcoIQ can stand behind.
      </p>

      {gaps.unevidenced.length > 0 ? (
        <p className="state__detail">
          {gaps.unevidenced.length} input(s) hold a value with seeded or legacy
          provenance, which does not count as evidence. EcoIQ holds a number for
          these; it cannot stand behind it.
        </p>
      ) : null}

      {!published && gaps.reasons.length > 0 ? (
        <ul>{gaps.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
      ) : null}

      {gaps.missing.length > 0 ? (
        <details>
          <summary>{gaps.missing.length} input(s) with nothing recorded</summary>
          <ul>{gaps.missing.map((m) => <li key={m}>{m}</li>)}</ul>
        </details>
      ) : null}
    </section>
  );
}

/**
 * The entry point into the 114-principle framework (§21).
 *
 * WHAT CHANGED, AND WHY IT COULD
 * ------------------------------
 * This was hard-coded to principle #114 — the one principle with a worked
 * corpus — with a note that rendering anything wider "would mean fetching every
 * principle's evidence to show one line each". That objection was correct
 * against the endpoints that existed then.
 *
 * `/api/v2/companies/<slug>/principles/` now returns all 114 states in one
 * request and a fixed number of queries, so the doorway can show what has
 * actually been investigated instead of one hardcoded link.
 *
 * STILL A DOORWAY, NOT A VERDICT
 * ------------------------------
 * It lists the principles someone has looked at and sends the reader to the
 * investigation for the evidence. It does not render a verdict here, because a
 * verdict on a page that has not loaded the evidence behind it is exactly the
 * claim this product refuses to make.
 *
 * THE EMPTY STATE IS THE HONEST ONE
 * ---------------------------------
 * With no assessments this says so, and says it as a fact about EcoIQ's
 * coverage. It does not hide the section: a missing section reads as "nothing
 * to say here" when the true statement is "nobody has investigated this yet".
 */
function StewardshipKpiPreview({ slug }: { slug: string }) {
  const state = useApi((signal) => fetchCompanyPrinciples(slug, signal), [slug]);

  return (
    <section aria-labelledby="stewardship-kpis" className="kpi-preview">
      <h2 id="stewardship-kpis">Stewardship principles</h2>
      <p className="kpi-preview__lede">
        EcoIQ assesses organisations against 114 stewardship principles. Each is
        evidence-led: a principle with no confirmed evidence is reported as
        unassessed rather than scored.
      </p>
      <StewardshipKpiBody slug={slug} state={state} />
    </section>
  );
}

function StewardshipKpiBody(
  { slug, state }: { slug: string; state: AsyncState<CompanyPrincipleMatrix> },
) {
  if (state.status === 'loading') return <Loading />;
  if (state.status === 'error') {
    return <ErrorState error={state.error} />;
  }

  const { summary, principles } = state.data;
  const investigated = principles.filter(hasBeenInvestigated);

  if (investigated.length === 0) {
    return (
      <p className="kpi-preview__empty">
        None of the {summary.total} principles has been investigated for this
        organisation yet. That is a statement about EcoIQ&rsquo;s coverage, not a
        finding about the organisation.
      </p>
    );
  }

  return (
    <>
      <p className="kpi-preview__coverage">
        {summary.assessed} of {summary.total} principles investigated
        {summary.not_assessed > 0
          ? `; ${summary.not_assessed} not yet looked at`
          : ''}
        .
      </p>
      <ul className="kpi-preview__list">
        {investigated.map((principle) => (
          <li key={principle.kpi_id}>
            {/* Trailing slash: Django owns this path. The slashless form now
                redirects rather than 404ing, but linking to the canonical URL
                avoids making every reader pay for the extra hop. */}
            <Link
              className="kpi-preview__item"
              to={`/companies/${slug}/kpis/${principle.kpi_id}/`}
            >
              <span className="kpi-preview__num">#{principle.kpi_id}</span>
              <span className="kpi-preview__title">{principle.title}</span>
              <span className="kpi-preview__state">{principle.state_label}</span>
              {principle.has_material_conflict ? (
                <span className="kpi-preview__flag">
                  Material regulatory conflict
                </span>
              ) : null}
              {principle.remediation_step_count > 0 ? (
                <span className="kpi-preview__flag kpi-preview__flag--muted">
                  Remediation recorded
                </span>
              ) : null}
              <span className="kpi-preview__go" aria-hidden="true">
                Investigate &rarr;
              </span>
              <span className="visually-hidden">
                Investigate principle {principle.kpi_id}, {principle.title}, for
                this organisation
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
