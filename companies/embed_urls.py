"""companies/embed_urls.py — PART 5 embeddable badge/widget routes, mounted at /embed/."""
from django.urls import path

from . import embed_views

app_name = 'embed'

urlpatterns = [
    path('<slug:slug>/',                    embed_views.embed_snippets,          name='snippets'),
    path('<slug:slug>/badge.svg',           embed_views.ecoiq_score_badge,       name='ecoiq_badge'),
    path('<slug:slug>/ethical-badge.svg',   embed_views.ethical_screening_badge, name='ethical_badge'),
    path('<slug:slug>/islamic-badge.svg',   embed_views.islamic_screening_badge, name='islamic_badge'),
    path('<slug:slug>/risk-card/',          embed_views.risk_card,               name='risk_card'),
]
