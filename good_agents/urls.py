"""good_agents/urls.py — routes (mounted at /good-agents/)."""
from django.urls import path

from good_agents import views

app_name = 'good_agents'

urlpatterns = [
    path('', views.opportunity_list, name='opportunity_list'),
    path('morning-brief/', views.morning_brief, name='morning_brief'),
    path('api/map/', views.good_map_api, name='good_map_api'),
    path('api/observatory-health/', views.observatory_health_api, name='observatory_health_api'),
    path('<int:pk>/', views.opportunity_detail, name='opportunity_detail'),
]
