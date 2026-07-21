from django.urls import path
from . import views
from company_intelligence import views as ci_views
from company_intelligence import discovery_views as discovery
from company_intelligence import review_views as review

app_name = 'companies'

urlpatterns = [
    path('',                                       views.directory,            name='directory'),
    # feat/company-halal-intelligence (PR 9) — the one user-scoped route
    # ('watchlist/') must be registered before the '<slug:slug>/' catch-all
    # below, same discipline as capital_guardian/urls.py, since a bare
    # SlugField pattern would otherwise swallow it.
    path('watchlist/',                              ci_views.watchlist_view,    name='watchlist'),
    # feat/company-discovery-ranking (PR 11) — 'discover/' and 'compare/'
    # must also be registered before the '<slug:slug>/' catch-all below.
    path('discover/',                               discovery.discover_companies_view, name='discover'),
    path('compare/',                                discovery.company_comparison_view, name='compare'),
    # feat/evidence-review-workbench (PR 12) — staff-only, spans all
    # companies, so 'review/' must also precede the '<slug:slug>/' catch-all.
    path('review/',                                 review.review_queue_view,   name='review_queue'),
    path('review/bulk/',                            review.review_bulk_action_view, name='review_bulk_action'),
    path('review/<int:link_id>/',                   review.review_detail_view,  name='review_detail'),
    path('review/<int:link_id>/explain/',           review.explain_review_decision_view, name='review_explain'),
    path('<slug:slug>/',                            views.company_detail,       name='detail'),
    path('<slug:slug>/explain-match/',              discovery.explain_match_view, name='explain_match'),
    path('<slug:slug>/register-document-source/',   discovery.register_document_source_view, name='register_document_source'),
    path('<slug:slug>/explain/',                    ci_views.explain_view,      name='explain'),
    path('<slug:slug>/watchlist/add/',              ci_views.watchlist_add_view, name='watchlist_add'),
    path('<slug:slug>/watchlist/remove/',           ci_views.watchlist_remove_view, name='watchlist_remove'),
    # feat/company-evidence-ingestion (PR 10) — staff-only actions.
    path('<slug:slug>/refresh/',                    ci_views.refresh_company_view, name='refresh'),
    path('<slug:slug>/evidence-review/',            ci_views.evidence_review_action_view, name='evidence_review_action'),
    path('<slug:slug>/report.pdf',                  views.company_pdf_report,   name='pdf_report'),
    path('<slug:slug>/ml-insights.json',            views.company_ml_insights,  name='ml_insights'),
    path('<slug:slug>/certificate/',                views.generate_certificate, name='certificate'),
    path('reports/',                               views.report_index,          name='report_index'),
    path('reports/sector/<str:sector>/',           views.sector_pdf_report,     name='sector_report'),
]
