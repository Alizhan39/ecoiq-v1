from django.urls import path
from . import views

# NOTE: the namespace is 'projects_site' (not 'projects') because the API app
# (api/projects_urls.py) already registers the 'projects' namespace. URL paths
# remain /projects/ and /projects/<slug>/.
app_name = 'projects_site'

urlpatterns = [
    path('',              views.project_index,  name='index'),
    path('<slug:slug>/',  views.project_detail, name='detail'),
]
