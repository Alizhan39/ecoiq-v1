"""mobile_inspection_mode/urls.py — routes (mounted at /mobile-inspection-mode/)."""
from django.urls import path

from mobile_inspection_mode import views

app_name = 'mobile_inspection_mode'

urlpatterns = [
    path('', views.overview, name='overview'),
]
