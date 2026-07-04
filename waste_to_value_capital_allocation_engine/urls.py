"""waste_to_value_capital_allocation_engine/urls.py — routes (mounted at /waste-to-value-capital-allocation/)."""
from django.urls import path

from waste_to_value_capital_allocation_engine import views

app_name = 'waste_to_value_capital_allocation_engine'

urlpatterns = [
    path('', views.overview, name='overview'),
    path('decision/<int:decision_id>/', views.decision_detail, name='decision_detail'),
]
