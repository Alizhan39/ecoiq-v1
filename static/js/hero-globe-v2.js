/*
 * EcoIQ — Photorealistic Earth Globe v2 (homepage hero) — FULLY SELF-HOSTED.
 *
 * three.js + three-globe + textures are all served from our own Django static
 * files (no esm.sh, no external CDN at runtime, no API keys, no backend calls).
 * The vendored script + texture URLs are passed in via data-* attributes on the
 * #hero-globe canvas (resolved with {% static %} in landing.html).
 *
 * Loading is lazy and conditional: the heavy three.js/three-globe scripts are
 * injected only on this page, only on desktop with WebGL, only after first paint
 * (requestIdleCallback). Camera controls (drag / slow auto-rotate / gentle zoom)
 * are hand-rolled so we don't need OrbitControls.
 *
 * Any failure → leave the CSS radial-glow fallback on #hero-globe-wrap.
 */
(function () {
  var canvas = document.getElementById('hero-globe');
  if (!canvas) return;

  // ── Guards → fall back to CSS glow ──────────────────────────────────
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var smallScreen = window.matchMedia('(max-width: 860px)').matches;
  if (smallScreen || reduceMotion) return;
  if ((navigator.hardwareConcurrency || 4) <= 2) return;   // low-power heuristic
  try {
    var test = document.createElement('canvas');
    if (!(test.getContext('webgl2') || test.getContext('webgl') || test.getContext('experimental-webgl'))) return;
  } catch (e) { return; }

  var URLS = {
    three: canvas.dataset.three,
    globe: canvas.dataset.globe,
    night: canvas.dataset.texNight,
    bump:  canvas.dataset.texBump,
  };
  if (!URLS.three || !URLS.globe) return;

  // ── Defer heavy script injection until the browser is idle ──────────
  var start = function () { boot().catch(function () { /* leave CSS glow */ }); };
  if ('requestIdleCallback' in window) requestIdleCallback(start, { timeout: 2500 });
  else setTimeout(start, 600);

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = src; s.async = true;
      s.onload = resolve; s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  var MARKETS = [
    { name: 'Kazakhstan',     lat: 43.2220, lng: 76.8512 },
    { name: 'United Kingdom', lat: 51.5074, lng: -0.1278 },
    { name: 'Saudi Arabia',   lat: 24.7136, lng: 46.6753 },
    { name: 'Türkiye',        lat: 41.0082, lng: 28.9784 },
  ];
  var ARCS = [[0, 1], [0, 2], [0, 3], [1, 2]].map(function (p) {
    return {
      startLat: MARKETS[p[0]].lat, startLng: MARKETS[p[0]].lng,
      endLat: MARKETS[p[1]].lat, endLng: MARKETS[p[1]].lng,
    };
  });

  async function boot() {
    await loadScript(URLS.three);          // global THREE
    await loadScript(URLS.globe);          // global ThreeGlobe (uses THREE)
    var THREE = window.THREE, ThreeGlobe = window.ThreeGlobe;
    if (!THREE || !ThreeGlobe) throw new Error('three/three-globe unavailable');

    var w = canvas.clientWidth || 600, h = canvas.clientHeight || 600;

    var renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(w, h, false);

    var scene = new THREE.Scene();
    scene.add(new THREE.AmbientLight(0xbfc6d0, 1.1));
    var dir = new THREE.DirectionalLight(0xffffff, 0.55);
    dir.position.set(-1, 0.6, 1); scene.add(dir);

    var globe = new ThreeGlobe({ animateIn: true })
      .globeImageUrl(URLS.night)
      .showAtmosphere(true).atmosphereColor('#00e89a').atmosphereAltitude(0.18)
      .pointsData(MARKETS).pointLat('lat').pointLng('lng')
      .pointColor(function () { return '#e8c46a'; }).pointAltitude(0.012).pointRadius(0.55)
      .ringsData(MARKETS)
      .ringColor(function () { return function (tt) { return 'rgba(0,232,154,' + (1 - tt) + ')'; }; })
      .ringMaxRadius(4).ringPropagationSpeed(2).ringRepeatPeriod(1400)
      .arcsData(ARCS)
      .arcColor(function () { return ['rgba(0,232,154,0.05)', 'rgba(0,232,154,0.65)']; })
      .arcAltitude(0.22).arcStroke(0.4)
      .arcDashLength(0.5).arcDashGap(0.25).arcDashAnimateTime(4200);
    if (URLS.bump) globe.bumpImageUrl(URLS.bump);

    var gm = globe.globeMaterial();
    gm.bumpScale = 6; gm.shininess = 6;
    scene.add(globe);

    // faint orbit rings
    var ringMat = new THREE.MeshBasicMaterial({ color: 0x00e89a, transparent: true, opacity: 0.06, side: THREE.DoubleSide });
    [125, 150].forEach(function (r, i) {
      var ring = new THREE.Mesh(new THREE.RingGeometry(r, r + 0.4, 96), ringMat);
      ring.rotation.x = Math.PI / 2 - (i ? 0.5 : 0.25);
      ring.rotation.y = i ? 0.3 : 0;
      scene.add(ring);
    });

    var camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 2000);

    // ── Hand-rolled camera controls (spherical) ───────────────────────
    var theta = Math.PI * 0.1, phi = Math.PI * 0.46, radius = 320;
    var MIN_R = 240, MAX_R = 420, MIN_PHI = Math.PI * 0.18, MAX_PHI = Math.PI * 0.82;
    var down = false, lastX = 0, lastY = 0, autoRotate = 0.0016;
    function place() {
      camera.position.set(
        radius * Math.sin(phi) * Math.sin(theta),
        radius * Math.cos(phi),
        radius * Math.sin(phi) * Math.cos(theta)
      );
      camera.lookAt(0, 0, 0);
    }
    canvas.style.cursor = 'grab';
    canvas.addEventListener('pointerdown', function (e) { down = true; lastX = e.clientX; lastY = e.clientY; canvas.style.cursor = 'grabbing'; });
    window.addEventListener('pointerup', function () { down = false; canvas.style.cursor = 'grab'; });
    window.addEventListener('pointermove', function (e) {
      if (!down) return;
      theta -= (e.clientX - lastX) * 0.005;
      phi = Math.max(MIN_PHI, Math.min(MAX_PHI, phi - (e.clientY - lastY) * 0.005));
      lastX = e.clientX; lastY = e.clientY;
    });
    canvas.addEventListener('wheel', function (e) {
      e.preventDefault();
      radius = Math.max(MIN_R, Math.min(MAX_R, radius + e.deltaY * 0.25));
    }, { passive: false });

    var running = true;
    function loop() {
      if (!running) return;
      if (!down) theta += autoRotate;       // slow cinematic spin
      place();
      renderer.render(scene, camera);
      requestAnimationFrame(loop);
    }
    function play() { if (!running) { running = true; loop(); } }
    function pause() { running = false; }

    document.addEventListener('visibilitychange', function () { document.hidden ? pause() : play(); });
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es) { es.forEach(function (en) { en.isIntersecting ? play() : pause(); }); }).observe(canvas);
    }
    window.addEventListener('resize', function () {
      var nw = canvas.clientWidth, nh = canvas.clientHeight;
      if (!nw || !nh) return;
      camera.aspect = nw / nh; camera.updateProjectionMatrix();
      renderer.setSize(nw, nh, false);
    });

    place(); loop();
    requestAnimationFrame(function () { canvas.style.opacity = '1'; });
  }
})();
