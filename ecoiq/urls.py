from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

from companies.sitemaps import CompanySitemap, StaticSitemap
from core import health as health_views
from companies.throttle import rate_limit
from core import spa
from leads import views as leads_views

_sitemaps = {
    'static':    StaticSitemap,
    'companies': CompanySitemap,
}

urlpatterns = [

    # Liveness probe for the Render health check (render.yaml healthCheckPath).
    # First so it resolves without walking the rest of this URLconf, and so it
    # can never be shadowed by a later prefix. Touches no database — see
    # core/health.py for why a liveness probe must not.
    path('healthz/', health_views.healthz, name='healthz'),
    # Readiness. Deliberately NOT render.yaml's healthCheckPath: a dependency
    # outage should stop traffic, not restart a healthy process. See core/health.py.
    path('readyz/', health_views.readyz, name='readyz'),

    # i18n — language switcher endpoint (set_language view, POST)
    path('i18n/', include('django.conf.urls.i18n')),

    # Django admin (data management)
    path('admin/', admin.site.urls),

    # Auth
    # Rate-limited: the sign-in form is an unauthenticated write surface and
    # was previously unlimited (DRF's throttles cover /api/, not Django's auth
    # views). staff_exempt=False on purpose — the request that needs limiting
    # is made by someone who is not signed in as anybody yet.
    path('login/',  rate_limit('auth_login_web', anon_per_min='LOGIN_RATE_PER_MIN',
                               auth_per_min='LOGIN_RATE_PER_MIN', staff_exempt=False)(
        auth_views.LoginView.as_view(template_name='registration/login.html')),  name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'),                           name='logout'),

    # Existing Django apps (unchanged)
    path('', include('core.urls')),
    path('audit/', include('audit.urls')),
    path('request-access/', include('leads.urls', namespace='leads')),
    # GCC investor SEO pages — paths defined directly in gcc_investors/urls.py
    # (English and Arabic pages don't share a common prefix; see that file).
    path('', include('gcc_investors.urls', namespace='gcc_investors')),
    # Staff-only Investor Readiness Report previews (not in public nav)
    path('admin-report-preview/<int:access_request_id>/', leads_views.admin_report_preview, name='admin_report_preview'),
    path('client-report-preview/<int:access_request_id>/', leads_views.client_report_preview, name='client_report_preview'),
    # Short-form claim URL used in company detail CTAs
    path('claim/', RedirectView.as_view(url='/request-access/claim/', query_string=True), name='claim_shortcut'),
    path('league/', include('league.urls', namespace='league')),

    # AI company ingestion
    path('ingest/', include('ingestion.urls', namespace='ingestion')),

    # Environmental Intelligence OS — moved off /intelligence/ so that path can
    # carry the PUBLIC Intelligence page (see core.urls). Every view in this app
    # is already @staff_member_required, it is absent from sitemap.xml and
    # robots.txt, and every inbound link uses {% url 'intelligence:...' %}, so
    # the namespace is unchanged and those links follow this move automatically.
    # /intelligence/ itself is NOT redirected here: it is now a public page.
    path('intelligence-os/', include('intelligence.urls', namespace='intelligence')),

    # Industrial Transition Engine
    path('transition/', include('transition.urls', namespace='transition')),

    # EcoIQ Company Intelligence
    path('companies/', include('companies.urls', namespace='companies')),

    # Investor portfolios and watchlists (authenticated, owner-scoped)
    path('portfolio/', include('investor_portfolio.urls', namespace='portfolio')),

    # Public embeddable badges/widgets for a company (read-only, cached, no auth)
    path('embed/', include('companies.embed_urls', namespace='embed')),

    # EcoIQ Commercial Platform — PART 14 catalogue, PART 17 self-service keys, PART 12 dashboard
    path('products/', include('ecoiq_commerce.urls', namespace='commerce')),

    # Stripe billing — Checkout, Customer Portal, and the webhook endpoint.
    # /billing/webhook/ is registered by hand in the Stripe Dashboard; changing
    # this prefix breaks payment provisioning in production silently.
    path('billing/', include('ecoiq_commerce.billing_urls', namespace='billing')),

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

    # EcoIQ REST API v2 — the canonical contract, with explicit evidence
    # semantics: a score is null when EcoIQ cannot support it with evidence,
    # and score_status/evidence_coverage say so rather than a stand-in number.
    #
    # Purely additive. v1 above is unchanged and stays mounted for existing
    # integrators; see docs/product/API_EVIDENCE_MIGRATION.md for the
    # deprecation conditions.
    path('api/v2/',     include('api.v2_urls', namespace='api_v2')),

    # EcoIQ AI Gateway — one provider-neutral, free-only AI system over
    # OpenRouter / Bytez / NVIDIA NIM, with automatic free-only model routing.
    path('api/ai/',     include('ai_gateway.urls',     namespace='ai_gateway')),
    path('ai-assistant/', include('ai_gateway.web_urls', namespace='ai_gateway_web')),

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

    # EcoIQ 114 Good Agents — the 114 canonical principles as specialised
    # opportunity-discovery lenses over the capital pipeline above.
    path('good-agents/', include('good_agents.urls', namespace='good_agents')),

    # Evidence-backed Capability Graph — reusable Organisation/Capability/
    # PublicRoute infrastructure good_agents is the first real consumer of.
    path('capability-graph/', include('capability_graph.urls', namespace='capability_graph')),

    # Partner Participation Protocol — consented organisation claims,
    # capability/resource/funding declarations, and governed opportunity
    # routing. The reciprocal half of capability_graph.
    path('partner-network/', include('partner_participation.urls', namespace='partner_participation')),

    # Governed Collaboration Rooms — the narrow, opportunity-scoped
    # coordination layer between "organisation interested" and "consented
    # next step created", anchored to partner_participation.RoutingCandidate.
    path('collaboration/', include('collaboration_rooms.urls', namespace='collaboration_rooms')),

    # First Real Outreach Readiness — candidate suitability review,
    # recipient responsibility test, route provenance, message versioning,
    # risk review, dry run, Founder Send Review. No real send exists here.
    path('outreach-readiness/', include('outreach_readiness.urls', namespace='outreach_readiness')),

    # Actionable Public-Need Discovery — the actionability layer between
    # discovery (GoodOpportunity) and outreach_readiness: jurisdiction
    # resolution, organisation role separation, small-action generation,
    # official-process preference. Never sends anything.
    path('public-need-discovery/', include('public_need_discovery.urls', namespace='public_need_discovery')),

    # First Legitimate Public Action — takes ONE real actionable
    # candidate and prepares the exact legitimate action (official
    # process / clarification / referral / data request / funding
    # surfacing / zero-capital connection / outreach handoff). Stops at
    # Founder Action Review; no real external submission exists here.
    path('public-action-preparation/', include('public_action_preparation.urls', namespace='public_action_preparation')),

    # EcoIQ Industrial Digital Twin & Modernisation Engine — living baseline
    # model of an industrial asset, deterministic loss detection and
    # scenario simulation, draft Qur'anic Stewardship KPIs, Agent Council
    # review and human-approved promotion into the existing capital-
    # allocation workflow.
    path('digital-twin/', include('digital_twin.urls', namespace='digital_twin')),

    # EcoIQ Global Research, Technology & Manufacturer Discovery Engine —
    # governed discovery of technologies and manufacturers worldwide to
    # solve a verified Digital Twin problem, with deterministic evidence
    # scoring, mandatory-requirement compatibility gating, transparent
    # comparison, Agent Council review and human-approved promotion.
    path('global-research/', include('global_research.urls', namespace='global_research')),

    # SEO — sitemap and robots
    path('sitemap.xml', sitemap, {'sitemaps': _sitemaps}, name='sitemap'),

    # ── React SPA ────────────────────────────────────────────────────────────
    #
    # Routes that exist ONLY in the React app — they have no Django template
    # equivalent and never had one. Registered explicitly rather than left to
    # the catch-all so they answer 200 rather than 404, and so `{% url %}` can
    # reach them from the templates that are still server-rendered.
    #
    # The routes that ARE being migrated off Django templates keep their
    # registration where it already is (core/urls.py, companies/urls.py,
    # league/urls.py) and swap their view for spa.spa_view there, so URL names,
    # ordering and prefix behaviour are unchanged. See core/spa.py.
    # The framework itself. Registered explicitly, like the routes below it,
    # so a direct hit answers 200 rather than falling to the catch-all's 404.
    # The detail route validates the 1-114 bound server-side and 404s outside
    # it — React can show a reader "no such principle", but a crawler reads the
    # status line, and 200 for a principle that does not exist misstates how
    # big the framework is. Same rule company_kpi_spa_view already applies.
    path('principles/', spa.spa_view, name='principles'),
    path('principles/<int:kpi_id>/', spa.principle_spa_view, name='principle_detail'),
    path('tours/', spa.spa_view, name='tours'),
    path('labs/',  spa.spa_view, name='labs'),
    path('trust/', spa.spa_view, name='trust'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# ── SPA history fallback ─────────────────────────────────────────────────────
#
# LAST, and it must stay last: it matches everything, so anything appended
# below it becomes unreachable.
#
# It is a fallback, not a router. Server-owned prefixes (/api/, /admin/,
# /static/, the Stripe webhook, …) are refused inside spa_catch_all with a
# plain 404 — a mistyped API route must never answer `200 text/html`. Unknown
# frontend paths get the React shell with HTTP 404: the NotFound page for a
# person, the true status code for a crawler.
urlpatterns += [
    re_path(r'^(?P<path>.*)$', spa.spa_catch_all, name='spa_catch_all'),
]
