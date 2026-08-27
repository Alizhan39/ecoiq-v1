import { useEffect, useRef, useState } from 'react';

/**
 * How far an element has travelled through the viewport, 0 to 1.
 *
 * WHY NOT A LIBRARY
 * -----------------
 * The stashed cinematic work this technique comes from used framer-motion's
 * `useScroll`. `frontend/web` has three runtime dependencies on purpose, and
 * the whole homepage is 276 lines — adding an animation library to the main
 * bundle so one decorative canvas can read a scroll position would cost every
 * visitor for something most never scroll to.
 *
 * WHY IT IS CHEAP
 * ---------------
 * An IntersectionObserver decides whether to listen at all, so a page whose
 * hero is off-screen does no scroll work. While visible, updates are coalesced
 * to one requestAnimationFrame per frame, and the listener is passive so it
 * never blocks scrolling.
 *
 * There is no timer. Progress is a pure function of scroll position, which is
 * what makes anything drawn from it deterministic: the same scroll offset
 * always produces the same frame, so a single frame can be asserted in a test
 * instead of a moving target.
 */
export function useScrollProgress<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const element = ref.current;
    if (!element) return undefined;

    let frame = 0;
    let listening = false;

    const measure = () => {
      frame = 0;
      // Reads layout and sets state synchronously. The rAF coalescing lives in
      // onScroll, not here, so this is safe to call directly on mount.
      const rect = element.getBoundingClientRect();
      const viewport = window.innerHeight || 1;
      // 0 when the element's top reaches the bottom of the viewport, 1 when
      // its bottom reaches the top: the span over which it is on screen at all.
      const total = rect.height + viewport;
      const travelled = viewport - rect.top;
      const next = total > 0 ? travelled / total : 0;
      setProgress(Math.min(1, Math.max(0, next)));
    };

    const onScroll = () => {
      if (frame) return;
      frame = window.requestAnimationFrame(measure);
    };

    // Measure once, immediately, whatever happens next.
    //
    // IntersectionObserver delivers its first callback asynchronously, and in
    // a backgrounded tab it does not deliver one at all (nor does rAF run) —
    // found while verifying this in a pane whose document.visibilityState was
    // "hidden". Without this line, a section already on screen at load paints
    // its progress-0 frame and holds it until the reader scrolls, which for a
    // section near the top of the page can be never.
    measure();

    // Degrade, never throw. A browser without IntersectionObserver (and jsdom,
    // which is the same case) still gets the page; it simply listens the whole
    // time instead of only while visible. Decoration must never be the reason
    // a page fails to render.
    if (typeof IntersectionObserver !== 'function') {
      listening = true;
      window.addEventListener('scroll', onScroll, { passive: true });
      window.addEventListener('resize', onScroll, { passive: true });
      measure();
      return () => {
        if (frame) window.cancelAnimationFrame(frame);
        window.removeEventListener('scroll', onScroll);
        window.removeEventListener('resize', onScroll);
      };
    }

    const observer = new IntersectionObserver(([entry]) => {
      if (entry?.isIntersecting && !listening) {
        listening = true;
        window.addEventListener('scroll', onScroll, { passive: true });
        window.addEventListener('resize', onScroll, { passive: true });
        measure();
      } else if (!entry?.isIntersecting && listening) {
        listening = false;
        window.removeEventListener('scroll', onScroll);
        window.removeEventListener('resize', onScroll);
      }
    });

    observer.observe(element);

    return () => {
      observer.disconnect();
      if (frame) window.cancelAnimationFrame(frame);
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
    };
  }, []);

  return { ref, progress };
}
