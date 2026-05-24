from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

urlpatterns = [
    # Django admin (data management)
    path('admin/', admin.site.urls),

    # Wagtail CMS admin (content editing)
    path('cms-admin/', include(wagtailadmin_urls)),
    path('documents/',  include(wagtaildocs_urls)),

    # Auth
    path('login/',  auth_views.LoginView.as_view(template_name='registration/login.html'),  name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'),                           name='logout'),

    # Existing Django apps (unchanged)
    path('', include('core.urls')),
    path('audit/', include('audit.urls')),
    path('request-access/', include('leads.urls', namespace='leads')),
    path('league/', include('league.urls', namespace='league')),

    # Wagtail CMS pages served at /pages/ (safe — no conflict with existing routes)
    path('pages/', include(wagtail_urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
