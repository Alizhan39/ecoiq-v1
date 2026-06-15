/*
 * EcoIQ — Living Infrastructure Earth (Phase 1 MVP).
 *
 * Breathing Earth + 5 toggleable data layers + 4 featured-country chips +
 * live stat strip, all fed by /api/globe/layers/ (real data). Self-hosted
 * three.js + three-globe (no CDN, no API keys). The HUD (stats, toggles,
 * chips) is plain DOM and always works; the 3D canvas is progressive
 * enhancement. No fly-to country twin in this phase.
 *
 * Fallback: no-WebGL / reduced-motion / low-power / small screen / any error →
 * keep the CSS poster + DOM HUD. rAF pauses when hidden/offscreen.
 */
(function () {
  var root = document.getElementById('living-earth');
  if (!root) return;
  var canvas = document.getElementById('le-canvas');
  var endpoint = root.dataset.endpoint;

  var LAYER_COLOR = {
    energy: '#f4a261', infrastructure: '#58a6ff', capital: '#00e89a',
    carbon: '#a855f7', water: '#38bdf8',
  };
  var LAYER_PRIORITY = ['capital', 'carbon', 'energy', 'water', 'infrastructure'];
  var active = { energy: true, infrastructure: true, capital: true, carbon: true, water: true };
  var DATA = null;

  // ── 1. Always: fetch live data → populate the DOM HUD (works without WebGL) ──
  fetch(endpoint, { headers: { Accept: 'application/json' } })
    .then(function (r) { return r.json(); })
    .then(function (d) { DATA = d; renderStats(d.stats); wireToggles(); wireChips(d.countries); bootGlobe(); })
    .catch(function () { /* HUD shows skeleton; globe stays as poster */ });

  function setText(id, v) { var el = document.getElementById(id); if (el) el.textContent = v; }
  function renderStats(s) {
    setText('le-stat-companies', s.companies);
    setText('le-stat-datapoints', s.datapoints);
    setText('le-stat-evidence', s.evidence);
    setText('le-stat-countries', s.countries);
    setText('le-stat-verification', s.verification_rate == null ? '—' : s.verification_rate + '%');
    setText('le-stat-freshness', s.freshness_days == null ? '—' : (s.freshness_days <= 0 ? 'today' : s.freshness_days + 'd'));
  }
  function wireToggles() {
    root.querySelectorAll('[data-layer]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var L = btn.dataset.layer; active[L] = !active[L];
        btn.classList.toggle('off', !active[L]);
        applyLayers();
      });
    });
  }
  var focusISO = null;
  function wireChips(countries) {
    root.querySelectorAll('[data-iso]').forEach(function (chip) {
      chip.addEventListener('click', function () {
        var iso = chip.dataset.iso;
        focusISO = (focusISO === iso) ? null : iso;
        root.querySelectorAll('[data-iso]').forEach(function (c) { c.classList.toggle('active', c.dataset.iso === focusISO); });
        applyLayers();
        if (window.__leFocus) window.__leFocus(iso, !!focusISO, countries);
      });
    });
  }

  function visibleMarkers() {
    if (!DATA) return [];
    return DATA.markers.filter(function (m) {
      if (focusISO && m.country !== focusISO) return false;
      return m.layers.some(function (L) { return active[L]; });
    }).map(function (m) {
      var primary = LAYER_PRIORITY.find(function (L) { return m.layers.indexOf(L) >= 0 && active[L]; }) || m.layers[0];
      return { lat: m.lat, lng: m.lng, color: LAYER_COLOR[primary] || '#94a3b8', name: m.name };
    });
  }
  var applyLayers = function () {};   // replaced once globe boots

  // ── 2. Progressive enhancement: the 3D globe (skipped on weak/!webgl) ──
  function bootGlobe() {
    if (!canvas) return;
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var small = window.matchMedia('(max-width: 860px)').matches;
    if (small || reduce || (navigator.hardwareConcurrency || 4) <= 2) return;
    try {
      var t = document.createElement('canvas');
      if (!(t.getContext('webgl2') || t.getContext('webgl') || t.getContext('experimental-webgl'))) return;
    } catch (e) { return; }
    var U = root.dataset;
    if (!U.three || !U.globe) return;

    var booted = false;
    var start = function () { if (booted) return; booted = true; build().catch(function () {}); };
    setTimeout(start, 800);   // reliable trigger (rIC can be throttled in bg tabs)
    if ('requestIdleCallback' in window) requestIdleCallback(start, { timeout: 2000 });

    function loadScript(src) {
      return new Promise(function (res, rej) {
        var s = document.createElement('script'); s.src = src; s.async = true;
        s.onload = res; s.onerror = rej; document.head.appendChild(s);
      });
    }

    async function build() {
      await loadScript(U.three); await loadScript(U.globe);
      var THREE = window.THREE, ThreeGlobe = window.ThreeGlobe;
      if (!THREE || !ThreeGlobe) return;

      var w = canvas.clientWidth || 700, h = canvas.clientHeight || 700;
      var renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setSize(w, h, false);
      var scene = new THREE.Scene();
      scene.add(new THREE.AmbientLight(0xbfc6d0, 1.1));
      var dl = new THREE.DirectionalLight(0xffffff, 0.5); dl.position.set(-1, 0.6, 1); scene.add(dl);

      var globe = new ThreeGlobe({ animateIn: true })
        .globeImageUrl(U.texNight)
        .showAtmosphere(true).atmosphereColor('#00e89a').atmosphereAltitude(0.18)
        .pointColor('color').pointLat('lat').pointLng('lng').pointAltitude(0.02).pointRadius(0.45);
      if (U.texBump) globe.bumpImageUrl(U.texBump);
      scene.add(globe);

      // country outlines + featured-market highlight
      if (U.geo) {
        try {
          var gj = await fetch(U.geo).then(function (r) { return r.json(); });
          var FOCUS = { GB: 1, KZ: 1, SA: 1, TR: 1 };
          function iso(f) { var p = f.properties || {}; return p.ISO_A2 || p.iso_a2 || ''; }
          globe.polygonsData(gj.features || [])
            .polygonAltitude(function (f) { return FOCUS[iso(f)] ? 0.016 : 0.006; })
            .polygonCapColor(function (f) { return (focusISO && iso(f) === focusISO) ? 'rgba(0,232,154,0.30)' : (FOCUS[iso(f)] ? 'rgba(0,232,154,0.14)' : 'rgba(255,255,255,0.02)'); })
            .polygonSideColor(function () { return 'rgba(0,232,154,0.05)'; })
            .polygonStrokeColor(function (f) { return FOCUS[iso(f)] ? '#c9a84c' : 'rgba(255,255,255,0.08)'; });
        } catch (e) {}
      }

      applyLayers = function () { globe.pointsData(visibleMarkers()); if (globe.polygonsData) globe.polygonsData(globe.polygonsData()); };
      applyLayers();

      var camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 2000);
      var theta = Math.PI * 0.1, phi = Math.PI * 0.46, radius = 330, tTheta = theta, tPhi = phi;
      var MIN_PHI = Math.PI * 0.16, MAX_PHI = Math.PI * 0.84;
      var down = false, lx = 0, ly = 0;
      function place() {
        theta += (tTheta - theta) * 0.1; phi += (tPhi - phi) * 0.1;
        camera.position.set(radius * Math.sin(phi) * Math.sin(theta), radius * Math.cos(phi), radius * Math.sin(phi) * Math.cos(theta));
        camera.lookAt(0, 0, 0);
      }
      canvas.style.cursor = 'grab';
      canvas.addEventListener('pointerdown', function (e) { down = true; lx = e.clientX; ly = e.clientY; canvas.style.cursor = 'grabbing'; });
      window.addEventListener('pointerup', function () { down = false; canvas.style.cursor = 'grab'; });
      window.addEventListener('pointermove', function (e) {
        if (!down) return;
        tTheta -= (e.clientX - lx) * 0.005; tPhi = Math.max(MIN_PHI, Math.min(MAX_PHI, tPhi - (e.clientY - ly) * 0.005));
        lx = e.clientX; ly = e.clientY;
      });

      // gentle chip focus (NOT the cinematic country twin — that's a later phase)
      var CENTROID = {}; (DATA.countries || []).forEach(function (c) { CENTROID[c.iso] = c; });
      window.__leFocus = function (isoCode, on) {
        if (on && CENTROID[isoCode]) {
          var c = CENTROID[isoCode];
          tPhi = Math.max(MIN_PHI, Math.min(MAX_PHI, (90 - c.lat) * Math.PI / 180));
          tTheta = (c.lng) * Math.PI / 180;
        }
        applyLayers();
      };

      var running = true, auto = 0.0015, breathe = 0;
      function loop() {
        if (!running) return;
        if (!down && !focusISO) tTheta += auto;
        breathe += 0.016;
        var s = 1 + Math.sin(breathe * 0.5) * 0.012;   // breathing
        globe.scale.set(s, s, s);
        place(); renderer.render(scene, camera); requestAnimationFrame(loop);
      }
      function play() { if (!running) { running = true; loop(); } }
      function pause() { running = false; }
      document.addEventListener('visibilitychange', function () { document.hidden ? pause() : play(); });
      if ('IntersectionObserver' in window) new IntersectionObserver(function (es) { es.forEach(function (en) { en.isIntersecting ? play() : pause(); }); }).observe(canvas);
      window.addEventListener('resize', function () { var nw = canvas.clientWidth, nh = canvas.clientHeight; if (!nw || !nh) return; camera.aspect = nw / nh; camera.updateProjectionMatrix(); renderer.setSize(nw, nh, false); });

      place(); loop();
      requestAnimationFrame(function () { canvas.style.opacity = '1'; root.classList.add('le-3d-on'); });
    }
  }
})();
