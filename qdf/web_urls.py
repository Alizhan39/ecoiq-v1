"""qdf/web_urls.py — Decision Engine + Stewardship Dashboard web routes (/decisions/)."""
from django.urls import path

from qdf import views

app_name = 'qdf_web'

urlpatterns = [
    path('',              views.stewardship_dashboard, name='dashboard'),
    path('<slug:slug>/',  views.decision_engine,       name='engine'),
]
