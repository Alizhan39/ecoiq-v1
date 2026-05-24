from django.urls import path
from . import views

urlpatterns = [
    # Landing page — public homepage
    path('',                                        views.landing,           name='home'),

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
]
