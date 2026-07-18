"""ai_observatory/urls.py — routes (mounted at /ai-observatory/)."""
from django.urls import path

from ai_observatory import views

app_name = 'ai_observatory'

urlpatterns = [
    path('<slug:slug>/', views.observatory_view, name='observatory'),
    path('<slug:slug>/methodology/', views.methodology_view, name='methodology'),
    path('<slug:slug>/sessions/<int:session_id>/', views.session_detail_view, name='session_detail'),
]
