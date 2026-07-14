/**
 * Cinematic homepage hero — shared copy and data.
 *
 * Used by both the desktop scroll-driven stage and the reduced-motion /
 * mobile static stack, so the two render paths can never drift apart.
 */

export const intro = {
  eyebrow: 'EcoIQ',
  heading: 'Find the Better Way',
  body: 'EcoIQ connects evidence, AI agents, human judgment, responsible capital, and verified outcomes into one continuous decision system.',
  primaryCta: { label: 'Explore EcoIQ', href: '/platform/' },
  secondaryCta: { label: 'View Command Centre', href: '/command-centre/' },
}

export const evidence = {
  copy: 'Every decision begins with evidence.',
  sources: [
    'Satellite Data',
    'Sensor Networks',
    'Scientific Studies',
    'Community Feedback',
    'Financial Evidence',
  ],
}

export const agents = {
  copy: 'Specialist agents analyse the system together.',
  roster: [
    'Evidence Agent',
    'Resource Agent',
    'Risk Agent',
    'Capital Guardian',
    'Verification Agent',
  ],
}

/**
 * Left/right arm metrics for Scene 3's waste and repair sub-stages — one
 * visible per side at a time, per the brief's "max 1-2 visible metrics"
 * constraint. Values are deliberately round (not fake-precise decimals) so
 * they read as illustrative/directional rather than measured telemetry —
 * this hero has no real backing data source, unlike CountUpValue's other
 * uses elsewhere in the app for genuine server-rendered numbers.
 */
export interface StewardshipMetric {
  label: string
  value: number
  suffix: string
  prefix?: string
}

export const stewardship: { left: StewardshipMetric; right: StewardshipMetric } = {
  left: { label: 'Waste recovered', value: 2.4, suffix: 'T' },
  right: { label: 'System efficiency', value: 31, suffix: '%', prefix: '+' },
}

export interface Pillar {
  title: string
  body: string
}

export const pillars: Pillar[] = [
  { title: 'Evidence Memory', body: 'Every claim is traced back to its source — satellite, sensor, study, or ledger.' },
  { title: 'AI Agents', body: 'Specialist agents investigate, challenge assumptions, and disagree in the open.' },
  { title: 'Humanity in Control', body: 'High-impact actions wait for human approval. The agents recommend; people decide.' },
  { title: 'Verified Outcomes', body: 'Impact is confirmed after the fact, not assumed from a model.' },
  { title: 'The Better Way', body: 'Balanced for impact, affordability, resilience, justice, and evidence quality.' },
]
