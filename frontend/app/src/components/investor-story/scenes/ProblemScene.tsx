/**
 * ProblemScene — "The world as it is" + "See what is wrong," combined into
 * one scene (audited case: the real Almaty Clean Heating Pilot project
 * anchor — region/status are its real field values; no financial data
 * exists for it, so none is shown here).
 */
import { m } from 'framer-motion'
import { Reveal, stagger, staggerItem, hoverLift } from '../../../motion'
import { problem, project } from '../content'
import ManipulatorGlyph from '../ManipulatorGlyph'

export default function ProblemScene() {
  return (
    <Reveal as="section" className="eiq-inv__scene eiq-inv__scene--problem">
      <div className="eiq-inv__glyph-row" aria-hidden="true">
        <ManipulatorGlyph tint="var(--eiq-muted)" />
        <ManipulatorGlyph tint="var(--eiq-muted)" />
        <span className="eiq-inv__glyph-label">Detect — dormant until a case is isolated</span>
      </div>

      <div className="eiq-inv__eyebrow eiq-eyebrow">{problem.eyebrow}</div>
      <h2 className="eiq-inv__lines">
        {problem.lines.map((l) => (
          <span key={l}>{l}</span>
        ))}
      </h2>
      <p className="eiq-inv__lede">{problem.lede}</p>

      <div className="eiq-inv__cta-row">
        <a className="eiq-btn eiq-btn--primary" href={problem.primaryCta.href}>
          {problem.primaryCta.label}
        </a>
        <a className="eiq-btn eiq-btn--secondary" href={problem.secondaryCta.href}>
          {problem.secondaryCta.label}
        </a>
      </div>

      <m.div className="eiq-inv__case" variants={stagger(0.1)} initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.3 }}>
        <m.div variants={staggerItem} className="eiq-inv__case-head">
          <div className="eiq-inv__case-title">{project.name}</div>
          <div className="eiq-inv__case-meta">{project.region} · {project.status}</div>
        </m.div>
        <m.div variants={staggerItem} whileHover={hoverLift.hover} className="eiq-inv__case-card">
          <div className="eiq-inv__case-label">Current use</div>
          <div className="eiq-inv__case-value">{project.currentUse}</div>
        </m.div>
        <m.div variants={staggerItem} whileHover={hoverLift.hover} className="eiq-inv__case-card">
          <div className="eiq-inv__case-label">Intended human service</div>
          <div className="eiq-inv__case-value">{project.intendedService}</div>
        </m.div>
        <m.div variants={staggerItem} whileHover={hoverLift.hover} className="eiq-inv__case-card eiq-inv__case-card--concern">
          <div className="eiq-inv__case-label">Identified concern</div>
          <div className="eiq-inv__case-value">{project.identifiedConcern}</div>
        </m.div>
      </m.div>
    </Reveal>
  )
}
