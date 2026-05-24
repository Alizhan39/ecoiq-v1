from django.urls import path
from . import views

app_name = 'leads'

urlpatterns = [
    path('',        views.request_access, name='request_access'),
    path('success/', views.success,       name='success'),
]
