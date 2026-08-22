"""
api/v2_urls.py — mounted at /api/v2/ from the root urls.py.

Separate module from api/urls.py so the two versions cannot accidentally share a
route or a name. v1 keeps namespace 'api'; v2 uses 'api_v2', so
{% url 'api:...' %} and reverse('api:...') continue to resolve to v1 exactly as
before.

Only the score-bearing endpoints are versioned. The other v1 routes expose no
score and have nothing to correct, so duplicating them would double the
maintenance surface for no truthfulness gain.
"""
from django.urls import path

from api import (
    v2_assessment, v2_contact, v2_platform, v2_projects, v2_session,
    v2_views,
)

app_name = 'api_v2'

urlpatterns = [
    path('',                       v2_views.api_root_v2,       name='root'),
    # Platform counters and module statuses. The single source of truth for
    # any number the product shows about itself.
    # Session boundary. See api/v2_session.py for why this is session-based
    # rather than a token system.
    path('session/',               v2_session.session,   name='session'),
    path('session/sign-in/',       v2_session.sign_in,   name='sign_in'),
    path('session/sign-out/',      v2_session.sign_out,  name='sign_out'),
    path('platform/',              v2_platform.platform, name='platform'),
    # The contact enquiry flow. Runs the SAME abuse screening as the
    # server-rendered form it replaces — see api/v2_contact.py for why that is
    # not optional.
    path('contact/',               v2_contact.contact,   name='contact'),
    path('projects/',              v2_projects.projects, name='projects'),
    path('companies/',             v2_views.CompanyListV2View.as_view(), name='company_list'),
    path('companies/<slug:slug>/', v2_views.company_detail_v2, name='company_detail'),
    # The full organisation assessment. One gate, applied at the top: an
    # organisation without a publishable score gets identity, evidence state
    # and gaps, and none of the panel keys at all.
    path('companies/<slug:slug>/assessment/', v2_assessment.company_assessment,
         name='company_assessment'),
    path('leaderboard/',           v2_views.leaderboard_v2,    name='leaderboard'),
]
