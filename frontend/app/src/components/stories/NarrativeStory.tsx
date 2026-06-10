/**
 * NarrativeStory — the reusable storytelling island.
 *
 * One island powers any visual narrative: pick a scene `variant`, pass the
 * scene text + optional data (from Django), and the Narrative Engine binds them
 * — sticky morphing visual + stepped text + scroll interaction. This is the
 * primary EcoIQ UI pattern; Country / Company / Tours pages all reuse it.
 *
 *   data-island="NarrativeStory"
 *   data-props='{"variant":"village","heading":"…","scenes":[…],"data":{…}}'
 */
import Scrollytelling from '../../narrative/Scrollytelling'
import type { Scene } from '../../narrative/Scrollytelling'
import { Reveal, fadeUp } from '../../motion'
import { SCENES } from './scenes'

export interface NarrativeStoryProps {
  variant: string
  eyebrow?: string
  heading?: string
  scenes?: Scene[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data?: Record<string, any>
}

export default function NarrativeStory({ variant, eyebrow, heading, scenes = [], data }: NarrativeStoryProps) {
  const Scene = SCENES[variant]
  if (!Scene) {
    console.warn(`[ecoiq-islands] NarrativeStory: unknown variant "${variant}"`)
    return null
  }
  return (
    <Reveal variants={fadeUp} className="eiq-story-section eiq-panel">
      <Scrollytelling
        eyebrow={eyebrow}
        heading={heading}
        scenes={scenes}
        renderVisual={(active) => <Scene active={active} data={data} />}
      />
    </Reveal>
  )
}
