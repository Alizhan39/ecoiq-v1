"""ecoiq_commerce/urls.py — mounted at /products/ from the root urls.py."""
from django.urls import path

from . import views

app_name = 'commerce'

urlpatterns = [
    path('',                     views.products,        name='products'),
    path('api-keys/',            views.api_keys,        name='api_keys'),
    path('api-keys/<int:pk>/rotate/', views.api_key_rotate, name='api_key_rotate'),
    path('api-keys/<int:pk>/revoke/', views.api_key_revoke, name='api_key_revoke'),
    path('dashboard/',           views.dashboard,        name='dashboard'),
]
