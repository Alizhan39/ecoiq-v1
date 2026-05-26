from django.urls import path
from . import views

app_name = 'ingestion'

urlpatterns = [
    path('',             views.index,      name='index'),
    path('start/',       views.start,      name='start'),
    path('status/<int:job_id>/', views.status, name='status'),
    path('job/<int:job_id>/',    views.job_detail, name='job_detail'),
]
