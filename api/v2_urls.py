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

from api import v2_views

app_name = 'api_v2'

urlpatterns = [
    path('',                       v2_views.api_root_v2,       name='root'),
    path('companies/',             v2_views.CompanyListV2View.as_view(), name='company_list'),
    path('companies/<slug:slug>/', v2_views.company_detail_v2, name='company_detail'),
    path('leaderboard/',           v2_views.leaderboard_v2,    name='leaderboard'),
]
