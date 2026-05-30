"""
api/urls.py — EcoIQ REST API v1 URL configuration.

All routes mounted under /api/v1/ from the root urls.py.
"""
from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # Root
    path('',                                          views.api_root,             name='root'),

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
]
