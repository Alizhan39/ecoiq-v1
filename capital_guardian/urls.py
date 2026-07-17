"""capital_guardian/urls.py — routes (mounted at /capital-guardian/)."""
from django.urls import path

from capital_guardian import views

app_name = 'capital_guardian'

urlpatterns = [
    path('', views.directory, name='directory'),
    # Project-independent routes must be registered before the
    # '<slug:slug>/' catch-all.
    path('portfolio/', views.portfolio_view, name='portfolio'),
    path('suppliers/', views.supplier_comparison_view, name='supplier_comparison'),
    path('<slug:slug>/', views.investor_dashboard, name='investor_dashboard'),
    path('<slug:slug>/command-centre/', views.project_command_centre, name='project_command_centre'),
    path('<slug:slug>/trace/', views.capital_trace_view, name='capital_trace'),
    path('<slug:slug>/trace/<int:entry_id>/', views.capital_trace_entry_detail_view, name='capital_trace_entry_detail'),
    path('<slug:slug>/governance/', views.governance_view, name='governance'),
    path('<slug:slug>/equipment/', views.equipment_insurance_view, name='equipment_insurance'),
    path('<slug:slug>/equipment/<int:equipment_id>/', views.equipment_detail_view, name='equipment_detail'),
    path('<slug:slug>/digital-twin/', views.digital_twin_view, name='digital_twin'),
    path('<slug:slug>/live-cameras/', views.live_cameras_view, name='live_cameras'),
    path('<slug:slug>/milestones/', views.milestone_control_view, name='milestone_control'),
    path('<slug:slug>/red-flags/', views.red_flag_view, name='red_flags'),
    path('<slug:slug>/evidence/', views.evidence_centre_view, name='evidence_centre'),
    path('<slug:slug>/evidence/add/', views.add_project_evidence, name='add_project_evidence'),
    path('<slug:slug>/analysis/run/', views.run_project_analysis, name='run_project_analysis'),
    path('<slug:slug>/analysis/value-loss/', views.create_value_loss_confirm, name='create_value_loss_confirm'),
    path('<slug:slug>/analysis/value-loss/execute/', views.create_value_loss_execute, name='create_value_loss_execute'),
    path('<slug:slug>/losses/<int:loss_id>/', views.operational_loss_detail, name='operational_loss_detail'),
    path('<slug:slug>/losses/<int:loss_id>/interventions/add/', views.create_intervention_option_confirm, name='create_intervention_option_confirm'),
    path('<slug:slug>/losses/<int:loss_id>/interventions/add/execute/', views.create_intervention_option_execute, name='create_intervention_option_execute'),
    path('<slug:slug>/losses/<int:loss_id>/better-way/', views.run_better_way_comparison, name='run_better_way_comparison'),
    path(
        '<slug:slug>/losses/<int:loss_id>/interventions/<int:option_id>/decision/',
        views.create_capital_decision_confirm, name='create_capital_decision_confirm',
    ),
    path(
        '<slug:slug>/losses/<int:loss_id>/interventions/<int:option_id>/decision/execute/',
        views.create_capital_decision_execute, name='create_capital_decision_execute',
    ),
    path('<slug:slug>/audit-history/', views.audit_history_view, name='audit_history'),
    path('<slug:slug>/monitoring/', views.project_monitoring_view, name='project_monitoring'),
    path('<slug:slug>/monitoring/capital-trace/add/', views.add_capital_trace_entry, name='add_capital_trace_entry'),
    path('<slug:slug>/monitoring/milestones/add/', views.add_milestone, name='add_milestone'),
    path('<slug:slug>/monitoring/milestones/<int:milestone_id>/update/', views.update_milestone, name='update_milestone'),
    path('<slug:slug>/monitoring/evidence/add/', views.add_implementation_evidence, name='add_implementation_evidence'),
    path(
        '<slug:slug>/monitoring/decisions/<int:decision_id>/outcome/',
        views.record_outcome_confirm, name='record_outcome_confirm',
    ),
    path(
        '<slug:slug>/monitoring/decisions/<int:decision_id>/outcome/execute/',
        views.record_outcome_execute, name='record_outcome_execute',
    ),
    path(
        '<slug:slug>/monitoring/decisions/<int:decision_id>/outcome/sync-to-evidence-memory/',
        views.sync_outcome_to_evidence_memory, name='sync_outcome_to_evidence_memory',
    ),
    path('<slug:slug>/decisions/<int:decision_id>/review/', views.human_decision_gate_view, name='human_decision_gate'),
    path(
        '<slug:slug>/decisions/<int:decision_id>/review/<str:action>/confirm/',
        views.human_decision_gate_action_confirm, name='human_decision_gate_action_confirm',
    ),
    path(
        '<slug:slug>/decisions/<int:decision_id>/review/<str:action>/execute/',
        views.human_decision_gate_action_execute, name='human_decision_gate_action_execute',
    ),
    path('<slug:slug>/govern/', views.govern_hub_view, name='govern_hub'),
    path('<slug:slug>/ai-director/', views.ai_director_view, name='ai_director'),
    path('<slug:slug>/decision-intelligence/', views.decision_intelligence_view, name='decision_intelligence'),
]
