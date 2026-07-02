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

    # SEO — sitemap and robots
    path('sitemap.xml', sitemap, {'sitemaps': _sitemaps}, name='sitemap'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
