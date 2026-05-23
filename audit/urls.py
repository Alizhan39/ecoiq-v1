from django.urls import path
from . import views

urlpatterns = [
    path('',                                          views.index,          name='audit_index'),
    path('new/',                                      views.upload,         name='audit_upload'),
    path('<int:pk>/',                                 views.detail,         name='audit_detail'),
    path('<int:pk>/questionnaire/',                   views.questionnaire,  name='audit_questionnaire'),
    path('<int:pk>/analyse/',                         views.analyse,        name='audit_analyse'),
    path('<int:pk>/report/',                          views.report,         name='audit_report'),
    path('<int:pk>/report/pdf/',                      views.report_pdf,     name='audit_report_pdf'),
]
