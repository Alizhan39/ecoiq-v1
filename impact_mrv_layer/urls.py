"""impact_mrv_layer/urls.py — routes (mounted at /impact-mrv-layer/)."""
from django.urls import path

from impact_mrv_layer import views

app_name = 'impact_mrv_layer'

urlpatterns = [
    path('', views.overview, name='overview'),
]
