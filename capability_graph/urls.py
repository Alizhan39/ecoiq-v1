"""capability_graph/urls.py — routes (mounted at /capability-graph/)."""
from django.urls import path

from capability_graph import views

app_name = 'capability_graph'

urlpatterns = [
    path('', views.organisation_list, name='organisation_list'),
    path('<int:pk>/', views.organisation_detail, name='organisation_detail'),
    path('capability/<int:capability_pk>/verify/', views.verify_capability_view, name='verify_capability'),
]
