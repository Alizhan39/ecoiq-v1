/**
 * LearningScene — Scene 10. The manipulator visibly performs four distinct
 * actions (take → store → retrieve → deliver) as a composition rather than
 * a text list: Project A's reviewed outcome is taken into Evidence Memory,
 * then a later Project B retrieves it via a delivered evidence token. This
 * mirrors the real evidence_memory.services.memory.retrieve_relevant_
 * verified_outcomes() mechanism; both disclaimer lines are carried over
 * from that service's own docstring, not invented here.
 */
import { m } from 'framer-motion'
import { Reveal, drawPath, popIn, stagger, staggerItem } from '../../../motion'
import { learning } from '../content'
import ManipulatorGlyph from '../ManipulatorGlyph'

export default function LearningScene() {
  return (
    <Reveal as="section" className="eiq-inv__scene eiq-inv__scene--learning">
      <div className="eiq-inv__glyph-row" aria-hidden="true">
        <span className="eiq-inv__glyph-label">Learning Retrieval</span>
      </div>
      <p className="eiq-inv__scene-copy">{learning.copy}</p>
      <p className="eiq-inv__supporting-line">{learning.supportingLine}</p>

      <m.div
        className="eiq-inv__learning-composition"
        variants={stagger(0.18)}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.2 }}
      >
        {/* Project A → take/store → Evidence Memory */}
        <m.div className="eiq-inv__learning-node" variants={staggerItem}>
          <div className="eiq-inv__learning-node-label">{learning.projectA.label}</div>
          <div className="eiq-inv__learning-node-detail">{learning.projectA.detail}</div>
          <span className="eiq-inv__flag">Real project, illustrative outcome</span>
        </m.div>

        <m.div className="eiq-inv__learning-link" variants={staggerItem}>
          <svg className="eiq-inv__learning-link-svg" viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden="true">
            <m.path d="M0 12 H100" variants={drawPath({ duration: 0.5 })} fill="none" stroke="var(--eiq-accent)" strokeWidth="1.5" />
            <m.circle cx="50" cy="12" r="3" fill="var(--eiq-accent)" variants={popIn({ delay: 0.3 }, 0.3)} />
          </svg>
          <span className="eiq-inv__learning-action">{learning.actions.take} → {learning.actions.store}</span>
        </m.div>

        <m.div className="eiq-inv__learning-vault" variants={staggerItem}>
          <ManipulatorGlyph tint="var(--eiq-accent)" size={40} />
          <div className="eiq-inv__learning-vault-label">{learning.memoryStep.label}</div>
          <div className="eiq-inv__learning-vault-detail">{learning.memoryStep.detail}</div>
        </m.div>

        {/* Evidence Memory → retrieve/deliver → Project B */}
        <m.div className="eiq-inv__learning-link" variants={staggerItem}>
          <svg className="eiq-inv__learning-link-svg" viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden="true">
            <m.path d="M0 12 H100" variants={drawPath({ duration: 0.5 })} fill="none" stroke="var(--eiq-gold)" strokeWidth="1.5" />
            <m.circle cx="50" cy="12" r="3" fill="var(--eiq-gold)" variants={popIn({ delay: 0.3 }, 0.3)} />
          </svg>
          <span className="eiq-inv__learning-action">{learning.actions.retrieve} → {learning.actions.deliver}</span>
        </m.div>

        <m.div className="eiq-inv__learning-node eiq-inv__learning-node--b" variants={staggerItem}>
          <div className="eiq-inv__learning-node-label">{learning.projectB.label}</div>
          <div className="eiq-inv__learning-node-detail">{learning.projectB.detail}</div>
          <span className="eiq-inv__flag">Illustrative</span>
          <span className="eiq-inv__learning-retrieved-tag">{learning.retrievedTag}</span>
        </m.div>
      </m.div>

      <ul className="eiq-inv__disclaimers">
        {learning.disclaimers.map((d) => (
          <li key={d}>{d}</li>
        ))}
      </ul>
    </Reveal>
  )
}
