/**
 * HeatingTransitionStory — EcoIQ's core story told as a Visual Narrative.
 *
 * Information + Visual + Interaction in one section: as the reader moves through
 * the text, the bound HeatingScene morphs from a coal-heated home to a clean
 * electrified village under a clear sky. The visual explains the words; no chart
 * required. Text content is data-driven (props from Django); the visual
 * vocabulary is the four-stage HeatingScene.
 */
import Scrollytelling from '../../narrative/Scrollytelling'
import type { Scene } from '../../narrative/Scrollytelling'
import { Reveal, fadeUp } from '../../motion'
import HeatingScene from './HeatingScene'

export interface HeatingTransitionStoryProps {
  eyebrow?: string
  heading?: string
  scenes?: Scene[]
}

const DEFAULT_SCENES: Scene[] = [
  {
    kicker: 'The starting point',
    title: 'A million homes heated by coal',
    body: 'Across southern Kazakhstan, families burn coal to survive winter. Each stove fills the home with soot and the sky with particulates — roughly 5.4 tonnes of CO₂ per household every year.',
  },
  {
    kicker: 'The intervention',
    title: 'One retrofit changes everything',
    body: 'Swap the coal stove for an efficient electric heat pump. The smoke clears, the air inside warms cleanly, and emissions per home fall immediately — before the grid is even decarbonised.',
  },
  {
    kicker: 'The multiplier',
    title: 'From one home to a region',
    body: 'Financed at scale, the retrofit repeats street by street. A single clean home becomes a village, then a region — turning a fragmented problem into a coordinated, investment-grade transition.',
  },
  {
    kicker: 'The outcome',
    title: 'Clean air, paired with clean power',
    body: 'Pair electrification with renewable supply and the sky clears for good — CO₂ per home approaches zero, while families gain warmer houses, lower bills, and healthier air.',
  },
]

export default function HeatingTransitionStory(props: HeatingTransitionStoryProps) {
  const {
    eyebrow = 'Visual Narrative',
    heading = 'How the coal-to-clean transition actually happens',
    scenes = DEFAULT_SCENES,
  } = props

  return (
    <Reveal variants={fadeUp} className="eiq-heat eiq-panel">
      <Scrollytelling
        eyebrow={eyebrow}
        heading={heading}
        scenes={scenes}
        renderVisual={(active) => <HeatingScene active={active} />}
      />
    </Reveal>
  )
}
