/**
 * AIStorytelling — scroll-driven narrative. A sequence of AI-framed insights
 * reveal one by one over an ambient animated field, each with a luminous index
 * marker and an accent statistic. Closes the brief with a synthesised takeaway.
 */
import { m } from 'framer-motion'
import { Reveal, fadeUp, stagger, staggerItem } from '../motion'

export interface Insight {
  stat?: string
  headline: string
  body: string
}

export interface AIStorytellingProps {
  eyebrow?: string
  title?: string
  insights?: Insight[]
  takeaway?: string
}

export default function AIStorytelling(props: AIStorytellingProps) {
  const {
    eyebrow = 'AI Synthesis',
    title = 'What the data is telling us',
    insights = [],
    takeaway,
  } = props

  return (
    <Reveal variants={fadeUp} className="eiq-story eiq-panel">
      {/* ambient field */}
      <div className="eiq-story__field" aria-hidden="true">
        <span className="eiq-story__orb eiq-story__orb--a" />
        <span className="eiq-story__orb eiq-story__orb--b" />
      </div>

      <div className="eiq-story__inner">
        <div className="eiq-eyebrow">{eyebrow}</div>
        <h2 className="eiq-story__title">{title}</h2>

        <m.ol className="eiq-story__list" variants={stagger(0.12, 0.1)} initial="hidden" whileInView="show" viewport={{ once: true, amount: 0.2 }}>
          {insights.map((ins, i) => (
            <m.li key={i} className="eiq-story__item" variants={staggerItem}>
              <span className="eiq-story__index eiq-num">{String(i + 1).padStart(2, '0')}</span>
              <div className="eiq-story__content">
                {ins.stat ? <div className="eiq-story__stat eiq-num">{ins.stat}</div> : null}
                <h3 className="eiq-story__headline">{ins.headline}</h3>
                <p className="eiq-story__body">{ins.body}</p>
              </div>
            </m.li>
          ))}
        </m.ol>

        {takeaway ? (
          <m.blockquote className="eiq-story__takeaway" initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.2 }}>
            {takeaway}
          </m.blockquote>
        ) : null}
      </div>
    </Reveal>
  )
}
