# GCC Investor Pages — Indexing, Analytics & Conversion Reporting Checklist

Companion doc to the `gcc_investors` app (routes, content, SEO — see
`gcc_investors/views.py`, `seo.py`) and its analytics layer (`templates/_analytics_head.html`,
`templates/_analytics_body.html`, `ecoiq/context_processors.py`). Covers the
manual steps required in Google Search Console and Bing Webmaster Tools, plus
the recurring checks that keep the 8 GCC investor pages indexed and the
conversion numbers trustworthy.

The 8 pages:

| Page | English | Arabic |
|---|---|---|
| GCC hub | `/gcc-investors/` | `/ar/gcc-investors/` |
| Qatar | `/qatar/investors/` | `/ar/qa/investors/` |
| Saudi Arabia | `/saudi-arabia/investors/` | `/ar/sa/investors/` |
| Kuwait | `/kuwait/investors/` | `/ar/kw/investors/` |

---

## 1. One-time setup — env vars

Nothing in §2–5 below activates until these are set as environment variables
on Render (Dashboard → the EcoIQ service → Environment). All are optional and
independently gated — setting one doesn't require the others. As of the
`feat/gcc-investor-analytics-indexing` branch, **none of these are set** —
the site currently has no GA4, no GTM, no Search Console verification, and no
Bing verification.

| Variable | Purpose | Where to get it |
|---|---|---|
| `GOOGLE_SITE_VERIFICATION` | Verifies domain ownership in Search Console via HTML meta tag | Search Console → Settings → Ownership verification → HTML tag method → copy the `content` value only |
| `BING_SITE_VERIFICATION` | Verifies domain ownership in Bing Webmaster Tools via meta tag | Bing Webmaster Tools → Settings → Verify ownership → Meta tag method → copy the `content` value only |
| `GTM_CONTAINER_ID` | Loads Google Tag Manager (recommended over raw GA4 — configure GA4 as a tag inside the container instead) | Your GTM container, format `GTM-XXXXXXX` |
| `GA4_MEASUREMENT_ID` | Loads GA4 directly via gtag.js — **only set this if you are not using GTM**; if both are set, GTM wins and gtag.js is skipped (see `templates/_analytics_head.html`) | GA4 property → Admin → Data Streams → your web stream, format `G-XXXXXXXXXX` |

After setting any of these on Render, redeploy and re-run the "URL Inspection"
step in §3 to confirm the tag/meta appears live.

---

## 2. Sitemap submission

The sitemap already includes all 8 URLs automatically (`companies/sitemaps.py`
→ `StaticSitemap._pages`) — verified in `gcc_investors/tests.py`
(`SitemapTests`) and directly against production. Live at:

```
https://ecoiq.uk/sitemap.xml
```

### Google Search Console

1. Sign in at [search.google.com/search-console](https://search.google.com/search-console) with a Google account that has (or can be granted) access to the `ecoiq.uk` property.
2. If the property doesn't exist yet: **Add property** → **Domain** → `ecoiq.uk` → follow the DNS TXT verification flow, **or** use **URL prefix** → `https://ecoiq.uk` → **HTML tag** method → copy the tag's `content` value into `GOOGLE_SITE_VERIFICATION` (see §1) → deploy → click **Verify**.
3. Left sidebar → **Sitemaps**.
4. Under "Add a new sitemap", enter `sitemap.xml` (relative to the verified property) → **Submit**.
5. Status should move from "Pending" to "Success" within a few hours to ~1 day. If it errors, open it and check the reported line/URL.

### Bing Webmaster Tools

1. Sign in at [www.bing.com/webmasters](https://www.bing.com/webmasters). Bing supports **importing directly from Google Search Console** (Settings → Import from Google Search Console) once GSC is verified — this is the fastest path and also imports the sitemap.
2. If adding manually instead: **Add a site** → `https://ecoiq.uk` → **Meta tag** verification method → copy the tag's `content` value into `BING_SITE_VERIFICATION` (see §1) → deploy → click **Verify**.
3. Left sidebar → **Sitemaps** → **Submit sitemap** → enter `https://ecoiq.uk/sitemap.xml` → **Submit**.

---

## 3. URL inspection checklist

Run this for each of the 8 URLs after first submitting the sitemap, and again
any time a page's content or SEO markup changes.

- [ ] **URL is on Google**: Search Console → URL Inspection → paste the full URL → confirm "URL is on Google" (or request indexing if not yet crawled).
- [ ] **Coverage**: no "Excluded" reason (noindex, duplicate, crawl anomaly). All 8 pages must show `<meta name="robots">` absent (i.e. indexable) — verified in `gcc_investors/tests.py`.
- [ ] **Mobile usability**: no mobile-usability errors reported for the URL.
- [ ] **Canonical**: Search Console's "Google-selected canonical" matches the page's own self-referencing `<link rel="canonical">` (the EN page canonicalizes to itself, not the AR variant, and vice versa).
- [ ] **hreflang**: no hreflang errors in Search Console's International Targeting report (once it has enough data) — each EN/AR pair should reciprocally reference each other plus `x-default` on the hub.
- [ ] **Rich results**: Search Console's Rich Results report picks up the page's JSON-LD (`Organization`, `Service`, `BreadcrumbList`, `WebPage`) without errors.
- [ ] **Page fetch renders correctly**: "View Crawled Page" screenshot in URL Inspection matches the live page (catches JS-rendering or blocked-resource issues).

---

## 4. Weekly SEO monitoring checklist

A 15-minute weekly check, ideally the same day each week:

- [ ] **Search Console → Coverage**: no new "Excluded" or "Error" pages among the 8 URLs.
- [ ] **Search Console → Performance**: filter by page path `/gcc-investors/`, `/qatar/investors/`, `/saudi-arabia/investors/`, `/kuwait/investors/` (and `/ar/...` equivalents) — check impressions/clicks trend, and note any sudden drop (often signals a deindexing or ranking issue worth investigating same-day).
- [ ] **Search Console → Performance → Queries**: skim the query list for each country page against its target queries (§5) — are we appearing for them at all, and at roughly what position?
- [ ] **Bing Webmaster Tools → Site Explorer**: spot-check crawl stats and any reported errors.
- [ ] **`sitemap.xml` still returns 200** and still lists all 8 URLs (`curl -s https://ecoiq.uk/sitemap.xml | grep -c gcc-investors` as a quick sanity check alongside the other 3 country slugs).
- [ ] **`robots.txt` still returns 200** and none of the 8 paths have been accidentally added to a `Disallow` rule.
- [ ] **Spot-check one EN and one AR page live**: title, meta description, H1, canonical, hreflang, `lang`/`dir`, JSON-LD, language switcher, both legal disclaimers, no horizontal overflow on mobile — the same checklist used in the post-merge production verification for PR #201.
- [ ] **No regressions in internal linking**: homepage footer, `/pricing/`, `/amanah-autopilot/` still link to `/gcc-investors/`.

---

## 5. Target queries — Qatar, Saudi Arabia, Kuwait

Starting query set to track in Search Console's Performance report (filtered
per country page) and to inform future content additions. Not exhaustive —
expand based on what Performance data shows visitors are already finding the
pages for.

### Qatar (`/qatar/investors/`, `/ar/qa/investors/`)
- AI investment platform Qatar
- ESG scoring Qatar investors
- decision intelligence Qatar banks
- Islamic finance AI platform Qatar
- Qatar sovereign wealth fund technology partner
- climate transition intelligence Qatar
- الذكاء الاصطناعي للمستثمرين في قطر
- منصة تقييم الاستدامة قطر

### Saudi Arabia (`/saudi-arabia/investors/`, `/ar/sa/investors/`)
- AI decision intelligence Saudi Arabia
- ESG platform Saudi investors
- Vision 2030 AI transition intelligence
- Saudi family office AI platform
- industrial transition scoring KSA
- شركة ذكاء اصطناعي للمستثمرين السعوديين
- منصة الذكاء الاصطناعي رؤية 2030

### Kuwait (`/kuwait/investors/`, `/ar/kw/investors/`)
- AI investment intelligence Kuwait
- Kuwait sovereign investment technology
- ESG scoring platform Kuwait
- Islamic finance intelligence Kuwait
- الذكاء الاصطناعي لمستثمري الكويت
- منصة تقييم الشركات الكويت

### GCC-wide hub (`/gcc-investors/`, `/ar/gcc-investors/`)
- AI decision intelligence GCC
- GCC investor relations platform
- ESG scoring GCC institutions
- Gulf sovereign wealth AI platform
- الذكاء الاصطناعي لمستثمري الخليج

---

## 6. Conversion reporting checklist

The staff-only dashboard at `/request-access/investors/report/`
(`leads.views.investor_enquiry_report`, `@staff_member_required`) surfaces
enquiries by country, organisation type, type of interest, source page, UTM
campaign, submission date (last 30 days), and totals — read-only, no PII
beyond what's already visible in the Django admin changelist for the same
model.

- [ ] **Weekly**: open the report, compare total enquiries this week vs. last week's number (track manually or in the linked spreadsheet, if one exists).
- [ ] **Per-campaign**: for any live UTM campaign (`utm_campaign`), confirm its enquiry count in the report roughly matches expected traffic volume from that channel — a big mismatch (e.g. lots of clicks, zero enquiries) usually means a broken CTA link or a client-side JS error, not a genuine conversion problem.
- [ ] **Cross-check with GA4/GTM** (once configured per §1): the 6 client-side events below should show up in GA4's Realtime / Events report with the same relative volumes as the report's totals:
  - `gcc_investor_page_view` — fires once per page load on all 8 GCC investor pages.
  - `investor_briefing_click` — fires on any of the 4 "Request Investor Briefing" CTAs per page.
  - `investor_form_start` — fires once on the enquiry form, on first field interaction.
  - `investor_form_submit` — fires once on the success page, only immediately after a real submission (a session flag prevents it firing again on refresh or a bookmarked/direct visit to the success URL — see `leads.views.investor_enquiry_success`).
  - `investor_language_switch` — fires on the EN/AR toggle link, on both the GCC pages and the enquiry form page.
  - `enterprise_pricing_click` — fires on the "Enterprise pricing model" CTA linking to `/pricing/`.
- [ ] **PII check** (re-run periodically, not just at launch): none of these events ever carry `full_name`, `work_email`, `phone_whatsapp`, `message`, `job_title`, or the free-text organisation name — enforced by an allowlist in the shared `ecoiqTrack()` helper (`templates/_analytics_head.html`) and covered by automated tests in `leads/tests.py` (`InvestorConversionEventTests`, `InvestorFormStartEventTests`) and `gcc_investors/tests.py`.
- [ ] **No duplicate analytics scripts**: confirm exactly one of GTM or gtag.js loads per page, never both — automated tests cover this (`gcc_investors/tests.py` → `AnalyticsLoaderGtmTests`, `AnalyticsLoaderGtagTests`), but it's worth a manual spot-check in the browser Network tab after any change to `templates/_analytics_head.html` or `templates/base.html`.
