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


def requires_sign_in(path: str) -> bool:
    """Is this path one of the de-published surfaces?"""
    if path in SIGN_IN_EXACT:
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
