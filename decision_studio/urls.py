"""decision_studio/urls.py — routes (mounted at /decision-studio/)."""
from django.urls import path

from decision_studio import views

app_name = 'decision_studio'

urlpatterns = [
    path('', views.studio, name='studio'),
    path('ask/', views.ask, name='ask'),
    path('result/<int:query_id>/', views.result_detail, name='result_detail'),
]
