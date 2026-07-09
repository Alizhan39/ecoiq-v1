from django.urls import path
from django.views.generic import RedirectView
from . import views
from . import globe as globe_views
from . import why_views
from harvester import views as harvester_views

urlpatterns = [
    # Landing page — public homepage
    path('',                                        views.landing,           name='home'),

    # /rankings/ → canonical company rankings (alias for /companies/)
    path('rankings/', RedirectView.as_view(url='/companies/', permanent=False), name='rankings'),
    # UK Infrastructure & Utilities Intelligence ranking (read-only)
    path('rankings/utilities/', harvester_views.utilities_ranking, name='utilities_ranking'),

    # Living Infrastructure Earth — read-only globe data (Phase 0 + 2)
    path('api/globe/layers/', globe_views.globe_layers, name='globe_layers'),
    path('api/globe/country/<slug:slug>/', globe_views.globe_country, name='globe_country'),
    # Global Intelligence Command Globe (Phase 2)
    path('api/globe/heatmap/', globe_views.globe_heatmap, name='globe_heatmap'),
    path('api/globe/compare/', globe_views.globe_compare, name='globe_compare'),
    path('api/globe/signals/', globe_views.globe_signals, name='globe_signals'),
    path('api/globe/agent-activity/', globe_views.globe_agent_activity, name='globe_agent_activity'),

    # WHY Engine — explainability (Boardroom Mode + Decision Defense Pack + API)
    path('why/country/<slug:slug>/', why_views.why_country_page, name='why_country'),
    path('why/company/<slug:slug>/', why_views.why_company_page, name='why_company'),
    path('why/country/<slug:slug>/pack.pdf', why_views.defense_pack_country, name='why_country_pack'),
    path('why/company/<slug:slug>/pack.pdf', why_views.defense_pack_company, name='why_company_pack'),
    path('api/why/country/<slug:slug>/', why_views.api_why_country, name='api_why_country'),
    path('api/why/company/<slug:slug>/', why_views.api_why_company, name='api_why_company'),

    # ESG Assessment app
    path('esg/',                                    views.index,             name='index'),
    path('esg/upload/',                             views.upload,            name='upload'),
    path('esg/assessment/<int:pk>/',                views.assessment_detail, name='assessment_detail'),
    path('esg/assessment/<int:pk>/questionnaire/',  views.questionnaire,     name='questionnaire'),
    path('esg/assessment/<int:pk>/run-analysis/',   views.run_analysis,      name='run_analysis'),
    path('esg/assessment/<int:pk>/report/',         views.report,            name='report'),
    path('esg/assessment/<int:pk>/report/pdf/',     views.report_pdf,        name='report_pdf'),

    # Public share link — no auth required
    path('share/<uuid:token>/',                      views.share_report,      name='share_report'),

    # EcoIQ Methodology — public Ethical Intelligence Framework page
    path('methodology/',                             views.methodology,        name='methodology'),

    # EcoIQ About — founder story, mission, framework
    path('about/',                                   views.about,              name='about'),

    # EcoIQ Pricing — plan comparison, billing toggle, FAQ
    path('pricing/',                                 views.pricing,            name='pricing'),

    # EcoIQ API Documentation — v1 endpoints, auth, rate limits, SDK quick-start
    path('api-docs/',                                views.api_docs,           name='api_docs'),

    # EcoIQ Register — new account creation
    path('register/',                                views.register,           name='register'),

    # EcoIQ Dashboard — authenticated user home
    path('dashboard/',                               views.dashboard,          name='dashboard'),

    # /claim/ → canonical claim-profile shortcut (leads app handles the form)
    path('claim/', RedirectView.as_view(url='/request-access/claim/', permanent=False), name='claim'),

    # EcoIQ Platform — five intelligence modules overview
    path('platform/',              views.platform,              name='platform'),

    # EcoIQ Ethical Governance Intelligence Framework
    path('ethical-governance/',    views.ethical_governance,    name='ethical_governance'),

    # EcoIQ Capital Ethics Compendium — 114 governance principles
    path('governance-principles/', views.governance_principles,  name='governance_principles'),

    # EcoIQ Investors — pre-seed opportunity page
    path('investors/',          views.investors,          name='investors'),

    # EcoIQ Press — press kit, key facts, boilerplate, media contact
    path('press/',              views.press,              name='press'),

    # EcoIQ Newsletter — popup signup endpoint (JSON/AJAX, POST only)
    path('newsletter/signup/',  views.newsletter_signup,  name='newsletter_signup'),

    # EcoIQ Value Distribution — stakeholder value map + Rizq model
    path('value-distribution/', views.value_distribution, name='value_distribution'),

    # EcoIQ Visual Intelligence — Khalifa Impact + Kazakhstan transition map
    path('khalifa-impact/', views.khalifa_impact,  name='khalifa_impact'),
    path('kazakhstan-map/', views.kazakhstan_map,  name='kazakhstan_map'),

    # EcoIQ Sample Investor Readiness Report — public demo report
    path('sample-report/', views.sample_report, name='sample_report'),

    # EcoIQ Stewardship — climate intelligence + real-world stewardship
    path('stewardship/', views.stewardship, name='stewardship'),

    # Tazkiyah 114 — PUBLIC concept/marketing landing page (no draft content).
    # Detailed Surah/reflection content stays in the staff-only previews
    # (tazkiyah_preview, …_struggles_preview, …_daily_preview, …_repair_engine_preview).
    path('tazkiyah-114/', views.tazkiyah_landing, name='tazkiyah'),
    path('surah-map/',    views.tazkiyah_landing, name='surah_map'),   # public alias

    # EcoIQ Global Intelligence — interactive country coverage map
    path('global-intelligence/', views.global_intelligence, name='global_intelligence'),

    # EcoIQ Khalifa Tours Impact Story — flagship visual narrative
    path('khalifa-tours-impact/', views.khalifa_tours_impact, name='khalifa_tours_impact'),

    # Khalifa Stewardship Tours — premium institutional landing page
    path('khalifa-tours/', views.khalifa_stewardship_tours, name='khalifa_stewardship_tours'),

    # EcoIQ Kazakhstan Transition Brief — flagship visual intelligence page
    path('kazakhstan-transition-brief/', views.kazakhstan_transition_brief, name='kazakhstan_transition_brief'),

    # EcoIQ Visual Lab — staff-only verification page for Visual Intelligence islands
    path('visual-lab/', views.visual_lab, name='visual_lab'),

    # Tazkiyah 114 — STAFF-ONLY internal preview of the surah seed dataset (not public)
    path('tazkiyah-114-preview/', views.tazkiyah_preview, name='tazkiyah_preview'),

    # Tazkiyah 114 — STAFF-ONLY "Choose Your Struggle" journey preview (not public)
    path('tazkiyah-114-struggles-preview/', views.tazkiyah_struggles_preview, name='tazkiyah_struggles_preview'),

    # Tazkiyah 114 — STAFF-ONLY Daily Tazkiyah tracker preview (static/demo, not public)
    path('tazkiyah-114-daily-preview/', views.tazkiyah_daily_preview, name='tazkiyah_daily_preview'),

    # Tazkiyah 114 — STAFF-ONLY Qur'an Repair Engine architecture preview (read-only, not public)
    path('tazkiyah-114-repair-engine-preview/', views.tazkiyah_repair_engine_preview, name='tazkiyah_repair_engine_preview'),

    # Tazkiyah 114 — STAFF-ONLY internal dashboard linking all preview tools (not public)
    path('tazkiyah-114-dashboard/', views.tazkiyah_dashboard, name='tazkiyah_dashboard'),

    # EcoIQ Video Studio — staff-only video workflow (rendering is offline/build-time)
    path('video-studio/', views.video_studio, name='video_studio'),

    # Hikma Company Intelligence — Evidence Layer terminal (read-only, API-driven)
    path('company-intelligence/<slug:slug>/', views.company_intelligence, name='company_intelligence'),

    # EcoIQ Contact — enquiry form + founder/company details
    path('contact/',        views.contact,        name='contact'),
    path('contact/submit/', views.contact_submit, name='contact_submit'),

    # SEO — robots.txt served as plain text from templates/robots.txt
    path('robots.txt', views.robots_txt, name='robots_txt'),
]
