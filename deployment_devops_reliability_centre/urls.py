"""deployment_devops_reliability_centre/urls.py — routes (mounted at /deployment-devops-reliability-centre/)."""
from django.urls import path

from deployment_devops_reliability_centre import views

app_name = 'deployment_devops_reliability_centre'

urlpatterns = [
    path('', views.overview, name='overview'),
]
