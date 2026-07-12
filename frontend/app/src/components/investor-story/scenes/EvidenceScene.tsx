/**
 * EvidenceScene — "Start with evidence." Column headers and status/review
 * vocabulary (verification_status, review_tier) are the real EvidenceMemory
 * field values; the specific claims/confidence numbers are illustrative
 * examples (flagged per-row in content.ts).
 */
import { m } from 'framer-motion'
import { Reveal, stagger, staggerItem } from '../../../motion'
import { evidence } from '../content'
import ManipulatorGlyph from '../ManipulatorGlyph'

export default function EvidenceScene() {
  return (
    <Reveal as="section" className="eiq-inv__scene eiq-inv__scene--evidence">
      <div className="eiq-inv__glyph-row" aria-hidden="true">
        <ManipulatorGlyph tint="var(--eiq-accent)" />
        <span className="eiq-inv__glyph-label">Connect — Evidence Intelligence</span>
      </div>
      <p className="eiq-inv__scene-copy">{evidence.copy}</p>

      <div className="eiq-inv__evidence-table" role="table" aria-label="Evidence claims and their verification status">
        <div className="eiq-inv__evidence-row eiq-inv__evidence-row--head" role="row">
          <span role="columnheader">Claim</span>
          <span role="columnheader">Source</span>
          <span role="columnheader">Status</span>
          <span role="columnheader">Confidence</span>
          <span role="columnheader">Review</span>
        </div>
        <m.div variants={stagger(0.1)} initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.3 }}>
          {evidence.rows.map((row) => (
            <m.div key={row.claim} variants={staggerItem} className="eiq-inv__evidence-row" role="row">
              <span role="cell">
                {row.claim}
                {row.illustrative && <span className="eiq-inv__flag">Illustrative</span>}
              </span>
              <span role="cell" className="eiq-num">{row.source}</span>
              <span role="cell">
                <span className={`eiq-inv__status eiq-inv__status--${row.status}`}>{row.status.replace('_', ' ')}</span>
              </span>
              <span role="cell" className="eiq-num">{row.confidence}</span>
              <span role="cell" className="eiq-num">{row.review.replace('_', ' ')}</span>
            </m.div>
          ))}
        </m.div>
      </div>
    </Reveal>
  )
}
