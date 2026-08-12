"""
api/urls.py — EcoIQ REST API v1 URL configuration.

All routes mounted under /api/v1/ from the root urls.py.
"""
from django.urls import include, path
from . import views
from . import commercial_views
from . import app_views

app_name = 'api'

urlpatterns = [
    # Root
    path('',                                          views.api_root,             name='root'),

    # ── EcoIQ Mobile/Desktop App — auth (mobile_auth app) ──
    path('auth/', include('mobile_auth.urls')),

    # ── EcoIQ Mobile/Desktop App — current-user + remote config (api/app_views.py) ──
    path('me/',          app_views.MeView.as_view(),        name='me'),
    path('app-config/',  app_views.AppConfigView.as_view(), name='app_config'),

    # Companies
    path('companies/',                                views.CompanyListView.as_view(),        name='company_list'),
    path('companies/<slug:slug>/',                    views.CompanyDetailView.as_view(),      name='company_detail'),
    path('companies/<slug:slug>/scores/',             views.CompanyScoresView.as_view(),      name='company_scores'),
    path('companies/<slug:slug>/harm-signals/',       views.CompanyHarmSignalsView.as_view(), name='company_harm_signals'),

    # Leaderboard
    path('leaderboard/',                              views.LeaderboardView.as_view(),        name='leaderboard'),

    # Countries
    path('countries/',                                views.CountryListView.as_view(),        name='country_list'),
    path('countries/<slug:slug>/',                    views.CountryDetailView.as_view(),      name='country_detail'),

    # Search
    path('search/',                                   views.search,                         name='search'),
    path('semantic-search/',                          views.semantic_search,                name='semantic_search'),

    # Responsible Finance alignment score
    path('companies/<slug:slug>/responsible-finance/', views.responsible_finance_detail,    name='responsible_finance'),

    # Ethical Intelligence
    path('intelligence/ethical-score/',                    views.ethical_intelligence_score,       name='ethical_intelligence_score'),
    path('companies/<slug:slug>/ethical-intelligence/',    views.company_ethical_intelligence,     name='company_ethical_intelligence'),
    path('countries/<slug:slug>/ethical-intelligence/',    views.country_ethical_intelligence,     name='country_ethical_intelligence'),

    # Capital Integrity Score
    path('capital-integrity/',                             views.capital_integrity_score,          name='capital_integrity_score'),

    # Hikma assessment (auth: enqueue evidence-ingestion + regeneration)
    path('assess/<slug:slug>/refresh/', views.hikma_refresh_assessment, name='hikma_refresh_assessment'),
    # Hikma Evidence Layer (read-only)
    path('assess/<slug:slug>/evidence/',       views.hikma_evidence_list,   name='hikma_evidence_list'),
    path('assess/<slug:slug>/contradictions/', views.hikma_contradictions,  name='hikma_contradictions'),

    # Hikma assessment (read-only latest)
    path('assess/<slug:slug>/latest/', views.hikma_latest_assessment, name='hikma_latest_assessment'),

    # Islamic & Ethical Finance Fit
    path('finance/islamic-fit/',                           views.islamic_finance_fit,              name='islamic_finance_fit'),

    # ── EcoIQ Commercial Platform — PART 4 endpoints (api/commercial_views.py) ──
    path('companies/<slug:slug>/risks/',                 commercial_views.CompanyRisksView.as_view(),               name='company_risks'),
    path('companies/<slug:slug>/evidence/',              commercial_views.CompanyEvidenceView.as_view(),            name='company_evidence'),
    path('companies/<slug:slug>/ethical-screening/',     commercial_views.CompanyEthicalScreeningView.as_view(),    name='company_ethical_screening'),
    path('companies/<slug:slug>/islamic-screening/',     commercial_views.CompanyIslamicScreeningView.as_view(),    name='company_islamic_screening'),
    path('companies/<slug:slug>/investment-relevance/',  commercial_views.CompanyInvestmentRelevanceView.as_view(), name='company_investment_relevance'),
    path('sectors/<slug:slug>/benchmark/',               commercial_views.SectorBenchmarkView.as_view(),            name='sector_benchmark'),
    path('methodologies/',                               commercial_views.MethodologiesView.as_view(),              name='methodologies'),
    path('controversies/',                               commercial_views.ControversiesView.as_view(),              name='controversies'),
]
