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

    # EcoIQ REST API — docs at /api/, endpoints at /api/v1/
    path('api/',        __import__('core.views', fromlist=['api_docs']).api_docs, name='api_docs_root'),
    path('api/v1/',     include('api.urls',   namespace='api')),

    # EcoIQ Mizan Engine — ethical intelligence API
    path('api/mizan/',  include('mizan.urls',          namespace='mizan')),

    # EcoIQ Project Intelligence — readiness and pipeline scoring
    path('api/projects/', include('api.projects_urls', namespace='projects')),

    # SEO — sitemap and robots
    path('sitemap.xml', sitemap, {'sitemaps': _sitemaps}, name='sitemap'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
