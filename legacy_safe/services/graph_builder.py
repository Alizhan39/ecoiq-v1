"""
LegacySafe AI — dependency / lineage graph.

Builds a NetworkX DiGraph over a project's documents and derived memories and
exports it as plain nodes/edges JSON. PyVis rendering can be layered on top
of this same graph later without touching the data model.
"""
import networkx as nx

from legacy_safe.models import DerivedMemory, SourceDocument


def build_dependency_graph(project):
    graph = nx.DiGraph()

    project_node = f'project:{project.id}'
    graph.add_node(project_node, label=project.name, type='project',
                    access_level='public', is_revoked=False)

    documents = list(SourceDocument.objects.filter(project=project).order_by('created_at', 'id'))
    previous_node = project_node
    for doc in documents:
        node_id = f'document:{doc.id}'
        graph.add_node(node_id, label=doc.title, type='document',
                        access_level=doc.access_level, is_revoked=doc.is_revoked)
        graph.add_edge(previous_node, node_id)
        previous_node = node_id

    for derived in DerivedMemory.objects.filter(project=project).order_by('created_at', 'id'):
        node_id = f'derived:{derived.id}'
        graph.add_node(node_id, label=derived.title, type='derived_memory',
                        access_level=derived.access_level, is_revoked=derived.is_revoked)
        # Link from every lineage source, falling back to the last document
        # in the chain if lineage is empty (keeps the graph connected).
        sources = [f'document:{sid}' for sid in derived.lineage_source_ids if sid] or [previous_node]
        for source_node in sources:
            if graph.has_node(source_node):
                graph.add_edge(source_node, node_id)

    nodes = [{'id': n, **data} for n, data in graph.nodes(data=True)]
    edges = [{'source': u, 'target': v} for u, v in graph.edges()]
    return {'nodes': nodes, 'edges': edges}
