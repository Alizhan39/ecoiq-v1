"""
customer_ai_chat/urls.py — JSON API URL routing for Ask EcoIQ.
Mounted at /api/customer-chat/ from root urls.py.
"""
from django.urls import path

from customer_ai_chat import views

app_name = 'customer_ai_chat'

urlpatterns = [
    path('chat/',     views.customer_chat_view,     name='chat'),
    path('starters/', views.customer_starters_view, name='starters'),
]
