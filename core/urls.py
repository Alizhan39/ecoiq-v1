from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # Landing page — public homepage
    path('',                                        views.landing,           name='home'),

    # /rankings/ → canonical company rankings (alias for /companies/)
    path('rankings/', RedirectView.as_view(url='/companies/', permanent=False), name='rankings'),

    # ESG Assessment app
    path('esg/',                                    views.index,             name='index'),
    path('esg/upload/',                             views.upload,            name='upload'),
    path('esg/assessment/<int:pk>/',                views.assessment_detail, name='assessment_detail'),
    path('esg/assessment/<int:pk>/questionnaire/',  views.questionnaire,     name='questionnaire'),
    path('esg/assessment/<int:pk>/run-analysis/',   views.run_analysis,      name='run_analysis'),
    path('esg/assessment/<int:pk>/report/',         views.report,            name='report'),
    path('esg/assessment/<int:pk>/report/pdf/',     views.report_pdf,        name='report_pdf'),

    # Public share link — no auth required
    path('share/<uuid:token>/',                      views.share_report,      name='share_report'),

    # EcoIQ Methodology — public Ethical Intelligence Framework page
    path('methodology/',                             views.methodology,        name='methodology'),
]
