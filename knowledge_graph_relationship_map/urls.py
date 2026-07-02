"""knowledge_graph_relationship_map/urls.py — routes (mounted at /knowledge-graph-relationship-map/)."""
from django.urls import path

from knowledge_graph_relationship_map import views

app_name = 'knowledge_graph_relationship_map'

urlpatterns = [
    path('', views.overview, name='overview'),
]
