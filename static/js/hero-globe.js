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
    // EcoIQ focus markets — emphasised
    { location: [43.2220, 76.8512], size: 0.09 }, // Almaty
    { location: [51.1605, 71.4704], size: 0.06 }, // Astana
    { location: [51.5074, -0.1278], size: 0.07 }, // London
    { location: [24.7136, 46.6753], size: 0.07 }, // Riyadh
    { location: [41.0082, 28.9784], size: 0.07 }, // Istanbul
    // Global "night-light" city points
    { location: [25.2048, 55.2708], size: 0.05 }, // Dubai
    { location: [40.7128, -74.0060], size: 0.06 }, // New York
    { location: [34.0522, -118.2437], size: 0.05 }, // Los Angeles
    { location: [19.4326, -99.1332], size: 0.05 }, // Mexico City
    { location: [-23.5505, -46.6333], size: 0.05 }, // São Paulo
    { location: [1.3521, 103.8198], size: 0.05 }, // Singapore
    { location: [-1.2921, 36.8219], size: 0.05 }, // Nairobi
    { location: [6.5244, 3.3792], size: 0.05 }, // Lagos
    { location: [30.0444, 31.2357], size: 0.05 }, // Cairo
    { location: [55.7558, 37.6173], size: 0.05 }, // Moscow
    { location: [39.9042, 116.4074], size: 0.06 }, // Beijing
    { location: [35.6762, 139.6503], size: 0.06 }, // Tokyo
    { location: [28.6139, 77.2090], size: 0.06 }, // Delhi
    { location: [19.0760, 72.8777], size: 0.05 }, // Mumbai
    { location: [48.8566, 2.3522], size: 0.05 }, // Paris
    { location: [52.5200, 13.4050], size: 0.04 }, // Berlin
    { location: [-33.8688, 151.2093], size: 0.05 }, // Sydney
    { location: [-26.2041, 28.0473], size: 0.04 }, // Johannesburg
    { location: [41.3851, 2.1734], size: 0.04 }, // Barcelona
  ];

  let phi = 0;
  try {
    createGlobe(canvas, {
      devicePixelRatio: dpr,
      width: width * dpr,
      height: height * dpr,
      phi: 0,
      theta: 0.26,
      dark: 1.08,                       // deeper night-side shadow → realistic Earth
      diffuse: 1.5,                     // stronger directional shading (cinematic)
      mapSamples: 24000,                // denser landmass dots → reads as continents, not a sparse grid
      mapBrightness: 7.5,               // brighter continents so land/ocean contrast is clear
      baseColor: [0.045, 0.075, 0.07],  // dark realistic earth, faint green tint
      markerColor: [0.92, 0.74, 0.36],  // warm gold satellite night-lights
      glowColor: [0.02, 0.52, 0.40],    // green transition/data-signal halo
      opacity: 1,
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
