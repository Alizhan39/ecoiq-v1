from django.urls import path
from . import views
from company_intelligence import views as ci_views

app_name = 'companies'

urlpatterns = [
    path('',                                       views.directory,            name='directory'),
    # feat/company-halal-intelligence (PR 9) — the one user-scoped route
    # ('watchlist/') must be registered before the '<slug:slug>/' catch-all
    # below, same discipline as capital_guardian/urls.py, since a bare
    # SlugField pattern would otherwise swallow it.
    path('watchlist/',                              ci_views.watchlist_view,    name='watchlist'),
    path('<slug:slug>/',                            views.company_detail,       name='detail'),
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
