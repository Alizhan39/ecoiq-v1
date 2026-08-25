---
name: ecoiq-seo-audit
description: Audit or change EcoIQ's discoverability — robots.txt, sitemaps, canonical URLs, redirects, title/description metadata, Open Graph, structured data, hreflang, internal linking, page speed, and AI-search (LLM crawler) visibility. Use when adding a public page, changing URLs, or asked why something is not being indexed or previewed correctly. Not for authenticated or admin surfaces, which are intentionally not indexed.
---

# EcoIQ SEO audit

## Run the audit, don't eyeball it

```bash
.venv/bin/python manage.py seo_audit            # human-readable findings
.venv/bin/python manage.py seo_audit --strict   # exit 1 on any ERROR (CI gate)
.venv/bin/python manage.py seo_audit --explain  # also lists what it cannot check
```

Implementation: [`core/management/commands/seo_audit.py`](../../../core/management/commands/seo_audit.py).
It is **offline by design** — it renders `/robots.txt` and `/sitemap.xml`
through Django's test client and reads templates and static files from disk.
It never fetches the production domain, so it cannot report a live-production
result it has no access to. Do not "improve" it by adding a network call.

## Current state (recorded 2026-08-25, this branch)

`17 passed, 1 warning, 1 error`.

**ERROR — every page's `og:image` is a 404.** `templates/base.html:22` and
`templates/contact.html:12` both point at
`https://ecoiq.uk/static/brand/ecoiq-og.png`, which does not exist —
`static/brand/` contains only `ecoiq-logo.svg`, `ecoiq-icon.svg`,
`ecoiq-icon-mono.svg`. Every share on LinkedIn, X, Slack, and WhatsApp
renders with no preview image.
*Decision required, not auto-fixed:* `static/img/og-card.svg` exists and is
plausible source material, but SVG is not a supported Open Graph image
format on the major platforms — this needs a real 1200×630 PNG, which is a
brand asset decision (see `ecoiq-brand`), not something to generate blind.

**WARN — no `twitter:card` meta** in `base.html`, so X falls back to a small
preview even once the image exists.

Verified good: robots.txt serves and declares its sitemap; the wildcard group
is not blanket-disallowed (Bytespider, CCBot and PetalBot are deliberately
blocked in their own groups — that is correct, not a de-indexing bug);
sitemap serves 424 URLs; all nine required head tags present; one canonical
host; no hreflang, which is right for a one-language site; JSON-LD on
`companies/detail.html`.

## Rules for new public pages

1. Extend `base.html` — never hand-roll a `<head>`. Override the
   `title` / `meta_description_content` / `og_title` / `og_description`
   blocks. A page that inherits the site-wide description is a duplicate.
2. If it should be indexed, add its URL name to
   `StaticSitemap._pages` in [`companies/sitemaps.py`](../../../companies/sitemaps.py).
   `seo_audit` fails if a name there stops resolving.
3. If it should not be indexed, add a `Disallow` to `templates/robots.txt`
   **and** keep it out of the sitemap — the audit flags the contradiction.
4. Changing a URL means adding a redirect. There is no redirect map in this
   repo; a 404 on a previously indexed URL is a real cost.
5. Reference static assets with `{% static %}`. Absolute
   `https://ecoiq.uk/static/...` URLs bypass the manifest and 404 silently —
   that is exactly how the `og:image` bug survived.

## Heavy endpoints stay disallowed

`robots.txt` blocks `/companies/*/report.pdf`, `/*ml-insights.json`, and
`/companies/reports/` because they run WeasyPrint and scikit-learn per hit
and caused 502s on Render's 512 MB tier. Do not "open these up for SEO."
Expose a cached HTML summary instead if the content needs to be indexed.

## AI-search discoverability

`ClaudeBot`, `GPTBot`, and `OAI-SearchBot` have their own groups: allowed to
read pages, blocked from PDF/ML endpoints, `Crawl-delay: 30`. Keep that
shape for new AI crawlers — allow content, block compute.

For LLM answerability, the lever is content structure, not markup tricks:
one clear claim per heading, definitions near the term, tables over prose for
comparable figures. Any factual or regulatory claim on an indexed page still
goes through `ecoiq-impact-claims` and `ecoiq-regulatory-review` — an SEO
motive never relaxes claim discipline.

## Out of scope here

Index coverage, Core Web Vitals field data, backlinks, and live redirect
chains need Search Console / CrUX / a paid API and network access. `--explain`
lists them. Report them as unavailable; never estimate them.
