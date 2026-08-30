/**
 * /industrial-modernisation/ — the first product expression of the direction.
 *
 * TWO AXES, NEVER MERGED
 * ----------------------
 * Axis A is what happens to the plant: LEGACY through VERIFY, eight physical
 * stages, shown as the scroll-driven schematic. Axis B is what EcoIQ does:
 * seven workflow stages, each with a capability status from the platform
 * registry's own vocabulary.
 *
 * They correlate and they are not the same list. RETROFIT, ELECTRIFY, RECOVER
 * and CIRCULARISE all sit inside ENGINEER; SIMULATE, FINANCE and EXECUTE have
 * no physical stage at all. Rendering them as one seven-step sequence would
 * misdescribe both, so the layout keeps them apart and the containment is
 * drawn rather than described.
 *
 * WHAT THIS PAGE MAY NOT SAY
 * --------------------------
 * Physical visualisation is not live facility capability. Electrification is
 * not decarbonisation. Illustrative state is not measured performance. A
 * scenario model is not a validated engineering recommendation. An available
 * data slot is not collected data.
 *
 * Each of those has a section that states it rather than a footnote hoping to
 * cover it, and the CTA is "Discuss a facility" rather than "Analyse your
 * facility" because the second describes a workflow that does not exist end
 * to end.
 */
import { Link } from 'react-router-dom';

/**
 * Photography slots, left explicit rather than filled.
 *
 * The brief asks for roughly 70% engineering visual and 30% real industrial
 * photography, and rules out the stock vocabulary this category always
 * attracts — solar panels, green leaves, handshakes, hard hats over tablets.
 *
 * No licensed assets matching the brief exist in this repository. The honest
 * options were an empty page or a placeholder that names what is needed;
 * committing questionable imagery to fill space is the one option the brief
 * rules out and the one that would be hardest to undo, because a wrong image
 * becomes the page's visual language before anyone reviews it.
 *
 * Each slot states its subject, why it belongs where it is, and what would
 * make a candidate wrong. Rendered visibly on purpose — a gap you can see is
 * a gap someone fills.
 */
interface ImageSlot {
  id: string;
  subject: string;
  purpose: string;
  avoid: string;
}

const IMAGE_SLOTS: Record<string, ImageSlot> = {
  hero: {
    id: 'hero',
    subject: 'Real process plant at working scale — pipework, insulation, '
      + 'valves, a heat exchanger or boiler house in situ.',
    purpose: 'Establishes that the subject is heavy physical industry before '
      + 'the schematic abstracts it.',
    avoid: 'Renders, glowing overlays, anything that looks generated.',
  },
  engineer: {
    id: 'engineer',
    subject: 'Motor and drive cabinet, or a variable-speed drive installation.',
    purpose: 'The retrofit the ENGINEER stage describes, as a real object.',
    avoid: 'Stock "engineer with tablet"; the equipment is the subject.',
  },
  recover: {
    id: 'recover',
    subject: 'Heat exchanger or thermal store, ideally plate or shell-and-tube '
      + 'with visible pipework.',
    purpose: 'RECOVER is the least legible stage as a diagram; a photograph '
      + 'of the actual equipment carries it.',
    avoid: 'Cutaway diagrams — the schematic already does that job.',
  },
  verify: {
    id: 'verify',
    subject: 'Industrial control room or metering panel, in use.',
    purpose: 'VERIFY is about measurement existing at all.',
    avoid: 'Futuristic dashboards, screens of invented data.',
  },
};

function ImageSlotPlaceholder({ slot }: { slot: ImageSlot }) {
  return (
    <figure className="itpage__imageslot" data-slot={slot.id}>
      <p><strong>Photography needed — {slot.id}</strong></p>
      <p>{slot.subject}</p>
      <p className="itpage__note itpage__note--slot">
        Why here: {slot.purpose} · Avoid: {slot.avoid}
      </p>
    </figure>
  );
}

import { DataReadiness } from '@/features/transition/DataReadiness';
import { IndustrialTransitionScene } from '@/features/transition/IndustrialTransitionScene';
import { SystemStatePanel } from '@/features/transition/SystemStatePanel';
import { WorkflowAxis } from '@/features/transition/WorkflowAxis';
import { TransitionNarrative } from '@/features/transition/semantic/TransitionNarrative';
import { stageAt } from '@/features/transition/model/stages';
import { useStickyProgress } from '@/hooks/useStickyProgress';

export default function IndustrialModernisation() {
  const { ref, progress } = useStickyProgress<HTMLDivElement>();
  const stage = stageAt(progress);

  return (
    <div className="itpage">
      {/* 1 — HERO. What EcoIQ does to a physical system, in one line. No
          rating, no score, no organisation. */}
      <header className="itpage__hero">
        <p className="itpage__eyebrow">Industrial modernisation</p>
        <h1>Find industrial losses. Engineer the transition. Verify what changed.</h1>
        <p className="itpage__lede">
          EcoIQ maps industrial systems, identifies where energy, heat, water
          and material are lost, structures the engineering interventions that
          stop the losses, and builds an evidence trail from diagnosis through
          to verification.
        </p>
        <p className="itpage__note">
          The system below is an illustration of how a modernisation sequence
          works. It describes no specific facility and contains no measured
          data.
        </p>
        <ImageSlotPlaceholder slot={IMAGE_SLOTS.hero!} />
      </header>

      {/* 2 — AXIS A. The dominant visual: the plant transforming. */}
      <div className="itpage__scroller" ref={ref}>
        <div className="itpage__sticky">
          <IndustrialTransitionScene progress={progress} />
          <SystemStatePanel progress={progress} />
        </div>
        <div className="itpage__track" aria-hidden="true" />
      </div>

      <TransitionNarrative progress={progress} />

      {/* 3 — AXIS B. What EcoIQ does, correlated but separate. */}
      <WorkflowAxis physicalStage={stage.key} />

      <div className="itpage__gallery">
        <ImageSlotPlaceholder slot={IMAGE_SLOTS.engineer!} />
        <ImageSlotPlaceholder slot={IMAGE_SLOTS.recover!} />
        <ImageSlotPlaceholder slot={IMAGE_SLOTS.verify!} />
      </div>

      {/* 4 — the boundary between the illustration and a real facility. */}
      <section className="itpage__boundary" aria-labelledby="itboundary-heading">
        <h2 id="itboundary-heading">From illustration to a real facility</h2>
        <div className="itpage__columns">
          <div className="itpage__column">
            <h3>Today</h3>
            <p className="itpage__status">Illustrative industrial system</p>
            <p>
              A generic plant, drawn to show what a modernisation sequence
              does. No equipment list, no meter, no organisation. Every
              quantity in it is unknown rather than zero.
            </p>
          </div>
          <div className="itpage__column">
            <h3>What a real engagement would follow</h3>
            <p className="itpage__status itpage__status--future">
              Not built. This is the shape, not a capability.
            </p>
            <ol className="itpage__chain">
              {['Your facility', 'Equipment', 'Energy', 'Process heat',
                'Water', 'Materials', 'Losses', 'Interventions', 'Scenarios',
                'Economics', 'Verification'].map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
            <p className="itpage__note">
              EcoIQ has no facility ingestion. Nothing in this chain runs
              today, and saying otherwise would be the claim this whole page
              is built to avoid.
            </p>
          </div>
        </div>
      </section>

      {/* 5 — what the model could take, against what it holds. */}
      <DataReadiness />

      {/* 6 — the governance layer, mentioned and not centred. */}
      <section className="itpage__principles" aria-labelledby="itprinciples-heading">
        <h2 id="itprinciples-heading">The 114 principles, underneath</h2>
        <p>
          The 114 stewardship principles are the governance and evidence layer
          beneath this work, not the product on top of it. They are how EcoIQ
          asks <em>why</em> an intervention is justified and <em>what evidence</em>{' '}
          would be required to stand behind it — questions about the reasoning,
          where the model above is about the physical system.
        </p>
        <p className="itpage__note">
          No principle mapping has been recorded for any intervention yet. The
          architecture supports the link; making it is a claim about meaning
          and belongs to whoever owns the canon.{' '}
          <Link to="/principles">See the 114 principles</Link>.
        </p>
      </section>

      {/* 7 — a CTA the workflow can actually honour. */}
      <section className="itpage__cta" aria-labelledby="itcta-heading">
        <h2 id="itcta-heading">Discuss a facility</h2>
        <p>
          If you operate an industrial site and want to talk about where its
          losses are, that is a conversation rather than a product flow. There
          is no self-serve analysis to run — the diagnosis and engineering
          model exist, the facility data pipeline does not.
        </p>
        <Link className="itpage__button" to="/contact">Discuss a facility</Link>
      </section>
    </div>
  );
}
