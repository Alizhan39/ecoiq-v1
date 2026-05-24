from django.urls import path
from . import views

urlpatterns = [
    # ── Industrial audit ──────────────────────────────────────────────────────
    path('',                                          views.index,          name='audit_index'),
    path('new/',                                      views.upload,         name='audit_upload'),
    path('<int:pk>/',                                 views.detail,         name='audit_detail'),
    path('<int:pk>/questionnaire/',                   views.questionnaire,  name='audit_questionnaire'),
    path('<int:pk>/analyse/',                         views.analyse,        name='audit_analyse'),
    path('<int:pk>/report/',                          views.report,         name='audit_report'),
    path('<int:pk>/report/pdf/',                      views.report_pdf,     name='audit_report_pdf'),

    # ── AI Findings Engine ────────────────────────────────────────────────────
    path('ai/',                                       views.ai_jobs,            name='ai_jobs'),
    path('ai/<int:pk>/',                              views.ai_job_detail,      name='ai_job_detail'),
    path('ai/<int:pk>/run/',                          views.ai_job_run,         name='ai_job_run'),
    path('ai/<int:pk>/apply/',                        views.ai_job_apply,       name='ai_job_apply'),
    path('ai/<int:pk>/company/',                      views.ai_job_set_company, name='ai_job_set_company'),
    path('ai/<int:pk>/score/',                        views.ai_score_action,    name='ai_score_action'),
    path('ai/<int:pk>/bulk/',                         views.ai_bulk_action,     name='ai_bulk_action'),
    path('ai/finding/<int:pk>/action/',               views.ai_finding_action,  name='ai_finding_action'),
    path('ai/<int:pk>/note/',                         views.ai_job_save_note,   name='ai_job_save_note'),
]
