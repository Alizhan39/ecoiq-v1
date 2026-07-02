"""frontend_experience_google_stitch_design_system/urls.py — routes (mounted at /frontend-experience-google-stitch-design-system/)."""
from django.urls import path

from frontend_experience_google_stitch_design_system import views

app_name = 'frontend_experience_google_stitch_design_system'

urlpatterns = [
    path('', views.overview, name='overview'),
]
