"""ai_gateway/web_urls.py — the assistant page (mounted at /ai-assistant/).

Separate from `urls.py` for the same reason `qdf` splits `urls.py` (JSON, at
/api/qdf/) from `web_urls.py` (HTML, at /decisions/): one app, two very
different response contracts.
"""
from django.urls import path

from ai_gateway import web_views

app_name = 'ai_gateway_web'

urlpatterns = [
    path('', web_views.assistant, name='assistant'),
]
