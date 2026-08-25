import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { fetchKpiInvestigation } from '@/api/kpi';
import { Loading } from '@/components/States';
import { EvidenceDrawer } from '@/features/kpi/EvidenceDrawer';
import { EvidenceGraph } from '@/features/kpi/EvidenceGraph';
import { KhalifahPanel } from '@/features/kpi/KhalifahPanel';
import { RemediationTimeline } from '@/features/kpi/RemediationTimeline';
import { StewardshipPrincipleHeader } from '@/features/kpi/StewardshipPrincipleHeader';
import type { KpiEvidence, KpiInvestigation as Investigation } from '@/types/kpi';
import { isInsufficient } from '@/types/kpi';

/**
 * One organisation, one principle, the whole evidence chain.
 *
 * GENERIC BY CONSTRUCTION
 * -----------------------
 * Nothing on this page knows about Apple or about principle #114. Both arrive
 * as route parameters and everything else is payload. The same route renders
 * any of the 114 principles for any company that has an assessment, and a
 * company with none gets the insufficient-evidence state rather than a zero.
 */
export default function KPIInvestigation() {
  const { slug = '', kpiId = '' } = useParams();
  const [inv, setInv] = useState<Investigation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<KpiEvidence | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setInv(null); setError(null); setSelected(null);
    fetchKpiInvestigation(slug, Number(kpiId), controller.signal)
      .then(setInv)
      .catch((err: unknown) => {
        if ((err as { name?: string }).name === 'AbortError') return;
        setError('This investigation could not be loaded.');
      });
    return () => controller.abort();
  }, [slug, kpiId]);

  const select = useCallback((e: KpiEvidence | null) => setSelected(e), []);

  if (error) return <p className="state state--error" role="alert">{error}</p>;
  if (!inv) return <Loading />;

  return (
    <article className="kpi-investigation">
      <StewardshipPrincipleHeader inv={inv} />

      {isInsufficient(inv) ? (
        /*
          §28. Absence of evidence is not negative evidence, and it is certainly
          not zero. This state exists so the two can never look alike.
        */
        <section className="kpi-empty" role="status">
          <h2>Insufficient evidence</h2>
          <p>
            EcoIQ holds no confirmed evidence linking {inv.company.name} to this
            principle. That is not a finding in the organisation's favour, and not
            one against it — it is an absence, and it is reported as one.
          </p>
          {inv.counts.excluded_from_assessment > 0 ? (
            <p>
              {inv.counts.excluded_from_assessment} item
              {inv.counts.excluded_from_assessment === 1 ? ' is' : 's are'} linked but
              not in a confirmed review state, so {inv.counts.excluded_from_assessment === 1
                ? 'it does' : 'they do'} not count toward an assessment.
            </p>
          ) : null}
        </section>
      ) : (
        <div className="kpi-investigation__body">
          <div className="kpi-investigation__main">
            <EvidenceGraph
              inv={inv}
              onSelect={select}
              selectedId={selected?.id ?? null}
            />
            {selected ? (
              <EvidenceDrawer
                evidence={selected}
                principle={inv.stewardship_principle}
                onClose={() => setSelected(null)}
              />
            ) : (
              <p className="kpi-investigation__hint">
                Select any evidence item to see its source, the claim drawn from it,
                and how it was weighed.
              </p>
            )}
            <RemediationTimeline steps={inv.remediation} />
          </div>

          <div className="kpi-investigation__aside">
            <KhalifahPanel inv={inv} />
            <AffectedParty principle={inv.stewardship_principle.title} />
          </div>
        </div>
      )}
    </article>
  );
}

/**
 * §12: whose choice is affected.
 *
 * Generic on purpose — the stakeholder set is a property of the principle, not
 * of a company. Today it is derived from the principle's category so that
 * workers, patients, borrowers or citizens can be named for other principles
 * without touching this component.
 */
export function AffectedParty({ principle }: { principle: string }) {
  return (
    <section className="affected" aria-labelledby="affected-heading">
      <h2 id="affected-heading">Whose choice is affected</h2>
      <ul>
        <li>People choosing and paying for digital goods and services</li>
        <li>Developers who reach those people through the platform</li>
        <li>Competing providers of the same goods and services</li>
      </ul>
      <p className="affected__note">
        Named because “{principle}” is only meaningful with reference to
        someone. An assessment that never says who was affected is describing a
        rule, not an impact.
      </p>
    </section>
  );
}
