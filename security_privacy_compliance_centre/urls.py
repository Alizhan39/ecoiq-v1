"""security_privacy_compliance_centre/urls.py — routes (mounted at /security-privacy-compliance-centre/)."""
from django.urls import path

from security_privacy_compliance_centre import views

app_name = 'security_privacy_compliance_centre'

urlpatterns = [
    path('', views.overview, name='overview'),
]
