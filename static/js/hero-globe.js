/*
 * EcoIQ — premium 3D hero globe (Variant 1).
 *
 * Lightweight vanilla-JS island built on COBE (~5KB WebGL globe). No build step,
 * no API keys, no backend changes. Loaded as an ES module via an import map.
 *
 * Behaviour:
 *   - dark green-tinted globe, gold "city-light" markers, soft green EcoIQ glow
 *   - slow automatic rotation; pointer drag to rotate
 *   - skipped on small screens / reduced-motion / no-WebGL → CSS glow fallback
 *   - any failure (CDN blocked, WebGL error) leaves the CSS fallback in place
 */
import createGlobe from 'cobe';

(function () {
  const canvas = document.getElementById('hero-globe');
  if (!canvas) return;

  // ── Performance / accessibility guards ──────────────────────────────
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const smallScreen = window.matchMedia('(max-width: 860px)').matches;
  if (smallScreen) return; // mobile: keep the lightweight CSS glow only

  try {
    const t = document.createElement('canvas');
    if (!(t.getContext('webgl') || t.getContext('experimental-webgl'))) return;
  } catch (e) {
    return;
  }

  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  let width = 0;
  let height = 0;

  function measure() {
    width = canvas.offsetWidth || 600;
    height = canvas.offsetHeight || 600;
  }
  measure();
  window.addEventListener('resize', measure);

  // ── Pointer drag to rotate ──────────────────────────────────────────
  let down = false;
  let startX = 0;
  let target = 0;   // drag target
  let current = 0;  // smoothed drag
  canvas.style.cursor = 'grab';
  canvas.addEventListener('pointerdown', (e) => {
    down = true; startX = e.clientX - target; canvas.style.cursor = 'grabbing';
    canvas.setPointerCapture && canvas.setPointerCapture(e.pointerId);
  });
  const release = () => { down = false; canvas.style.cursor = 'grab'; };
  window.addEventListener('pointerup', release);
  window.addEventListener('pointermove', (e) => { if (down) target = e.clientX - startX; });

  // ── Gold "city-light" markers (EcoIQ focus markets + global cities) ──
  const markers = [
    { location: [43.2220, 76.8512], size: 0.07 }, // Almaty
    { location: [51.1605, 71.4704], size: 0.05 }, // Astana
    { location: [51.5074, -0.1278], size: 0.06 }, // London
    { location: [24.7136, 46.6753], size: 0.06 }, // Riyadh
    { location: [41.0082, 28.9784], size: 0.06 }, // Istanbul
    { location: [25.2048, 55.2708], size: 0.05 }, // Dubai
    { location: [40.7128, -74.0060], size: 0.05 }, // New York
    { location: [1.3521, 103.8198], size: 0.05 }, // Singapore
    { location: [-1.2921, 36.8219], size: 0.05 }, // Nairobi
    { location: [55.7558, 37.6173], size: 0.05 }, // Moscow
    { location: [39.9042, 116.4074], size: 0.05 }, // Beijing
    { location: [48.8566, 2.3522], size: 0.05 }, // Paris
  ];

  let phi = 0;
  try {
    createGlobe(canvas, {
      devicePixelRatio: dpr,
      width: width * dpr,
      height: height * dpr,
      phi: 0,
      theta: 0.28,
      dark: 1,
      diffuse: 1.15,
      mapSamples: 16000,
      mapBrightness: 5.2,
      baseColor: [0.06, 0.12, 0.09],   // dark, green-tinted globe
      markerColor: [0.81, 0.66, 0.30], // warm gold city lights
      glowColor: [0.0, 0.45, 0.34],    // soft EcoIQ green glow
      opacity: 0.95,
      markers: markers,
      onRender: (state) => {
        current += (target - current) * 0.08;       // smooth drag easing
        if (!down && !reduceMotion) phi += 0.0028;   // slow cinematic auto-rotate
        state.phi = phi + current / 200;
        state.width = width * dpr;
        state.height = height * dpr;
      },
    });
    requestAnimationFrame(() => { canvas.style.opacity = '1'; });
  } catch (e) {
    canvas.style.display = 'none'; // fall back to the CSS glow on the wrapper
  }
})();
