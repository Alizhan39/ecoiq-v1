/**
 * How far a reader has scrolled THROUGH a pinned section, 0 to 1.
 *
 * WHY NOT useScrollProgress
 * -------------------------
 * That hook measures an element travelling across the viewport: 0 when its top
 * reaches the bottom of the screen, 1 when its bottom reaches the top. Right
 * for a section that scrolls past. Wrong for a scrollytelling section, where
 * the visual is `position: sticky` and deliberately does NOT move — measured
 * that way, a 6660px scroller reads 0.055 at the top of the page and never
 * reaches 1 at the bottom, so the first and last stages of an eight-stage
 * sequence are unreachable. Found by scrolling to the end and landing on
 * "optimise".
 *
 * Here the question is different: given a tall container whose child is
 * pinned, how much of the container's travel has been consumed? That is
 * scroll-within-the-container over container-height-minus-one-viewport, which
 * is exactly 0 when the container's top hits the top of the screen and exactly
 * 1 when its bottom does.
 *
 * SAME DISCIPLINE AS ITS SIBLING
 * ------------------------------
 * No timer, no animation loop. An IntersectionObserver decides whether to
 * listen at all; while listening, updates are coalesced to one rAF per frame
 * and the listener is passive. Progress remains a pure function of scroll
 * position, which is what lets a test assert a single frame.
 */
import { useEffect, useRef, useState } from 'react';

export function useStickyProgress<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const element = ref.current;
    if (!element) return undefined;

    let frame = 0;
    let listening = false;

    const measure = () => {
      frame = 0;
      const rect = element.getBoundingClientRect();
      const viewport = window.innerHeight || 1;
      // Travel available once the container's top is at the top of the screen.
      // A container shorter than the viewport has none, and reports 0 rather
      // than dividing by a negative.
      const travel = rect.height - viewport;
      if (travel <= 0) { setProgress(0); return; }
      setProgress(Math.min(1, Math.max(0, -rect.top / travel)));
    };

    const onScroll = () => {
      if (frame) return;
      frame = window.requestAnimationFrame(measure);
    };

    // Measure immediately: IntersectionObserver's first callback is async, and
    // in a backgrounded tab it never arrives. Same reason as its sibling.
    measure();

    const listen = () => {
      if (listening) return;
      listening = true;
      window.addEventListener('scroll', onScroll, { passive: true });
      window.addEventListener('resize', onScroll, { passive: true });
    };
    const stop = () => {
      if (!listening) return;
      listening = false;
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
    };

    // Degrade, never throw. Without IntersectionObserver (jsdom included) the
    // hook simply listens the whole time.
    if (typeof IntersectionObserver !== 'function') {
      listen();
      return () => { stop(); if (frame) cancelAnimationFrame(frame); };
    }

    const observer = new IntersectionObserver(([entry]) => {
      if (entry?.isIntersecting) { listen(); measure(); } else { stop(); }
    });
    observer.observe(element);

    return () => {
      observer.disconnect();
      stop();
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  return { ref, progress };
}
