"""asset_passport/urls.py — routes (mounted at /asset-passport/)."""
from django.urls import path

from asset_passport import views

app_name = 'asset_passport'

urlpatterns = [
    path('', views.overview, name='overview'),
]
