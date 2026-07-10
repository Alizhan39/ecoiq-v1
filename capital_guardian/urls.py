"""capital_guardian/urls.py — routes (mounted at /capital-guardian/)."""
from django.urls import path

from capital_guardian import views

app_name = 'capital_guardian'

urlpatterns = [
    path('', views.directory, name='directory'),
    # 'portfolio/' must be registered before the '<slug:slug>/' catch-all.
    path('portfolio/', views.portfolio_view, name='portfolio'),
    path('<slug:slug>/', views.investor_dashboard, name='investor_dashboard'),
    path('<slug:slug>/trace/', views.capital_trace_view, name='capital_trace'),
    path('<slug:slug>/governance/', views.governance_view, name='governance'),
    path('<slug:slug>/equipment/', views.equipment_insurance_view, name='equipment_insurance'),
    path('<slug:slug>/digital-twin/', views.digital_twin_view, name='digital_twin'),
    path('<slug:slug>/milestones/', views.milestone_control_view, name='milestone_control'),
    path('<slug:slug>/red-flags/', views.red_flag_view, name='red_flags'),
    path('<slug:slug>/evidence/', views.evidence_centre_view, name='evidence_centre'),
    path('<slug:slug>/audit-history/', views.audit_history_view, name='audit_history'),
    path('<slug:slug>/decision-intelligence/', views.decision_intelligence_view, name='decision_intelligence'),
]
