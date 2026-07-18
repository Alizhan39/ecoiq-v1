from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

from companies.sitemaps import CompanySitemap, StaticSitemap
from leads import views as leads_views

_sitemaps = {
    'static':    StaticSitemap,
    'companies': CompanySitemap,
}

urlpatterns = [
    # i18n — language switcher endpoint (set_language view, POST)
    path('i18n/', include('django.conf.urls.i18n')),

    # Django admin (data management)
    path('admin/', admin.site.urls),

    # Auth
    path('login/',  auth_views.LoginView.as_view(template_name='registration/login.html'),  name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'),                           name='logout'),

    # Existing Django apps (unchanged)
    path('', include('core.urls')),
    path('audit/', include('audit.urls')),
    path('request-access/', include('leads.urls', namespace='leads')),
    # Staff-only Investor Readiness Report previews (not in public nav)
    path('admin-report-preview/<int:access_request_id>/', leads_views.admin_report_preview, name='admin_report_preview'),
    path('client-report-preview/<int:access_request_id>/', leads_views.client_report_preview, name='client_report_preview'),
    # Short-form claim URL used in company detail CTAs
    path('claim/', RedirectView.as_view(url='/request-access/claim/', query_string=True), name='claim_shortcut'),
    path('league/', include('league.urls', namespace='league')),

    # AI company ingestion
    path('ingest/', include('ingestion.urls', namespace='ingestion')),

    # Environmental Intelligence OS
    path('intelligence/', include('intelligence.urls', namespace='intelligence')),

    # Industrial Transition Engine
    path('transition/', include('transition.urls', namespace='transition')),

    # EcoIQ Company Intelligence
    path('companies/', include('companies.urls', namespace='companies')),

    # EcoIQ Country Intelligence
    path('countries/', include('countries.urls', namespace='countries')),

    # EcoIQ Projects — real-world implementation portfolio
    # (namespace 'projects_site' — 'projects' is taken by the API app below)
    path('projects/', include('projects.urls', namespace='projects_site')),

    # Khalifa Heat — coal-to-electric heating retrofit
    path('heating/', include('heating.urls', namespace='heating')),

    # Khalifa Tours — served by core.urls (Khalifa Stewardship Tours landing page).
    # The old redirect to /khalifa-tours-impact/ has been retired in favour of the
    # dedicated landing page (core.views.khalifa_stewardship_tours).

    # Manufacturer intelligence — currently surfaced inside the global explorer
    path('manufacturers/', RedirectView.as_view(url='/global-intelligence/', query_string=True, permanent=False), name='manufacturers'),

    # EcoIQ Evidence Harvester — standalone read-only Company Evidence Dashboard
    path('evidence/',   include('harvester.urls', namespace='harvester')),

    # EcoIQ REST API — docs at /api/, endpoints at /api/v1/
    path('api/',        __import__('core.views', fromlist=['api_docs']).api_docs, name='api_docs_root'),
    path('api/v1/',     include('api.urls',   namespace='api')),

    # EcoIQ Mizan Engine — ethical intelligence API
    path('api/mizan/',  include('mizan.urls',          namespace='mizan')),

    # EcoIQ Project Intelligence — readiness and pipeline scoring
    path('api/projects/', include('api.projects_urls', namespace='projects')),

    # EcoIQ Quranic Decision Filter — "Create rizq without zulm"
    path('api/qdf/',    include('qdf.urls',           namespace='qdf')),
    path('decisions/',  include('qdf.web_urls',       namespace='qdf_web')),

    # EcoIQ LegacySafe AI — hackathon module (started 2026-07-01), Conduct AI / BasedAI
    path('legacy-safe/', include('legacy_safe.urls',  namespace='legacy_safe')),

    # EcoIQ Amanah Autopilot — overnight ethical AI agent product module
    path('amanah-autopilot/', include('amanah_autopilot.urls', namespace='amanah_autopilot')),

    # EcoIQ Omnimodal Evidence Panel — live visual evidence interface product module
    path('omnimodal-evidence-panel/', include('omnimodal_evidence_panel.urls', namespace='omnimodal_evidence_panel')),

    # EcoIQ Microsoft Ecosystem Core Stack — Microsoft ecosystem readiness architecture module
    path('microsoft-ecosystem-core-stack/', include('microsoft_core_stack.urls', namespace='microsoft_core_stack')),

    # EcoIQ Asset Passport — living digital passport for industrial assets
    path('asset-passport/', include('asset_passport.urls', namespace='asset_passport')),

    # EcoIQ Impact MRV Layer — measurement, reporting and verification of modernisation impact
    path('impact-mrv-layer/', include('impact_mrv_layer.urls', namespace='impact_mrv_layer')),

    # EcoIQ Industrial Playbook Library — reusable industrial modernisation pathways
    path('industrial-playbook-library/', include('industrial_playbook_library.urls', namespace='industrial_playbook_library')),

    # EcoIQ Supplier & Funding Marketplace — supplier and funding matching for financed implementation
    path('supplier-funding-marketplace/', include('supplier_funding_marketplace.urls', namespace='supplier_funding_marketplace')),

    # EcoIQ Institutional Finance Engine — investor-grade financial modelling and decision memos
    path('institutional-finance-engine/', include('institutional_finance_engine.urls', namespace='institutional_finance_engine')),

    # EcoIQ Mobile / iPad Inspection Mode — mobile-first field inspection and evidence capture
    path('mobile-inspection-mode/', include('mobile_inspection_mode.urls', namespace='mobile_inspection_mode')),

    # EcoIQ Command Centre — central operational view of the modernisation project pipeline
    path('command-centre/', include('command_centre.urls', namespace='command_centre')),

    # EcoIQ Governance & Expert Review Board — human-in-the-loop expert review and approval layer
    path('governance-expert-review-board/', include('governance_expert_review_board.urls', namespace='governance_expert_review_board')),

    # EcoIQ API & Integration Layer — API and enterprise integration connectivity layer
    path('api-integration-layer/', include('api_integration_layer.urls', namespace='api_integration_layer')),

    # EcoIQ Data Room & Evidence Vault — investor-grade evidence and due diligence storage
    path('data-room-evidence-vault/', include('data_room_evidence_vault.urls', namespace='data_room_evidence_vault')),

    # EcoIQ Portfolio & Country Transition Atlas — country-scale and portfolio-scale transition mapping
    path('portfolio-country-transition-atlas/', include('portfolio_country_transition_atlas.urls', namespace='portfolio_country_transition_atlas')),

    # EcoIQ Executive Briefing & Board Pack Generator — investor, board and government decision-pack generation
    path('executive-briefing-board-pack-generator/', include('executive_briefing_board_pack_generator.urls', namespace='executive_briefing_board_pack_generator')),

    # EcoIQ Revenue & Pricing Engine — commercial productisation and pricing model
    path('revenue-pricing-engine/', include('revenue_pricing_engine.urls', namespace='revenue_pricing_engine')),

    # EcoIQ Public Trust & Impact Portal — approved public-facing verified impact reporting
    path('public-trust-impact-portal/', include('public_trust_impact_portal.urls', namespace='public_trust_impact_portal')),

    # EcoIQ Sales CRM & Partner Pipeline — sales, partnership and funder pipeline management
    path('sales-crm-partner-pipeline/', include('sales_crm_partner_pipeline.urls', namespace='sales_crm_partner_pipeline')),

    # EcoIQ Customer Success & Renewal Engine — post-sale customer success, health scoring and renewal
    path('customer-success-renewal-engine/', include('customer_success_renewal_engine.urls', namespace='customer_success_renewal_engine')),

    # EcoIQ Product Analytics & KPI Engine — platform usage, conversion, revenue and impact analytics
    path('product-analytics-kpi-engine/', include('product_analytics_kpi_engine.urls', namespace='product_analytics_kpi_engine')),

    # EcoIQ AI Agent Operations Console — observability and control layer for AI agents
    path('ai-agent-operations-console/', include('ai_agent_operations_console.urls', namespace='ai_agent_operations_console')),

    # EcoIQ Security, Privacy & Compliance Centre — security, privacy and compliance governance layer
    path('security-privacy-compliance-centre/', include('security_privacy_compliance_centre.urls', namespace='security_privacy_compliance_centre')),

    # EcoIQ Deployment, DevOps & Reliability Centre — production readiness, monitoring and incident response
    path('deployment-devops-reliability-centre/', include('deployment_devops_reliability_centre.urls', namespace='deployment_devops_reliability_centre')),

    # EcoIQ Knowledge Graph & Relationship Map — connected relationship graph across assets, evidence and impact
    path('knowledge-graph-relationship-map/', include('knowledge_graph_relationship_map.urls', namespace='knowledge_graph_relationship_map')),

    # EcoIQ Frontend Experience & Google Stitch Design System — visual design system and frontend library stack
    path('frontend-experience-google-stitch-design-system/', include('frontend_experience_google_stitch_design_system.urls', namespace='frontend_experience_google_stitch_design_system')),

    # EcoIQ Certification & Trust Badge Engine — readiness, verification and trust badges
    path('certification-trust-badge-engine/', include('certification_trust_badge_engine.urls', namespace='certification_trust_badge_engine')),

    # EcoIQ Frontend Implementation Roadmap — frontend delivery plan across Django, Next.js, Microsoft and Google Stitch
    path('frontend-implementation-roadmap/', include('frontend_implementation_roadmap.urls', namespace='frontend_implementation_roadmap')),

    # EcoIQ Agent Training & Evaluation Lab — training, evaluation and human-review workflow for AI agents
    path('agent-training-evaluation-lab/', include('agent_training_evaluation_lab.urls', namespace='agent_training_evaluation_lab')),

    # EcoIQ Document Reader Agent Training Pack — training pack for evidence-extraction agent
    path('document-reader-agent-training-pack/', include('document_reader_agent_training_pack.urls', namespace='document_reader_agent_training_pack')),

    # EcoIQ MRV Agent Training Pack — training pack for the estimated-vs-verified impact agent
    path('mrv-agent-training-pack/', include('mrv_agent_training_pack.urls', namespace='mrv_agent_training_pack')),

    # EcoIQ AI Agent Council — public presentation and control page for the multi-agent system
    path('ai-agent-council/', include('ai_agent_council.urls', namespace='ai_agent_council')),

    # EcoIQ Agent Runtime & Model Router — governed execution layer connecting training packs to the Council
    path('agent-runtime-model-router/', include('agent_runtime_model_router.urls', namespace='agent_runtime_model_router')),

    # EcoIQ AI Agent Workbench — homepage discovery, directory and interactive testing for the 12 operational agents
    path('ai-agents/', include('ai_agent_workbench.urls', namespace='ai_agent_workbench')),

    # EcoIQ Waste-to-Value Capital Allocation Engine — fintech / capital-allocation layer for operational waste
    path('waste-to-value-capital-allocation/', include('waste_to_value_capital_allocation_engine.urls', namespace='waste_to_value_capital_allocation_engine')),

    # EcoIQ Financial Intelligence Cloud — commercial subscription layer for accounting firms, financial institutions and investment portfolios
    path('financial-intelligence-cloud/', include('financial_intelligence_cloud.urls', namespace='financial_intelligence_cloud')),

    # EcoIQ Khalifa Stewardship Tour Operating System — the mission layer: AI-planned, human-led, financed and verified stewardship tours
    path('khalifa-tour-operating-system/', include('khalifa_stewardship_tour_operating_system.urls', namespace='khalifa_stewardship_tour_operating_system')),

    # EcoIQ Geo Intelligence — geo-spatial climate/risk/investment map (Phase 1: Kazakhstan)
    path('geo-intelligence/', include('geo_intelligence.urls', namespace='geo_intelligence')),

    # EcoIQ Intelligence Dashboard — Plotly visual decision-intelligence layer
    # over Evidence Memory, Geo Intelligence, Pandas Scoring Engine,
    # Intelligence Analytics Engine and LangGraph Orchestration (Phase 1)
    path('intelligence-dashboard/', include('plotly_visual_intelligence.urls', namespace='plotly_visual_intelligence')),

    # EcoIQ Natural-Language Decision Studio — the user-facing orchestration
    # layer: turns a free-text decision question into a routed, explainable,
    # evidence-backed answer (Phase 1)
    path('decision-studio/', include('decision_studio.urls', namespace='decision_studio')),

    # EcoIQ Gold Intelligence — first flagship vertical: institutional-grade
    # Kazakhstan gold mining investment intelligence, built on top of Geo
    # Intelligence, Pandas Scoring, Intelligence Analytics, Evidence Memory,
    # AI Agent Workbench, Decision Studio and Plotly Visual Intelligence.
    path('gold-intelligence/', include('gold_intelligence.urls', namespace='gold_intelligence')),

    # EcoIQ Capital Guardian — investor transparency and capital intelligence
    # over a real gold_intelligence.GoldProject: capital traceability, SPV/
    # governance, equipment & insurance lifecycle, a mining digital twin,
    # milestone-based capital control, and a deterministic red flag engine.
    path('capital-guardian/', include('capital_guardian.urls', namespace='capital_guardian')),
    path('ai-observatory/', include('ai_observatory.urls', namespace='ai_observatory')),

    # SEO — sitemap and robots
    path('sitemap.xml', sitemap, {'sitemaps': _sitemaps}, name='sitemap'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
