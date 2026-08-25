import type { KpiInvestigation } from '@/types/kpi';
import { CONFIDENCE_LABEL } from '@/types/kpi';

/**
 * The investigation header: what is being tested, and where the answer landed.
 *
 * DELIBERATELY NOT A SCORE. The first thing a reader meets is the QUESTION,
 * because a number answers "how much?" when the useful question is "what did
 * we observe, and how sure are we?". The verdict follows, in words.
 *
 * NO SACRED SOURCE APPEARS HERE. The operational principle is public; the
 * source layer behind it is internal (docs/governance-principles-surah-map.md)
 * and the API never sends it. This component could not render it if it tried.
 */
export function StewardshipPrincipleHeader({ inv }: { inv: KpiInvestigation }) {
  const { stewardship_principle: p, assessment: a, company } = inv;
  const tone = verdictTone(a.verdict);

  return (
    <header className="kpi-header">
      <div className="kpi-header__eyebrow">
        <span className="kpi-header__company">{company.name}</span>
        <span className="kpi-header__sep" aria-hidden="true">·</span>
        <span className="kpi-header__id">Stewardship principle #{p.kpi_id}</span>
      </div>

      <h1 className="kpi-header__title">{p.title}</h1>
      <p className="kpi-header__question">{p.question}</p>

      <dl className="kpi-header__verdict">
        <div className={`kpi-verdict kpi-verdict--${tone}`}>
          <dt>Assessment</dt>
          {/* The tone is also stated in text, never colour alone (§32). */}
          <dd data-tone={tone}>{a.verdict_label}</dd>
        </div>
        <div className="kpi-verdict kpi-verdict--muted">
          <dt>Confidence</dt>
          <dd>{CONFIDENCE_LABEL[a.confidence]}</dd>
        </div>
        <div className="kpi-verdict kpi-verdict--muted">
          <dt>Evidence</dt>
          <dd>
            {inv.counts.confirmed} confirmed
            {inv.counts.excluded_from_assessment > 0
              ? ` · ${inv.counts.excluded_from_assessment} excluded` : ''}
          </dd>
        </div>
      </dl>

      {a.is_demo ? (
        <p className="kpi-header__demo" role="note">
          Demonstration corpus. These are real, citable public sources, assembled to
          demonstrate the assessment architecture — not output of EcoIQ's ingestion
          and review pipeline, and not independently verified intelligence.
        </p>
      ) : null}
    </header>
  );
}

/** Verdict → tone. Kept in one place so no surface invents its own mapping. */
export function verdictTone(v: string): 'support' | 'conflict' | 'mixed' | 'unknown' {
  if (v === 'strong_support' || v === 'support') return 'support';
  if (v === 'conflict') return 'conflict';
  if (v === 'mixed' || v === 'mixed_material_conflict') return 'mixed';
  return 'unknown';
}
