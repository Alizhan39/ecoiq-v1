/**
 * ecoiq-embed.js — EcoIQ badge/risk-card auto-loader.
 *
 * Finds every `[data-ecoiq-embed]` placeholder on the page and replaces it
 * with the matching public, unauthenticated iframe. No API key involved —
 * this script (and the endpoints it points at) only ever serves already-
 * public company data.
 *
 * Usage:
 *   <div data-ecoiq-embed="risk-card" data-company="acme-co" data-theme="light"></div>
 *   <script src="https://ecoiq.uk/static/js/ecoiq-embed.js" async></script>
 */
(function () {
  var ORIGIN = (document.currentScript && new URL(document.currentScript.src).origin) || window.location.origin;

  function mountRiskCard(el) {
    var company = el.getAttribute('data-company');
    if (!company) return;
    var theme = el.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    var iframe = document.createElement('iframe');
    iframe.src = ORIGIN + '/embed/' + encodeURIComponent(company) + '/risk-card/?theme=' + theme;
    iframe.width = el.getAttribute('data-width') || '320';
    iframe.height = el.getAttribute('data-height') || '260';
    iframe.loading = 'lazy';
    iframe.title = 'EcoIQ Risk Card';
    iframe.style.border = '0';
    iframe.style.borderRadius = '10px';
    el.replaceWith(iframe);
  }

  function init() {
    var nodes = document.querySelectorAll('[data-ecoiq-embed="risk-card"]');
    for (var i = 0; i < nodes.length; i++) mountRiskCard(nodes[i]);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
