from django.urls import path

from core import spa

# NOTE: the namespace is 'projects_site' (not 'projects') because the API app
# (api/projects_urls.py) already registers the 'projects' namespace. URL paths
# remain /projects/ and /projects/<slug>/.
app_name = 'projects_site'

# React SPA. Paths and URL names unchanged — only the views.
#
# The five programme concepts these pages rendered are NOT lost: they are
# served from projects/data.py through /api/v2/projects/ (key `concepts`), and
# React renders them in their own section, separated from recorded projects so
# five intentions never read as five delivered projects.
urlpatterns = [
    path('',              spa.spa_view,  name='index'),
    path('<slug:slug>/',  spa.project_concept_spa_view,  name='detail'),
]
