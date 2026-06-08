/*
 * EcoIQ — Photorealistic Earth Globe v2 (homepage hero).
 *
 * three.js + three-globe, loaded LAZILY via dynamic import (CDN ES modules
 * resolved by the page's import map). The heavy bundle is fetched only:
 *   - on this page (the script is only referenced from landing.html), and
 *   - on desktop with WebGL, no reduced-motion, after first paint (idle).
 *
 * Everything degrades gracefully: on mobile / no-WebGL / reduced-motion / any
 * failure we simply leave the CSS radial-glow on #hero-globe-wrap. No API keys,
 * no backend calls. Renders onto the existing #hero-globe <canvas>.
 *
 * Textures: NASA "Black Marble" night lights + Earth topology bump, served from
 * the three-globe example CDN (public-domain imagery). See PR notes for vendoring.
 */
(function () {
  const canvas = document.getElementById('hero-globe');
  if (!canvas) return;

  // ── Guards → fall back to CSS glow ──────────────────────────────────
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const smallScreen = window.matchMedia('(max-width: 860px)').matches;
  if (smallScreen || reduceMotion) return;

  // crude low-power heuristic: very low core count → skip the 3D globe
  if ((navigator.hardwareConcurrency || 4) <= 2) return;

  try {
    const t = document.createElement('canvas');
    if (!(t.getContext('webgl2') || t.getContext('webgl') || t.getContext('experimental-webgl'))) return;
  } catch (e) { return; }

  // ── Defer the heavy import until the browser is idle (after first paint) ──
  const start = () => init().catch(() => { /* leave CSS glow */ });
  if ('requestIdleCallback' in window) {
    requestIdleCallback(start, { timeout: 2500 });
  } else {
    setTimeout(start, 600);
  }

  const TEX = 'https://cdn.jsdelivr.net/npm/three-globe@2.31.0/example/img/';

  // EcoIQ priority markets
  const MARKETS = [
    { name: 'Kazakhstan',    lat: 43.2220, lng: 76.8512 },
    { name: 'United Kingdom',lat: 51.5074, lng: -0.1278 },
    { name: 'Saudi Arabia',  lat: 24.7136, lng: 46.6753 },
    { name: 'Türkiye',       lat: 41.0082, lng: 28.9784 },
  ];
  // subtle green data arcs between markets
  const ARCS = [
    [0, 1], [0, 2], [0, 3], [1, 2],
  ].map(([a, b]) => ({
    startLat: MARKETS[a].lat, startLng: MARKETS[a].lng,
    endLat: MARKETS[b].lat,   endLng: MARKETS[b].lng,
  }));

  async function init() {
    const THREE = await import('three');
    const ThreeGlobe = (await import('three-globe')).default;
    const { OrbitControls } = await import('three/addons/controls/OrbitControls.js');

    const w = canvas.clientWidth || 600;
    const h = canvas.clientHeight || 600;

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(w, h, false);

    const scene = new THREE.Scene();
    scene.add(new THREE.AmbientLight(0xbfc6d0, 1.1));
    const dir = new THREE.DirectionalLight(0xffffff, 0.55);
    dir.position.set(-1, 0.6, 1);
    scene.add(dir);

    const globe = new ThreeGlobe({ animateIn: true })
      .globeImageUrl(TEX + 'earth-night.jpg')      // dark earth + warm gold city lights (baked)
      .bumpImageUrl(TEX + 'earth-topology.png')    // subtle relief (small file)
      .showAtmosphere(true)
      .atmosphereColor('#00e89a')                  // soft green EcoIQ halo
      .atmosphereAltitude(0.18)
      // gold glowing market markers
      .pointsData(MARKETS)
      .pointLat('lat').pointLng('lng')
      .pointColor(() => '#e8c46a')
      .pointAltitude(0.012)
      .pointRadius(0.55)
      // subtle pulsing green rings at markets
      .ringsData(MARKETS)
      .ringColor(() => (tt) => `rgba(0,232,154,${1 - tt})`)
      .ringMaxRadius(4)
      .ringPropagationSpeed(2)
      .ringRepeatPeriod(1400)
      // subtle animated green data arcs
      .arcsData(ARCS)
      .arcColor(() => ['rgba(0,232,154,0.05)', 'rgba(0,232,154,0.65)'])
      .arcAltitude(0.22)
      .arcStroke(0.4)
      .arcDashLength(0.5).arcDashGap(0.25).arcDashAnimateTime(4200);

    // calmer, premium material tone
    const gm = globe.globeMaterial();
    gm.bumpScale = 6;
    gm.shininess = 6;
    scene.add(globe);

    // a couple of faint orbit/data rings around the globe
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x00e89a, transparent: true, opacity: 0.06, side: THREE.DoubleSide });
    [125, 150].forEach((r, i) => {
      const ring = new THREE.Mesh(new THREE.RingGeometry(r, r + 0.4, 96), ringMat);
      ring.rotation.x = Math.PI / 2 - (i ? 0.5 : 0.25);
      ring.rotation.y = i ? 0.3 : 0;
      scene.add(ring);
    });

    const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 2000);
    camera.position.z = 320;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.rotateSpeed = 0.4;
    controls.enablePan = false;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.34;          // slow cinematic spin
    controls.enableZoom = true;                // gentle zoom only
    controls.minDistance = 240;
    controls.maxDistance = 420;
    controls.minPolarAngle = Math.PI * 0.18;
    controls.maxPolarAngle = Math.PI * 0.82;

    let running = true;
    function loop() {
      if (!running) return;
      controls.update();
      renderer.render(scene, camera);
      requestAnimationFrame(loop);
    }
    function play() { if (!running) { running = true; loop(); } }
    function pause() { running = false; }

    // pause when tab hidden / globe scrolled off-screen (perf)
    document.addEventListener('visibilitychange', () => (document.hidden ? pause() : play()));
    if ('IntersectionObserver' in window) {
      new IntersectionObserver((es) => es.forEach((e) => (e.isIntersecting ? play() : pause())))
        .observe(canvas);
    }

    function onResize() {
      const nw = canvas.clientWidth, nh = canvas.clientHeight;
      if (!nw || !nh) return;
      camera.aspect = nw / nh; camera.updateProjectionMatrix();
      renderer.setSize(nw, nh, false);
    }
    window.addEventListener('resize', onResize);

    canvas.style.cursor = 'grab';
    canvas.addEventListener('pointerdown', () => (canvas.style.cursor = 'grabbing'));
    window.addEventListener('pointerup', () => (canvas.style.cursor = 'grab'));

    loop();
    requestAnimationFrame(() => { canvas.style.opacity = '1'; });
  }
})();
