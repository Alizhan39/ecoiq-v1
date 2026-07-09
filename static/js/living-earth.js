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
  var FEATURED_ISO_ORDER = ['GB', 'KZ', 'SA', 'TR'];
  var active = { energy: true, infrastructure: true, capital: true, carbon: true, water: true };
  var intelActive = {};   // which "intelligence layers" toggles are on (empty = no emphasis filter)
  var revealMax = 5;   // layers revealed (staggered during a country flight)
  var DATA = null;

  var INTEL_LABELS = {
    climate_risk: 'Climate Risk', investment_opportunity: 'Investment Opportunity',
    modernisation_priority: 'Modernisation Priority', evidence_strength: 'Evidence Strength',
    stewardship_impact: 'Stewardship / Impact',
  };

  // ── 1. Always: fetch live data → populate the DOM HUD (works without WebGL) ──
  fetch(endpoint, { headers: { Accept: 'application/json' } })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      DATA = d; renderStats(d.stats); wireToggles(); wireIntelLayers(d.intelligence_layers_available);
      wireChips(d.countries); wireJump(d.countries); wirePanelDrag(); wirePanelSwipe(d.countries);
      wireResetView(); wireSignalsFeed(); bootGlobe();
    })
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
        btn.setAttribute('aria-pressed', active[L] ? 'true' : 'false');
        applyLayers();
      });
    });
  }

  // Intelligence-layer toggles are only ever shown when at least one featured
  // country genuinely has data for them (server-computed availability) — a
  // layer with zero real rows anywhere is never rendered as a toggle at all.
  function wireIntelLayers(availability) {
    root.querySelectorAll('[data-intel-layer]').forEach(function (btn) {
      var key = btn.dataset.intelLayer;
      if (!availability || !availability[key]) return;   // stays hidden
      btn.hidden = false;
      btn.addEventListener('click', function () {
        intelActive[key] = !intelActive[key];
        btn.classList.toggle('off', !intelActive[key]);
        btn.setAttribute('aria-pressed', intelActive[key] ? 'true' : 'false');
        applyIntelEmphasis();
      });
    });
  }

  var focusISO = null;
  function focusCountry(iso, countries) {
    if (focusISO === iso) { closeCountry(); return; }
    focusISO = iso;
    root.querySelectorAll('[data-iso]').forEach(function (c) { c.classList.toggle('active', c.dataset.iso === iso); });
    var jump = document.getElementById('le-jump'); if (jump) jump.value = iso;
    applyLayers();
    if (window.__leFlyTo) window.__leFlyTo(iso);   // desktop globe flight (no-op on mobile)
    openCountry(iso, countries);
  }

  function wireChips(countries) {
    root.querySelectorAll('[data-iso]').forEach(function (chip) {
      chip.addEventListener('click', function () { focusCountry(chip.dataset.iso, countries); });
    });
    var closeBtn = document.getElementById('le-panel-close');
    if (closeBtn) closeBtn.addEventListener('click', closeCountry);
  }

  // Simple, dependency-free "quick jump" — a native <select> works well on
  // mobile (large tap target, built-in accessibility) without inventing a
  // search/autocomplete widget from scratch for just 4 countries.
  function wireJump(countries) {
    var jump = document.getElementById('le-jump');
    if (!jump) return;
    jump.addEventListener('change', function () {
      if (jump.value) focusCountry(jump.value, countries);
    });
  }

  // "Reset view" — clears country focus and any active intelligence-layer
  // emphasis, returning every toggle to its default on-state. No page
  // reload: same lightweight DOM-only path as closeCountry()/applyLayers().
  function wireResetView() {
    var btn = document.getElementById('le-reset-view');
    if (!btn) return;
    btn.addEventListener('click', function () {
      closeCountry();
      Object.keys(intelActive).forEach(function (k) { intelActive[k] = false; });
      root.querySelectorAll('[data-intel-layer]').forEach(function (b) {
        b.classList.remove('off'); b.setAttribute('aria-pressed', 'false');
      });
      Object.keys(active).forEach(function (k) { active[k] = true; });
      root.querySelectorAll('[data-layer]').forEach(function (b) {
        b.classList.remove('off'); b.setAttribute('aria-pressed', 'true');
      });
      applyLayers();
    });
  }

  // ── Live intelligence signals feed (Phase 2) — real, already-persisted
  // EcoIQ records only (risk zones, opportunities, modernisation changes,
  // evidence, real agent activity). See core/globe.py globe_signals(). ──
  var SIGNAL_TYPE_LABEL = {
    risk: 'Risk', opportunity: 'Opportunity', change: 'Change',
    evidence_update: 'Evidence Update', agent_finding: 'Agent Finding',
  };
  function wireSignalsFeed() {
    var list = document.getElementById('le-signals-list');
    if (!list) return;
    var currentPeriod = 'latest';

    function load(period) {
      currentPeriod = period;
      setHTML('le-signals-list', '<div class="le-signals-empty">Loading…</div>');
      fetch('/api/globe/signals/?period=' + encodeURIComponent(period), { headers: { Accept: 'application/json' } })
        .then(function (r) { return r.json(); })
        .then(renderSignals)
        .catch(function () { setHTML('le-signals-list', '<div class="le-signals-empty">Signals temporarily unavailable.</div>'); });
    }

    function renderSignals(d) {
      var note = document.getElementById('le-signals-note');
      if (d.historical_coverage_developing) {
        note.hidden = false;
        note.textContent = 'Historical intelligence coverage is still developing.';
      } else {
        note.hidden = true;
      }
      if (!d.signals || !d.signals.length) {
        setHTML('le-signals-list', '<div class="le-signals-empty">No real signals recorded for this period yet.</div>');
        return;
      }
      setHTML('le-signals-list', d.signals.map(function (s) {
        var tagLabel = SIGNAL_TYPE_LABEL[s.type] || s.type;
        var inner = '<span class="le-sig-tag ' + esc(s.type) + '">' + esc(tagLabel) + '</span>' +
          '<span class="le-signal-body"><span class="le-signal-title">' + esc(s.title) + '</span>' +
          '<span class="le-signal-detail">' + esc(s.iso) + (s.detail ? ' · ' + esc(s.detail) : '') + '</span></span>';
        return s.link ? '<div class="le-signal"><a href="' + esc(s.link) + '">' + inner + '</a></div>'
          : '<div class="le-signal">' + inner + '</div>';
      }).join(''));
    }

    root.querySelectorAll('.le-period').forEach(function (btn) {
      btn.addEventListener('click', function () {
        root.querySelectorAll('.le-period').forEach(function (b) {
          b.classList.toggle('active', b === btn); b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
        });
        load(btn.dataset.period);
      });
    });
    load(currentPeriod);
  }

  function closeCountry() {
    focusISO = null;
    var jump = document.getElementById('le-jump'); if (jump) jump.value = '';
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

    // intelligence layers — real per-country data, honest fallback text when absent
    setHTML('le-panel-intel', Object.keys(INTEL_LABELS).map(function (key) {
      var layer = (d.intelligence || {})[key] || {};
      var detail = layer.available
        ? '<span class="d">' + esc(layer.label) + '</span>'
        : '<span class="d na">' + esc(layer.label || 'Limited EcoIQ coverage') + '</span>';
      var demoBadge = layer.is_demo ? '<span class="badge demo">demo</span>' : '';
      return '<div class="le-intel-row" data-intel-key="' + key + '"><span class="lab">' + esc(INTEL_LABELS[key]) + detail + '</span>' + demoBadge + '</div>';
    }).join(''));
    applyIntelEmphasis();

    // recommended next action — deterministic, never fabricated (see core/globe.py)
    var actionBox = document.getElementById('le-panel-action');
    if (d.recommended_next_action) {
      actionBox.hidden = false;
      actionBox.innerHTML = '<h5>Recommended next action</h5><p>' + esc(d.recommended_next_action) + '</p>';
    } else {
      actionBox.hidden = true;
    }

    // action links — every href is a real, existing EcoIQ route (see core/globe.py actions block)
    var ACTION_LABELS = {
      country_intelligence: 'Open Country Intelligence', geo_intelligence: 'View Geo Intelligence',
      decision_studio: 'Ask EcoIQ Decision Studio', ai_agents: 'Analyse with AI Agents', evidence: 'View Evidence',
    };
    setHTML('le-panel-actions', Object.keys(ACTION_LABELS).map(function (key) {
      var href = (d.actions || {})[key];
      if (!href) return '';
      return '<a href="' + esc(href) + '">' + esc(ACTION_LABELS[key]) + ' →</a>';
    }).join(''));

    renderEconomicSignals(d.economic_signals);
    renderCapitalFlows(d.capital_flows);
    renderTradeAndRevenue(d.trade_and_revenue_composition);
  }

  function factRow(label, value, formatter) {
    var v = (value === null || value === undefined)
      ? '<span class="val na">Insufficient evidence</span>'
      : '<span class="val">' + esc(formatter ? formatter(value) : value) + '</span>';
    return '<div class="le-fact"><span class="lab">' + esc(label) + '</span>' + v + '</div>';
  }
  function fmtUsd(n) {
    if (n >= 1e12) return '$' + (n / 1e12).toFixed(1) + 'T';
    if (n >= 1e9) return '$' + (n / 1e9).toFixed(1) + 'B';
    if (n >= 1e6) return '$' + (n / 1e6).toFixed(1) + 'M';
    return '$' + n;
  }
  function fmtPct(n) { return n + '%'; }

  // Real CountryProfile macro fields only (core/globe.py _economic_signals) —
  // never computed or invented here.
  function renderEconomicSignals(e) {
    var el = document.getElementById('le-panel-economic');
    if (!el) return;
    if (!e) { el.innerHTML = '<div class="le-honest-stub">Limited EcoIQ coverage.</div>'; return; }
    el.innerHTML =
      factRow('GDP', e.gdp_usd, fmtUsd) +
      factRow('GDP growth', e.gdp_growth_pct, fmtPct) +
      factRow('Inflation', e.inflation_pct, fmtPct) +
      factRow('Population', e.population_millions, function (v) { return v + 'M'; }) +
      factRow('Industrial share of GDP', e.industrial_gdp_share, fmtPct) +
      factRow('Renewable electricity share', e.renewable_energy_share, fmtPct) +
      factRow('Fossil fuel dependency', e.fossil_fuel_dependency, fmtPct) +
      factRow('CO₂ (megatonnes/yr)', e.co2_megatonnes) +
      (e.data_sources ? '<div class="le-panel-source">Source: ' + esc(e.data_sources) + '</div>' : '');
  }

  // Real CountryProfile financing fields + the country's real top
  // InvestmentGeoOpportunity (core/globe.py _capital_flows) — never a
  // fabricated inflow/outflow figure.
  function renderCapitalFlows(c) {
    var el = document.getElementById('le-panel-capital');
    if (!el) return;
    if (!c) { el.innerHTML = '<div class="le-honest-stub">Limited EcoIQ coverage.</div>'; return; }
    var html = factRow('Estimated transition financing gap', c.estimated_transition_gap_usd, fmtUsd) +
      factRow('Green finance available', c.green_finance_available_usd, fmtUsd);
    if (c.top_opportunity) {
      html += '<div class="le-fact"><span class="lab">Top real opportunity</span>' +
        '<span class="val">' + esc(c.top_opportunity.title) + ' (' + esc(c.top_opportunity.investment_score) + '/100)</span></div>';
    }
    el.innerHTML = html;
  }

  // Government revenue composition and exports/imports have no real EcoIQ
  // data source today (see core/globe.py _trade_and_revenue_composition) —
  // this renders the honest "not yet available" reason, never a fabricated
  // pie chart or trade figure.
  function renderTradeAndRevenue(t) {
    var el = document.getElementById('le-panel-trade');
    if (!el) return;
    el.innerHTML = '<div class="le-honest-stub">' + esc((t && t.reason) || 'Not yet available.') + '</div>';
  }

  // Toggling an intelligence layer emphasises that metric row in the open
  // panel (dims the rest) — a lightweight visual filter, no 3D dependency,
  // so it works identically with or without the WebGL globe.
  function applyIntelEmphasis() {
    var anyActive = Object.keys(intelActive).some(function (k) { return intelActive[k]; });
    document.querySelectorAll('#le-panel-intel .le-intel-row').forEach(function (row) {
      var isActive = !!intelActive[row.dataset.intelKey];
      row.classList.toggle('dim', anyActive && !isActive);
      row.classList.toggle('emph', isActive);
    });
  }

  // Mobile bottom-sheet: swipe down to dismiss, without blocking normal page
  // scroll elsewhere on the page (touch-action:none is scoped to the panel
  // itself in CSS, only while it's open).
  function wirePanelDrag() {
    var panel = document.getElementById('le-panel');
    var handle = panel && panel.querySelector('.le-panel-drag');
    if (!panel || !handle) return;
    var startY = 0, dragging = false, panelHeight = 0;
    handle.addEventListener('pointerdown', function (e) {
      if (!panel.classList.contains('open')) return;
      dragging = true; startY = e.clientY; panelHeight = panel.getBoundingClientRect().height;
      panel.classList.add('le-dragging');
      handle.setPointerCapture && handle.setPointerCapture(e.pointerId);
    });
    handle.addEventListener('pointermove', function (e) {
      if (!dragging) return;
      var dy = Math.max(0, e.clientY - startY);
      panel.style.transform = 'translateY(' + dy + 'px)';
    });
    function endDrag(e) {
      if (!dragging) return;
      dragging = false;
      panel.classList.remove('le-dragging');
      var dy = Math.max(0, (e.clientY || startY) - startY);
      panel.style.transform = '';
      if (panelHeight && dy > panelHeight * 0.25) closeCountry();
    }
    handle.addEventListener('pointerup', endDrag);
    handle.addEventListener('pointercancel', endDrag);
  }

  // Mobile: swipe left/right on the panel header to move between the 4
  // featured countries (wraps around) — a real touch gesture distinct from
  // the drag-to-dismiss handle above (different element, horizontal axis only).
  function wirePanelSwipe(countries) {
    var panel = document.getElementById('le-panel');
    var head = panel && panel.querySelector('.le-panel-head');
    if (!panel || !head) return;
    var startX = 0, startY = 0, tracking = false;
    head.addEventListener('pointerdown', function (e) { tracking = true; startX = e.clientX; startY = e.clientY; });
    head.addEventListener('pointerup', function (e) {
      if (!tracking) return;
      tracking = false;
      var dx = e.clientX - startX, dy = e.clientY - startY;
      if (Math.abs(dx) < 40 || Math.abs(dx) < Math.abs(dy) * 1.5) return;   // not a clear horizontal swipe
      var order = FEATURED_ISO_ORDER;
      var i = order.indexOf(focusISO);
      if (i === -1) return;
      var next = dx < 0 ? order[(i + 1) % order.length] : order[(i - 1 + order.length) % order.length];
      focusCountry(next, countries);
    });
  }

  // Simple grid-based clustering + LOD: when many markers would render at
  // once, nearby markers (within ~3° lat/lng — roughly the same jitter
  // radius core/globe.py's representative offsets already use) are merged
  // into a single point sized by count, instead of drawing every point.
  // Keeps the point-count (and therefore render cost) bounded regardless of
  // how many real companies a future data expansion adds.
  var CLUSTER_THRESHOLD = 12;    // only cluster once there's enough real markers to matter
  var CLUSTER_CELL_DEGREES = 3;
  function clusterMarkers(markers) {
    if (markers.length <= CLUSTER_THRESHOLD) return markers;
    var cells = {};
    markers.forEach(function (m) {
      var key = Math.round(m.lat / CLUSTER_CELL_DEGREES) + ':' + Math.round(m.lng / CLUSTER_CELL_DEGREES);
      if (!cells[key]) cells[key] = [];
      cells[key].push(m);
    });
    return Object.keys(cells).map(function (key) {
      var group = cells[key];
      if (group.length === 1) return group[0];
      var lat = group.reduce(function (s, m) { return s + m.lat; }, 0) / group.length;
      var lng = group.reduce(function (s, m) { return s + m.lng; }, 0) / group.length;
      return { lat: lat, lng: lng, color: group[0].color, name: group.length + ' markers', count: group.length };
    });
  }

  function visibleMarkers() {
    if (!DATA) return [];
    var revealed = LAYER_PRIORITY.slice(0, revealMax);
    var markers = DATA.markers.filter(function (m) {
      if (focusISO && m.country !== focusISO) return false;
      return m.layers.some(function (L) { return active[L] && revealed.indexOf(L) >= 0; });
    }).map(function (m) {
      var primary = LAYER_PRIORITY.find(function (L) { return m.layers.indexOf(L) >= 0 && active[L]; }) || m.layers[0];
      return { lat: m.lat, lng: m.lng, color: LAYER_COLOR[primary] || '#94a3b8', name: m.name };
    });
    return clusterMarkers(markers);
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
        .pointColor('color').pointLat('lat').pointLng('lng').pointAltitude(0.02)
        .pointRadius(function (m) { return m.count ? Math.min(0.45 + m.count * 0.05, 1.1) : 0.45; });
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
