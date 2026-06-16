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
  var revealMax = 5;   // layers revealed (staggered during a country flight)
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
        if (focusISO === iso) { closeCountry(); return; }
        focusISO = iso;
        root.querySelectorAll('[data-iso]').forEach(function (c) { c.classList.toggle('active', c.dataset.iso === iso); });
        applyLayers();
        if (window.__leFlyTo) window.__leFlyTo(iso);   // desktop globe flight (no-op on mobile)
        openCountry(iso, countries);
      });
    });
    var closeBtn = document.getElementById('le-panel-close');
    if (closeBtn) closeBtn.addEventListener('click', closeCountry);
  }

  function closeCountry() {
    focusISO = null;
    root.querySelectorAll('[data-iso]').forEach(function (c) { c.classList.remove('active'); });
    var panel = document.getElementById('le-panel');
    if (panel) { panel.classList.remove('open'); panel.setAttribute('aria-hidden', 'true'); }
    applyLayers();
    if (window.__leFlyTo) window.__leFlyTo(null);
  }

  // ── Country Intelligence Panel (works with or without the 3D globe) ──
  function openCountry(iso, countries) {
    var c = (countries || []).find(function (x) { return x.iso === iso; });
    if (!c) return;
    var panel = document.getElementById('le-panel');
    panel.classList.add('open'); panel.setAttribute('aria-hidden', 'false');
    setText('le-panel-name', c.name);
    setHTML('le-panel-stats', 'loading…');
    fetch('/api/globe/country/' + c.slug + '/', { headers: { Accept: 'application/json' } })
      .then(function (r) { return r.json(); }).then(renderPanel)
      .catch(function () { setHTML('le-panel-stats', 'Country data temporarily unavailable.'); });
  }
  function setHTML(id, h) { var el = document.getElementById(id); if (el) el.innerHTML = h; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (m) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m]; }); }

  function renderPanel(d) {
    setText('le-panel-name', d.name);
    setHTML('le-panel-stats', '<b>' + d.stats.companies + '</b> companies · <b>' + d.stats.evidence +
      '</b> evidence · <b>' + d.stats.datapoints + '</b> datapoints');
    var banner = document.getElementById('le-panel-banner');
    if (d.no_registry) { banner.hidden = false; banner.textContent = 'Company registry — data expansion in progress.'; }
    else if (d.data_expansion) { banner.hidden = false; banner.textContent = d.stats.companies + ' companies registered · evidence harvest in progress.'; }
    else { banner.hidden = true; }

    // scores — real value or honest "Insufficient evidence"
    setHTML('le-panel-scores', d.scores.map(function (s) {
      var v = (s.value === null || s.value === undefined)
        ? '<span class="val na">Insufficient evidence</span>'
        : '<span class="val">' + esc(s.value) + '</span>';
      return '<div class="le-score"><span class="lab">' + esc(s.label) + '</span>' + v +
        '<button class="why" data-why="' + esc(s.label) + '">Why?</button></div>';
    }).join(''));

    // companies
    setHTML('le-panel-companies', (d.companies.length ? d.companies.map(function (co) {
      var op = (co.operating_profit != null) ? '£' + co.operating_profit + 'm' : '—';
      return '<div class="le-co"><a href="/evidence/' + esc(co.slug) + '/">' + esc(co.company_name) +
        '</a><span class="m">' + esc(co.sector) + ' · ' + op + ' · ' + co.evidence_count + ' ev</span></div>';
    }).join('') : '<div class="le-co"><span class="m">No companies tracked yet.</span></div>'));

    var link = document.getElementById('le-panel-link');
    link.href = d.why.country_url;
    setText('le-panel-disc', d.disclaimer);

    // "Why?" drill-down (evidence-grounded checklist + links)
    var why = document.getElementById('le-panel-why');
    function showWhy(metricLabel) {
      var rows = d.why.checklist.map(function (k) {
        return '<div class="le-chk ' + (k.ok ? 'ok' : 'no') + '"><span class="mk">' + (k.ok ? '✓' : '⚠') + '</span>' + esc(k.label) + '</div>';
      }).join('');
      why.innerHTML = '<h5>Why “' + esc(metricLabel) + '”?</h5>' +
        '<div style="font-family:var(--mono);font-size:.66rem;color:var(--muted);margin-bottom:.5rem">Source: ' + esc(d.score_source) + ' · basis: ' + esc(d.why.confidence_basis) + '</div>' +
        rows +
        '<div style="margin-top:.6rem"><a href="' + d.why.evidence_url + '">View evidence ↗</a> &nbsp; <a href="' + d.why.country_url + '">Full country ↗</a></div>';
      why.hidden = false;
    }
    document.querySelectorAll('#le-panel-scores .why').forEach(function (b) {
      b.addEventListener('click', function () { showWhy(b.dataset.why); });
    });
  }

  function visibleMarkers() {
    if (!DATA) return [];
    var revealed = LAYER_PRIORITY.slice(0, revealMax);
    return DATA.markers.filter(function (m) {
      if (focusISO && m.country !== focusISO) return false;
      return m.layers.some(function (L) { return active[L] && revealed.indexOf(L) >= 0; });
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
      var theta = Math.PI * 0.1, phi = Math.PI * 0.46, radius = 330;
      var tTheta = theta, tPhi = phi, tRadius = radius;
      var MIN_PHI = Math.PI * 0.16, MAX_PHI = Math.PI * 0.84;
      var down = false, lx = 0, ly = 0;
      function place() {
        // eased flight: ~0.07/frame lerp ≈ 1–1.5s settle
        theta += (tTheta - theta) * 0.07; phi += (tPhi - phi) * 0.07; radius += (tRadius - radius) * 0.07;
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

      // Country Twin flight: 1–2s eased camera flight + staggered layer reveal.
      var CENTROID = {}; (DATA.countries || []).forEach(function (c) { CENTROID[c.iso] = c; });
      var revealTimer = null;
      window.__leFlyTo = function (isoCode) {
        if (revealTimer) { clearInterval(revealTimer); revealTimer = null; }
        if (isoCode && CENTROID[isoCode]) {
          var c = CENTROID[isoCode];
          tPhi = Math.max(MIN_PHI, Math.min(MAX_PHI, (90 - c.lat) * Math.PI / 180));
          tTheta = (c.lng) * Math.PI / 180;
          tRadius = 235;                          // fly closer
          revealMax = 0;                          // layers gradually appear during flight
          applyLayers();
          revealTimer = setInterval(function () {
            revealMax = Math.min(5, revealMax + 1); applyLayers();
            if (revealMax >= 5) { clearInterval(revealTimer); revealTimer = null; }
          }, 260);
        } else {
          tRadius = 330; revealMax = 5; applyLayers();   // back to world view
        }
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
