"""
ecoiq/celery.py — the Celery application instance for the EcoIQ Backend
Intelligence Engine.

Broker and result backend are both Redis (one dependency, not two) — see
`CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` in ecoiq/settings.py, both
driven by the `REDIS_URL` environment variable so local dev and Render
production configure identically without hardcoded credentials.

Task modules are auto-discovered from every INSTALLED_APPS app's `tasks.py`
(Celery's standard convention) — new task modules need no registration here.
"""
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecoiq.settings')

app = Celery('ecoiq')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
