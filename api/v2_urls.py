"""
api/v2_urls.py — mounted at /api/v2/ from the root urls.py.

Separate module from api/urls.py so the two versions cannot accidentally share a
route or a name. v1 keeps namespace 'api'; v2 uses 'api_v2', so
{% url 'api:...' %} and reverse('api:...') continue to resolve to v1 exactly as
before.

Only the score-bearing endpoints are versioned. The other v1 routes expose no
score and have nothing to correct, so duplicating them would double the
maintenance surface for no truthfulness gain.
"""
from django.urls import path
from api.v2_formula_flow import project_formula_flow
from ai_gateway.workflow_views import decision_flow_preview

from api import (
    v2_assessment, v2_contact, v2_interactive, v2_kpi, v2_platform, v2_principles, v2_projects,
    v2_decision_islah, v2_process_analyses, v2_session, v2_views,
)

app_name = 'api_v2'

urlpatterns = [
    path('projects/<slug:project_slug>/formulas/flow/', project_formula_flow,
         name='project_formula_flow'),
    # Staff-only, read-only React Flow-compatible draft (no AI execution).
    path('decision-flow/preview/', decision_flow_preview, name='decision_flow_preview'),
    path('interactive/libraries/', v2_interactive.libraries, name='interactive_libraries'),
    path('interactive/scenes/', v2_interactive.scenes, name='interactive_scenes'),
    path('interactive/scenes/<slug:scene_id>/', v2_interactive.scene, name='interactive_scene'),
    path('',                       v2_views.api_root_v2,       name='root'),
    # Platform counters and module statuses. The single source of truth for
    # any number the product shows about itself.
    # Session boundary. See api/v2_session.py for why this is session-based
    # rather than a token system.
    path('session/',               v2_session.session,   name='session'),
    path('session/sign-in/',       v2_session.sign_in,   name='sign_in'),
    path('session/sign-out/',      v2_session.sign_out,  name='sign_out'),
    path('platform/',              v2_platform.platform, name='platform'),
    # The contact enquiry flow. Runs the SAME abuse screening as the
    # server-rendered form it replaces — see api/v2_contact.py for why that is
    # not optional.
    path('contact/',               v2_contact.contact,   name='contact'),
    path('projects/',              v2_projects.projects, name='projects'),
    # Private project-specific process inspections; these are NOT public scores.
    path('projects/<slug:project_slug>/process-analyses/',
         v2_process_analyses.process_analyses, name='process_analyses'),
    path('projects/<slug:project_slug>/process-analyses/<int:run_id>/',
         v2_process_analyses.process_analysis_detail, name='process_analysis_detail'),
    path('projects/<slug:project_slug>/process-analyses/<int:run_id>/decision-brief/',
         v2_decision_islah.process_decision_brief, name='process_decision_brief'),
    # The 114 stewardship principles EcoIQ assesses against. A fact about the
    # method, not about any organisation — so it takes no slug.
    path('principles/',            v2_principles.principles, name='principles'),
    path('companies/',             v2_views.CompanyListV2View.as_view(), name='company_list'),
    path('companies/<slug:slug>/', v2_views.company_detail_v2, name='company_detail'),
    # The full organisation assessment. One gate, applied at the top: an
    # organisation without a publishable score gets identity, evidence state
    # and gaps, and none of the panel keys at all.
    # One organisation against one of the 114 principles. Separate from
    # assessment/ on purpose: an investigation needs one KPI's full evidence
    # chain, a company page needs a summary of many.
    # One organisation across all 114 — the matrix, and the way into an
    # investigation. Registered before the single-KPI route it feeds.
    path('companies/<slug:slug>/principles/', v2_principles.company_principles,
         name='company_principles'),
    path('companies/<slug:slug>/kpis/<int:kpi_id>/', v2_kpi.company_kpi,
         name='company_kpi'),
    path('companies/<slug:slug>/assessment/', v2_assessment.company_assessment,
         name='company_assessment'),
    path('leaderboard/',           v2_views.leaderboard_v2,    name='leaderboard'),
]
