"""
core/spa.py — Django serves the React single-page app.

ONE ORIGIN, ONE SERVICE
-----------------------
`ecoiq.uk` serves the React app, `/api/*`, `/admin/*` and the server-owned
technical endpoints from a single Django service. No second hostname, no
separate static host, no SSR framework.

That is not a compromise. The API is session-authenticated, and a session
cookie plus CSRF across two origins means SameSite=None, CORS preflights and a
credential surface that exists only to serve an architecture nobody asked for.
Same-origin keeps the boundary that api/v2_session.py was built against.

WHAT THIS IS NOT
----------------
It is not server-side rendering. The body is rendered by React in the browser.
The only thing Django contributes to the document is the contents of <head>:
title, description, canonical, Open Graph, and — where truthful — robots. See
`head_tags` for why that is enough, and `docs/product/FRONTEND_DEPLOYMENT.md`
for the conditions under which real SSR should be reconsidered.

THE CATCH-ALL, AND THE THING IT MUST NEVER DO
---------------------------------------------
`spa_catch_all` is registered LAST in the root URLconf, so it only sees paths
that matched nothing else. The failure mode that matters is a mistyped or
retired API route falling through to it and answering `200 text/html` — an API
client would parse a React shell as a failed JSON decode instead of seeing the
404 that actually happened. So server-owned prefixes are rejected explicitly,
before anything else, and `tests_spa.py` asserts it for every one of them.

Unknown FRONTEND paths get the shell with HTTP 404: a human sees the React
NotFound page, and a crawler sees the status code that is true. Serving 200 for
a page that does not exist is the same category of untruth as serving a score
for a company that has no evidence.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.utils.html import escape

#: The built artefact. Committed to the repository — see vite.config.ts for why
#: (Render's build environment runs Python only; Node is a build-time layer in
#: this repo, never a runtime dependency).
SPA_INDEX = Path(settings.BASE_DIR) / 'static' / 'spa' / 'index.html'

#: Everything Django owns. A path starting with one of these NEVER receives the
#: React shell — it gets a plain 404, so a client that asked for JSON is told
#: the truth in a form it can act on.
#:
#: `api/` is the one that matters most: without it, GET /api/v2/typo/ would
#: return an HTML 200.
SERVER_OWNED_PREFIXES: tuple[str, ...] = (
    'api/',
    'admin/',
    'static/',
    'media/',
    'billing/',      # includes the Stripe webhook registered in their dashboard
    'i18n/',
    'healthz',
    'readyz',
    'embed/',        # public embeddable badges — server-rendered by design
    'share/',        # tokenised report shares — server-owned
    'ingest/',
    'login/',
    'logout/',
    'robots.txt',
    'sitemap.xml',
    'favicon.ico',
)

#: Server-generated documents and data. A request for one of these that reached
#: the catch-all is a request for a file that does not exist; answering it with
#: an HTML shell would hand a PDF reader a web page.
SERVER_OWNED_SUFFIXES: tuple[str, ...] = (
    '.pdf', '.json', '.xml', '.csv', '.txt', '.ics', '.zip', '.map',
    '.js', '.css', '.png', '.jpg', '.jpeg', '.svg', '.webp', '.ico', '.woff2',
)

_HEAD_BLOCK = re.compile(
    r'<!--ecoiq:head:start-->.*?<!--ecoiq:head:end-->', re.DOTALL)


class SpaArtefactMissing(RuntimeError):
    """The built SPA is absent or malformed. Deliberately fatal."""


def _shell() -> str:
    """
    The built index.html.

    Cached for the process lifetime in production: it is an immutable build
    artefact, a deploy starts a new process, and re-reading it per request
    would put a disk hit on every page view.

    NOT cached under DEBUG, and that is not a convenience. Caching it in
    development reproduces the single worst failure this setup has: the shell
    names content-hashed assets, so a cached shell survives a rebuild and goes
    on pointing at a bundle that no longer exists. The page then renders
    completely blank, with one 404 in the console and no server-side error at
    all — and it looks like a routing bug, which is where the next hour goes.

    Found exactly that way: `runserver --noreload`, an `npm run build`, and a
    white page.
    """
    if getattr(settings, 'DEBUG', False):
        return _read_shell()
    return _cached_shell()


@lru_cache(maxsize=1)
def _cached_shell() -> str:
    return _read_shell()


def _read_shell() -> str:
    """
    Read and validate the artefact.

    Fails loudly rather than degrading. A missing artefact means the frontend
    was never built, and serving a blank page would turn a build error into a
    silent production outage that looks like a routing bug.
    """
    try:
        html = SPA_INDEX.read_text(encoding='utf-8')
    except OSError as exc:
        raise SpaArtefactMissing(
            f'The SPA build artefact is missing at {SPA_INDEX}. Run '
            '`npm --prefix frontend/web ci && npm --prefix frontend/web run '
            'build` and commit the result.') from exc

    if not _HEAD_BLOCK.search(html):
        raise SpaArtefactMissing(
            f'{SPA_INDEX} has no <!--ecoiq:head:start--> block, so per-route '
            'metadata cannot be injected. frontend/web/index.html must keep '
            'the markers.')
    return html


def reload_shell() -> None:
    """Drop the cached shell. For tests, and after a rebuild in a long-lived
    process."""
    _cached_shell.cache_clear()


def site_url() -> str:
    return str(getattr(settings, 'SITE_URL', 'https://ecoiq.uk')).rstrip('/')


def head_tags(*, title: str, description: str, path: str,
              robots: str = '') -> str:
    """
    The <head> for one route.

    Title, description, canonical and Open Graph — the four things a crawler
    and a link preview actually read, and the four things a client-rendered
    page would otherwise have none of.

    Everything is escaped. `title` and `description` are module constants
    today, but `company_meta` builds them from database values, and an
    organisation named `Foo & Bar "Ltd"` must not be able to close an
    attribute.
    """
    canonical = f'{site_url()}{path}'
    tags = [
        f'<title>{escape(title)}</title>',
        f'<meta name="description" content="{escape(description)}" />',
        f'<link rel="canonical" href="{escape(canonical)}" />',
        '<meta property="og:type" content="website" />',
        f'<meta property="og:title" content="{escape(title)}" />',
        f'<meta property="og:description" content="{escape(description)}" />',
        f'<meta property="og:url" content="{escape(canonical)}" />',
        '<meta property="og:site_name" content="EcoIQ" />',
        '<meta name="twitter:card" content="summary" />',
    ]
    if robots:
        tags.append(f'<meta name="robots" content="{escape(robots)}" />')
    return '\n    '.join(tags)


def render_shell(*, title: str, description: str, path: str,
                 robots: str = '', status: int = 200) -> HttpResponse:
    """
    The React shell with this route's metadata substituted in.

    `no-store` on the document, deliberately. The shell names hashed asset
    files; a cached shell would keep pointing at the previous deploy's bundle
    long after that bundle stopped existing, which presents as a blank page
    nobody can reproduce. The assets themselves are immutable and cached hard —
    see `WHITENOISE_IMMUTABLE_FILE_TEST` in settings.py. Caching the cheap file
    and not the expensive ones would be exactly backwards.
    """
    html = _HEAD_BLOCK.sub(
        lambda _match: head_tags(
            title=title, description=description, path=path, robots=robots),
        _shell(),
        count=1,
    )
    response = HttpResponse(html, content_type='text/html; charset=utf-8',
                            status=status)
    response['Cache-Control'] = 'no-store, must-revalidate'
    return response


# ── Route metadata ───────────────────────────────────────────────────────────
#
# Every claim here is one the product can currently support. "Evidence-backed
# decision intelligence for companies, investments and projects" is the CURRENT
# capability; the four long-term verticals are not described as working, and no
# page below promises a score, a ranking or a count.

DEFAULT_DESCRIPTION = (
    'Evidence-backed decision intelligence for companies, investments and '
    'projects. EcoIQ publishes an assessment only where the evidence supports '
    'one.')

ROUTE_META: dict[str, dict[str, str]] = {
    '/': {
        'title': 'EcoIQ — Evidence-backed decision intelligence',
        'description': DEFAULT_DESCRIPTION,
    },
    '/intelligence': {
        'title': 'Intelligence — EcoIQ',
        'description': (
            'Assess an organisation against recorded evidence: what is known, '
            'how much of it is supported, and where the gaps are. No score is '
            'shown unless the evidence supports one.'),
    },
    '/projects': {
        'title': 'Projects — EcoIQ',
        'description': (
            'Interventions with a stated problem, a capital requirement and an '
            'execution status, separated from programme concepts that are not '
            'yet implemented.'),
    },
    '/tours': {
        'title': 'Eco Tours — EcoIQ',
        'description': (
            'Khalifa Stewardship Tours — stewardship travel linked to real '
            'environmental work. Register interest; nothing is sold here.'),
    },
    '/about': {
        'title': 'About — EcoIQ',
        'description': (
            'What EcoIQ is today: evidence coverage, provenance and confidence '
            'behind every assessment, and an honest account of what is still '
            'experimental.'),
    },
    '/contact': {
        'title': 'Contact — EcoIQ',
        'description': (
            'Contact EcoIQ about an assessment, a pilot or a partnership. '
            'Enquiries reach the team directly.'),
    },
    '/pricing': {
        'title': 'Pricing — EcoIQ',
        'description': (
            'EcoIQ engagements begin with an enquiry. Scope, evidence access '
            'and duration are agreed per engagement rather than sold as '
            'fixed tiers.'),
    },
    # No '/companies' entry. That route is served by Django, not by spa_view —
    # see the note at the top of frontend/web/src/app/routes.tsx — so an entry
    # here would be metadata nothing reads, describing a page this module does
    # not render. The template supplies its own title.
    '/league': {
        'title': 'League — EcoIQ',
        'description': (
            'Comparative standings across tracked organisations. A rank is '
            'published only for organisations whose score is itself '
            'publishable.'),
    },
    '/labs': {
        'title': 'EcoIQ Labs — EcoIQ',
        'description': (
            'Experimental and planned work, listed with its real status. '
            'Nothing here is presented as a production capability.'),
    },
    '/trust': {
        'title': 'Trust Center — EcoIQ',
        'description': (
            'How EcoIQ handles evidence, provenance, confidence and data — '
            'including the certifications it does not hold.'),
    },
}


def meta_for(path: str) -> dict[str, str]:
    """Metadata for a known route, falling back to the site default."""
    key = path if path == '/' else '/' + path.strip('/')
    meta = ROUTE_META.get(key)
    if meta is None:
        return {'title': 'EcoIQ', 'description': DEFAULT_DESCRIPTION}
    return meta


# ── Views ────────────────────────────────────────────────────────────────────

def spa_view(request, *args, **kwargs) -> HttpResponse:
    """
    A known SPA route. 200, with this route's metadata.

    Registered under the SAME url name the Django template view used, so
    `{% url 'about' %}` in the ~100 templates that are still server-rendered
    keeps resolving. The template and the view are what get deleted; the name
    is part of the site's contract with itself.
    """
    path = request.path if request.path == '/' else '/' + request.path.strip('/')
    meta = meta_for(path)
    return render_shell(title=meta['title'], description=meta['description'],
                        path=request.path)


def project_concept_spa_view(request, slug: str) -> HttpResponse:
    """
    /projects/<slug>/ — one programme concept, with its own metadata.

    The concepts are editorial content in projects/data.py, not database rows,
    so this costs a dict lookup rather than a query.

    404s on an unknown slug. Without it every typo under /projects/ would
    answer 200 with a page that says "no programme concept with that name" —
    a page that does not exist, reporting that it does.

    The description says what the page is: a concept, not an implementation.
    A crawler reading only the metadata must not come away thinking EcoIQ has
    delivered this.
    """
    from projects.data import PROJECTS_BY_SLUG

    concept = PROJECTS_BY_SLUG.get(slug)
    if concept is None:
        raise Http404(f'No programme concept named {slug!r}')

    return render_shell(
        title=f'{concept["name"]} — EcoIQ',
        description=(
            f'{concept["tagline"]} A programme concept at '
            f'{concept.get("status_key", "concept")} stage — not implemented, '
            'and every figure indicative.'),
        path=request.path,
    )


def _is_server_owned(path: str) -> bool:
    """Does Django own this path outright?"""
    stripped = path.lstrip('/')
    if stripped.startswith(SERVER_OWNED_PREFIXES):
        return True
    return stripped.lower().endswith(SERVER_OWNED_SUFFIXES)


def spa_catch_all(request, path: str = '') -> HttpResponse:
    """
    Anything the URLconf did not match.

    Registered last. Two outcomes and no third:

      unknown /api/ path → JSON 404, so a client parses an error, not HTML.
      server-owned path  → Http404, plain. Never the React shell.
      anything else      → the React shell with HTTP 404, so the browser shows
                           the NotFound page and a crawler reads the real
                           status.
    """
    # An API path that reached here is a route that does not exist. Answer in
    # the content type the caller asked for: a JSON client that receives an
    # HTML error page reports a parse failure, which sends whoever is debugging
    # it looking for a serialiser bug instead of a wrong URL. Shape matches
    # DRF's own 404 body so error handling does not need a special case.
    if path.lstrip('/').startswith('api/'):
        return JsonResponse({'detail': 'Not found.'}, status=404)

    if _is_server_owned(path):
        raise Http404(f'No server route matches /{path}')

    return render_shell(
        title='Page not found — EcoIQ',
        description='This page does not exist.',
        path=request.path,
        robots='noindex, follow',
        status=404,
    )
