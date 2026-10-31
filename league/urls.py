from django.contrib.admin.views.decorators import staff_member_required
from django.urls import path

from core import spa
from . import views

app_name = 'league'

urlpatterns = [
    # React SPA. The leaderboard truthfully contains zero ranked organisations
    # today, and the React page says so rather than rendering an empty table.
    path('',                       spa.spa_view,          name='leaderboard'),

    # The full internal league table, staff only.
    #
    # The public league is fail-closed for everybody, including staff: it reads
    # /api/v2/leaderboard/, which applies the publication gate with no
    # exemption. That is correct for a public surface and useless for the
    # people who have to see what the estate actually holds — so the
    # server-rendered table survives here rather than being deleted.
    #
    # Staff-only server-rendered tooling is an intentional exception to the
    # template migration (docs/product/FRONTEND_DEPLOYMENT.md); this route is
    # in neither the sitemap nor robots.txt.
    #
    # Registered BEFORE the bare-slug redirect below, which would swallow it.
    path('internal/', staff_member_required(views.leaderboard),
         name='leaderboard_internal'),

    # report.pdf FIRST: it is server-generated output and must not be shadowed
    # by the bare-slug redirect below.
    path('<slug:slug>/report.pdf',  views.report_pdf,      name='report_pdf'),

    # /league/<slug>/ redirects to the company page rather than getting a React
    # page of its own. Both routes were rendering league.Company by the same
    # slug, so a second implementation would be two surfaces for one
    # organisation — and two chances for them to disagree about what is
    # publishable.
    #
    # It 404s on an unknown slug instead of redirecting to a page that will
    # 404 anyway: a 302-then-404 tells a crawler the URL moved before telling
    # it the destination does not exist.
    path('<slug:slug>/', views.company_redirect, name='company'),
]
