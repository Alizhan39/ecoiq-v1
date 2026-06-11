/*
 * EcoIQ — Realistic Interactive Globe (self-hosted, no CDN).
 *
 * three.js + three-globe + Earth textures + a country GeoJSON are all served
 * from Django static files (URLs passed via data-* on #hero-globe). No esm.sh,
 * no import map, no runtime CDN, no API keys, no backend calls.
 *
 * Features: dark NASA night-lights Earth, green atmosphere, country outlines
 * with EcoIQ focus markets (KZ/UK/SA/TR) highlighted, gold market markers +
 * green data arcs, smooth auto-rotation, drag-rotate, gentle zoom, and
 * click-to-focus (eases the clicked point to centre). Hand-rolled camera
 * controls (no OrbitControls).
 *
 * Fallbacks: mobile / reduced-motion / low-power / no-WebGL / any failure →
 * leave the CSS radial-glow on #hero-globe-wrap. rAF pauses when hidden/offscreen.
 */
(function () {
  var canvas = document.getElementById('hero-globe');
  if (!canvas) return;

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var smallScreen = window.matchMedia('(max-width: 860px)').matches;
  if (smallScreen || reduceMotion) return;
  if ((navigator.hardwareConcurrency || 4) <= 2) return;
  try {
    var test = document.createElement('canvas');
    if (!(test.getContext('webgl2') || test.getContext('webgl') || test.getContext('experimental-webgl'))) return;
  } catch (e) { return; }

  var URLS = {
    three: canvas.dataset.three, globe: canvas.dataset.globe,
    night: canvas.dataset.texNight, bump: canvas.dataset.texBump, geo: canvas.dataset.geo,
  };
  if (!URLS.three || !URLS.globe) return;

  var start = function () { boot().catch(function () {}); };
  if ('requestIdleCallback' in window) requestIdleCallback(start, { timeout: 2500 });
  else setTimeout(start, 600);

  function loadScript(src) {
    return new Promise(function (res, rej) {
      var s = document.createElement('script'); s.src = src; s.async = true;
      s.onload = res; s.onerror = rej; document.head.appendChild(s);
    });
  }

  var FOCUS = { KZ: 1, GB: 1, SA: 1, TR: 1 };   // EcoIQ priority markets (ISO A2)
  var MARKETS = [
    { name: 'Kazakhstan', lat: 43.2220, lng: 76.8512 },
    { name: 'United Kingdom', lat: 51.5074, lng: -0.1278 },
    { name: 'Saudi Arabia', lat: 24.7136, lng: 46.6753 },
    { name: 'Türkiye', lat: 41.0082, lng: 28.9784 },
  ];
  var ARCS = [[0, 1], [0, 2], [0, 3], [1, 2]].map(function (p) {
    return { startLat: MARKETS[p[0]].lat, startLng: MARKETS[p[0]].lng, endLat: MARKETS[p[1]].lat, endLng: MARKETS[p[1]].lng };
  });
  function iso(f) { var p = f.properties || {}; return p.ISO_A2 || p.iso_a2 || ''; }

  async function boot() {
    await loadScript(URLS.three);
    await loadScript(URLS.globe);
    var THREE = window.THREE, ThreeGlobe = window.ThreeGlobe;
    if (!THREE || !ThreeGlobe) throw new Error('three unavailable');

    var w = canvas.clientWidth || 600, h = canvas.clientHeight || 600;
    var renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(w, h, false);

    var scene = new THREE.Scene();
    scene.add(new THREE.AmbientLight(0xbfc6d0, 1.1));
    var dl = new THREE.DirectionalLight(0xffffff, 0.55); dl.position.set(-1, 0.6, 1); scene.add(dl);

    var globe = new ThreeGlobe({ animateIn: true })
      .globeImageUrl(URLS.night)
      .showAtmosphere(true).atmosphereColor('#00e89a').atmosphereAltitude(0.18)
      .pointsData(MARKETS).pointLat('lat').pointLng('lng')
      .pointColor(function () { return '#e8c46a'; }).pointAltitude(0.012).pointRadius(0.6)
      .ringsData(MARKETS).ringColor(function () { return function (t) { return 'rgba(0,232,154,' + (1 - t) + ')'; }; })
      .ringMaxRadius(4).ringPropagationSpeed(2).ringRepeatPeriod(1400)
      .arcsData(ARCS).arcColor(function () { return ['rgba(0,232,154,0.05)', 'rgba(0,232,154,0.6)']; })
      .arcAltitude(0.22).arcStroke(0.4).arcDashLength(0.5).arcDashGap(0.25).arcDashAnimateTime(4200);
    if (URLS.bump) globe.bumpImageUrl(URLS.bump);
    var gm = globe.globeMaterial(); gm.bumpScale = 6; gm.shininess = 6;
    scene.add(globe);

    // Country outlines + focus-market highlighting (best-effort; never blocks globe)
    if (URLS.geo) {
      try {
        var gj = await fetch(URLS.geo).then(function (r) { return r.json(); });
        globe.polygonsData(gj.features || [])
          .polygonAltitude(function (f) { return FOCUS[iso(f)] ? 0.02 : 0.007; })
          .polygonCapColor(function (f) { return FOCUS[iso(f)] ? 'rgba(0,232,154,0.22)' : 'rgba(255,255,255,0.02)'; })
          .polygonSideColor(function () { return 'rgba(0,232,154,0.05)'; })
          .polygonStrokeColor(function (f) { return FOCUS[iso(f)] ? '#c9a84c' : 'rgba(255,255,255,0.10)'; });
      } catch (e) { /* outlines optional */ }
    }

    var camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 2000);

    // invisible sphere for click-to-focus raycasting (globe radius ≈ 100)
    var pickSphere = new THREE.Mesh(new THREE.SphereGeometry(100, 32, 32), new THREE.MeshBasicMaterial({ visible: false }));
    scene.add(pickSphere);
    var raycaster = new THREE.Raycaster(), ndc = new THREE.Vector2();

    var theta = Math.PI * 0.1, phi = Math.PI * 0.46, radius = 320;
    var tTheta = theta, tPhi = phi;
    var MIN_R = 240, MAX_R = 420, MIN_PHI = Math.PI * 0.16, MAX_PHI = Math.PI * 0.84;
    var down = false, dragged = false, lx = 0, ly = 0;
    function place() {
      theta += (tTheta - theta) * 0.1; phi += (tPhi - phi) * 0.1;
      camera.position.set(radius * Math.sin(phi) * Math.sin(theta), radius * Math.cos(phi), radius * Math.sin(phi) * Math.cos(theta));
      camera.lookAt(0, 0, 0);
    }
    canvas.style.cursor = 'grab';
    canvas.addEventListener('pointerdown', function (e) { down = true; dragged = false; lx = e.clientX; ly = e.clientY; canvas.style.cursor = 'grabbing'; });
    window.addEventListener('pointerup', function () { down = false; canvas.style.cursor = 'grab'; });
    window.addEventListener('pointermove', function (e) {
      if (!down) return;
      if (Math.abs(e.clientX - lx) + Math.abs(e.clientY - ly) > 3) dragged = true;
      tTheta -= (e.clientX - lx) * 0.005; tPhi = Math.max(MIN_PHI, Math.min(MAX_PHI, tPhi - (e.clientY - ly) * 0.005));
      lx = e.clientX; ly = e.clientY;
    });
    canvas.addEventListener('wheel', function (e) { e.preventDefault(); radius = Math.max(MIN_R, Math.min(MAX_R, radius + e.deltaY * 0.25)); }, { passive: false });
    // click-to-focus: ease the clicked point toward centre
    canvas.addEventListener('click', function (e) {
      if (dragged) return;
      var r = canvas.getBoundingClientRect();
      ndc.x = ((e.clientX - r.left) / r.width) * 2 - 1; ndc.y = -((e.clientY - r.top) / r.height) * 2 + 1;
      raycaster.setFromCamera(ndc, camera);
      var hit = raycaster.intersectObject(pickSphere)[0];
      if (!hit) return;
      var v = hit.point.clone().normalize();
      tPhi = Math.max(MIN_PHI, Math.min(MAX_PHI, Math.acos(v.y)));
      tTheta = Math.atan2(v.x, v.z);
    });

    var running = true, auto = 0.0016;
    function loop() { if (!running) return; if (!down) tTheta += auto; place(); renderer.render(scene, camera); requestAnimationFrame(loop); }
    function play() { if (!running) { running = true; loop(); } }
    function pause() { running = false; }
    document.addEventListener('visibilitychange', function () { document.hidden ? pause() : play(); });
    if ('IntersectionObserver' in window) new IntersectionObserver(function (es) { es.forEach(function (en) { en.isIntersecting ? play() : pause(); }); }).observe(canvas);
    window.addEventListener('resize', function () { var nw = canvas.clientWidth, nh = canvas.clientHeight; if (!nw || !nh) return; camera.aspect = nw / nh; camera.updateProjectionMatrix(); renderer.setSize(nw, nh, false); });

    place(); loop();
    requestAnimationFrame(function () { canvas.style.opacity = '1'; });
  }
})();
