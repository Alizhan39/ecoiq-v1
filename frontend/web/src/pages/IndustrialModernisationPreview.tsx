/**
 * /industrial-modernisation-preview/ — the industrial scene, in a browser.
 *
 * INTERNAL PREVIEW. Not in the navigation, not on the homepage, not linked
 * from anywhere. It exists so the model can be looked at and argued with
 * before any decision about where it belongs.
 *
 * WHAT A READER SHOULD UNDERSTAND, AND HOW FAST
 * ---------------------------------------------
 * Within about twenty seconds: EcoIQ modernises a physical industrial system —
 * it finds where resources are being lost, changes the plant's topology to
 * stop losing them, closes the loops, and leaves the result measurable.
 *
 * So the page leads with that sentence in plain words, then shows the system
 * transforming, then explains each step. A reader who stops after the first
 * screen has the argument; a reader who scrolls gets the engineering.
 *
 * THREE LAYERS, ONE SOURCE
 * ------------------------
 * The scene, the state panel and the narrative all derive from the same
 * STAGES and the same state functions. They cannot describe different systems,
 * and a test asserts they report the same stage at every scroll position.
 */
import { useState } from 'react';

import { IndustrialTransitionScene } from '@/features/transition/IndustrialTransitionScene';
import { SystemStatePanel } from '@/features/transition/SystemStatePanel';
import { TransitionNarrative } from '@/features/transition/semantic/TransitionNarrative';
import { NARRATIVE_DISCLAIMER } from '@/features/transition/semantic/narrative';
import { useStickyProgress } from '@/hooks/useStickyProgress';

export default function IndustrialModernisationPreview() {
  const { ref, progress } = useStickyProgress<HTMLDivElement>();
  // Debug mode is opt-in via the URL, never a default, and what it reveals is
  // labelled as animation state at the point it is shown.
  const [debug] = useState(() =>
    typeof window !== 'undefined'
    && new URLSearchParams(window.location.search).has('debug'));

  return (
    <div className="itpreview">
      <header className="itpreview__intro">
        <p className="itpreview__eyebrow">Internal preview</p>
        <h1>EcoIQ modernises industrial systems</h1>
        <p className="itpreview__lede">
          It finds where a plant loses energy, heat, water and material;
          changes the physical topology so those losses stop leaving the
          system; closes the loops that return them to useful work; and leaves
          the result measurable.
        </p>
        <p className="itpreview__disclaimer">{NARRATIVE_DISCLAIMER}</p>
      </header>

      {/*
        The scroll driver. The scene inside it reads its own progress from the
        same hook, so the sticky visual and the panel beside it advance
        together without either owning the other.
      */}
      <div className="itpreview__scroller" ref={ref}>
        <div className="itpreview__sticky">
          <IndustrialTransitionScene progress={progress} />
          <SystemStatePanel progress={progress} debug={debug} />
        </div>
        {/* Scroll length. Each block is one stage's worth of travel. */}
        <div className="itpreview__track" aria-hidden="true">
          {Array.from({ length: 8 }, (_, i) => (
            <div key={i} className="itpreview__tick" />
          ))}
        </div>
      </div>

      <TransitionNarrative progress={progress} />
    </div>
  );
}
