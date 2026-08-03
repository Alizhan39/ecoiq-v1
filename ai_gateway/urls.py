"""ai_gateway/urls.py — JSON API routes (mounted at /api/ai/)."""
from django.urls import path

from ai_gateway import views

app_name = 'ai_gateway'

urlpatterns = [
    path('models/', views.ai_models, name='models'),
    path('chat/',   views.ai_chat,   name='chat'),
    path('health/', views.ai_health, name='health'),
]
