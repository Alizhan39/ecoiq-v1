from django.urls import path
from . import views

app_name = 'companies'

urlpatterns = [
    path('',                              views.directory,            name='directory'),
    path('<slug:slug>/',                  views.company_detail,       name='detail'),
    path('<slug:slug>/report.pdf',        views.company_pdf_report,   name='pdf_report'),
    path('<slug:slug>/ml-insights.json',  views.company_ml_insights,  name='ml_insights'),
]
