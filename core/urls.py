from django.urls import path
from . import views

urlpatterns = [
    path('',                                        views.index,             name='index'),
    path('upload/',                                 views.upload,            name='upload'),
    path('assessment/<int:pk>/',                    views.assessment_detail, name='assessment_detail'),
    path('assessment/<int:pk>/questionnaire/',      views.questionnaire,     name='questionnaire'),
    path('assessment/<int:pk>/run-analysis/',       views.run_analysis,      name='run_analysis'),
    path('assessment/<int:pk>/report/',             views.report,            name='report'),
    path('assessment/<int:pk>/report/pdf/',         views.report_pdf,        name='report_pdf'),
]
