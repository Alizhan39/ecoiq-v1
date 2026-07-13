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
