/**
 * EcoIQ Investor Scroll Story — content.
 *
 * Every field below is one of: a REAL concept/vocabulary term audited
 * directly against the live backend (evidence_memory, capital_guardian
 * services), or an ILLUSTRATIVE example value with no live backend call
 * behind it in this pass. The `illustrative` flags are load-bearing — the
 * UI renders a visible "Illustrative" label wherever `true`. Nothing here
 * is a fabricated platform-scale metric (no totals, no user counts).
 *
 * Audited sources:
 *  - evidence_memory/models.py (EvidenceMemory: verification_status,
 *    review_tier, confidence, source_type)
 *  - capital_guardian/services/resource_purpose_review.py (stewardship
 *    questions + Almaty alternative pathways — real content for the
 *    'almaty-clean-heating-pilot-200-homes' project specifically)
 *  - capital_guardian/services/capital_trace.py (capital_protection_chain_for_entry
 *    — real lifecycle stage names)
 *  - capital_guardian/services/red_flag_engine.py (real deterministic rule concept)
 *  - waste_to_value_capital_allocation_engine/models.py + capital_guardian/services/
 *    execution_monitoring.py (expected_vs_actual field shape, real 'NOT YET REPORTED'
 *    literal)
 *
 * The Almaty project itself (gold_intelligence's real anchor row) has no
 * populated financial figures — every number in this file is illustrative,
 * never presented as this project's actual reported data.
 */

export const project = {
  name: 'Almaty Clean Heating Pilot — 200 Homes',
  region: 'Almaty region', // real field value on the project anchor
  status: 'Exploration', // real field value on the project anchor
  currentUse: 'Coal burned for household warmth',
  intendedService: 'Safe and affordable heating',
  identifiedConcern: 'Energy inefficiency, avoidable cost, pollution, and weak execution visibility',
}

export const problem = {
  eyebrow: 'The World As It Is',
  lines: [
    'The world has capital.',
    'The world has resources.',
    'The world has problems worth solving.',
  ],
  lede: 'But capital and purpose do not always meet efficiently.',
  primaryCta: { label: 'Explore how EcoIQ works', href: '/platform/' },
  secondaryCta: { label: 'Join as a Capital Partner', href: 'mailto:alizhan@ecoiq.uk?subject=Capital+Partner+Enquiry' },
}

export interface EvidenceRow {
  claim: string
  source: string
  status: string
  confidence: string
  review: string
  illustrative: boolean
}

// status/review values are the REAL EvidenceMemory vocabulary
// (verification_status, review_tier) — the specific claims/confidence
// numbers are illustrative examples, not this project's real evidence.
export const evidence: { copy: string; rows: EvidenceRow[] } = {
  copy: 'Trust does not begin with a promise. It begins with evidence.',
  rows: [
    {
      claim: 'Coal heating is the dominant method in the pilot area',
      source: 'harvester_evidence',
      status: 'verified',
      confidence: '82%',
      review: 'human_reviewed',
      illustrative: true,
    },
    {
      claim: 'Retrofit demand exists among pilot-area households',
      source: 'manual',
      status: 'requires_review',
      confidence: 'Not yet assessed',
      review: 'uploaded',
      illustrative: true,
    },
    {
      claim: 'Regional grid capacity supports electrification at scale',
      source: 'agent_output',
      status: 'pending',
      confidence: 'Not yet assessed',
      review: 'system_checked',
      illustrative: true,
    },
  ],
}

// Compact node form — term + one-line meaning preserved verbatim in full
// (nothing deleted), just presented as a dense grid of short signals rather
// than seven stacked paragraphs. Terms kept consistently Arabic (matching
// resource_purpose_review.py's own framing) rather than mixing in English
// glosses for two of the seven.
export const stewardshipQuestions = [
  { term: 'Amanah', short: 'Trust', body: 'Is this resource held as a trust, used responsibly for its intended purpose?' },
  { term: 'Mizan', short: 'Balance', body: 'Is there balance between cost, benefit, harm, and who carries each?' },
  { term: 'Adl', short: 'Justice', body: 'Is the arrangement just to everyone affected, not only the party with more power?' },
  { term: 'Maslahah', short: 'Public benefit', body: 'Does this serve genuine public benefit, not just private gain?' },
  { term: 'Israf', short: 'Waste', body: 'Is anything being wasted or used beyond genuine need?' },
  { term: 'Darar', short: 'Harm', body: 'What harm is created today, and is it being prevented or merely priced?' },
  { term: 'Khilafah', short: 'Stewardship', body: 'Is this use consistent with responsible stewardship, accountable and reviewable later?' },
]

export const resourcePurposeReview = {
  eyebrow: 'Resource Purpose Review',
  dominantMessage: 'Before capital moves, EcoIQ asks whether the project should exist in this form at all.',
  copy: 'Before optimising a system, question whether the resource is being used for the right purpose.',
  pathway: ['Coal', 'Transport', 'Combustion', 'Heat', 'Cost', 'Pollution', 'Ash / Loss'],
  decisionFlow: ['Resource', 'Purpose review', 'Stewardship questions'],
  outcomes: [
    { label: 'Proceed', tone: 'eligible' as SafetyState, detail: 'Stewardship questions raise no material concern' },
    { label: 'Reconsider', tone: 'conditional' as SafetyState, detail: 'Some questions surface a real but addressable tension' },
    { label: 'Block', tone: 'blocked' as SafetyState, detail: 'A question surfaces harm that isn’t offset by the benefit' },
  ],
  closingCopy: 'Better does not only mean cheaper. Better means more balanced, more transparent, and more accountable.',
}

export type SafetyState = 'eligible' | 'conditional' | 'blocked'

export interface PathwayOption {
  id: string
  label: string
  description: string
  state: SafetyState
  note: string
}

// The five real alternative-pathway categories + the blocked coal-byproduct
// option are audited as real content in resource_purpose_review.py's Almaty
// profile. Feasibility/risk labels below are illustrative qualitative
// judgments, not computed financial results.
export const betterWay = {
  copy: "Don't guess. Compare the paths. Find the better way.",
  supportingLine: 'Based on currently entered evidence and assumptions.',
  baseline: { label: 'Baseline', description: 'Continue current coal heating' },
  options: [
    { id: 'a', label: 'Insulation & demand reduction', description: 'Reduce heat loss before adding new supply', state: 'eligible', note: 'Low disruption, low risk' },
    { id: 'b', label: 'Heat-pump retrofit', description: 'Replace coal appliance with an electric heat pump', state: 'eligible', note: 'Requires grid capacity check' },
    { id: 'c', label: 'Electric heating', description: 'Direct electric resistance heating', state: 'conditional', note: 'Higher running cost — conditional on tariff' },
    { id: 'd', label: 'District heating', description: 'Connect to a shared district heat network', state: 'conditional', note: 'Depends on network proximity' },
    { id: 'e', label: 'Grid upgrade & electrification', description: 'Upgrade local grid ahead of full electrification', state: 'conditional', note: 'Longer implementation time' },
    { id: 'f', label: 'Hybrid solution', description: 'Combine insulation with partial electrification', state: 'eligible', note: 'Balances cost and disruption' },
    { id: 'g', label: 'Coal by-product reuse', description: 'Reuse coal ash/by-products on site', state: 'blocked', note: 'Blocked — does not address the identified harm' },
  ] as PathwayOption[],
}

export const mandate = {
  illustrative: true,
  dominantMessage: 'Even a good project must fit the investor’s purpose, risk, and constraints.',
  title: '£50M Climate Infrastructure Mandate',
  sublabel: 'Illustrative example — EcoIQ does not yet have a live investment-mandate matching system',
  // Headline criteria carry the 3-second read; the rest are preserved in
  // full below as secondary detail, not deleted.
  headlineCriteria: [
    { label: 'Region', value: 'Central Asia' },
    { label: 'Sector', value: 'Residential heating infrastructure' },
    { label: 'Risk tolerance', value: 'Moderate' },
    { label: 'Return target', value: '8–12% IRR' },
  ],
  secondaryCriteria: [
    { label: 'Project stage', value: 'Pilot to early scale' },
    { label: 'Evidence threshold', value: 'Human-reviewed or better' },
    { label: 'Impact criteria', value: 'Verified emissions and cost reduction' },
    { label: 'Exclusions', value: 'No new coal infrastructure' },
    { label: 'Investment horizon', value: '7–10 years' },
  ],
  // One overall verdict — derived honestly from the six checks below (4
  // confirmed, 2 still requiring review), not a separate invented figure.
  overallFit: {
    verdict: 'Conditional' as const,
    detail: '4 of 6 fit dimensions confirmed — governance and financial review still required.',
  },
  fitChecks: [
    { label: 'Mandate fit', note: 'Region and sector match' },
    { label: 'Evidence fit', note: 'Meets the human-reviewed threshold' },
    { label: 'Risk fit', note: 'Within stated tolerance' },
    { label: 'Impact fit', note: 'Aligned to stated impact criteria' },
    { label: 'Governance fit', note: 'Requires project governance review' },
    { label: 'Financial fit', note: 'Requires full financial model' },
  ],
  humanReviewNote: 'A fit assessment is not an approval — it still requires human review before any capital commitment.',
  copy: 'Capital should not chase the loudest promise. It should meet the strongest evidence-backed purpose.',
  primaryCta: { label: 'Submit Investment Mandate', href: 'mailto:alizhan@ecoiq.uk?subject=Investment+Mandate+Submission' },
  secondaryCta: { label: 'Request Project Access', href: 'mailto:alizhan@ecoiq.uk?subject=Project+Access+Request' },
}

export const humanDecision = {
  copy: 'EcoIQ can analyse. EcoIQ can compare. EcoIQ can explain. The decision remains human.',
  fields: [
    { label: 'Selected intervention', value: 'Heat-pump retrofit (Option B)' },
    { label: 'Evidence quality', value: 'Human-reviewed' },
    { label: 'Risk', value: 'Moderate' },
    { label: 'Conditions', value: 'Grid capacity confirmation required' },
    { label: 'Project status', value: project.status },
  ],
  reviewLabel: 'Human review required',
  actions: ['Approve', 'Approve with conditions', 'Reject'],
  // Command Centre is a real, live page — but its content is a static/
  // illustrative pipeline mockup (audited, not a live-data workflow), so
  // this copy deliberately avoids "real"/"live" to describe it.
  linkOutCta: { label: 'See how the review flow works →', href: '/command-centre/' },
}

export interface LifecycleStage {
  label: string
  detail: string
}

// Real stage sequence audited from capital_trace.py's
// capital_protection_chain_for_entry(). Per-stage status shown in the UI is
// illustrative (no live entry bound to this project).
export const capitalGuardian = {
  copy: 'Trust requires more than approval. It requires visibility after the money moves.',
  supportingLine: 'From capital commitment to physical assets and project milestones.',
  stages: [
    { label: 'Investor capital', detail: 'Committed' },
    { label: 'Escrow', detail: 'Held' },
    { label: 'Board approval', detail: 'Reviewed' },
    { label: 'Supplier', detail: 'Selected' },
    { label: 'Factory', detail: 'Manufacturing' },
    { label: 'Shipment', detail: 'In transit' },
    { label: 'Site', detail: 'Delivered' },
    { label: 'Commissioning', detail: 'In progress' },
    { label: 'Operating asset', detail: 'Pending' },
  ] as LifecycleStage[],
  redFlagExample: {
    label: 'Example red-flag rule',
    description: 'CAPEX variance exceeds threshold',
    note: 'One of 12 deterministic rules EcoIQ’s Capital Guardian checks against real stored project data — shown here as a worked example, not a live alert.',
  },
}

export interface ExpectedActualMetric {
  label: string
  expected: string
  actual: string
}

// Field shape audited from capital_guardian/services/execution_monitoring.py
// expected_vs_actual(). 'NOT YET REPORTED' is the literal real string the
// system itself returns when no actual value has been recorded — used here
// verbatim rather than invented.
export const expectedVsActual = {
  copy: "Did the project actually deliver? Don't assume. Measure. Review. Verify.",
  metrics: [
    { label: 'CAPEX', expected: 'Illustrative estimate', actual: 'NOT YET REPORTED' },
    { label: 'OPEX change', expected: 'Illustrative estimate', actual: 'NOT YET REPORTED' },
    { label: 'Savings', expected: 'Illustrative estimate', actual: 'NOT YET REPORTED' },
    { label: 'Loss avoided', expected: 'Illustrative estimate', actual: 'NOT YET REPORTED' },
    { label: 'Payback', expected: 'Illustrative estimate', actual: 'NOT YET REPORTED' },
  ] as ExpectedActualMetric[],
}

export const bridge = {
  headline: 'Capital meets verified purpose.',
  copy: 'We do not ask investors to trust a promise. We build the infrastructure to examine every step.',
  steps: ['Evidence', 'Analysis', 'Governance', 'Human approval', 'Monitoring', 'Verification'],
}

// Scene 10 — Learning. Grounded in evidence_memory/services/memory.py's real
// retrieve_relevant_verified_outcomes() function: real mechanism, illustrative
// project names/values. The two disclaimer lines are carried over verbatim
// from that service's own docstring ("never a guaranteed predictor and never
// proof that EcoIQ 'learned' anything automatically").
export const learning = {
  copy: 'Every reviewed outcome can become evidence for the next decision.',
  supportingLine: 'Learning means retrieving real historical outcomes for future human analysis.',
  // The manipulator's four visible actions — take, store, retrieve, deliver —
  // each tied to one arrow in the composition below rather than a flat list.
  projectA: { label: 'Project A', detail: project.name },
  outcomeStep: { label: 'Outcome', detail: 'Reviewed expected-vs-actual result' },
  humanReviewStep: { label: 'Human review', detail: 'Verified or reviewed by an analyst' },
  memoryStep: { label: 'Evidence memory', detail: 'Indexed for retrieval' },
  projectB: {
    illustrative: true,
    label: 'Project B',
    detail: 'Illustrative — residential heating retrofit, different region',
  },
  actions: {
    take: 'Take',
    store: 'Store',
    retrieve: 'Retrieve',
    deliver: 'Deliver',
  },
  retrievedTag: 'Relevant historical evidence',
  disclaimers: [
    'Retrieved evidence is not a guaranteed recommendation.',
    'Not automatic retraining. Not a guarantee.',
  ],
}

// Scene 11 — The Philosophical Hand. Reuses capitalGuardian.stages (the same
// real audited lifecycle) rather than redefining it, and the same six-step
// chain already introduced in `bridge`.
export const philosophicalHand = {
  eyebrow: 'The Bridge',
  question: 'How does technology extend a hand to capital?',
  answer: 'Not through a handshake. By giving capital eyes, intelligence, conscience, memory, and a path.',
  headline: 'Capital can move the world.',
  headlineLine2: 'But first, it must know where to go.',
  leftLabel: 'Capital',
  rightLabel: 'Real-world need',
  // Left side — capital's own journey, compact (the full 9-stage lifecycle
  // is Scene 8's job; this is the same real concept, summarised).
  capitalFlow: ['Investor capital', 'Mandate', 'Approval', 'Protected allocation'],
  // Three manipulators, each with one clear conceptual role — never all
  // actions in every scene, never autonomous approval.
  manipulators: [
    {
      label: 'Intelligence',
      tint: 'var(--eiq-accent)',
      actions: ['Receives evidence', 'Isolates the problem', 'Compares pathways', 'Identifies the better way'],
    },
    {
      label: 'Governance',
      tint: 'var(--eiq-gold)',
      actions: ['Reviews purpose', 'Blocks unsuitable pathways', 'Presents the decision to humans'],
      note: 'Does not approve autonomously.',
    },
    {
      label: 'Execution & Verification',
      tint: 'var(--eiq-info)',
      actions: ['Guides capital toward execution', 'Monitoring data returns', 'Verified outcomes become evidence'],
      note: 'Only after human approval.',
    },
  ],
  chain: bridge.steps,
  transformExamples: [
    'Clean heating infrastructure',
    'Energy-efficient buildings',
    'Industrial equipment',
    'Renewable infrastructure',
    'Responsible resource development',
    'Verified environmental improvements',
  ],
  closingLines: [
    'Evidence reveals the problem.',
    'Intelligence finds the better way.',
    'Humans make the decision.',
    'Capital enables execution.',
    'Outcomes create new evidence.',
  ],
  brand: 'EcoIQ.',
  triple: ['See what is wrong.', 'Find the better way.', 'Fix it together.'],
}

// Scene 12 — Final Joining Moment.
export const finalJoining = {
  progression: ['One problem', 'One better decision', 'One verified outcome', 'More evidence', 'Better-informed future decisions'],
  progressionDisclaimer: 'This is the intended architecture and vision — not a claim of current scale or traction.',
  brand: 'EcoIQ.',
  triple: ['See what is wrong.', 'Find the better way.', 'Fix it together.'],
  supportingLines: [
    'From evidence to action.',
    'From capital to measurable outcomes.',
    'From one project to better decisions everywhere.',
  ],
  ctas: {
    primary: { label: 'Explore EcoIQ', href: '/platform/' },
    secondary: { label: 'View Real-World Projects', href: '/projects/' },
    investor: { label: 'Explore Capital Guardian', href: '/capital-guardian/' },
    textLink: { label: 'See how EcoIQ works', href: '/platform/' },
  },
}

export const capabilities = [
  'Evidence Intelligence',
  'Resource Purpose Review',
  'Mizan & Stewardship Questions',
  'Better Way Comparison',
  'Financial Modelling',
  'Capital Allocation',
  'Capital Guardian',
  'Monitoring',
  'Verified Outcome',
  'Learning Retrieval',
]
