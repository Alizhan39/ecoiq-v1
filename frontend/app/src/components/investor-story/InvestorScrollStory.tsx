/**
 * InvestorScrollStory — "Capital meets verified purpose."
 *
 * A connected sequence of scroll-reveal scenes (not a second pinned
 * cinematic stage) walking Problem → Evidence → Resource Purpose Review →
 * Better Way → Investment Mandate → Human Decision → Capital Guardian →
 * Expected vs Actual → Learning → the Philosophical Hand bridge → Final
 * Joining. Every primitive used (Reveal, stagger, staggerItem, popIn,
 * drawPath, hoverLift) is exactly Motion Library v1 — nothing new.
 */
import { Reveal } from '../../motion'
import { bridge } from './content'
import ProblemScene from './scenes/ProblemScene'
import EvidenceScene from './scenes/EvidenceScene'
import ResourcePurposeReviewScene from './scenes/ResourcePurposeReviewScene'
import BetterWayScene from './scenes/BetterWayScene'
import InvestmentMandateScene from './scenes/InvestmentMandateScene'
import HumanDecisionScene from './scenes/HumanDecisionScene'
import CapitalGuardianScene from './scenes/CapitalGuardianScene'
import ExpectedVsActualScene from './scenes/ExpectedVsActualScene'
import LearningScene from './scenes/LearningScene'
import PhilosophicalHandScene from './scenes/PhilosophicalHandScene'
import FinalJoiningScene from './scenes/FinalJoiningScene'

export default function InvestorScrollStory() {
  return (
    <div className="eiq-inv">
      <Reveal as="section" className="eiq-inv__intro">
        <div className="eiq-eyebrow">EcoIQ Investor Story</div>
        <h2 className="eiq-inv__headline">{bridge.headline}</h2>
        <p className="eiq-inv__intro-copy">
          EcoIQ helps investors and project owners move from evidence to better decisions,
          transparent deployment, and measurable real-world outcomes.
        </p>
      </Reveal>

      <ProblemScene />
      <EvidenceScene />
      <ResourcePurposeReviewScene />
      <BetterWayScene />
      <InvestmentMandateScene />
      <HumanDecisionScene />
      <CapitalGuardianScene />
      <ExpectedVsActualScene />
      <LearningScene />
      <PhilosophicalHandScene />
      <FinalJoiningScene />
    </div>
  )
}
