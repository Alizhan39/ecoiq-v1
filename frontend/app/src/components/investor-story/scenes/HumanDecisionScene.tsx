/**
 * HumanDecisionScene — a still, deliberately non-interactive demonstration.
 * The three action labels (Approve / Approve with conditions / Reject) are
 * rendered as plain, disabled-looking demonstration chips, never as working
 * buttons — this is a public marketing page, not the real approval flow, so
 * nothing here can be clicked to actually decide anything. The real flow is
 * linked out to explicitly.
 */
import { Reveal } from '../../../motion'
import { humanDecision } from '../content'
import ManipulatorGlyph from '../ManipulatorGlyph'

export default function HumanDecisionScene() {
  return (
    <Reveal as="section" className="eiq-inv__scene eiq-inv__scene--decision">
      <div className="eiq-inv__glyph-row eiq-inv__glyph-row--still" aria-hidden="true">
        <ManipulatorGlyph tint="var(--eiq-muted)" />
        <ManipulatorGlyph tint="var(--eiq-muted)" />
        <span className="eiq-inv__glyph-label">Still — present, awaiting human decision</span>
      </div>
      <p className="eiq-inv__scene-copy">{humanDecision.copy}</p>

      <div className="eiq-inv__decision-card">
        <dl className="eiq-inv__decision-fields">
          {humanDecision.fields.map((f) => (
            <div key={f.label}>
              <dt>{f.label}</dt>
              <dd>{f.value}</dd>
            </div>
          ))}
        </dl>

        <div className="eiq-inv__decision-banner">{humanDecision.reviewLabel}</div>

        <div className="eiq-inv__decision-actions" role="group" aria-label="Illustrative decision options — not interactive">
          {humanDecision.actions.map((a) => (
            <span key={a} className="eiq-inv__decision-action" aria-disabled="true">
              {a}
            </span>
          ))}
        </div>
        <p className="eiq-inv__decision-note">Demonstration only — this page does not submit real decisions.</p>

        <a className="eiq-inv__link-out" href={humanDecision.linkOutCta.href}>
          {humanDecision.linkOutCta.label}
        </a>
      </div>
    </Reveal>
  )
}
