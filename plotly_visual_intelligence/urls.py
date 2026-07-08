"""plotly_visual_intelligence/urls.py — routes (mounted at /intelligence-dashboard/)."""
from django.urls import path

from plotly_visual_intelligence import views

app_name = 'plotly_visual_intelligence'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
]
