"""
gcc_investors/urls.py — mounted with an empty prefix directly on
ecoiq/urls.py (path('', include('gcc_investors.urls'))) because the
required URL shapes don't share a common app-level prefix: English pages
use the full country name (/qatar/investors/), Arabic pages use a
/ar/<iso-code>/investors/ shape. See gcc_investors/seo.py:PAGE_PATHS for
the single source of truth these paths must stay in sync with.
"""
from django.urls import path

from . import views

app_name = 'gcc_investors'

urlpatterns = [
    path('gcc-investors/',           views.gcc_hub_en,          name='hub_en'),
    path('ar/gcc-investors/',        views.gcc_hub_ar,          name='hub_ar'),

    path('qatar/investors/',         views.qatar_investors_en,  name='qatar_en'),
    path('ar/qa/investors/',         views.qatar_investors_ar,  name='qatar_ar'),

    path('saudi-arabia/investors/',  views.saudi_investors_en,  name='saudi_en'),
    path('ar/sa/investors/',         views.saudi_investors_ar,  name='saudi_ar'),

    path('kuwait/investors/',        views.kuwait_investors_en, name='kuwait_en'),
    path('ar/kw/investors/',         views.kuwait_investors_ar, name='kuwait_ar'),
]
