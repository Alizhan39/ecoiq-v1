"""
core/access.py — which experimental surfaces stop answering anonymously.

THE PROBLEM THIS SOLVES
-----------------------
The estate had 102 anonymously-reachable server-rendered pages. Most were not
product: fourteen pages under a path literally named "legacy-safe" (two of them
called "demo"), an eight-page pitch deck for a tours operating system that does
not exist, and the UIs of a dozen modules the status registry marks
EXPERIMENTAL or does not list at all.

None of them was linked from the public navigation. None was in the sitemap.
They answered 200 to anyone who typed the URL.

That is the same failure as an unevidenced score: a surface that presents as
more finished than it is. EcoIQ Labs exists precisely so experimental work can
be listed with its real status; a module whose UI is one anonymous URL away
from the homepage is not being presented as experimental, whatever Labs says
about it.

SIGN-IN, NOT DELETION
---------------------
Every gated surface keeps its views, templates, models and tests. Nothing is
removed and nothing is lost — the pages simply require a signed-in user, which
is what "internal" has always meant here. De-publication and deletion are
different decisions, and this module only makes the first one.

Reversing it is deleting a line from a tuple.

WHY MIDDLEWARE AND NOT 58 DECORATORS
------------------------------------
Because the list is the point. Decorating fifty-eight views across twenty apps
would spread one policy over twenty files, and the next experimental app would
be added without one. Here the policy is a list you can read, a test iterates
it, and a new app is gated by adding its prefix.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse, JsonResponse

#: Whole path prefixes that require a signed-in user.
#:
#: Each entry is a module whose UI is experimental, unregistered, or explicitly
#: legacy. The app's own API endpoints live under the same prefix and are gated
#: with it, deliberately: if a page needs sign-in, the XHR behind it does too.
SIGN_IN_PREFIXES: tuple[str, ...] = (
    # AI agent surfaces. No AI module in this repository has a measured
    # evaluation, so none is claimed as production.
    '/ai-agents/',
    '/ai-agent-council/',
    '/agent-runtime-model-router/',
    '/good-agents/',
    '/decision-studio/',
    '/global-research/',
    '/digital-twin/',
    # Unregistered intelligence prototypes.
    '/capital-guardian/',
    '/financial-intelligence-cloud/',
    '/geo-intelligence/',
    '/gold-intelligence/',
    '/intelligence-dashboard/',
    '/waste-to-value-capital-allocation/',
    # A PRODUCTION engine behind a prototype UI. The engine
    # (qdf.decision_integrity) is real; this dashboard is not the product.
    '/decisions/',
    # Analyst-facing evidence tooling.
    '/evidence/',
    # Explicitly legacy, including two pages named "demo".
    '/legacy-safe/',
    # An eight-page pitch deck for a system that does not exist.
    '/khalifa-tour-operating-system/',
    # Concept landing unrelated to the decision-intelligence product.
    '/tazkiyah-114/',
    # Commerce catalogue while ECOIQ_BILLING_PROVIDER is "none" — nothing here
    # is purchasable, so nothing here should be browsable.
    '/products/',
    # Two per-organisation Django pages that outlived the React company page.
    #
    # Found by the Phase 10 route audit, not by anyone using them: both are
    # orphans. Nothing in the React app, the Django templates or the sitemap
    # links to either, and both answered 200 for a slug that does not exist —
    # /company-intelligence/does-not-exist-xyz/ rendered a full page in
    # production. A public per-company URL that never 404s is an unbounded
    # supply of indexable pages about organisations EcoIQ holds nothing on.
    #
    # /companies/<slug>/ is now the organisation page and it is gated by
    # companies.eligibility. These two are not: /company-intelligence/ fetches
    # the Hikma endpoints client-side, and /why/company/ renders harvested
    # datapoints with a percentage confidence. Neither asks decide().
    #
    # /why/company/<slug>/pack.pdf is gated WITH the page, not exempted as a
    # server document. The PDF carries the same per-organisation content, so
    # leaving it open would de-publish the page and publish it again in another
    # format. It is still generated, for signed-in users.
    #
    # KNOWN GAP, deliberately not closed here: /api/why/company/<slug>/ serves
    # the same payload as JSON and stays public. Gating it is an API contract
    # change, which is not this phase's to make. Recorded in
    # docs/product/FINAL_TEMPLATE_MIGRATION.md.
    '/company-intelligence/',
    '/why/company/',
    # An unfinished prototype of the industrial-modernisation scene. Gated for
    # the reason this module exists: a surface one anonymous URL away from the
    # homepage is not being presented as experimental, whatever anyone intends.
    # It is a preview to look at and argue with, not a page.
    '/industrial-modernisation-preview/',
)

#: Exact paths that require sign-in where the PREFIX must stay public.
#:
#: /companies/ is the public company directory and /companies/<slug>/ is a
#: public organisation page; only the analyst tooling underneath them is gated.
#: Same for /rankings/, which redirects to the public directory.
SIGN_IN_EXACT: frozenset[str] = frozenset({
    '/companies/discover/',
    '/companies/compare/',
    '/companies/strongest-alignment/',
    '/rankings/utilities/',
    # Byte-identical alias of /tazkiyah-114/ — same view, same template. Gated
    # rather than redirected to its twin, because the twin is gated too and
    # /surah-map/ -> /tazkiyah-114/ -> /login/ is a chain.
    '/surah-map/',
})


#: Per-organisation pages that hang off the PUBLIC /companies/<slug>/ route.
#:
#: A prefix cannot express these and an exact path cannot either — the slug is
#: in the middle. /companies/ must stay public because /companies/<slug>/ IS
#: the organisation page; only these three leaves are de-published.
#:
#: All three are Django full pages with their own dark-theme CSS and their own
#: navigation, left over from when the organisation page was server-rendered.
#: Found by the Phase 10 route audit.
#:
#: They ARE linked — and every page that links them already requires sign-in:
#: /companies/discover/ and /companies/strongest-alignment/ (both in
#: SIGN_IN_EXACT), the @login_required portfolio dashboard, and
#: companies/detail.html, which since the React cutover is rendered only by the
#: @login_required /companies/<slug>/internal/. So gating the leaves costs
#: those journeys nothing: the user arriving at them is signed in already.
#:
#: What it removes is the anonymous route — the leaf answering 200 to anyone
#: who types the URL, which is the same charge this module was written for.
#:
#: Nor were they unmaintained: 13 tests asserted their anonymous 200, and those
#: tests are what caught this change. None was deleted; each now asserts the
#: new boundary instead, so the suite still pins what the pages SAY.
#:
#: /stock/ is not a new decision. docs/product/COMPANY_PAGE_PANELS.md already
#: removed the stock strip from the organisation page, because a share price
#: beside an ethics assessment implies a relationship EcoIQ does not assert and
#: has no evidence for. The standalone page makes the same implication over a
#: whole page; leaving it public would have honoured the decision on the panel
#: and reversed it one URL away.
#:
#: MEASURED, not assumed: none of the three publishes a withheld composite. A
#: probe rendered all three for a profile holding 73.6 at 0% coverage — the
#: production state — and the number appears in none of them. They are gated
#: for being unlinked, unmaintained duplicates of a page React now owns, which
#: is a different and lesser charge. Asserted in core/tests_access.py.
COMPANY_LEAF_SUFFIXES: tuple[str, ...] = (
    '/explain/',
    '/explain-match/',
    '/stock/',
)


def _is_gated_company_leaf(path: str) -> bool:
    """One of the de-published leaves under a public /companies/<slug>/."""
    if not path.startswith('/companies/'):
        return False
    if not path.endswith(COMPANY_LEAF_SUFFIXES):
        return False
    # Exactly /companies/<slug>/<leaf>/ — three non-empty segments. Anything
    # deeper is a route this rule was not written for, and guessing at it would
    # gate pages nobody looked at.
    return len([segment for segment in path.split('/') if segment]) == 3


def requires_sign_in(path: str) -> bool:
    """Is this path one of the de-published surfaces?"""
    if path in SIGN_IN_EXACT:
        return True
    if _is_gated_company_leaf(path):
        return True
    return path.startswith(SIGN_IN_PREFIXES)


class ExperimentalSurfaceMiddleware:
    """
    Require a signed-in user for the paths declared above.

    Placed after AuthenticationMiddleware, so `request.user` exists.

    Staff-only surfaces keep their own `@staff_member_required`; this is a
    floor, not a replacement. A page that was already staff-gated stays
    staff-gated.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if requires_sign_in(request.path) and not request.user.is_authenticated:
            # An API path under a gated prefix answers in JSON. Redirecting an
            # XHR to a login page gives the caller an HTML body and a 200,
            # which reads as a parse error rather than as "sign in".
            if '/api/' in request.path:
                return JsonResponse(
                    {'detail': 'Authentication required.'}, status=403)
            return redirect_to_login(
                request.get_full_path(), settings.LOGIN_URL)
        return self.get_response(request)
