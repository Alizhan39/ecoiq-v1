from django.urls import path
from . import views
from company_intelligence import views as ci_views
from company_intelligence import discovery_views as discovery
from company_intelligence import review_views as review
from company_intelligence import stewardship_views as stewardship
from company_intelligence import monitor_views as monitor

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
    # feat/global-stewardship-universe (PR 15) — cross-company ranking view,
    # so 'strongest-alignment/' must also precede the '<slug:slug>/' catch-all.
    path('strongest-alignment/',                    discovery.strongest_alignment_view, name='strongest_alignment'),
    # feat/evidence-review-workbench (PR 12) — staff-only, spans all
    # companies, so 'review/' must also precede the '<slug:slug>/' catch-all.
    path('review/',                                 review.review_queue_view,   name='review_queue'),
    path('review/bulk/',                            review.review_bulk_action_view, name='review_bulk_action'),
    path('review/<int:link_id>/',                   review.review_detail_view,  name='review_detail'),
    path('review/<int:link_id>/explain/',           review.explain_review_decision_view, name='review_explain'),
    # feat/stewardship-universe (PR 13) — staff-only operational view across
    # all tracked companies, so 'universe/' must also precede the
    # '<slug:slug>/' catch-all.
    path('universe/',                               stewardship.universe_view,  name='universe'),
    # feat/stewardship-monitor (PR 14) — staff-only, cross-company dashboard,
    # so 'monitor/' must also precede the '<slug:slug>/' catch-all.
    path('monitor/',                                monitor.monitor_dashboard_view, name='monitor'),
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
    # feat/stewardship-universe (PR 13) — per-company operational status +
    # staff-triggered refresh/source governance actions.
    path('<slug:slug>/status/',                     stewardship.company_status_view,  name='company_status'),
    path('<slug:slug>/status/refresh/',              stewardship.trigger_refresh_view, name='trigger_refresh'),
    path('<slug:slug>/status/pause/',                stewardship.pause_tracking_view,  name='pause_tracking'),
    path('<slug:slug>/status/resume/',               stewardship.resume_tracking_view, name='resume_tracking'),
    path('<slug:slug>/status/sources/<int:source_id>/approve/', stewardship.approve_source_view, name='approve_source'),
    path('<slug:slug>/status/sources/<int:source_id>/reject/',  stewardship.reject_source_view,  name='reject_source'),
    # feat/stewardship-monitor (PR 14) — refresh diff + alert actions.
    path('<slug:slug>/status/refresh/<int:run_id>/diff/',       monitor.refresh_diff_view,      name='refresh_diff'),
    path('<slug:slug>/status/alerts/<int:alert_id>/acknowledge/', monitor.alert_acknowledge_view, name='alert_acknowledge'),
    path('<slug:slug>/status/alerts/<int:alert_id>/resolve/',     monitor.alert_resolve_view,    name='alert_resolve'),
    path('<slug:slug>/status/alerts/<int:alert_id>/dismiss/',     monitor.alert_dismiss_view,    name='alert_dismiss'),
    path('reports/',                               views.report_index,          name='report_index'),
    path('reports/sector/<str:sector>/',           views.sector_pdf_report,     name='sector_report'),
]
