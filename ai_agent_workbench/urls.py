"""ai_agent_workbench/urls.py — routes (mounted at /ai-agents/)."""
from django.urls import path

from ai_agent_workbench import views

app_name = 'ai_agent_workbench'

urlpatterns = [
    path('', views.directory, name='directory'),
    path('workbench/', views.workbench, name='workbench'),
    path('presentation/', views.presentation, name='presentation'),
    path('performance/', views.performance, name='performance'),
    path('council-demo/', views.council_demo, name='council_demo'),
    path('agent/<slug:slug>/', views.agent_profile, name='agent_profile'),
    path('run/<int:run_id>/', views.run_alias, name='run_alias'),
    path('orchestration/<int:run_id>/', views.orchestration_detail, name='orchestration_detail'),
]
